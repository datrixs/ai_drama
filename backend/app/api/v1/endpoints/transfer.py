from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud
from app.api.deps import get_current_user, get_db
from app.core.response import success_response
from app.core.security import verify_password
from app.crud.membership_crud import membership_crud
from app.crud.transfer_crud import transfer_crud
from app.enums.transfer import PointTransferType, PointTransferStatus
from app.models.user import User
from app.schemas.transfer import TransferCreateSchema, TransferRecordPageParams

router = APIRouter()


@router.post("", summary="发起转账")
def create_transfer(
    body: TransferCreateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """向指定用户名转账积分"""
    # 子账号不允许发起转账
    if current_user.parent_user_id is not None:
        raise HTTPException(status_code=400, detail="子用户不能转账")

    # 免费用户不能发起转账（积分转出仅限付费会员）
    if not membership_crud.is_active_member(db, current_user.id):
        raise HTTPException(status_code=400, detail="免费用户不可发起转账，请先开通会员")

    # 校验当前用户密码
    if not verify_password(body.password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="密码错误")

    # 不能给自己转账
    if body.target_username == current_user.username:
        raise HTTPException(status_code=400, detail="不能给自己转账")

    # 查找目标用户
    target_user = db.query(User).filter_by(
        username=body.target_username, is_deleted=False
    ).first()
    if not target_user:
        raise HTTPException(status_code=400, detail="目标用户不存在")

    if target_user.parent_user_id is not None:
        raise HTTPException(status_code=400, detail="不能转账给子账号")

    if target_user.status != "enable":
        raise HTTPException(status_code=400, detail="目标用户已被禁用")

    # 不能转账给免费用户（接收方也必须是付费会员）
    if not membership_crud.is_active_member(db, target_user.id):
        raise HTTPException(status_code=400, detail="对方为免费用户，无法接收转账")

    try:
        # 执行余额划转
        snapshot = crud.user_balance_crud.transfer_balance(
            db,
            from_user_id=current_user.id,
            to_user_id=target_user.id,
            amount=body.amount,
        )
        # 写入转账记录
        transfer_crud.create_record(
            db,
            user_id=current_user.id,
            target_user_id=target_user.id,
            point=body.amount,
            transfer_type=PointTransferType.INNER_TRANSFER,
            status=PointTransferStatus.SUCCESS,
            from_before_point=snapshot["from_before"],
            from_after_point=snapshot["from_after"],
            to_before_point=snapshot["to_before"],
            to_after_point=snapshot["to_after"],
        )
        db.commit()
        return success_response(msg="转账成功")
    except ValueError as e:
        db.rollback()
        # 余额不足等业务异常，记录为失败
        transfer_crud.create_record(
            db,
            user_id=current_user.id,
            target_user_id=target_user.id,
            point=body.amount,
            transfer_type=PointTransferType.INNER_TRANSFER,
            status=PointTransferStatus.FAILED,
        )
        db.commit()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/records", summary="转账记录列表")
def get_transfer_records(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page_params: TransferRecordPageParams = Depends(),
) -> Any:
    """获取当前用户的转账记录"""
    result = transfer_crud.get_records_by_user(db, current_user.id, page_params)
    records = result["data"]

    # 补充对方用户名信息
    data = []
    for record in records:
        item = {
            "id": record.id,
            "user_id": record.user_id,
            "transfer_to_user_id": record.transfer_to_user_id,
            "point": str(record.point),
            "transfer_type": record.transfer_type,
            "status": record.status,
            "create_time": record.create_time.strftime("%Y-%m-%d %H:%M:%S") if record.create_time else None,
        }
        # 判断当前用户是转出方还是转入方，显示对方用户名
        if record.user_id == current_user.id:
            target = db.query(User).filter_by(id=record.transfer_to_user_id).first()
            item["target_username"] = target.username if target else "-"
            item["direction"] = "out"
        else:
            source = db.query(User).filter_by(id=record.user_id).first()
            item["target_username"] = source.username if source else "-"
            item["direction"] = "in"
        data.append(item)

    return success_response(data=data, pagination=result["pagination"])
