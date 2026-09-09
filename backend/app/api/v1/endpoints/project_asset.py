"""
项目资产库 API 端点
"""
import io
import datetime
import traceback

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.core.logging import logger
from app.core.ws import ws_manager
from app.crud.project_asset_crud import project_asset_crud
from app.crud.project_crud import project as project_crud
from app.crud.project_analyze_crud import analysis_result as ar_crud, analysis_version as av_crud
from app.enums.user import UserRegion
from app.utils.region import apply_region_volc_id
from app.models.project_asset import ProjectCharacter, ProjectLocation, ProjectProp
from app.models.project import Project
from app.models.user import User
from app.schemas.project_asset import (
    ProjectAssetTypeEnum,
    ProjectCharacterResponse,
    ProjectLocationResponse,
    ProjectPropResponse,
    ProjectAssetStatsResponse,
    ProjectAssetListResponse,
    ProjectAssetParseResponse,
    ProjectCharacterUpdateRequest,
    ProjectLocationUpdateRequest,
    ProjectPropUpdateRequest,
    ProjectCharacterCreateRequest,
    ProjectLocationCreateRequest,
    ProjectPropCreateRequest,
    ProjectAssetModifyImageRequest,
    ProjectAssetReferenceGenerateRequest,
    ProjectAssetExtractDescriptionRequest,
    ProjectAssetAiModifyDescriptionRequest,
    CopyFromGlobalRequest,
)
from app.services.config_reader import ConfigReader
from app.services.image_processor import normalize_image_urls, process_to_jpeg
from app.utils.tencent_cos_utils import cos_client
from app.utils.thumbnail import upload_thumbnail
from app.utils.response import success_response

router = APIRouter()

ASSET_MODEL_MAP = {
    "character": ProjectCharacter,
    "location": ProjectLocation,
    "prop": ProjectProp,
}

UPDATE_SCHEMA_MAP = {
    "character": ProjectCharacterUpdateRequest,
    "location": ProjectLocationUpdateRequest,
    "prop": ProjectPropUpdateRequest,
}


def _get_project(db, project_id, user) -> Project:
    proj = project_crud.get(id=project_id, db=db)
    if not proj or proj.is_deleted:
        raise HTTPException(status_code=404, detail="项目不存在")
    if proj.user_id != user.id:
        raise HTTPException(status_code=403, detail="无权访问该项目")
    return proj


def _get_asset(db, asset_type, asset_id, project_id):
    model_class = ASSET_MODEL_MAP.get(asset_type)
    if not model_class:
        raise HTTPException(status_code=400, detail=f"无效的资产类型: {asset_type}")
    asset = db.query(model_class).filter(
        model_class.id == asset_id,
        model_class.is_deleted == False,
    ).first()
    if not asset:
        raise HTTPException(status_code=404, detail="资产不存在")
    if str(asset.project_id) != str(project_id):
        raise HTTPException(status_code=400, detail="资产不属于该项目")
    return asset


def _resolve_config(db, user, project) -> dict:
    reader = ConfigReader(db)
    resolved = reader.get_project_config(str(user.id), project.config)
    return resolved.to_dict()


# ============ 1. 解析资产 ============

@router.post("/{project_id}/assets/parse")
def parse_assets(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """从分析结果解析创建资产、剧集、分镜记录"""
    proj = _get_project(db, project_id, current_user)
    if proj.status not in ("projectCreated", "storyReady"):
        raise HTTPException(status_code=400, detail="当前状态不允许解析资产")

    result = ar_crud.get_by_project(db, proj.id)
    if not result:
        raise HTTPException(status_code=400, detail="分析结果不存在")

    current_ver = av_crud.get_current_version(db, result.id)
    if not current_ver:
        raise HTTPException(status_code=400, detail="无可用分析版本")

    counts = project_asset_crud.parse_from_analysis(
        db, proj.id, current_ver, str(current_user.id),
    )

    ws_manager.publish_project_event(
        str(current_user.id), proj.id, "project_asset_parse_completed",
        {
            "characters_count": counts.get("characters", 0),
            "locations_count": counts.get("locations", 0),
            "props_count": counts.get("props", 0),
        },
    )

    data = ProjectAssetParseResponse(
        characters_count=counts.get("characters", 0),
        locations_count=counts.get("locations", 0),
        props_count=counts.get("props", 0),
        episodes_count=counts.get("episodes", 0),
        storyboards_count=counts.get("storyboards", 0),
    )
    return success_response(data=data)


# ============ 2. 获取项目全部资产 ============

@router.get("/{project_id}/assets")
def get_assets(
    project_id: str,
    type: str = Query("all", description="筛选类型: all/character/location/prop"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取项目资产列表"""
    _get_project(db, project_id, current_user)

    characters, locations, props = [], [], []
    if type in ("all", "character"):
        rows = project_asset_crud.get_by_project(db, project_id, ProjectCharacter)
        for r in rows:
            apply_region_volc_id(r, current_user.region)
        characters = [ProjectCharacterResponse.model_validate(r) for r in rows]
    if type in ("all", "location"):
        rows = project_asset_crud.get_by_project(db, project_id, ProjectLocation)
        for r in rows:
            apply_region_volc_id(r, current_user.region)
        locations = [ProjectLocationResponse.model_validate(r) for r in rows]
    if type in ("all", "prop"):
        rows = project_asset_crud.get_by_project(db, project_id, ProjectProp)
        for r in rows:
            apply_region_volc_id(r, current_user.region)
        props = [ProjectPropResponse.model_validate(r) for r in rows]

    stats_dict = project_asset_crud.compute_stats(db, project_id)
    all_ready = project_asset_crud.check_all_ready(db, project_id)

    data = ProjectAssetListResponse(
        characters=characters,
        locations=locations,
        props=props,
        all_ready=all_ready,
        stats=ProjectAssetStatsResponse(**stats_dict),
    )
    return success_response(data=data)


# ============ 3. 生成单个资产图片 ============

@router.post("/{project_id}/assets/{asset_type}/{asset_id}/generate")
def generate_asset_image(
    project_id: str,
    asset_type: str,
    asset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """生成单个资产图片"""
    proj = _get_project(db, project_id, current_user)
    asset = _get_asset(db, asset_type, asset_id, project_id)

    if asset.gen_status == "generating":
        raise HTTPException(status_code=400, detail="资产正在生成中")

    config_dict = _resolve_config(db, current_user, proj)
    art_style = proj.config.get("art_style", "realistic") if proj.config else "realistic"

    project_asset_crud.update_gen_status(db, asset, "generating")
    ws_manager.publish_project_event(
        current_user.id, project_id, "project_asset_generation_started",
        {"asset_id": asset_id, "asset_type": asset_type},
    )

    try:
        from app.celery_tasks.project_asset_image import generate_project_asset_image
        task = generate_project_asset_image.delay(
            project_id=project_id,
            asset_type=asset_type,
            asset_id=asset_id,
            model_config=config_dict,
            art_style=art_style,
        )
    except Exception:
        print(traceback.format_exc())
        project_asset_crud.update_gen_status(db, asset, "pending")
        raise HTTPException(status_code=500, detail="任务提交失败，请稍后重试")

    return success_response(data={
        "task_id": task.id,
        "asset_id": asset_id,
        "asset_type": asset_type,
        "gen_status": "generating",
    })


# ============ 4. 批量生成 ============

@router.post("/{project_id}/assets/batch_generate")
def batch_generate(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """批量生成所有未完成资产的图片"""
    proj = _get_project(db, project_id, current_user)

    pending = project_asset_crud.get_all_pending(db, project_id)
    if not pending:
        return success_response(data={"total": 0, "submitted": 0})

    config_dict = _resolve_config(db, current_user, proj)
    art_style = proj.config.get("art_style", "realistic") if proj.config else "realistic"

    # 更新所有为 generating
    for item in pending:
        asset = _get_asset(db, item["type"], item["id"], project_id)
        project_asset_crud.update_gen_status(db, asset, "generating")
        ws_manager.publish_project_event(
            current_user.id, project_id, "project_asset_generation_started",
            {"asset_id": item["id"], "asset_type": item["type"]},
        )

    try:
        from app.celery_tasks.project_asset_image import batch_generate_project_assets
        task = batch_generate_project_assets.delay(
            project_id=project_id,
            asset_ids=pending,
            model_config=config_dict,
            art_style=art_style,
        )
    except Exception:
        for item in pending:
            try:
                asset = _get_asset(db, item["type"], item["id"], project_id)
                if asset:
                    project_asset_crud.update_gen_status(db, asset, "pending")
            except Exception:
                pass
        raise HTTPException(status_code=500, detail="任务提交失败，请稍后重试")

    return success_response(data={
        "total": len(pending),
        "submitted": len(pending),
        "task_id": task.id,
    })


# ============ 5. 更新资产 ============

@router.put("/{project_id}/assets/{asset_type}/{asset_id}")
def update_asset(
    project_id: str,
    asset_type: str,
    asset_id: str,
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新资产信息"""
    _get_project(db, project_id, current_user)
    asset = _get_asset(db, asset_type, asset_id, project_id)

    allowed_fields = {"name", "description", "image_model_system_prompt"}
    if asset_type == "character":
        allowed_fields.update({"aliases", "voice_id", "voice_type", "custom_voice_url", "profile_data"})
    elif asset_type == "location":
        allowed_fields.update({"place", "time"})
    elif asset_type == "prop":
        allowed_fields.add("aliases")

    for key in allowed_fields:
        if key in body and body[key] is not None:
            value = body[key]
            if key == "custom_voice_url":
                value = cos_client.presigned_url_to_key(value)
            setattr(asset, key, value)

    asset.update_uid = current_user.id
    db.add(asset)
    db.commit()
    db.refresh(asset)

    model_class = ASSET_MODEL_MAP[asset_type]
    response_model = {
        "character": ProjectCharacterResponse,
        "location": ProjectLocationResponse,
        "prop": ProjectPropResponse,
    }[asset_type]

    apply_region_volc_id(asset, current_user.region)
    return success_response(data=response_model.model_validate(asset))


# ============ 5.5 角色音色上传 ============

@router.post("/{project_id}/assets/characters/{asset_id}/upload_voice")
async def upload_character_voice(
    project_id: str,
    asset_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """上传项目角色语音文件"""
    _get_project(db, project_id, current_user)
    asset = _get_asset(db, "character", asset_id, project_id)

    allowed_types = {"audio/mpeg", "audio/mp3", "audio/wav", "audio/ogg", "audio/m4a", "audio/x-m4a", "audio/aac"}
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="不支持的音频格式，支持 MP3、WAV、OGG、M4A、AAC")

    content = await file.read()
    ext = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "mp3"
    key = cos_client.generate_unique_key("upload", "project-voice", current_user.id, ext)
    cos_client.upload_object(content, key, content_type=file.content_type)

    asset.voice_type = "uploaded"
    asset.voice_id = None
    asset.custom_voice_url = key
    asset.update_uid = current_user.id
    db.add(asset)
    db.commit()
    db.refresh(asset)

    apply_region_volc_id(asset, current_user.region)
    return success_response(data=ProjectCharacterResponse.model_validate(asset))


# ============ 6. 删除资产 ============

@router.delete("/{project_id}/assets/{asset_type}/{asset_id}")
def delete_asset(
    project_id: str,
    asset_type: str,
    asset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """软删除资产"""
    _get_project(db, project_id, current_user)
    asset = _get_asset(db, asset_type, asset_id, project_id)
    project_asset_crud.soft_delete(db, asset)
    return success_response(data={"id": asset_id})


# ============ 7. 上传图片 ============

@router.post("/{project_id}/assets/{asset_type}/{asset_id}/upload_image")
def upload_asset_image(
    project_id: str,
    asset_type: str,
    asset_id: str,
    cos_key: str = Form(None),
    thumbnail_cos_key: str = Form(None),
    file: UploadFile = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """上传图片替换资产图片"""
    _get_project(db, project_id, current_user)
    asset = _get_asset(db, asset_type, asset_id, project_id)

    processed = None
    if cos_key:
        # 新模式：前端已直传 COS
        key = cos_key
    elif file:
        # 旧模式：文件中转（向后兼容）
        content = file.file.read()
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="文件大小超过 10MB 限制")

        processed = process_to_jpeg(content)
        key = cos_client.generate_unique_key("upload", f"project-{asset_type}", current_user.id, "jpg")
        cos_client.upload_object(processed, key)
    else:
        raise HTTPException(status_code=400, detail="请提供 file 或 cos_key")

    # 生成并上传缩略图：优先用前端直传的 key；否则回拉原图生成（向后兼容）
    if thumbnail_cos_key:
        thumb_key = thumbnail_cos_key
    elif processed is not None:
        thumb_key = upload_thumbnail(processed, key)
    else:
        thumb_key = upload_thumbnail(cos_client.download_object_as_bytes(key), key)

    project_asset_crud.update_image(db, asset, key, thumb_key)

    from app.utils.volc_sync import sync_asset_to_volc
    sync_error = None
    try:
        sync_asset_to_volc(
            db, project_id, asset, asset_type,
            user_id=str(current_user.id), raise_on_error=True,
        )
    except Exception as e:
        logger.warning(f"火山/BytePlus 同步失败: project_id={project_id}, asset_id={asset_id}, error={e}")
        sync_error = f"「{asset.name or ''}」{e}"

    # 按用户区域返回资产 ID（前端用此字段判断是否已同步）
    asset_id_field = "byteplus_asset_id" if current_user.region == UserRegion.OVERSEAS else "volc_private_asset_id"
    return success_response(data={
        "image_url": cos_client.key_to_url(key),
        "thumbnail_url": cos_client.key_to_url(thumb_key) if thumb_key else None,
        "asset_id": asset_id,
        "volc_private_asset_id": getattr(asset, asset_id_field, None),
        "sync_error": sync_error,
    })


# ============ 8. AI 修图 ============

@router.post("/{project_id}/assets/{asset_type}/{asset_id}/modify_image")
def modify_asset_image(
    project_id: str,
    asset_type: str,
    asset_id: str,
    body: ProjectAssetModifyImageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """AI 修图"""
    proj = _get_project(db, project_id, current_user)
    asset = _get_asset(db, asset_type, asset_id, project_id)

    if not asset.image_url:
        raise HTTPException(status_code=400, detail="资产无图片，无法修图")

    config_dict = _resolve_config(db, current_user, proj)
    art_style = proj.config.get("art_style", "realistic") if proj.config else "realistic"

    project_asset_crud.update_gen_status(db, asset, "generating")
    ws_manager.publish_project_event(
        current_user.id, project_id, "project_asset_generation_started",
        {"asset_id": asset_id, "asset_type": asset_type},
    )

    try:
        from app.celery_tasks.project_asset_image import modify_project_asset_image
        task = modify_project_asset_image.delay(
        project_id=project_id,
        asset_type=asset_type,
        asset_id=asset_id,
        modify_prompt=body.modify_prompt,
        extra_image_urls=normalize_image_urls(
            body.extra_image_urls,
            user_id=str(current_user.id), biz="asset-modify",
        ),
        model_config=config_dict,
        art_style=art_style,
    )
    except Exception:
        project_asset_crud.update_gen_status(db, asset, "pending")
        raise HTTPException(status_code=500, detail="任务提交失败，请稍后重试")

    return success_response(data={"task_id": task.id, "asset_id": asset_id})


# ============ 9. 参考图生图（角色） ============

@router.post("/{project_id}/assets/characters/{asset_id}/reference_generate")
def reference_generate_character(
    project_id: str,
    asset_id: str,
    body: ProjectAssetReferenceGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """参考图生图（角色专用）"""
    proj = _get_project(db, project_id, current_user)
    asset = _get_asset(db, "character", asset_id, project_id)

    config_dict = _resolve_config(db, current_user, proj)
    art_style = proj.config.get("art_style", "realistic") if proj.config else "realistic"

    project_asset_crud.update_gen_status(db, asset, "generating")
    ws_manager.publish_project_event(
        current_user.id, project_id, "project_asset_generation_started",
        {"asset_id": asset_id, "asset_type": "character"},
    )

    try:
        from app.celery_tasks.project_asset_image import reference_generate_project_character
        task = reference_generate_project_character.delay(
        project_id=project_id,
        asset_id=asset_id,
        reference_image_urls=normalize_image_urls(
            body.reference_image_urls,
            user_id=str(current_user.id), biz="asset-reference",
        ),
        description=body.description,
        mode=body.mode,
        art_style=art_style,
        model_config=config_dict,
    )
    except Exception:
        project_asset_crud.update_gen_status(db, asset, "pending")
        raise HTTPException(status_code=500, detail="任务提交失败，请稍后重试")

    return success_response(data={"task_id": task.id, "asset_id": asset_id})


# ============ 10. 提取角色描述 ============

@router.post("/{project_id}/assets/characters/extract_description")
def extract_character_description(
    project_id: str,
    body: ProjectAssetExtractDescriptionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """从参考图提取角色外观描述（同步调用）"""
    proj = _get_project(db, project_id, current_user)
    config_dict = _resolve_config(db, current_user, proj)

    from app.core.model_provider import ModelCaller

    caller = ModelCaller.from_config_snapshot(config_dict, db=db)
    result = caller.vision(
        model_key="analysis_model",
        prompt="请详细描述这个角色的外观特征，包括发型、脸型、五官、服装、配饰、体型等。用中文描述。",
        image_urls=normalize_image_urls(
            body.reference_image_urls,
            user_id=str(current_user.id), biz="extract-desc",
        ),
        project_id=project_id,
    )

    return success_response(data={"description": result.content})


# ============ 11. 成片资产（含 volc_private_asset_id） ============

@router.get("/{project_id}/storyboard-assets")
def get_storyboard_assets(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取项目全部资产（角色、场景、道具），含 volc_private_asset_id，供成片页面使用"""
    characters = (
        db.query(ProjectCharacter)
        .filter(ProjectCharacter.project_id == project_id, ProjectCharacter.is_deleted == False)
        .order_by(ProjectCharacter.create_time)
        .all()
    )
    locations = (
        db.query(ProjectLocation)
        .filter(ProjectLocation.project_id == project_id, ProjectLocation.is_deleted == False)
        .order_by(ProjectLocation.create_time)
        .all()
    )
    props = (
        db.query(ProjectProp)
        .filter(ProjectProp.project_id == project_id, ProjectProp.is_deleted == False)
        .order_by(ProjectProp.create_time)
        .all()
    )

    def _resolve_url(v):
        if v and not v.startswith("http"):
            return cos_client.key_to_url(v)
        return v

    # 按用户区域选资产 ID 字段（前端用 volc_private_asset_id 判断是否已同步）
    asset_id_field = "byteplus_asset_id" if current_user.region == UserRegion.OVERSEAS else "volc_private_asset_id"

    def _char_to_dict(c):
        return {
            "id": c.id,
            "name": c.name,
            "aliases": c.aliases,
            "description": c.description,
            "image_url": _resolve_url(c.image_url),
            "thumbnail_url": _resolve_url(c.thumbnail_url),
            "image_prompt": c.image_prompt,
            "volc_private_asset_id": getattr(c, asset_id_field, None),
            "voice_id": c.voice_id,
            "voice_type": c.voice_type,
            "custom_voice_url": _resolve_url(c.custom_voice_url),
        }

    def _loc_to_dict(l):
        return {
            "id": l.id,
            "name": l.name,
            "place": l.place,
            "time": l.time,
            "summary": l.summary,
            "description": l.description,
            "image_url": _resolve_url(l.image_url),
            "thumbnail_url": _resolve_url(l.thumbnail_url),
            "image_prompt": l.image_prompt,
            "volc_private_asset_id": getattr(l, asset_id_field, None),
        }

    def _prop_to_dict(p):
        return {
            "id": p.id,
            "name": p.name,
            "aliases": p.aliases,
            "description": p.description,
            "image_url": _resolve_url(p.image_url),
            "thumbnail_url": _resolve_url(p.thumbnail_url),
            "image_prompt": p.image_prompt,
            "volc_private_asset_id": getattr(p, asset_id_field, None),
        }

    return success_response(data={
        "characters": [_char_to_dict(c) for c in characters],
        "locations": [_loc_to_dict(l) for l in locations],
        "props": [_prop_to_dict(p) for p in props],
    })


# ============ 12. AI 修改资产描述 ============

@router.post("/{project_id}/assets/{asset_type}/{asset_id}/ai_modify_description")
def ai_modify_description(
    project_id: str,
    asset_type: str,
    asset_id: str,
    body: ProjectAssetAiModifyDescriptionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """AI 修改资产描述（同步调用，不写库）"""
    proj = _get_project(db, project_id, current_user)
    asset = _get_asset(db, asset_type, asset_id, project_id)
    config_dict = _resolve_config(db, current_user, proj)

    from app.core.model_provider import ModelCaller

    caller = ModelCaller.from_config_snapshot(config_dict, db=db)

    current_desc = asset.description or ""
    prompt = (
        f"请根据以下修改指令优化资产描述。仅返回优化后的描述文本，不要添加任何解释。\n\n"
        f"当前描述：{current_desc}\n"
        f"修改指令：{body.modify_instruction}"
    )

    result = caller.call(
        model_key="analysis_model",
        prompt=prompt,
        temperature=0.7,
        project_id=project_id,
    )

    return success_response(data={"description": result.content})


# ============ 12. 从资产中心导入 ============

def _get_owner_user_id(user: User) -> str:
    return user.parent_user_id if user.parent_user_id else str(user.id)


@router.post("/{project_id}/assets/{asset_type}/{asset_id}/copy-from-global")
def copy_from_global(
    project_id: str,
    asset_type: str,
    asset_id: str,
    body: CopyFromGlobalRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """从资产中心导入全局资产到项目资产库"""
    _get_project(db, project_id, current_user)
    owner_user_id = _get_owner_user_id(current_user)
    user_id = str(current_user.id)

    if asset_type == "character":
        updated = project_asset_crud.copy_character_from_global(
            db, asset_id, body.global_asset_id, user_id, owner_user_id,
        )
        if updated.image_url:
            from app.utils.volc_sync import sync_asset_to_volc
            sync_asset_to_volc(db, project_id, updated, asset_type, user_id=str(current_user.id))
        apply_region_volc_id(updated, current_user.region)
        return success_response(data=ProjectCharacterResponse.model_validate(updated))

    elif asset_type in ("location", "prop"):
        model_class = ASSET_MODEL_MAP[asset_type]
        updated = project_asset_crud.copy_location_from_global(
            db, asset_id, body.global_asset_id, owner_user_id, model_class,
        )
        if updated.image_url:
            from app.utils.volc_sync import sync_asset_to_volc
            sync_asset_to_volc(db, project_id, updated, asset_type, user_id=str(current_user.id))
        response_model = ProjectLocationResponse if asset_type == "location" else ProjectPropResponse
        apply_region_volc_id(updated, current_user.region)
        return success_response(data=response_model.model_validate(updated))

    raise HTTPException(status_code=400, detail=f"不支持的资产类型: {asset_type}")


# ============ 14. 创建资产 ============

CREATE_SCHEMA_MAP = {
    "character": ProjectCharacterCreateRequest,
    "location": ProjectLocationCreateRequest,
    "prop": ProjectPropCreateRequest,
}


@router.post("/{project_id}/assets/{asset_type}")
def create_asset(
    project_id: str,
    asset_type: str,
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """手动创建单个资产"""
    _get_project(db, project_id, current_user)

    schema_class = CREATE_SCHEMA_MAP.get(asset_type)
    if not schema_class:
        raise HTTPException(status_code=400, detail=f"不支持的资产类型: {asset_type}")

    validated = schema_class(**body)
    data = validated.model_dump(exclude_none=True)

    asset = project_asset_crud.create_asset(
        db, project_id, asset_type, data, str(current_user.id),
    )

    response_model = {
        "character": ProjectCharacterResponse,
        "location": ProjectLocationResponse,
        "prop": ProjectPropResponse,
    }[asset_type]

    apply_region_volc_id(asset, current_user.region)
    return success_response(data=response_model.model_validate(asset))


# ============ 15. 撤销图片 ============

@router.post("/{project_id}/assets/{asset_type}/{asset_id}/undo_image")
def undo_image(
    project_id: str,
    asset_type: str,
    asset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """撤销图片到上一版本"""
    _get_project(db, project_id, current_user)
    asset = _get_asset(db, asset_type, asset_id, project_id)

    if not asset.previous_image_url:
        raise HTTPException(status_code=400, detail="没有可撤销的图片")

    restored_url = project_asset_crud.undo_image(db, asset)

    from app.utils.volc_sync import sync_asset_to_volc
    sync_asset_to_volc(db, project_id, asset, asset_type, user_id=str(current_user.id))

    response_model = {
        "character": ProjectCharacterResponse,
        "location": ProjectLocationResponse,
        "prop": ProjectPropResponse,
    }[asset_type]

    apply_region_volc_id(asset, current_user.region)
    return success_response(data=response_model.model_validate(asset))


# ============ 16. 打包下载 ============

@router.get("/{project_id}/assets/download", summary="打包下载项目资产图片")
def download_assets(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """打包下载项目下所有有图片的资产"""
    _get_project(db, project_id, current_user)

    assets_dict = project_asset_crud.get_assets_with_images(db, project_id)
    buffer = project_asset_crud.build_download_zip(assets_dict)

    if buffer is None:
        raise HTTPException(status_code=404, detail="没有可下载的图片")

    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    filename = f"project-assets_{date_str}.zip"

    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
