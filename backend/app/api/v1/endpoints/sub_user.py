import copy
import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud, models
from app.api.deps import get_current_user, get_db
from app.core.logging import logger
from app.core.security import get_password_hash
from app.crud.permission_crud import permission_crud
from app.crud.sub_user_shared_folder_crud import sub_user_shared_folder_crud
from app.models import User
from app.schemas.sub_user import (
    SubUserCreateSchema,
    SubUserResponse,
    SubUserTransferBalanceSchema,
    SubUserUpdateSchema,
)
from app.utils.response import success_response
from app.enums.transfer import PointTransferType, PointTransferStatus

router = APIRouter()

_DEFAULT_PERMISSION_CODES = [
    "project:create",
    "project:read",
    "project:update",
    "project:delete",
    "asset:create",
    "asset:read",
    "asset:update",
    "asset:delete",
]

_ALL_PERMISSION_CODES = [*_DEFAULT_PERMISSION_CODES, "main_user_asset:read"]

_VALID_PERMISSION_CODES = set(_ALL_PERMISSION_CODES)


def _check_sub_user_owner(sub_user: User, current_user: User) -> None:
    if sub_user.parent_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权操作此子账号")


def _build_sub_user_response(db: Session, user: User) -> dict:
    user_balance_obj = crud.user_balance_crud.get_by_user_id(db, user.id)
    balance = user_balance_obj.balance if user_balance_obj else Decimal("0.00")

    perm_codes = permission_crud.get_user_permission_codes(db, user.id)
    permissions = {code: True for code in perm_codes if code in _VALID_PERMISSION_CODES}

    shared_folder_ids = sub_user_shared_folder_crud.get_shared_folder_ids(db, user.id)

    resp = SubUserResponse.model_validate(user)
    data = resp.model_dump()
    data["balance"] = str(balance)
    data["api_key"] = None
    data["permissions"] = permissions
    data["shared_folder_ids"] = shared_folder_ids
    return data


@router.get("")
def list_sub_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取当前登录用户所有子账号
    """
    sub_users = (
        db.query(User)
        .filter_by(parent_user_id=current_user.id, is_deleted=False)
        .order_by(User.create_time.desc())
        .all()
    )
    data = [_build_sub_user_response(db, u) for u in sub_users]
    return success_response(data=data)


@router.get("/folders", summary="获取主账号文件夹列表（用于子账号共享选择）")
def get_main_user_folders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.parent_user_id is not None:
        raise HTTPException(status_code=403, detail="仅主账号可调用此接口")
    query = crud.global_asset_folder_crud.get_queryset(db).filter(
        models.GlobalAssetFolder.user_id == current_user.id
    ).order_by(models.GlobalAssetFolder.name.asc())
    folders = query.all()
    data = [{"id": f.id, "name": f.name} for f in folders]
    return success_response(data=data)


@router.post("", status_code=201)
def create_sub_user(
    user_in: SubUserCreateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sub_count = db.query(User).filter_by(
        parent_user_id=current_user.id,
        is_deleted=False
    ).count()
    if sub_count >= current_user.sub_user_limit:
        raise HTTPException(status_code=400, detail="子账号数量已达上限")

    existing = crud.user_crud.get_by_username(username=user_in.username, db=db)
    if existing:
        raise HTTPException(status_code=409, detail="用户名已存在")

    sub_user = User(
        id=str(uuid.uuid4()),
        username=user_in.username,
        password_hash=get_password_hash(user_in.password),
        email=user_in.email,
        status="enable",
        type=current_user.type,
        parent_user_id=current_user.id,
        sub_user_limit=0,
        remark=user_in.remark,
    )
    db.add(sub_user)
    db.flush()

    api_config = crud.user_api_config_crud.get_default_api_config(sub_user.id)

    parent_config = crud.user_api_config_crud.get_by_user_id(
        user_id=current_user.id, db=db
    )
    if parent_config:
        _copy_config_fields = [
            "analysis_model", "character_model", "location_model",
            "storyboard_model", "edit_model", "video_model", "audio_model",
            "analysis_concurrency", "image_concurrency", "video_concurrency",
            "video_ratio", "video_resolution", "art_style", "tts_rate",
            "image_resolution", "capability_defaults",
            "fal_api_key",
            "google_api_key", "ark_api_key", "qwen_api_key", "jd_api_key",
            "custom_models", "custom_providers",
            "ark_video_watermark",
        ]
        for field in _copy_config_fields:
            parent_val = getattr(parent_config, field, None)
            if parent_val is not None:
                setattr(api_config, field, copy.deepcopy(parent_val) if isinstance(parent_val, (dict, list)) else parent_val)

    db.add(api_config)

    crud.user_balance_crud.init_user_balance(db=db, user_id=sub_user.id)

    permission_crud.set_user_permissions(db, sub_user.id, _DEFAULT_PERMISSION_CODES)

    db.commit()
    db.refresh(sub_user)

    logger.success(f"子账号创建成功，用户ID：{sub_user.id}，主账号：{current_user.id}")
    return success_response(data=_build_sub_user_response(db, sub_user))


@router.put("/{user_id}")
def update_sub_user(
    user_id: str,
    user_in: SubUserUpdateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sub_user = crud.user_crud.get(id=user_id, db=db)
    if not sub_user:
        raise HTTPException(status_code=404, detail="子账号不存在")
    _check_sub_user_owner(sub_user, current_user)

    update_data = user_in.model_dump(exclude_unset=True)

    if "status" in update_data:
        sub_user.status = update_data.pop("status")
    if "remark" in update_data:
        sub_user.remark = update_data.pop("remark")

    update_data.pop("api_key", None)

    permissions = update_data.pop("permissions", None)
    if permissions is not None:
        perm_codes = [
            code for code, enabled in permissions.items()
            if enabled and code in _VALID_PERMISSION_CODES
        ]
        permission_crud.set_user_permissions(db, sub_user.id, perm_codes)

    shared_folder_ids = update_data.pop("shared_folder_ids", None)
    if shared_folder_ids is not None:
        if "main_user_asset:read" not in [
            code for code, enabled in (permissions or {}).items()
            if enabled and code in _VALID_PERMISSION_CODES
        ]:
            has_main_asset = permission_crud.has_permission(
                db, sub_user.id, "main_user_asset:read"
            )
            if not has_main_asset:
                shared_folder_ids = []
        sub_user_shared_folder_crud.set_shared_folders(db, sub_user.id, shared_folder_ids)

    db.add(sub_user)
    db.commit()
    db.refresh(sub_user)

    logger.success(f"子账号更新成功，用户ID：{sub_user.id}")
    return success_response(data=_build_sub_user_response(db, sub_user))


@router.delete("/{user_id}", status_code=200)
def delete_sub_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sub_user = crud.user_crud.get(id=user_id, db=db)
    if not sub_user:
        raise HTTPException(status_code=404, detail="子账号不存在")
    _check_sub_user_owner(sub_user, current_user)

    permission_crud.set_user_permissions(db, sub_user.id, [])
    sub_user_shared_folder_crud.set_shared_folders(db, sub_user.id, [])

    crud.user_crud.remove(primary_id=user_id, db=db)
    logger.success(f"子账号删除成功，用户ID：{user_id}")
    return success_response(msg="删除成功")


@router.post("/{user_id}/transfer-balance")
def transfer_balance(
    user_id: str,
    body: SubUserTransferBalanceSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """将主账号积分划拨给子账号"""
    sub_user = crud.user_crud.get(id=user_id, db=db)
    if not sub_user:
        raise HTTPException(status_code=404, detail="子账号不存在")
    _check_sub_user_owner(sub_user, current_user)

    try:
        snapshot = crud.user_balance_crud.transfer_balance(
            db, from_user_id=current_user.id, to_user_id=sub_user.id, amount=body.amount
        )

        # 写入转账记录
        crud.transfer_crud.create_record(
            db,
            user_id=current_user.id,
            target_user_id=sub_user.id,
            point=body.amount,
            transfer_type=PointTransferType.SUBACCOUNT_TRANSFER,
            status=PointTransferStatus.SUCCESS,
            from_before_point=snapshot["from_before"],
            from_after_point=snapshot["from_after"],
            to_before_point=snapshot["to_before"],
            to_after_point=snapshot["to_after"],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    db.commit()
    logger.success(f"积分划拨成功，主账号 {current_user.id} 向子账号 {sub_user.id} 划拨 {body.amount}")
    return success_response(data=_build_sub_user_response(db, sub_user))


@router.post("/{user_id}/reclaim-balance")
def reclaim_balance(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """回收子账号全部积分到主账号"""
    sub_user = crud.user_crud.get(id=user_id, db=db)
    if not sub_user:
        raise HTTPException(status_code=404, detail="子账号不存在")
    _check_sub_user_owner(sub_user, current_user)

    try:
        result = crud.user_balance_crud.reclaim_balance(
            db, from_user_id=sub_user.id, to_user_id=current_user.id
        )
        if not result:
            raise HTTPException(status_code=400, detail="子账号无可回收积分")

        # 写入转账记录
        crud.transfer_crud.create_record(
            db,
            user_id=sub_user.id,
            target_user_id=current_user.id,
            point=result["reclaim_amount"],
            transfer_type=PointTransferType.SUBACCOUNT_TRANSFER,
            status=PointTransferStatus.SUCCESS,
            from_before_point=result["from_before"],
            from_after_point=result["from_after"],
            to_before_point=result["to_before"],
            to_after_point=result["to_after"],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    db.commit()
    logger.success(f"积分回收成功，从子账号 {sub_user.id} 回收 {result['reclaim_amount']} 到主账号 {current_user.id}")
    return success_response(data=_build_sub_user_response(db, sub_user))
