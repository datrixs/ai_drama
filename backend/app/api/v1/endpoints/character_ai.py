import hashlib
import json
import time
from typing import Any

from app.core.logging import logger

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app import crud, models
from app.api.deps import get_db, get_current_user
from app.core.response import success_response, fail_response
from app.deps.permission_deps import require_permission
from app.schemas.asset import GenerateImageRequest
from app.services import task as task_service
from app.services.config_reader import ConfigReader
from app.services.image_processor import normalize_image_urls
from app.enums import TaskType, TaskStatus
from app.utils.tencent_cos_utils import cos_client


router = APIRouter()


def _resolve_ai_config(db: Session, user_id: str):
    return ConfigReader(db).get_config(str(user_id))


@router.post("/ai-design-character", summary="AI 设计角色描述")
def ai_design_character(
    body: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission("asset:create")),
) -> Any:
    user_instruction = body.get("user_instruction", "").strip()
    if not user_instruction:
        return fail_response(msg="用户描述不能为空")

    resolved = _resolve_ai_config(db, current_user.id)

    digest = hashlib.sha1(f"{current_user.id}:character:{user_instruction}".encode()).hexdigest()[:16]
    dedupe_key = f"ai_design_character:{digest}"

    result = task_service.submit_task(
        task_type=TaskType.ASSET_HUB_AI_DESIGN_CHARACTER,
        user_id=current_user.id,
        payload={
            "user_instruction": user_instruction,
            "config_snapshot": resolved.to_dict(),
        },
        dedupe_key=dedupe_key,
    )
    return success_response(data=result)


@router.post("/ai-modify-character", summary="AI 修改角色描述")
def ai_modify_character(
    body: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission("asset:update")),
) -> Any:
    character_id = body.get("character_id", "")
    appearance_index = body.get("appearance_index", 0)
    current_description = body.get("current_description", "").strip()
    modify_instruction = body.get("modify_instruction", "").strip()

    if not all([character_id, current_description, modify_instruction]):
        return fail_response(msg="参数不完整")

    character = crud.global_character_crud.get(db=db, id=character_id)
    if not character or character.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="角色不存在")

    resolved = _resolve_ai_config(db, current_user.id)

    dedupe_key = f"ai_modify_character:{character_id}:{appearance_index}"

    result = task_service.submit_task(
        task_type=TaskType.ASSET_HUB_AI_MODIFY_CHARACTER,
        user_id=current_user.id,
        payload={
            "character_id": character_id,
            "appearance_index": appearance_index,
            "current_description": current_description,
            "modify_instruction": modify_instruction,
            "config_snapshot": resolved.to_dict(),
        },
        target_type="GlobalCharacter",
        target_id=character_id,
        dedupe_key=dedupe_key,
    )
    return success_response(data=result)


@router.post("/reference-to-character", summary="参考图生成角色")
def reference_to_character(
    body: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission("asset:create")),
) -> Any:
    reference_image_urls = body.get("reference_image_urls", [])
    if isinstance(reference_image_urls, str):
        reference_image_urls = [reference_image_urls]
    reference_image_urls = reference_image_urls[:5]

    if not reference_image_urls:
        return fail_response(msg="至少需要1张参考图")

    reference_image_urls = normalize_image_urls(
        reference_image_urls,
        user_id=str(current_user.id), biz="ref-to-character",
    )

    character_id = body.get("character_id")
    appearance_id = body.get("appearance_id")
    is_background_job = body.get("is_background_job", False)

    if is_background_job and (not character_id or not appearance_id):
        return fail_response(msg="后台任务需要 character_id 和 appearance_id")

    resolved = _resolve_ai_config(db, current_user.id)

    if appearance_id:
        from app.core.ws import ws_manager
        ws_manager.publish_asset_hub_event(
            user_id=current_user.id,
            event_type="asset_hub_generation_started",
            data={"target_type": "appearance", "target_id": appearance_id, "asset_type": "character", "action_type": "reference"},
        )

    dedupe_key = f"reference_to_character:{appearance_id or character_id or current_user.id}"

    result = task_service.submit_task(
        task_type=TaskType.ASSET_HUB_REFERENCE_TO_CHARACTER,
        user_id=current_user.id,
        payload={
            "reference_image_urls": reference_image_urls,
            "character_id": character_id,
            "appearance_id": appearance_id,
            "is_background_job": is_background_job,
            "art_style": body.get("art_style", ""),
            "custom_description": body.get("custom_description", ""),
            "extract_only": body.get("extract_only", False),
            "count": body.get("count", 3),
            "config_snapshot": resolved.to_dict(),
        },
        target_type="GlobalCharacterAppearance" if appearance_id else "GlobalCharacter",
        target_id=appearance_id or character_id or current_user.id,
        dedupe_key=dedupe_key,
    )
    return success_response(data=result)


@router.post("/generate-image", summary="生成图片")
def generate_image(
    body: GenerateImageRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission("asset:create")),
) -> Any:
    asset_type = body.type.value
    asset_id = body.id

    if asset_type == "character":
        asset = crud.global_character_crud.get(id=asset_id, db=db)
        if not asset or asset.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="角色不存在")
        target_type = "GlobalCharacter"
    else:
        asset = crud.global_location_crud.get(id=asset_id, db=db)
        if not asset or asset.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="场景/道具不存在")
        target_type = "GlobalLocation"

    resolved = _resolve_ai_config(db, current_user.id)

    config_dict = resolved.to_dict()
    logger.debug(f"[API/generate-image] 入口: user_id={current_user.id} asset_type={asset_type} asset_id={asset_id} config_user_id={config_dict.get('user_id')}")

    from app.core.ws import ws_manager

    if asset_type == "character":
        appearance = crud.global_character_appearance_crud.get_by_character_and_index(db, asset_id, body.appearance_index)
        if appearance:
            ws_manager.publish_asset_hub_event(
                user_id=current_user.id,
                event_type="asset_hub_generation_started",
                data={"target_type": "appearance", "target_id": appearance.id, "asset_type": "character", "action_type": "generate"},
            )
    else:
        from app.models.asset import GlobalLocationImage
        images = db.query(GlobalLocationImage).filter(
            GlobalLocationImage.location_id == asset_id,
            GlobalLocationImage.is_deleted == False,
        ).order_by(GlobalLocationImage.image_index).all()

        if images and images[0].image_url:
            # 重新生成：按 image_index 定位单条记录
            target_img = next((img for img in images if img.image_index == body.image_index), images[0])
            target_img.gen_status = "generating"
            db.commit()
            ws_manager.publish_asset_hub_event(
                user_id=current_user.id,
                event_type="asset_hub_generation_started",
                data={"target_type": "location_image", "target_id": target_img.id, "asset_type": asset_type, "action_type": "generate"},
            )
        else:
            # 首次生成：批量推送前 N 条
            for img in images[:body.count]:
                img.gen_status = "generating"
            db.commit()
            for img in images[:body.count]:
                ws_manager.publish_asset_hub_event(
                    user_id=current_user.id,
                    event_type="asset_hub_generation_started",
                    data={"target_type": "location_image", "target_id": img.id, "asset_type": asset_type, "action_type": "generate"},
                )

    result = task_service.submit_task(
        task_type=TaskType.ASSET_HUB_IMAGE,
        user_id=current_user.id,
        payload={
            "type": asset_type,
            "id": asset_id,
            "appearance_index": body.appearance_index,
            "image_index": body.image_index,
            "count": body.count,
            "art_style": body.art_style,
            "config_snapshot": resolved.to_dict(),
        },
        target_type=target_type,
        target_id=asset_id,
    )
    return success_response(data=result)


@router.post("/modify-image", summary="修改图片")
def modify_image(
    body: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission("asset:update")),
) -> Any:
    asset_id = body.get("id", "")
    modify_prompt = body.get("modify_prompt", "").strip()
    asset_type = body.get("type", "character")

    if not asset_id or not modify_prompt:
        return fail_response(msg="参数不完整")

    if asset_type == "character":
        asset = crud.global_character_crud.get(db=db, id=asset_id)
        if not asset or asset.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="角色不存在")
        target_type = "GlobalCharacterAppearance"
    else:
        asset = crud.global_location_crud.get(db=db, id=asset_id)
        if not asset or asset.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="场景/道具不存在")
        target_type = "GlobalLocation"

    resolved = _resolve_ai_config(db, current_user.id)

    from app.core.ws import ws_manager

    if asset_type == "character":
        appearance = crud.global_character_appearance_crud.get_by_character_and_index(db, asset_id, body.get("appearance_index", 0))
        if appearance:
            ws_manager.publish_asset_hub_event(
                user_id=current_user.id,
                event_type="asset_hub_generation_started",
                data={"target_type": "appearance", "target_id": appearance.id, "asset_type": "character", "action_type": "modify"},
            )
    else:
        from app.models.asset import GlobalLocationImage
        loc_image = db.query(GlobalLocationImage).filter(
            GlobalLocationImage.location_id == asset_id,
            GlobalLocationImage.image_index == body.get("image_index", 0),
            GlobalLocationImage.is_deleted == False,
        ).first()
        if loc_image:
            ws_manager.publish_asset_hub_event(
                user_id=current_user.id,
                event_type="asset_hub_generation_started",
                data={"target_type": "location_image", "target_id": loc_image.id, "asset_type": asset_type, "action_type": "modify"},
            )

    result = task_service.submit_task(
        task_type=TaskType.ASSET_HUB_MODIFY,
        user_id=current_user.id,
        payload={
            "id": asset_id,
            "type": asset_type,
            "appearance_index": body.get("appearance_index", 0),
            "image_index": body.get("image_index", 0),
            "modify_prompt": modify_prompt,
            "extra_image_urls": normalize_image_urls(
                body.get("extra_image_urls", []),
                user_id=str(current_user.id), biz="global-modify",
            ),
            "config_snapshot": resolved.to_dict(),
        },
        target_type=target_type,
        target_id=asset_id,
    )
    return success_response(data=result)


# ==================== 场景/道具 AI 端点 ====================

@router.post("/ai-design-location", summary="AI 设计场景描述")
def ai_design_location(
    body: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission("asset:create")),
) -> Any:
    user_instruction = body.get("user_instruction", "").strip()
    if not user_instruction:
        return fail_response(msg="用户描述不能为空")

    resolved = _resolve_ai_config(db, current_user.id)

    digest = hashlib.sha1(f"{current_user.id}:location:{user_instruction}".encode()).hexdigest()[:16]
    dedupe_key = f"ai_design_location:{digest}"

    result = task_service.submit_task(
        task_type=TaskType.ASSET_HUB_AI_DESIGN_LOCATION,
        user_id=current_user.id,
        payload={
            "user_instruction": user_instruction,
            "config_snapshot": resolved.to_dict(),
        },
        dedupe_key=dedupe_key,
    )
    return success_response(data=result)


@router.post("/ai-modify-location", summary="AI 修改场景描述")
def ai_modify_location(
    body: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission("asset:update")),
) -> Any:
    location_id = body.get("location_id", "")
    image_index = body.get("image_index", 0)
    current_description = body.get("current_description", "").strip()
    modify_instruction = body.get("modify_instruction", "").strip()

    if not all([location_id, modify_instruction]):
        return fail_response(msg="参数不完整")

    location = crud.global_location_crud.get(db=db, id=location_id)
    if not location or location.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="场景不存在")

    resolved = _resolve_ai_config(db, current_user.id)

    dedupe_key = f"ai_modify_location:{location_id}:{image_index}"

    result = task_service.submit_task(
        task_type=TaskType.ASSET_HUB_AI_MODIFY_LOCATION,
        user_id=current_user.id,
        payload={
            "location_id": location_id,
            "location_name": location.name,
            "image_index": image_index,
            "current_description": current_description,
            "modify_instruction": modify_instruction,
            "config_snapshot": resolved.to_dict(),
        },
        target_type="GlobalLocation",
        target_id=location_id,
        dedupe_key=dedupe_key,
    )
    return success_response(data=result)


@router.post("/ai-modify-prop", summary="AI 修改道具描述")
def ai_modify_prop(
    body: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission("asset:update")),
) -> Any:
    prop_id = body.get("prop_id", "")
    image_index = body.get("image_index", 0)
    current_description = body.get("current_description", "").strip()
    modify_instruction = body.get("modify_instruction", "").strip()

    if not all([prop_id, modify_instruction]):
        return fail_response(msg="参数不完整")

    prop = crud.global_location_crud.get(db=db, id=prop_id)
    if not prop or prop.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="道具不存在")

    resolved = _resolve_ai_config(db, current_user.id)

    dedupe_key = f"ai_modify_prop:{prop_id}:{image_index}"

    result = task_service.submit_task(
        task_type=TaskType.ASSET_HUB_AI_MODIFY_PROP,
        user_id=current_user.id,
        payload={
            "prop_id": prop_id,
            "prop_name": prop.name,
            "image_index": image_index,
            "current_description": current_description,
            "modify_instruction": modify_instruction,
            "config_snapshot": resolved.to_dict(),
        },
        target_type="GlobalLocation",
        target_id=prop_id,
        dedupe_key=dedupe_key,
    )
    return success_response(data=result)


@router.post("/undo-location-image", summary="撤回场景/道具图片")
def undo_location_image(
    body: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission("asset:update")),
) -> Any:
    location_id = body.get("location_id", "")
    image_index = body.get("image_index", 0)

    if not location_id:
        return fail_response(msg="参数不完整")

    location = crud.global_location_crud.get(db=db, id=location_id)
    if not location or location.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="场景/道具不存在")

    from app.models.asset import GlobalLocationImage

    loc_image = db.query(GlobalLocationImage).filter(
        GlobalLocationImage.location_id == location_id,
        GlobalLocationImage.image_index == image_index,
        GlobalLocationImage.is_deleted == False,
    ).first()
    if not loc_image:
        return fail_response(msg="图片不存在")

    if not loc_image.previous_image_url:
        return fail_response(msg="没有可撤回的图片")

    from app.core.ws import ws_manager
    ws_manager.publish_asset_hub_event(
        user_id=current_user.id,
        event_type="asset_hub_generation_started",
        data={"target_type": "location_image", "target_id": loc_image.id, "asset_type": location.asset_kind or "location", "action_type": "undo"},
    )

    loc_image.image_url, loc_image.previous_image_url = loc_image.previous_image_url, None
    # 同步交换缩略图
    if loc_image.previous_thumbnail_url:
        loc_image.thumbnail_url, loc_image.previous_thumbnail_url = loc_image.previous_thumbnail_url, None
    if loc_image.previous_description:
        loc_image.description, loc_image.previous_description = loc_image.previous_description, None
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
            "image_url": cos_client.key_to_url(loc_image.image_url) if loc_image.image_url else "",
            "thumbnail_url": cos_client.key_to_url(loc_image.thumbnail_url) if loc_image.thumbnail_url else None,
        },
    )

    return success_response(data={"image_url": loc_image.image_url})


# ==================== 任务状态查询 ====================

@router.get("/tasks/{task_id}", summary="查询任务状态")
def get_task_status(task_id: str) -> Any:
    task = task_service.get_task(task_id)
    if not task:
        return fail_response(msg="任务不存在")
    return success_response(data=task)


# ==================== SSE 任务进度推送 ====================

@router.get("/tasks/{task_id}/stream", summary="SSE 任务进度流")
def task_stream(task_id: str):
    def event_generator():
        while True:
            task = task_service.get_task(task_id)
            if not task:
                yield f"data: {json.dumps({'error': 'task not found'})}\n\n"
                break
            yield f"data: {json.dumps(task)}\n\n"
            if task["status"] in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELED):
                break
            time.sleep(1.5)
    return StreamingResponse(event_generator(), media_type="text/event-stream")
