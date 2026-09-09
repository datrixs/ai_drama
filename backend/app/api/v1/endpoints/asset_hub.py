import uuid
import json
import io
import re
import zipfile
import datetime
from typing import Any, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import or_, and_
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.api.deps import get_db, get_current_user
from app.core.logging import logger
from app.core.response import success_response, fail_response
from app.deps.permission_deps import require_permission, get_accessible_folder_ids
from app.enums.user import UserRegion
from app.prompts.constants import VALID_ART_STYLES
from app.utils.tencent_cos_utils import cos_client
from app.services.image_processor import process_to_jpeg
from app.utils.thumbnail import upload_thumbnail as _upload_thumb
from app.services import task as task_service
from app.services.config_reader import ConfigReader

from app.enums import TaskType


router = APIRouter()


def _get_owner_user_id(user: models.User) -> str:
    return user.parent_user_id if user.parent_user_id else user.id


from app.utils.region import apply_region_volc_id as _apply_region_volc_id


def _apply_self_only_filter(query, model_class, current_user: models.User):
    if current_user.parent_user_id is None:
        query = query.filter(model_class.user_id == current_user.id)
    return query


def _apply_folder_filter(query, model_class, current_user: models.User, db: Session, shared_ids=None):
    """应用文件夹过滤；授权资产(shared_ids)豁免 user_id 限制
    
    Args:
        shared_ids: 平台授权资产ID列表，这些资产不受 user_id/folder 归属限制
    """
    
    if current_user.parent_user_id is None:
        # 主账号：自己创建的 + 授权资产
        conditions = [model_class.user_id == current_user.id]
        if shared_ids:
            conditions.append(model_class.id.in_(shared_ids))
        query = query.filter(or_(*conditions))
        return query
    
    # 子账号逻辑：自己创建的 + 主账号共享的文件夹 + 授权资产
    accessible_ids = get_accessible_folder_ids(current_user, db)
    conditions = [model_class.user_id == current_user.id]
    
    if accessible_ids is not None:
        # 有 main_user_asset:read 权限，可以看主账号共享的文件夹
        conditions.append(model_class.folder_id.in_(accessible_ids))
    
    if shared_ids:
        conditions.append(model_class.id.in_(shared_ids))
    
    query = query.filter(or_(*conditions))
    return query


# ==================== 文件夹（保留原有） ====================

@router.get("/folders", summary="获取文件夹列表", response_model=schemas.GlobalAssetFolderPageMsg)
def get_folders(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission("asset:read")),
    page_params: schemas.GlobalAssetFolderPageParams = Depends(),
) -> Any:
    owner_user_id = _get_owner_user_id(current_user)
    query = crud.global_asset_folder_crud.get_by_owner(db=db, user_id=current_user.id, owner_user_id=owner_user_id)
    if current_user.parent_user_id is None:
        query = query.filter(models.GlobalAssetFolder.user_id == current_user.id)
    else:
        accessible_ids = get_accessible_folder_ids(current_user, db)
        if accessible_ids is not None:
            query = query.filter(
                or_(
                    models.GlobalAssetFolder.user_id == current_user.id,
                    models.GlobalAssetFolder.id.in_(accessible_ids),
                )
            )
        else:
            # 子账号无 main_user_asset:read 权限，只能看自己的文件夹
            query = query.filter(models.GlobalAssetFolder.user_id == current_user.id)
    if page_params.name:
        query = query.filter(models.GlobalAssetFolder.name.like(f"%{page_params.name}%"))
    result = crud.global_asset_folder_crud.get_multi(page_params=page_params, query=query)
    if current_user.parent_user_id is not None:
        for folder in result["data"]:
            folder.is_shared = folder.user_id != current_user.id
    return success_response(data=result["data"], pagination=result["pagination"])


@router.post("/folders", summary="创建文件夹", response_model=schemas.GlobalAssetFolderMsg)
def create_folder(
    folder_in: schemas.GlobalAssetFolderCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission("asset:create")),
) -> Any:
    create_data = folder_in.model_dump()
    create_data["user_id"] = current_user.id
    create_data["owner_user_id"] = _get_owner_user_id(current_user)
    folder = crud.global_asset_folder_crud.create(db=db, obj_in=create_data)
    return success_response(data=folder)


@router.get("/folders/{folder_id}", summary="获取文件夹详情", response_model=schemas.GlobalAssetFolderMsg)
def get_folder(
    folder_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission("asset:read")),
) -> Any:
    folder = crud.global_asset_folder_crud.receive(db=db, primary_id=folder_id)
    if folder.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权操作")
    return success_response(data=folder)


@router.put("/folders/{folder_id}", summary="更新文件夹", response_model=schemas.GlobalAssetFolderMsg)
def update_folder(
    folder_id: str,
    folder_in: schemas.GlobalAssetFolderUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission("asset:update")),
) -> Any:
    folder = crud.global_asset_folder_crud.receive(db=db, primary_id=folder_id)
    if folder.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权操作")
    folder = crud.global_asset_folder_crud.update(db=db, db_obj=folder, obj_in=folder_in)
    return success_response(data=folder)


@router.delete("/folders/{folder_id}", summary="删除文件夹", response_model=schemas.Msg)
def delete_folder(
    folder_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission("asset:delete")),
) -> Any:
    folder = crud.global_asset_folder_crud.receive(db=db, primary_id=folder_id)
    if folder.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权操作")
    crud.global_asset_folder_crud.clear_folder_references(db=db, folder_id=folder_id)
    crud.global_asset_folder_crud.remove(db=db, primary_id=folder_id)
    return success_response()



# ==================== 角色列表/创建 ====================

@router.get("/characters", summary="获取角色列表", response_model=schemas.GlobalCharacterPageMsg)
def get_characters(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission("asset:read")),
    page_params: schemas.GlobalCharacterPageParams = Depends(),
) -> Any:
    from app.crud.asset_share_relation_crud import asset_share_relation_crud
    
    owner_user_id = _get_owner_user_id(current_user)
    
    # 获取平台授权的角色ID（按主账号查询，子账号可继承主账号的授权）
    shared_character_ids = asset_share_relation_crud.get_shared_asset_ids(db, owner_user_id, "character")
    
    # 构建查询
    query = crud.global_character_crud.get_queryset(db)
    
    # 主账号逻辑
    if current_user.parent_user_id is None:
        # 主账号可以看到：1. 自己创建的  2. 平台授权的
        conditions = [models.GlobalCharacter.user_id == current_user.id]
        if shared_character_ids:
            conditions.append(models.GlobalCharacter.id.in_(shared_character_ids))
        query = query.filter(or_(*conditions))
    else:
        # 子账号可以看到：1. 自己创建的  2. 主账号共享文件夹的  3. 平台授权的
        accessible_folder_ids = get_accessible_folder_ids(current_user, db)
        conditions = [models.GlobalCharacter.user_id == current_user.id]
        
        if accessible_folder_ids is not None:
            conditions.append(models.GlobalCharacter.folder_id.in_(accessible_folder_ids))
        
        if shared_character_ids:
            conditions.append(models.GlobalCharacter.id.in_(shared_character_ids))
        
        query = query.filter(or_(*conditions))
    
    query = query.order_by(models.GlobalCharacter.create_time.desc())

    # 平台资产视图：folder_id='platform' 时只看 is_management_asset=True；
    # 其他所有视图（全部/未分组/具体资产组）都剔除平台资产，避免用户视图里混入
    if page_params.folder_id == "platform":
        query = query.filter(models.GlobalCharacter.is_management_asset.is_(True))
    else:
        query = query.filter(models.GlobalCharacter.is_management_asset.is_(False))
        # 文件夹过滤
        if page_params.folder_id:
            if page_params.folder_id == "null":
                query = query.filter(models.GlobalCharacter.folder_id.is_(None))
            else:
                query = query.filter(models.GlobalCharacter.folder_id == page_params.folder_id)
    if page_params.name:
        query = query.filter(models.GlobalCharacter.name.like(f"%{page_params.name}%"))
    result = crud.global_character_crud.get_multi(page_params=page_params, query=query)
    characters = result["data"]
    if characters:
        character_ids = [c.id for c in characters]
        appearances_map = crud.global_character_appearance_crud.get_batch_by_characters(db, character_ids)
        for char in characters:
            char_apps = appearances_map.get(char.id, [])
            char.appearances = char_apps
            char.preview_url = crud.global_character_appearance_crud.resolve_preview_url(char_apps)
            char.thumbnail_url = crud.global_character_appearance_crud.resolve_thumbnail_url(char_apps)
            for app in char_apps:
                _apply_region_volc_id(app, current_user.region)
    return success_response(data=characters, pagination=result["pagination"])


@router.post("/characters", summary="创建角色", response_model=schemas.GlobalCharacterCreateMsg)
def create_character(
    character_in: schemas.GlobalCharacterCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission("asset:create")),
) -> Any:
    if character_in.art_style and character_in.art_style not in VALID_ART_STYLES:
        return fail_response(msg=f"无效的艺术风格，可选值: {VALID_ART_STYLES}")

    if character_in.folder_id:
        folder = crud.global_asset_folder_crud.get(db=db, id=character_in.folder_id)
        if not folder or folder.user_id != current_user.id:
            return fail_response(msg="文件夹不存在")

    create_data = character_in.model_dump(exclude_unset=True, 
                                          exclude=['art_style', 'description',
                                          "initial_image_url", 'reference_image_urls',
                                          'generate_from_reference', 'custom_description',
                                          'count'])
    create_data["user_id"] = current_user.id
    create_data["owner_user_id"] = _get_owner_user_id(current_user)
    character = crud.global_character_crud.create(db=db, obj_in=create_data)

    appearance_data = {
        "character_id": character.id,
        "appearance_index": 0,
        "change_reason": "初始形象",
        "art_style": character_in.art_style,
        "description": character_in.description or "",
        "descriptions": json.dumps([character_in.description or ""]),
        "image_urls": json.dumps([]),
        "previous_image_urls": json.dumps([]),
    }
    if character_in.initial_image_url:
        appearance_data["image_url"] = cos_client.url_to_key(character_in.initial_image_url) or character_in.initial_image_url

    reference_urls = character_in.reference_image_urls or []
    if character_in.generate_from_reference and reference_urls:
        appearance_data["gen_status"] = "generating"

    appearance = crud.global_character_appearance_crud.create(db=db, obj_in=appearance_data)

    if character_in.generate_from_reference and reference_urls:
        from app.core.ws import ws_manager
        ws_manager.publish_asset_hub_event(
            user_id=current_user.id,
            event_type="asset_hub_generation_started",
            data={"target_type": "appearance", "target_id": appearance.id, "asset_type": "character", "action_type": "reference"},
        )

        locale = character_in.locale
        if not locale:
            accept_lang = request.headers.get("accept-language", "")
            if accept_lang:
                first = accept_lang.split(",")[0].strip().lower()
                if first.startswith("zh"):
                    locale = "zh"
                elif first.startswith("en"):
                    locale = "en"
        locale = locale or "zh"

        resolved = ConfigReader(db).get_config(str(current_user.id))

        task_service.submit_task(
            task_type=TaskType.ASSET_HUB_REFERENCE_TO_CHARACTER,
            user_id=current_user.id,
            payload={
                "reference_image_urls": reference_urls[:5],
                "character_id": character.id,
                "appearance_id": appearance.id,
                "art_style": character_in.art_style,
                "custom_description": character_in.custom_description or "",
                "is_background_job": True,
                "count": character_in.count,
                "locale": locale,
                "config_snapshot": resolved.to_dict(),
            },
            target_type="GlobalCharacterAppearance",
            target_id=appearance.id,
        )

    return success_response(data={"character": character, "appearance": appearance})


# ==================== 角色详情/更新/删除 ====================

@router.get("/characters/{character_id}", summary="获取角色详情", response_model=schemas.GlobalCharacterDetailMsg)
def get_character(
    character_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission("asset:read")),
) -> Any:
    from app.crud.asset_share_relation_crud import asset_share_relation_crud
    
    character = crud.global_character_crud.get(db=db, id=character_id)
    if not character:
        raise HTTPException(status_code=404, detail="角色不存在")
    
    # 权限检查：自己创建的 或 平台授权的（按主账号查询）
    owner_user_id = _get_owner_user_id(current_user)
    is_owner = character.user_id == current_user.id
    is_shared = asset_share_relation_crud.is_shared_to_user(db, character_id, owner_user_id)
    
    if not is_owner and not is_shared:
        raise HTTPException(status_code=404, detail="角色不存在")
    
    appearances = crud.global_character_appearance_crud.get_by_character(db, character_id).all()
    return success_response(data={"character": character, "appearances": appearances})


@router.put("/characters/{character_id}", summary="更新角色", response_model=schemas.GlobalCharacterMsg)
def update_character(
    character_id: str,
    character_in: schemas.GlobalCharacterUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission("asset:update")),
) -> Any:
    character = crud.global_character_crud.get(db=db, id=character_id)
    if not character or character.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权操作")
    
    # 禁止修改平台资产
    if character.is_management_asset:
        raise HTTPException(status_code=403, detail="平台资产不允许修改")
    
    if character_in.folder_id is not None and character_in.folder_id:
        owner_user_id = _get_owner_user_id(current_user)
        if not crud.global_character_crud.validate_folder_ownership(
            db, character_in.folder_id, current_user.id, owner_user_id
        ):
            return fail_response(msg="文件夹不存在或无权访问")
    update_data = character_in.model_dump(exclude_unset=True)
    if "custom_voice_url" in update_data and update_data["custom_voice_url"]:
        update_data["custom_voice_url"] = cos_client.presigned_url_to_key(update_data["custom_voice_url"])
    character = crud.global_character_crud.update(db=db, db_obj=character, obj_in=update_data)
    return success_response(data=character)


@router.delete("/characters/{character_id}", summary="删除角色", response_model=schemas.Msg)
def delete_character(
    character_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission("asset:delete")),
) -> Any:
    character = crud.global_character_crud.get(db=db, id=character_id)
    if not character or character.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权操作")
    
    # 禁止删除平台资产
    if character.is_management_asset:
        raise HTTPException(status_code=403, detail="平台资产不允许删除")
    
    crud.global_character_crud.cleanup_character_voices(db, character)
    appearances = crud.global_character_appearance_crud.get_by_character(db, character_id).all()
    for app in appearances:
        crud.global_character_appearance_crud.remove(db, app.id)
    crud.global_character_crud.remove(db, character_id)
    return success_response()


# ==================== 子外观管理 ====================

@router.post("/appearances", summary="添加子外观", response_model=schemas.GlobalCharacterAppearanceMsg)
def create_appearance(
    appearance_in: schemas.GlobalCharacterAppearanceCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission("asset:create")),
) -> Any:
    character = crud.global_character_crud.get(db=db, id=appearance_in.character_id)
    if not character or character.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="角色不存在")

    next_index = crud.global_character_appearance_crud.get_next_appearance_index(db, appearance_in.character_id)

    art_style = appearance_in.art_style
    if not art_style:
        primary = crud.global_character_appearance_crud.get_by_character_and_index(
            db, appearance_in.character_id, 0
        )
        art_style = primary.art_style if primary else "realistic"

    if art_style and art_style not in VALID_ART_STYLES:
        return fail_response(msg=f"无效的艺术风格，可选值: {VALID_ART_STYLES}")

    create_data = appearance_in.model_dump(exclude_unset=True)
    create_data["appearance_index"] = next_index
    create_data["art_style"] = art_style
    create_data["descriptions"] = json.dumps([appearance_in.description or ""])
    create_data["image_urls"] = json.dumps([])
    create_data["previous_image_urls"] = json.dumps([])

    appearance = crud.global_character_appearance_crud.create(db=db, obj_in=create_data)
    return success_response(data=appearance)


@router.patch("/appearances", summary="更新外观描述", response_model=schemas.Msg)
def update_appearance(
    appearance_in: schemas.GlobalCharacterAppearanceUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission("asset:update")),
) -> Any:
    character = crud.global_character_crud.get(db=db, id=appearance_in.character_id)
    if not character or character.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="角色不存在")

    # 禁止修改平台资产
    if character.is_management_asset:
        raise HTTPException(status_code=403, detail="平台资产不允许修改")

    appearance = crud.global_character_appearance_crud.get_by_character_and_index(
        db, appearance_in.character_id, appearance_in.appearance_index
    )
    if not appearance:
        raise HTTPException(status_code=404, detail="外观不存在")

    if appearance_in.art_style is not None and appearance_in.art_style not in VALID_ART_STYLES:
        return fail_response(msg=f"无效的艺术风格，可选值: {VALID_ART_STYLES}")

    update_data = appearance_in.model_dump(exclude_unset=True)
    desc_index = appearance_in.description_index
    if "description" in update_data and update_data["description"]:
        appearance = crud.global_character_appearance_crud.update_description_at_index(
            db, appearance, update_data["description"], desc_index if desc_index is not None else 0
        )
        update_data.pop("description", None)
        update_data.pop("descriptions", None)

    appearance = crud.global_character_appearance_crud.update(db=db, db_obj=appearance, obj_in=update_data)
    return success_response()


@router.delete("/appearances", summary="删除子外观", response_model=schemas.Msg)
def delete_appearance(
    character_id: str,
    appearance_index: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission("asset:delete")),
) -> Any:
    if appearance_index == 0:
        return fail_response(msg="不能删除主外观")

    character = crud.global_character_crud.get(db=db, id=character_id)
    if not character or character.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="角色不存在")

    # 禁止修改平台资产
    if character.is_management_asset:
        raise HTTPException(status_code=403, detail="平台资产不允许修改")

    appearance = crud.global_character_appearance_crud.get_by_character_and_index(
        db, character_id, appearance_index
    )
    if appearance:
        crud.global_character_appearance_crud.remove(db, appearance.id)
    return success_response()


# ==================== 直传凭证 ====================

# 禁止上传的文件类型（可执行、脚本等危险类型）
BLOCKED_CONTENT_TYPES = {
    # 可执行文件
    "application/x-executable", "application/x-msdownload",
    "application/x-dosexec", "application/x-msi",
    "application/java-archive", "application/x-java-applet",
    # 脚本
    "text/javascript", "application/x-javascript",
    "application/x-php", "text/x-php",
    "application/x-httpd-php", "application/x-sh",
    "application/x-bat", "application/x-csh",
    # HTML（XSS 风险）
    "text/html", "application/xhtml+xml",
}


@router.post("/upload-credential", summary="获取直传凭证")
def get_upload_credential(
    body: schemas.UploadCredentialRequest,
    current_user: models.User = Depends(require_permission("asset:update")),
) -> Any:
    """前端直传 COS 前获取预签名上传 URL"""
    if body.content_type in BLOCKED_CONTENT_TYPES:
        return fail_response(msg=f"不支持的文件类型: {body.content_type}")

    key = cos_client.generate_unique_key(
        category=body.category,
        biz=body.biz,
        user_id=str(current_user.id),
        ext=body.file_extension,
    )
    upload_url = cos_client.generate_presigned_put_url(
        key=key,
        content_type=body.content_type,
        expires=600,
    )
    url = cos_client.key_to_url(key)

    return success_response(data={
        "upload_url": upload_url,
        "cos_key": key,
        "url": url,
        "expires_in": 600,
    })


# ==================== 图片上传 ====================

@router.post("/upload-image", summary="上传资产图片", response_model=schemas.UploadImageMsg)
async def upload_image(
    type: str = Form(...),
    id: str = Form(...),
    appearance_index: int = Form(0),
    image_index: int = Form(None),
    label_text: str = Form(""),
    cos_key: str = Form(None),
    thumbnail_cos_key: str = Form(None),
    file: UploadFile = File(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission("asset:update")),
) -> Any:
    from app.core.ws import ws_manager

    if type == "character":
        appearance = crud.global_character_appearance_crud.get_by_character_and_index(db, id, appearance_index)
        if not appearance:
            return fail_response(msg="外观不存在")
        ws_manager.publish_asset_hub_event(
            user_id=current_user.id,
            event_type="asset_hub_generation_started",
            data={"target_type": "appearance", "target_id": appearance.id, "asset_type": "character", "action_type": "upload"},
        )
    elif type == "location":
        location = crud.global_location_crud.get(db=db, id=id)
        if location:
            from app.models.asset import GlobalLocationImage
            target_index = image_index if image_index is not None else None
            if target_index is not None:
                loc_image = db.query(GlobalLocationImage).filter(
                    GlobalLocationImage.location_id == id,
                    GlobalLocationImage.image_index == target_index,
                    GlobalLocationImage.is_deleted == False,
                ).first()
                if loc_image:
                    ws_manager.publish_asset_hub_event(
                        user_id=current_user.id,
                        event_type="asset_hub_generation_started",
                        data={"target_type": "location_image", "target_id": loc_image.id, "asset_type": location.asset_kind or "location", "action_type": "upload"},
                    )

    # 有 cos_key 时跳过文件读取和处理（前端已直传 COS）
    processed = None
    if not cos_key:
        if not file:
            return fail_response(msg="请提供 file 或 cos_key")
        content = await file.read()
        processed = process_to_jpeg(content)

    if type == "character":
        if cos_key:
            key = cos_key
        else:
            key = cos_client.generate_unique_key("upload", "char", current_user.id, "jpg")
            cos_client.upload_object(processed, key)

        # 优先用前端直传的缩略图 key；没有则回拉原图生成（向后兼容）
        if thumbnail_cos_key:
            thumb_key = thumbnail_cos_key
        elif processed is not None:
            thumb_key = _upload_thumb(processed, key)
        else:
            thumb_key = _upload_thumb(cos_client.download_object_as_bytes(key), key)

        appearance = crud.global_character_appearance_crud.get_by_character_and_index(db, id, appearance_index)
        if not appearance:
            return fail_response(msg="外观不存在")

        appearance.previous_image_url = appearance.image_url
        appearance.previous_image_urls = appearance.image_urls

        image_urls = json.loads(appearance.image_urls) if appearance.image_urls else []
        thumb_urls = json.loads(appearance.thumbnail_urls) if appearance.thumbnail_urls else []
        if image_index is not None and image_index < len(image_urls):
            image_urls[image_index] = key
        else:
            image_urls.append(key)
        # 同步维护 thumbnail_urls 数组（与 image_urls 一一对应）
        while len(thumb_urls) < len(image_urls) - 1:
            thumb_urls.append(None)
        if image_index is not None and image_index < len(thumb_urls):
            thumb_urls[image_index] = thumb_key
        else:
            thumb_urls.append(thumb_key)
        appearance.image_urls = json.dumps(image_urls)
        appearance.thumbnail_urls = json.dumps(thumb_urls)

        if appearance.selected_index is None or len(image_urls) == 1:
            appearance.image_url = key
            appearance.thumbnail_url = thumb_key

        appearance.gen_status = "completed"
        db.commit()
        db.refresh(appearance)

        from app.core.ws import ws_manager
        ws_manager.publish_asset_hub_event(
            user_id=current_user.id,
            event_type="asset_hub_generation_completed",
            data={
                "target_type": "appearance",
                "target_id": appearance.id,
                "asset_type": "character",
                "image_url": cos_client.key_to_url(key),
                "thumbnail_url": cos_client.key_to_url(thumb_key) if thumb_key else None,
            },
        )

        # 自动同步到火山/BytePlus；失败仅记日志并通过 sync_error 返回，不阻塞上传成功
        sync_error = None
        try:
            from app.utils.user_volc_sync import sync_user_asset_to_volc
            sync_user_asset_to_volc(db, str(current_user.id), appearance, raise_on_error=True)
        except Exception as e:
            logger.warning(f"自动同步火山失败 (character_appearance={appearance.id}): {e}")
            sync_error = str(e)

        return success_response(data={"image_key": key, "image_index": image_index or len(image_urls) - 1, "sync_error": sync_error})

    elif type == "location":
        location = crud.global_location_crud.get(db=db, id=id)
        if not location or location.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="场景/道具不存在")

        if cos_key:
            key = cos_key
        else:
            key = cos_client.generate_unique_key("upload", "loc", current_user.id, "jpg")
            cos_client.upload_object(processed, key)

        # 优先用前端直传的缩略图 key；没有则回拉原图生成（向后兼容）
        if thumbnail_cos_key:
            thumb_key = thumbnail_cos_key
        elif processed is not None:
            thumb_key = _upload_thumb(processed, key)
        else:
            thumb_key = _upload_thumb(cos_client.download_object_as_bytes(key), key)

        from app.models.asset import GlobalLocationImage

        target_index = image_index if image_index is not None else None
        image_to_sync = None

        if target_index is not None:
            loc_image = db.query(GlobalLocationImage).filter(
                GlobalLocationImage.location_id == id,
                GlobalLocationImage.image_index == target_index,
                GlobalLocationImage.is_deleted == False,
            ).first()

            if loc_image:
                loc_image.previous_image_url = loc_image.image_url
                loc_image.previous_thumbnail_url = loc_image.thumbnail_url
                loc_image.image_url = key
                loc_image.thumbnail_url = thumb_key
                loc_image.gen_status = "completed"
                db.commit()
                from app.core.ws import ws_manager
                ws_manager.publish_asset_hub_event(
                    user_id=current_user.id,
                    event_type="asset_hub_generation_completed",
                    data={
                        "target_type": "location_image",
                        "target_id": loc_image.id,
                        "asset_type": location.asset_kind or "location",
                        "image_url": cos_client.key_to_url(key),
                        "thumbnail_url": cos_client.key_to_url(thumb_key) if thumb_key else None,
                    },
                )
                image_to_sync = loc_image
            else:
                new_image = GlobalLocationImage(
                    location_id=id,
                    image_index=target_index,
                    image_url=key,
                    thumbnail_url=thumb_key,
                    description=label_text,
                    is_selected=(target_index == 0),
                    gen_status="completed",
                )
                db.add(new_image)
                db.commit()
                from app.core.ws import ws_manager
                ws_manager.publish_asset_hub_event(
                    user_id=current_user.id,
                    event_type="asset_hub_generation_completed",
                    data={
                        "target_type": "location_image",
                        "target_id": new_image.id,
                        "asset_type": location.asset_kind or "location",
                        "image_url": cos_client.key_to_url(key),
                        "thumbnail_url": cos_client.key_to_url(thumb_key) if thumb_key else None,
                    },
                )
                image_to_sync = new_image
        else:
            existing_count = db.query(GlobalLocationImage).filter(
                GlobalLocationImage.location_id == id,
                GlobalLocationImage.is_deleted == False,
            ).count()
            new_image = GlobalLocationImage(
                location_id=id,
                image_index=existing_count,
                image_url=key,
                thumbnail_url=thumb_key,
                description=label_text,
                is_selected=(existing_count == 0),
                gen_status="completed",
            )
            db.add(new_image)
            db.commit()
            from app.core.ws import ws_manager
            ws_manager.publish_asset_hub_event(
                user_id=current_user.id,
                event_type="asset_hub_generation_completed",
                data={
                    "target_type": "location_image",
                    "target_id": new_image.id,
                    "asset_type": location.asset_kind or "location",
                    "image_url": cos_client.key_to_url(key),
                    "thumbnail_url": cos_client.key_to_url(thumb_key) if thumb_key else None,
                },
            )
            image_to_sync = new_image

        # 自动同步到火山/BytePlus；失败仅记日志并通过 sync_error 返回，不阻塞上传成功
        sync_error = None
        if image_to_sync is not None:
            try:
                from app.utils.user_volc_sync import sync_user_asset_to_volc
                sync_user_asset_to_volc(db, str(current_user.id), image_to_sync, raise_on_error=True)
            except Exception as e:
                logger.warning(f"自动同步火山失败 (location_image={image_to_sync.id}): {e}")
                sync_error = str(e)

        return success_response(data={"image_key": key, "image_index": target_index or 0, "sync_error": sync_error})

    else:
        return fail_response(msg="不支持的类型")


# ==================== 图片选择 ====================

@router.post("/select-image", summary="选择候选图", response_model=schemas.Msg)
def select_image(
    body: schemas.SelectImageRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission("asset:update")),
) -> Any:
    if body.type in ("location", "prop"):
        return _select_location_image(body, db, current_user)

    appearance = crud.global_character_appearance_crud.get_by_character_and_index(
        db, body.id, body.appearance_index
    )
    if not appearance:
        return fail_response(msg="外观不存在")

    image_urls = json.loads(appearance.image_urls) if appearance.image_urls else []

    if body.confirm and appearance.selected_index is not None:
        selected_key = image_urls[appearance.selected_index] if appearance.selected_index < len(image_urls) else None
        if selected_key:
            keys_to_delete = [k for i, k in enumerate(image_urls) if i != appearance.selected_index]
            # TODO: 恢复 COS 删除
            # cos_client.delete_objects(keys_to_delete)
            thumb_urls = json.loads(appearance.thumbnail_urls) if appearance.thumbnail_urls else []
            selected_thumb = thumb_urls[appearance.selected_index] if appearance.selected_index < len(thumb_urls) else None
            appearance.image_urls = json.dumps([selected_key])
            appearance.thumbnail_urls = json.dumps([selected_thumb]) if selected_thumb else None
            appearance.image_url = selected_key
            appearance.thumbnail_url = selected_thumb
            appearance.selected_index = 0
            db.commit()
    else:
        if body.image_index is not None and body.image_index < len(image_urls):
            appearance.selected_index = body.image_index
            appearance.image_url = image_urls[body.image_index]
            # 同步切换 thumbnail_url（从 thumbnail_urls 数组按索引选取）
            thumb_urls = json.loads(appearance.thumbnail_urls) if appearance.thumbnail_urls else []
            if body.image_index < len(thumb_urls) and thumb_urls[body.image_index]:
                appearance.thumbnail_url = thumb_urls[body.image_index]
            db.commit()

    # 同步选中图片到火山私域
    if appearance.image_url:
        from app.utils.user_volc_sync import sync_user_asset_to_volc
        sync_user_asset_to_volc(db, str(current_user.id), appearance)

    return success_response()


def _select_location_image(body: schemas.SelectImageRequest, db: Session, current_user: models.User) -> Any:
    from app.models.asset import GlobalLocationImage

    images = db.query(GlobalLocationImage).filter(
        GlobalLocationImage.location_id == body.id,
        GlobalLocationImage.is_deleted == False,
    ).order_by(GlobalLocationImage.image_index).all()

    if not images:
        return fail_response(msg="场景图片不存在")

    selected_img = None
    if body.confirm:
        selected_img = next((img for img in images if img.is_selected), images[0])
        keys_to_delete = [img.image_url for img in images if img.id != selected_img.id and img.image_url]
        # if keys_to_delete:
            # TODO: 恢复 COS 删除
            # cos_client.delete_objects(keys_to_delete)
        for img in images:
            if img.id != selected_img.id:
                img.is_deleted = True
        selected_img.is_selected = True
        db.commit()
    else:
        target = next((img for img in images if img.image_index == body.image_index), None) if body.image_index is not None else None
        if target:
            for img in images:
                img.is_selected = (img.id == target.id)
            selected_img = target
            db.commit()

    # 同步选中图片到火山私域
    if selected_img and selected_img.image_url:
        from app.utils.user_volc_sync import sync_user_asset_to_volc
        sync_user_asset_to_volc(db, str(current_user.id), selected_img)

    return success_response()


# ==================== 图片撤销 ====================

@router.post("/undo-image", summary="撤销图片变更", response_model=schemas.Msg)
def undo_image(
    body: schemas.UndoImageRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission("asset:update")),
) -> Any:
    appearance = crud.global_character_appearance_crud.get_by_character_and_index(
        db, body.id, body.appearance_index
    )
    if not appearance:
        return fail_response(msg="外观不存在")

    if not appearance.previous_image_url and not appearance.previous_image_urls:
        return fail_response(msg="无可撤销的历史记录")

    from app.core.ws import ws_manager
    ws_manager.publish_asset_hub_event(
        user_id=current_user.id,
        event_type="asset_hub_generation_started",
        data={"target_type": "appearance", "target_id": appearance.id, "asset_type": "character", "action_type": "undo"},
    )

    appearance.image_url = appearance.previous_image_url
    appearance.image_urls = appearance.previous_image_urls
    if appearance.previous_description:
        appearance.description = appearance.previous_description
        appearance.previous_description = None
    if appearance.previous_descriptions:
        appearance.descriptions = appearance.previous_descriptions
        appearance.previous_descriptions = None
    appearance.previous_image_url = None
    appearance.previous_image_urls = None
    appearance.selected_index = None
    # 撤销后从 image_urls 重新计算 thumbnail_url：取第一张对应的缩略图
    if appearance.thumbnail_urls:
        try:
            thumb_list = json.loads(appearance.thumbnail_urls)
        except (json.JSONDecodeError, TypeError):
            thumb_list = []
    else:
        thumb_list = []
    appearance.thumbnail_url = thumb_list[0] if thumb_list else None
    appearance.gen_status = "completed"
    db.commit()

    from app.core.ws import ws_manager
    ws_manager.publish_asset_hub_event(
        user_id=current_user.id,
        event_type="asset_hub_generation_completed",
        data={
            "target_type": "appearance",
            "target_id": appearance.id,
            "asset_type": "character",
            "image_url": cos_client.key_to_url(appearance.image_url) if appearance.image_url else "",
            "thumbnail_url": cos_client.key_to_url(appearance.thumbnail_url) if appearance.thumbnail_url else None,
        },
    )

    return success_response()


# ==================== 音色管理 ====================

@router.get("/voices", summary="获取音色列表", response_model=schemas.GlobalVoicePageMsg)
def get_voices(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission("asset:read")),
    page_params: schemas.GlobalVoicePageParams = Depends(),
) -> Any:
    from app.crud.asset_share_relation_crud import asset_share_relation_crud
    
    owner_user_id = _get_owner_user_id(current_user)
    
    # 获取平台授权的音色ID（按主账号查询，子账号可继承主账号的授权）
    shared_voice_ids = asset_share_relation_crud.get_shared_asset_ids(db, owner_user_id, "voice")
    
    # 构建查询：owner过滤 OR 授权过滤
    query = crud.global_voice_crud.get_queryset(db)
    owner_condition = models.GlobalVoice.owner_user_id == owner_user_id
    
    if shared_voice_ids:
        query = query.filter(
            or_(
                owner_condition,
                models.GlobalVoice.id.in_(shared_voice_ids)
            )
        )
    else:
        query = query.filter(owner_condition)
    
    query = query.order_by(models.GlobalVoice.create_time.desc())
    
    # 再应用文件夹过滤（授权资产豁免 user_id 限制）
    query = _apply_folder_filter(query, models.GlobalVoice, current_user, db, shared_ids=shared_voice_ids)
    # 平台资产视图：folder_id='platform' 时只看 is_management_asset=True；
    # 其他视图剔除平台资产
    if page_params.folder_id == "platform":
        query = query.filter(models.GlobalVoice.is_management_asset.is_(True))
    else:
        query = query.filter(models.GlobalVoice.is_management_asset.is_(False))
        if page_params.folder_id:
            if page_params.folder_id == "null":
                query = query.filter(models.GlobalVoice.folder_id.is_(None))
            else:
                query = query.filter(models.GlobalVoice.folder_id == page_params.folder_id)
    if page_params.name:
        query = query.filter(models.GlobalVoice.name.like(f"%{page_params.name}%"))
    result = crud.global_voice_crud.get_multi(page_params=page_params, query=query)
    for v in result["data"]:
        _apply_region_volc_id(v, current_user.region)
    return success_response(data=result["data"], pagination=result["pagination"])


@router.get("/voices/{voice_id}", summary="获取音色详情", response_model=schemas.GlobalVoiceMsg)
def get_voice(
    voice_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission("asset:read")),
) -> Any:
    from app.crud.asset_share_relation_crud import asset_share_relation_crud
    
    owner_user_id = _get_owner_user_id(current_user)
    voice = crud.global_voice_crud.get(db=db, id=voice_id)
    if not voice:
        raise HTTPException(status_code=404, detail="音色不存在")
    
    # 权限检查：自己创建的 或 平台授权的（按主账号查询）
    is_owner = voice.user_id == current_user.id
    is_shared = asset_share_relation_crud.is_shared_to_user(db, voice_id, owner_user_id)
    
    if not is_owner and not is_shared:
        raise HTTPException(status_code=404, detail="音色不存在")
    
    return success_response(data=voice)


@router.post("/voices", summary="创建音色", response_model=schemas.GlobalVoiceMsg)
def create_voice(
    voice_in: schemas.GlobalVoiceCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission("asset:create")),
) -> Any:
    if voice_in.folder_id:
        folder = crud.global_asset_folder_crud.get(db=db, id=voice_in.folder_id)
        if not folder or folder.user_id != current_user.id:
            return fail_response(msg="文件夹不存在")

    create_data = voice_in.model_dump(exclude_unset=True)
    create_data["user_id"] = current_user.id
    create_data["owner_user_id"] = _get_owner_user_id(current_user)
    voice = crud.global_voice_crud.create(db=db, obj_in=create_data)
    return success_response(data=voice)


@router.put("/voices/{voice_id}", summary="更新音色", response_model=schemas.GlobalVoiceMsg)
def update_voice(
    voice_id: str,
    voice_in: schemas.GlobalVoiceUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission("asset:update")),
) -> Any:
    voice = crud.global_voice_crud.get(db=db, id=voice_id)
    if not voice or voice.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权操作")
    
    # 禁止修改平台资产
    if voice.is_management_asset:
        raise HTTPException(status_code=403, detail="平台资产不允许修改")

    if voice_in.folder_id is not None and voice_in.folder_id:
        folder = crud.global_asset_folder_crud.get(db=db, id=voice_in.folder_id)
        if not folder or folder.user_id != current_user.id:
            return fail_response(msg="文件夹不存在或无权访问")

    voice = crud.global_voice_crud.update(db=db, db_obj=voice, obj_in=voice_in)
    return success_response(data=voice)


@router.delete("/voices/{voice_id}", summary="删除音色", response_model=schemas.Msg)
def delete_voice(
    voice_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission("asset:delete")),
) -> Any:
    voice = crud.global_voice_crud.get(db=db, id=voice_id)
    if not voice or voice.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权操作")

    # 禁止删除平台资产
    if voice.is_management_asset:
        raise HTTPException(status_code=403, detail="平台资产不允许删除")

    crud.global_voice_crud.remove(db, voice_id)
    return success_response()


@router.post("/voices/upload", summary="上传音频文件创建音色", response_model=schemas.GlobalVoiceMsg)
async def upload_voice(
    name: str = Form(...),
    file: UploadFile = File(...),
    folder_id: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    gender: Optional[str] = Form(None),
    duration: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission("asset:create")),
) -> Any:
    if folder_id:
        folder = crud.global_asset_folder_crud.get(db=db, id=folder_id)
        if not folder or folder.user_id != current_user.id:
            return fail_response(msg="文件夹不存在")

    allowed_types = {"audio/mpeg", "audio/mp3", "audio/wav", "audio/ogg", "audio/m4a", "audio/x-m4a", "audio/aac"}
    if file.content_type not in allowed_types:
        return fail_response(msg="不支持的音频格式，支持 MP3、WAV、OGG、M4A、AAC")

    content = await file.read()
    ext = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "mp3"
    key = cos_client.generate_unique_key("upload", "voice", current_user.id, ext)
    cos_client.upload_object(content, key, content_type=file.content_type)

    create_data = {
        "id": str(uuid.uuid4()),
        "user_id": current_user.id,
        "owner_user_id": _get_owner_user_id(current_user),
        "name": name,
        "folder_id": folder_id or None,
        "description": description,
        "gender": gender,
        "voice_type": "uploaded",
        "custom_voice_url": key,
        "duration": duration,
    }
    voice = crud.global_voice_crud.create(db=db, obj_in=create_data)

    # 同步到火山私域
    from app.utils.user_volc_sync import sync_user_asset_to_volc
    sync_user_asset_to_volc(db, str(current_user.id), voice, display_name=name)

    return success_response(data=voice)


# ==================== AI 音色设计 ====================

@router.post("/voices/design", summary="AI 设计音色")
def design_voice(
    body: schemas.VoiceDesignRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission("asset:create")),
) -> Any:
    resolved = ConfigReader(db).get_config(str(current_user.id))
    return fail_response(msg="请先在设置中心配置音频模型")
    if not resolved.audio_model and not resolved.analysis_model:
        return fail_response(msg="请先在设置中心配置音频模型")

    result = task_service.submit_task(
        task_type=TaskType.ASSET_HUB_VOICE_DESIGN,
        user_id=current_user.id,
        payload={
            "voice_prompt": body.voice_prompt,
            "preview_text": body.preview_text,
            "count": body.count,
            "language": body.language,
            "config_snapshot": resolved.to_dict(),
        },
    )
    return success_response(data=result)


# ==================== 角色语音管理 ====================

@router.post("/character-voice", summary="设置角色语音", response_model=schemas.VoiceUploadMsg)
async def set_character_voice(
    character_id: str = Form(...),
    file: UploadFile = File(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission("asset:update")),
) -> Any:
    character = crud.global_character_crud.get(db=db, id=character_id)
    if not character or character.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="角色不存在")

    if not file:
        return fail_response(msg="请上传音频文件")

    allowed_types = {"audio/mpeg", "audio/mp3", "audio/wav", "audio/ogg", "audio/m4a"}
    if file.content_type not in allowed_types:
        return fail_response(msg="不支持的音频格式")

    content = await file.read()
    ext = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "mp3"
    key = cos_client.generate_unique_key("upload", "voice", current_user.id, ext)
    cos_client.upload_object(content, key, content_type=file.content_type)

    character.voice_type = "uploaded"
    character.voice_id = None
    character.custom_voice_url = key
    db.commit()

    return success_response(data={"audio_url": cos_client.key_to_url(key)})


@router.patch("/character-voice", summary="更新语音设置", response_model=schemas.Msg)
def update_voice_settings(
    body: schemas.VoiceSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission("asset:update")),
) -> Any:
    character = crud.global_character_crud.get(db=db, id=body.character_id)
    if not character or character.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="角色不存在")

    if body.voice_type is not None:
        character.voice_type = body.voice_type
    if body.voice_id is not None:
        character.voice_id = body.voice_id
    if body.custom_voice_url is not None:
        character.custom_voice_url = cos_client.presigned_url_to_key(body.custom_voice_url)
    db.commit()

    return success_response()


# ==================== 资产选择器 ====================

@router.get("/picker", summary="资产选择器", response_model=schemas.PickerMsg)
def get_picker(
    type: str = Query("character", description="资产类型: character/location/voice"),
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    asset_kind: Optional[str] = Query(None, description="资产类型过滤(location/prop)"),
    folder_id: Optional[str] = Query(None, description="资产组过滤；'null' 表示未分组"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission("asset:read")),
) -> Any:
    owner_user_id = _get_owner_user_id(current_user)
    offset = (page - 1) * size

    if type == "character":
        query = crud.global_character_crud.get_by_owner(db, current_user.id, owner_user_id)
        if folder_id == "null":
            query = query.filter(models.GlobalCharacter.folder_id.is_(None))
        elif folder_id:
            query = query.filter(models.GlobalCharacter.folder_id == folder_id)
        total_count = query.count()
        characters = query.offset(offset).limit(size).all()
        character_ids = [c.id for c in characters]
        appearances_map = crud.global_character_appearance_crud.get_batch_by_characters(db, character_ids)

        items = []
        for char in characters:
            apps = appearances_map.get(char.id, [])
            preview_url = crud.global_character_appearance_crud.resolve_preview_url(apps)
            thumbnail_url = crud.global_character_appearance_crud.resolve_thumbnail_url(apps)
            folder_name = None
            if char.folder_id:
                folder = crud.global_asset_folder_crud.get(db=db, id=char.folder_id)
                folder_name = folder.name if folder else None
            items.append(schemas.PickerCharacterItem(
                id=char.id,
                name=char.name,
                folder_name=folder_name,
                preview_url=preview_url,
                thumbnail_url=thumbnail_url,
                appearance_count=len(apps),
                has_voice=bool(char.voice_id or char.custom_voice_url),
            ))
        return success_response(data={
            "characters": items,
            "pagination": {"page": page, "size": size, "total_count": total_count},
        })

    elif type == "location":
        query = crud.global_location_crud.get_by_owner(db, owner_user_id)
        if asset_kind:
            query = query.filter(crud.global_location_crud.model.asset_kind == asset_kind)
        if folder_id == "null":
            query = query.filter(models.GlobalLocation.folder_id.is_(None))
        elif folder_id:
            query = query.filter(models.GlobalLocation.folder_id == folder_id)
        total_count = query.count()
        locations = query.offset(offset).limit(size).all()
        location_ids = [loc.id for loc in locations]
        images_map = crud.global_location_image_crud.get_batch_by_locations(db, location_ids)
        items = []
        for loc in locations:
            images = images_map.get(loc.id, [])
            preview_url = crud.global_location_image_crud.resolve_preview_url(images)
            thumbnail_url = crud.global_location_image_crud.resolve_thumbnail_url(images)
            folder_name = None
            if loc.folder_id:
                folder = crud.global_asset_folder_crud.get(db=db, id=loc.folder_id)
                folder_name = folder.name if folder else None
            items.append(schemas.PickerLocationItem(
                id=loc.id, name=loc.name, summary=loc.summary,
                folder_name=folder_name, preview_url=preview_url, thumbnail_url=thumbnail_url,
                image_count=len(images), asset_kind=loc.asset_kind,
            ))
        return success_response(data={
            "locations": items,
            "pagination": {"page": page, "size": size, "total_count": total_count},
        })

    elif type == "voice":
        query = crud.global_voice_crud.get_by_owner(db, owner_user_id)
        total_count = query.count()
        voices = query.offset(offset).limit(size).all()
        items = []
        for v in voices:
            preview_url = cos_client.key_to_url(v.custom_voice_url) if v.custom_voice_url else None
            folder_name = None
            if v.folder_id:
                folder = crud.global_asset_folder_crud.get(db=db, id=v.folder_id)
                folder_name = folder.name if folder else None
            items.append(schemas.PickerVoiceItem(
                id=v.id, name=v.name, description=v.description,
                folder_name=folder_name, preview_url=preview_url,
                voice_id=v.voice_id, voice_type=v.voice_type,
                gender=v.gender, language=v.language,
            ))
        return success_response(data={
            "voices": items,
            "pagination": {"page": page, "size": size, "total_count": total_count},
        })

    return fail_response(msg="不支持的类型")


# ==================== 临时上传 ====================

@router.post("/upload-temp", summary="上传临时文件", response_model=schemas.UploadTempMsg)
async def upload_temp(
    body: schemas.UploadTempRequest,
    current_user: models.User = Depends(require_permission("asset:create")),
) -> Any:
    # 新模式：前端已直传 COS，只需返回签名 URL
    if body.cos_key:
        url = cos_client.key_to_url(body.cos_key)
        return success_response(data={"url": url, "key": body.cos_key})

    # 旧模式：base64 中转（向后兼容）
    import base64
    import re

    _MIME_MAP = {
        "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
        "gif": "image/gif", "webp": "image/webp", "bmp": "image/bmp",
        "tiff": "image/tiff", "mp4": "video/mp4", "mov": "video/quicktime",
        "mp3": "audio/mpeg", "wav": "audio/wav",
    }

    ext = None
    data = None

    if body.image_base64:
        matches = re.match(r"^data:image/(\w+);base64,(.+)$", body.image_base64)
        if not matches:
            return fail_response(msg="无效的Base64图片格式")
        img_type = matches.group(1)
        ext = "jpg" if img_type == "jpeg" else img_type
        data = base64.b64decode(matches.group(2))
    elif body.base64 and body.extension:
        ext = body.extension
        data = base64.b64decode(body.base64)
    else:
        return fail_response(msg="参数不完整")

    content_type = _MIME_MAP.get(ext, "application/octet-stream")
    key = cos_client.generate_unique_key("upload", "temp", current_user.id, ext)
    cos_client.upload_object(data, key, content_type=content_type)
    url = cos_client.key_to_url(key)

    return success_response(data={"url": url, "key": key})


# ==================== 场景/道具列表/创建 ====================

@router.get("/locations", summary="获取场景/道具列表", response_model=schemas.GlobalLocationPageMsg)
def get_locations(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission("asset:read")),
    page_params: schemas.GlobalLocationPageParams = Depends(),
) -> Any:
    from app.crud.asset_share_relation_crud import asset_share_relation_crud
    
    owner_user_id = _get_owner_user_id(current_user)
    
    # 获取平台授权的场景ID（按主账号查询，子账号可继承主账号的授权）
    shared_location_ids = asset_share_relation_crud.get_shared_asset_ids(db, owner_user_id, "location")
    
    # 构建查询：owner过滤 OR 授权过滤
    query = crud.global_location_crud.get_queryset(db)
    owner_condition = models.GlobalLocation.owner_user_id == owner_user_id
    
    if shared_location_ids:
        query = query.filter(
            or_(
                owner_condition,
                models.GlobalLocation.id.in_(shared_location_ids)
            )
        )
    else:
        query = query.filter(owner_condition)
    
    query = query.order_by(models.GlobalLocation.create_time.desc())

    # 再应用文件夹过滤（授权资产豁免 user_id 限制）
    query = _apply_folder_filter(query, models.GlobalLocation, current_user, db, shared_ids=shared_location_ids)
    # 平台资产视图：folder_id='platform' 时只看 is_management_asset=True；
    # 其他视图剔除平台资产
    if page_params.folder_id == "platform":
        query = query.filter(models.GlobalLocation.is_management_asset.is_(True))
    else:
        query = query.filter(models.GlobalLocation.is_management_asset.is_(False))
        if page_params.folder_id:
            if page_params.folder_id == "null":
                query = query.filter(models.GlobalLocation.folder_id.is_(None))
            else:
                query = query.filter(models.GlobalLocation.folder_id == page_params.folder_id)
    if page_params.name:
        query = query.filter(models.GlobalLocation.name.like(f"%{page_params.name}%"))
    if page_params.asset_kind:
        query = query.filter(models.GlobalLocation.asset_kind == page_params.asset_kind)
    result = crud.global_location_crud.get_multi(page_params=page_params, query=query)
    locations = result["data"]
    if locations:
        location_ids = [loc.id for loc in locations]
        images_map = crud.global_location_image_crud.get_batch_by_locations(db, location_ids)
        for loc in locations:
            loc_images = images_map.get(loc.id, [])
            loc.images = loc_images
            loc.preview_url = crud.global_location_image_crud.resolve_preview_url(loc_images)
            loc.thumbnail_url = crud.global_location_image_crud.resolve_thumbnail_url(loc_images)
            for img in loc_images:
                _apply_region_volc_id(img, current_user.region)
    return success_response(data=locations, pagination=result["pagination"])


@router.post("/locations", summary="创建场景/道具", response_model=schemas.GlobalLocationMsg)
def create_location(
    location_in: schemas.GlobalLocationCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission("asset:create")),
) -> Any:
    if location_in.art_style and location_in.art_style not in VALID_ART_STYLES:
        return fail_response(msg=f"无效的艺术风格，可选值: {VALID_ART_STYLES}")

    if location_in.folder_id:
        folder = crud.global_asset_folder_crud.get(db=db, id=location_in.folder_id)
        if not folder or folder.user_id != current_user.id:
            return fail_response(msg="文件夹不存在")

    create_data = location_in.model_dump(
        exclude_unset=True,
        exclude=["description", "count"],
    )
    create_data["user_id"] = current_user.id
    create_data["owner_user_id"] = _get_owner_user_id(current_user)
    location = crud.global_location_crud.create(db=db, obj_in=create_data)

    # seed image records
    count = location_in.count or 1
    asset_kind = location_in.asset_kind or "location"
    image_description = (
        (location_in.description or location_in.summary or location_in.name)
        if asset_kind == "prop"
        else (location_in.summary or location_in.name)
    )
    for i in range(count):
        image_data = {
            "id": str(uuid.uuid4()),
            "location_id": location.id,
            "image_index": i,
            "description": image_description,
        }
        crud.global_location_image_crud.create(db=db, obj_in=image_data)

    db.refresh(location)
    return success_response(data=location)


# ==================== 场景/道具详情/更新/删除 ====================

@router.get("/locations/{location_id}", summary="获取场景/道具详情", response_model=schemas.GlobalLocationMsg)
def get_location(
    location_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission("asset:read")),
) -> Any:
    from app.crud.asset_share_relation_crud import asset_share_relation_crud
    
    location = crud.global_location_crud.get(db=db, id=location_id)
    if not location:
        raise HTTPException(status_code=404, detail="场景不存在")
    
    # 权限检查：自己创建的 或 平台授权的（按主账号查询）
    owner_user_id = _get_owner_user_id(current_user)
    is_owner = location.user_id == current_user.id
    is_shared = asset_share_relation_crud.is_shared_to_user(db, location_id, owner_user_id)
    
    if not is_owner and not is_shared:
        raise HTTPException(status_code=404, detail="场景不存在")

    images = crud.global_location_image_crud.get_by_location(db, location_id).all()
    return success_response(data={
        "location": location,
        "images": images,
    })


@router.put("/locations/{location_id}", summary="更新场景/道具", response_model=schemas.GlobalLocationMsg)
def update_location(
    location_id: str,
    location_in: schemas.GlobalLocationUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission("asset:update")),
) -> Any:
    location = crud.global_location_crud.get(db=db, id=location_id)
    if not location or location.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权操作")
    
    # 禁止修改平台资产
    if location.is_management_asset:
        raise HTTPException(status_code=403, detail="平台资产不允许修改")

    if location_in.folder_id is not None and location_in.folder_id:
        owner_user_id = _get_owner_user_id(current_user)
        folder = crud.global_asset_folder_crud.get(db=db, id=location_in.folder_id)
        if not folder or folder.user_id != current_user.id:
            return fail_response(msg="文件夹不存在或无权访问")

    location = crud.global_location_crud.update(db=db, db_obj=location, obj_in=location_in)
    return success_response(data=location)


@router.delete("/locations/{location_id}", summary="删除场景/道具", response_model=schemas.Msg)
def delete_location(
    location_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission("asset:delete")),
) -> Any:
    location = crud.global_location_crud.get(db=db, id=location_id)
    if not location or location.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权操作")
    
    # 禁止删除平台资产
    if location.is_management_asset:
        raise HTTPException(status_code=403, detail="平台资产不允许删除")

    images = crud.global_location_image_crud.get_by_location(db, location_id).all()
    for img in images:
        crud.global_location_image_crud.remove(db, img.id)

    crud.global_location_crud.remove(db, location_id)
    return success_response()


# ==================== 场景图片列表/创建 ====================

@router.get("/location-images", summary="获取场景图片列表", response_model=schemas.GlobalLocationImagePageMsg)
def get_location_images(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission("asset:read")),
    page_params: schemas.GlobalLocationImagePageParams = Depends(),
) -> Any:
    if not page_params.location_id:
        return fail_response(msg="请指定场景ID")

    location = crud.global_location_crud.get(db=db, id=page_params.location_id)
    if not location or location.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="场景不存在")

    query = crud.global_location_image_crud.get_by_location(db, page_params.location_id)

    if page_params.is_paginate is False:
        images = query.all()
        return success_response(data=images)

    result = crud.global_location_image_crud.get_multi(page_params=page_params, query=query)
    return success_response(data=result["data"], pagination=result["pagination"])


@router.post("/location-images", summary="创建场景图片", response_model=schemas.GlobalLocationImageMsg)
def create_location_image(
    image_in: schemas.GlobalLocationImageCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission("asset:create")),
) -> Any:
    location = crud.global_location_crud.get(db=db, id=image_in.location_id)
    if not location or location.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="场景不存在")

    image_data = image_in.model_dump()
    image = crud.global_location_image_crud.create(db=db, obj_in=image_data)
    return success_response(data=image)


@router.put("/location-images/{image_id}", summary="更新场景图片", response_model=schemas.GlobalLocationImageMsg)
def update_location_image(
    image_id: str,
    image_in: schemas.GlobalLocationImageUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission("asset:update")),
) -> Any:
    image = crud.global_location_image_crud.get(db=db, id=image_id)
    if not image:
        raise HTTPException(status_code=404, detail="图片不存在")

    location = crud.global_location_crud.get(db=db, id=image.location_id)
    if not location or location.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权操作")

    # 禁止修改平台资产
    if location.is_management_asset:
        raise HTTPException(status_code=403, detail="平台资产不允许修改")

    image = crud.global_location_image_crud.update(db=db, db_obj=image, obj_in=image_in)
    return success_response(data=image)


@router.delete("/location-images/{image_id}", summary="删除场景图片", response_model=schemas.Msg)
def delete_location_image(
    image_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission("asset:delete")),
) -> Any:
    image = crud.global_location_image_crud.get(db=db, id=image_id)
    if not image:
        raise HTTPException(status_code=404, detail="图片不存在")

    location = crud.global_location_crud.get(db=db, id=image.location_id)
    if not location or location.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权操作")

    crud.global_location_image_crud.remove(db, image_id)
    return success_response()


# ==================== 打包下载 ====================

_FILENAME_RE = re.compile(r'[/\\:*?"<>|]')


def _sanitize(name: str) -> str:
    return _FILENAME_RE.sub('_', name).strip() or 'unnamed'


def _fetch_image_bytes(url_or_key: str) -> bytes | None:
    if not url_or_key:
        return None
    try:
        url = cos_client.key_to_url(url_or_key) if not url_or_key.startswith('http') else url_or_key
        resp = httpx.get(url, timeout=30)
        return resp.content if resp.status_code == 200 else None
    except Exception:
        return None


@router.get("/download", summary="打包下载资产图片")
def download_assets(
    folder_id: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission("asset:read")),
):
    owner_user_id = _get_owner_user_id(current_user)

    # 查询全部角色
    char_query = crud.global_character_crud.get_by_owner(db, current_user.id, owner_user_id)
    char_query = _apply_folder_filter(char_query, models.GlobalCharacter, current_user, db)
    if folder_id:
        if folder_id == "null":
            char_query = char_query.filter(models.GlobalCharacter.folder_id.is_(None))
        else:
            char_query = char_query.filter(models.GlobalCharacter.folder_id == folder_id)
    characters = char_query.all()

    # 查询全部场景/道具
    loc_query = crud.global_location_crud.get_by_owner(db, owner_user_id)
    loc_query = _apply_folder_filter(loc_query, models.GlobalLocation, current_user, db)
    if folder_id:
        if folder_id == "null":
            loc_query = loc_query.filter(models.GlobalLocation.folder_id.is_(None))
        else:
            loc_query = loc_query.filter(models.GlobalLocation.folder_id == folder_id)
    locations = loc_query.all()

    # 批量获取子数据
    char_apps_map = {}
    if characters:
        char_apps_map = crud.global_character_appearance_crud.get_batch_by_characters(db, [c.id for c in characters])

    loc_imgs_map = {}
    if locations:
        loc_imgs_map = crud.global_location_image_crud.get_batch_by_locations(db, [l.id for l in locations])

    # 构建 ZIP
    buffer = io.BytesIO()
    has_file = False

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        # 角色
        for char in characters:
            apps = char_apps_map.get(char.id, [])
            if not apps:
                continue
            multi = len(apps) > 1
            for i, app in enumerate(apps):
                if not app.image_url:
                    continue
                data = _fetch_image_bytes(app.image_url)
                if not data:
                    continue
                name = _sanitize(char.name)
                fname = f"characters/{name}_appearance{i}.jpg" if multi else f"characters/{name}.jpg"
                zf.writestr(fname, data)
                has_file = True

        # 场景
        for loc in locations:
            if loc.asset_kind == 'prop':
                continue
            imgs = loc_imgs_map.get(loc.id, [])
            if not imgs:
                continue
            multi = len(imgs) > 1
            for i, img in enumerate(imgs):
                if not img.image_url:
                    continue
                data = _fetch_image_bytes(img.image_url)
                if not data:
                    continue
                name = _sanitize(loc.name)
                fname = f"locations/{name}_{i + 1}.jpg" if multi else f"locations/{name}.jpg"
                zf.writestr(fname, data)
                has_file = True

        # 道具
        for prop in locations:
            if prop.asset_kind != 'prop':
                continue
            imgs = loc_imgs_map.get(prop.id, [])
            if not imgs:
                continue
            multi = len(imgs) > 1
            for i, img in enumerate(imgs):
                if not img.image_url:
                    continue
                data = _fetch_image_bytes(img.image_url)
                if not data:
                    continue
                name = _sanitize(prop.name)
                fname = f"props/{name}_{i + 1}.jpg" if multi else f"props/{name}.jpg"
                zf.writestr(fname, data)
                has_file = True

    if not has_file:
        raise HTTPException(status_code=404, detail="没有可下载的图片")

    buffer.seek(0)
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    filename = f"asset-hub_{date_str}.zip"

    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
