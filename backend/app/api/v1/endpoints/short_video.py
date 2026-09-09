"""短视频生成 API 端点"""
import json
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.celery_tasks.short_video_gen import generate_short_video_task, process_short_video_callback
from app.core.ws import ws_manager
from app.crud.short_video_crud import short_video_task_crud, short_video_asset_crud
from app.deps.permission_deps import get_accessible_folder_ids
from app.enums.base import WSEventType
from app.enums.user import UserRegion
from app.enums.video import ShortVideoTaskStatus
from app.models import User
from app.models.project import Project
from app.models.project_asset import ProjectCharacter, ProjectLocation, ProjectProp
from app.models.asset import GlobalCharacter, GlobalCharacterAppearance, GlobalLocation, GlobalLocationImage, GlobalVoice, GlobalAssetFolder
from app.models.short_video import ShortVideoAsset, ShortVideoTask
from app.schemas.short_video import ShortVideoTaskCreate, ShortVideoAssetUpload
from app.services.seedance_client import SeedanceAPIError
from app.services.video_callback_handler import extract_video_url
from app.services.video_generation_service import VideoGenerationService
from app.utils.response import success_response
from app.utils.tencent_cos_utils import cos_client
from app.utils.user_volc_sync import sync_user_asset_to_volc

router = APIRouter()


def _resolve_url(v):
    """将永久 URL 或 COS key 转为签名 URL，用于前端展示或 API 调用"""
    if not v:
        return v
    if v.startswith("http"):
        # 永久 URL → 提取 key → 生成签名 URL
        key = cos_client.url_to_key(v)
        if key and key != v:
            return cos_client.get_signed_url(key)
        return v
    # COS key
    return cos_client.get_signed_url(v)


def _resolve_task_video_url(task: ShortVideoTask) -> str | None:
    """视频地址解析：COS 上传完成后返回签名 URL；尚未完成时 fallback 到回调源地址。

    异步上传任务跑完前 task.video_url 为空，此时从 api_response_data.content.video_url
    提取方舟/Seedance 返回的源地址直接返回（外部 URL 不签名），保证用户能立即播放。
    """
    if task.video_url:
        return _resolve_url(task.video_url)
    if task.api_response_data:
        try:
            return extract_video_url(task.api_response_data)
        except ValueError:
            return None
    return None


def _normalize_to_permanent(url: str) -> str:
    """将签名 URL 转为永久 URL 存储（去掉签名参数）"""
    if not url:
        return url
    key = cos_client.url_to_key(url)
    if key and key != url:
        return cos_client.get_permanent_url(key)
    return url


def _resolve_ref_json(ref_json_str: str) -> str:
    """将 reference_media_json 中的永久 URL 重新签名，用于前端展示"""
    try:
        ref = json.loads(ref_json_str)
        for key in ("images", "videos", "audios"):
            if key in ref:
                for item in ref[key]:
                    if isinstance(item, dict):
                        if item.get("url"):
                            item["url"] = _resolve_url(item["url"])
                        if item.get("thumbnail_url"):
                            item["thumbnail_url"] = _resolve_url(item["thumbnail_url"])
        for field in ("imageUrls", "videoUrls", "audioUrls"):
            if field in ref:
                ref[field] = [_resolve_url(u) for u in ref[field]]
        return json.dumps(ref, ensure_ascii=False)
    except (json.JSONDecodeError, TypeError):
        return ref_json_str


def _normalize_ref_json(ref_json_str: str) -> str:
    """将 reference_media_json 中的签名 URL 转为永久 URL"""
    try:
        ref = json.loads(ref_json_str)
        # 新格式：images/videos/audios 数组
        for key in ("images", "videos", "audios"):
            if key in ref:
                for item in ref[key]:
                    if isinstance(item, dict):
                        if item.get("url"):
                            item["url"] = _normalize_to_permanent(item["url"])
                        if item.get("thumbnail_url"):
                            item["thumbnail_url"] = _normalize_to_permanent(item["thumbnail_url"])
        # 旧格式兼容
        for field in ("imageUrls", "videoUrls", "audioUrls"):
            if field in ref:
                ref[field] = [_normalize_to_permanent(u) for u in ref[field]]
        return json.dumps(ref, ensure_ascii=False)
    except (json.JSONDecodeError, TypeError):
        return ref_json_str


# ── 短视频生成 ──────────────────────────────────────────

@router.post("/generate")
def generate_short_video(
    body: ShortVideoTaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """提交短视频生成任务"""
    # 校验首尾帧模式参数
    if body.generation_type == "first_last_frame":
        if not body.first_frame_url or not body.last_frame_url:
            raise HTTPException(status_code=400, detail="首尾帧模式需要提供首帧和尾帧图片")

    task_data = body.model_dump()
    task_data["user_id"] = current_user.id
    task_data["create_uid"] = current_user.id
    task_data["status"] = ShortVideoTaskStatus.PENDING
    task_data["region"] = current_user.region or UserRegion.DOMESTIC

    # 按 region 把首尾帧资产 ID 写入对应字段（前端始终用 volc_id 命名传入）
    user_region = current_user.region or UserRegion.DOMESTIC
    if user_region == UserRegion.OVERSEAS:
        ff_id = task_data.pop("first_frame_volc_id", None)
        if ff_id:
            task_data["first_frame_byteplus_id"] = ff_id
        lf_id = task_data.pop("last_frame_volc_id", None)
        if lf_id:
            task_data["last_frame_byteplus_id"] = lf_id

    # 将签名 URL 转为永久 URL 存储
    if task_data.get("first_frame_url"):
        task_data["first_frame_url"] = _normalize_to_permanent(task_data["first_frame_url"])
    if task_data.get("last_frame_url"):
        task_data["last_frame_url"] = _normalize_to_permanent(task_data["last_frame_url"])
    if task_data.get("reference_media_json"):
        task_data["reference_media_json"] = _normalize_ref_json(task_data["reference_media_json"])

    task = short_video_task_crud.create(db, task_data)

    generate_short_video_task.delay(task.id)

    return success_response(data={"task_id": task.id, "status": ShortVideoTaskStatus.PENDING})


# ── 任务管理 ──────────────────────────────────────────

@router.get("/tasks")
def list_tasks(
    cursor: str = None,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取用户任务列表（支持游标分页）"""
    limit = min(limit, 50)
    tasks, has_more, next_cursor = short_video_task_crud.get_user_tasks_paginated(
        db, current_user.id, cursor=cursor, limit=limit
    )
    return success_response(data={
        "items": [
            {
                "id": t.id,
                "generation_type": t.generation_type,
                "prompt_text": t.prompt_text,
                "ratio": t.ratio,
                "resolution": t.resolution,
                "duration": t.duration,
                "generate_audio": t.generate_audio,
                "status": t.status,
                "progress": t.progress,
                "region": t.region,
                "api_task_id": t.api_task_id,
                "video_url": _resolve_task_video_url(t),
                "thumbnail_url": _resolve_url(t.thumbnail_url),
                "first_frame_url": _resolve_url(t.first_frame_url),
                "last_frame_url": _resolve_url(t.last_frame_url),
                "reference_media_json": _resolve_ref_json(t.reference_media_json) if t.reference_media_json else None,
                "error_message": t.error_message,
                "first_frame_volc_id": t.first_frame_volc_id,
                "last_frame_volc_id": t.last_frame_volc_id,
                "create_time": t.create_time.isoformat() if t.create_time else None,
                "submitted_at": t.submitted_at.isoformat() if t.submitted_at else None,
                "completed_at": t.completed_at.isoformat() if t.completed_at else None,
            }
            for t in tasks
        ],
        "has_more": has_more,
        "next_cursor": next_cursor,
    })


@router.get("/tasks/{task_id}")
def get_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取任务详情"""
    task = short_video_task_crud.get_task(db, task_id, current_user.id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return success_response(data={
        "id": task.id,
        "generation_type": task.generation_type,
        "prompt_text": task.prompt_text,
        "ratio": task.ratio,
        "resolution": task.resolution,
        "duration": task.duration,
        "generate_audio": task.generate_audio,
        "api_task_id": task.api_task_id,
        "video_url": _resolve_task_video_url(task),
        "thumbnail_url": _resolve_url(task.thumbnail_url),
        "first_frame_url": _resolve_url(task.first_frame_url),
        "first_frame_volc_id": task.first_frame_volc_id,
        "last_frame_url": _resolve_url(task.last_frame_url),
        "last_frame_volc_id": task.last_frame_volc_id,
        "reference_media_json": _resolve_ref_json(task.reference_media_json) if task.reference_media_json else None,
        "status": task.status,
        "progress": task.progress,
        "region": task.region,
        "error_message": task.error_message,
        "create_time": task.create_time.isoformat() if task.create_time else None,
        "submitted_at": task.submitted_at.isoformat() if task.submitted_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
    })


@router.post("/tasks/{task_id}/cancel")
def cancel_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """取消任务。

    - PENDING / SUBMITTED：任务尚未到方舟，仅本地标记 cancelled（无 ark_task_id 即无预扣日志，无退款）
    - QUEUED：调用火山 SDK 取消（按 task.region 走国内/国际版），失败则本地状态不变，返回 502
    - 其他状态：不允许取消（火山 running 之后无法取消）
    取消成功后退还预扣积分并推送 WS。
    """
    task = short_video_task_crud.get_task(db, task_id, current_user.id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    cancellable = (ShortVideoTaskStatus.PENDING, ShortVideoTaskStatus.SUBMITTED, ShortVideoTaskStatus.QUEUED)
    if task.status not in cancellable:
        raise HTTPException(status_code=400, detail="模型生成视频中，不可取消")

    # 仅 QUEUED 且已拿到 ark_task_id 时调火山 SDK 取消
    if task.status == ShortVideoTaskStatus.QUEUED and task.api_task_id:
        try:
            service = VideoGenerationService(db, current_user.id)
            # 优先用任务自身的 region（避免用户切区域后走错 SDK）
            if task.region:
                service.region = task.region
            # 从提交时存的请求参数中取 model_name，便于按 model_provider_map 解析对应 api_key
            api_params = task.api_request_params if isinstance(task.api_request_params, dict) else {}
            model_name = api_params.get("model")
            service.cancel_video_task(task.api_task_id, task_id=task.id, model_name=model_name)
        except SeedanceAPIError as e:
            logger.error(f"取消方舟任务失败: task_id={task_id}, ark_task_id={task.api_task_id}, err={e.message}")
            raise HTTPException(status_code=502, detail=f"取消失败: {e.message}")

    # 退还预扣积分（仅有 ark_task_id 时才有预扣日志）
    if task.api_task_id:
        service = VideoGenerationService(db, current_user.id)
        service.refund_points(task.api_task_id, task_id=task.id)
        service._update_log_on_failure(task.api_task_id, "用户取消任务", task_id=task.id)

    # 本地状态切到 cancelled
    task = short_video_task_crud.update_status(
        db, task_id, ShortVideoTaskStatus.CANCELLED, completed_at=datetime.utcnow(),
    )

    # 推送 WS 通知前端
    ws_manager.publish_asset_hub_event(
        str(current_user.id), WSEventType.SHORT_VIDEO_PROGRESS,
        {"task_id": task_id, "status": ShortVideoTaskStatus.CANCELLED},
    )

    return success_response(data={"task_id": task_id, "status": ShortVideoTaskStatus.CANCELLED})


@router.post("/tasks/{task_id}/retry")
def retry_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """重试失败任务"""
    task = short_video_task_crud.get_task(db, task_id, current_user.id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if task.status not in (ShortVideoTaskStatus.FAILED, ShortVideoTaskStatus.CANCELLED):
        raise HTTPException(status_code=400, detail="只有失败或已取消的任务可以重试")

    task = short_video_task_crud.update_status(db, task_id, ShortVideoTaskStatus.PENDING, error_message=None, progress=0)

    generate_short_video_task.delay(task.id)

    return success_response(data={"task_id": task.id, "status": ShortVideoTaskStatus.PENDING})


@router.delete("/tasks/{task_id}")
def delete_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除任务"""
    task = short_video_task_crud.get_task(db, task_id, current_user.id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    short_video_task_crud.remove(db, task_id)
    return success_response(data={"task_id": task_id})


# ── 短视频资产 ──────────────────────────────────────────

@router.post("/assets/upload")
def upload_asset(
    body: ShortVideoAssetUpload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """上传/记录短视频资产"""
    # 文件大小校验（兜底）
    SIZE_LIMITS = {"image": 30 * 1024 * 1024, "video": 50 * 1024 * 1024, "audio": 15 * 1024 * 1024}
    limit = SIZE_LIMITS.get(body.asset_type)
    if limit and body.asset_size and body.asset_size > limit:
        raise HTTPException(status_code=400, detail=f"文件大小超过限制（{limit // 1024 // 1024}MB）")

    # 时长校验
    if body.asset_type == "video":
        if body.duration is not None:
            if body.duration < 2 or body.duration > 15:
                raise HTTPException(status_code=400, detail="视频时长需在 2-15 秒之间")
    elif body.asset_type == "audio":
        if body.duration is not None and body.duration > 15:
            raise HTTPException(status_code=400, detail="音频时长不能超过 15 秒")

    asset_data = body.model_dump()
    asset_data["user_id"] = current_user.id
    asset_data["create_uid"] = current_user.id

    # 用 asset_key 存永久 URL 到数据库
    if body.asset_key:
        asset_data["asset_url"] = cos_client.get_permanent_url(body.asset_key)
    asset_data.pop("asset_key", None)

    # 图片类型：前端直传的缩略图 COS key → 永久 URL
    if body.thumbnail_key:
        asset_data["thumbnail_url"] = cos_client.get_permanent_url(body.thumbnail_key)
    asset_data.pop("thumbnail_key", None)

    # 视频类型：提取封面图
    if body.asset_type == "video" and (body.asset_key or body.asset_url):
        thumbnail_url = _extract_and_upload_thumbnail(
            body.asset_key or body.asset_url, current_user.id
        )
        if thumbnail_url:
            asset_data["thumbnail_url"] = thumbnail_url

    asset = short_video_asset_crud.create(db, asset_data)

    # 同步到火山私域
    if asset.asset_type in ("image", "video", "audio"):
        try:
            sync_user_asset_to_volc(
                db, str(current_user.id), asset,
                asset.asset_name or "", raise_on_error=True
            )
        except Exception as e:
            db.delete(asset)
            db.commit()
            raise HTTPException(status_code=500, detail=f"同步火山失败: {e}")

    return success_response(data={
        "id": asset.id,
        "asset_name": asset.asset_name,
        "asset_type": asset.asset_type,
        "asset_url": _resolve_url(asset.asset_url),
        "thumbnail_url": _resolve_url(asset.thumbnail_url),
        # 国内/国际版统一通过 volc_asset_id 返回（按当前用户区域写入的资产 ID）
        "volc_asset_id": asset.volc_asset_id or asset.byteplus_asset_id,
        "duration": asset.duration,
    })


def _extract_and_upload_thumbnail(video_key_or_url: str, user_id: str) -> str | None:
    """从视频中截取封面图，上传到 COS，返回永久 URL"""
    import subprocess
    import tempfile
    import os

    tmp_video_path = None
    tmp_thumb_path = None
    try:
        # 生成签名 URL 用于下载
        if video_key_or_url.startswith("http"):
            key = cos_client.url_to_key(video_key_or_url)
            signed_url = cos_client.get_signed_url(key) if key and key != video_key_or_url else video_key_or_url
        else:
            signed_url = cos_client.get_signed_url(video_key_or_url)

        # 下载到临时文件
        import urllib.request
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_video:
            tmp_video_path = tmp_video.name
        urllib.request.urlretrieve(signed_url, tmp_video_path)

        # 生成封面临时文件路径
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_thumb:
            tmp_thumb_path = tmp_thumb.name

        # 用 ffmpeg 截取第 0.5 秒帧
        result = subprocess.run(
            ["ffmpeg", "-y", "-i", tmp_video_path, "-ss", "0.5",
             "-frames:v", "1", "-q:v", "2", tmp_thumb_path],
            capture_output=True, timeout=30,
        )

        if os.path.getsize(tmp_thumb_path) > 0:
            with open(tmp_thumb_path, "rb") as f:
                thumb_data = f.read()
            thumb_key = cos_client.generate_unique_key(f"temp-{user_id}", "thumbnail", user_id, "jpg")
            cos_client.upload_object(thumb_data, thumb_key, content_type="image/jpeg")
            return cos_client.get_permanent_url(thumb_key)
    except Exception as e:
        logger.warning(f"视频封面提取失败: {e}")
    finally:
        for p in (tmp_video_path, tmp_thumb_path):
            if p:
                try:
                    os.unlink(p)
                except OSError:
                    pass
    return None


@router.get("/assets")
def list_assets(
    asset_type: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取用户资产列表"""
    assets = short_video_asset_crud.get_user_assets(db, current_user.id, asset_type)
    return success_response(data=[
        {
            "id": a.id,
            "asset_name": a.asset_name,
            "asset_type": a.asset_type,
            "asset_url": _resolve_url(a.asset_url),
            "asset_size": a.asset_size,
            "mime_type": a.mime_type,
            "volc_asset_id": a.volc_asset_id or a.byteplus_asset_id,
            "thumbnail_url": _resolve_url(a.thumbnail_url),
            "duration": a.duration,
            "source": a.source,
            "create_time": a.create_time.isoformat() if a.create_time else None,
        }
        for a in assets
    ])


@router.delete("/assets/{asset_id}")
def delete_asset(
    asset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除资产"""
    asset = short_video_asset_crud.get_asset(db, asset_id, current_user.id)
    if not asset:
        raise HTTPException(status_code=404, detail="资产不存在")
    short_video_asset_crud.remove(db, asset_id)
    return success_response(data={"asset_id": asset_id})


# ── 资产选择器 ──────────────────────────────────────────

@router.get("/project-assets")
def list_project_assets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取用户所有项目的资产（按项目分组），用于资产选择器"""
    # 子账号可查看主账号的项目资产
    owner_user_id = _get_owner_user_id(current_user)
    # 按用户区域选资产 ID 字段（前端始终用 volc_asset_id key 接收）
    asset_id_field = "byteplus_asset_id" if current_user.region == UserRegion.OVERSEAS else "volc_private_asset_id"
    project_query = db.query(Project).filter(
        Project.user_id == owner_user_id, Project.is_deleted == False
    )
    if current_user.parent_user_id is not None:
        # 子账号同时也能看到自己创建的项目
        project_query = db.query(Project).filter(
            or_(Project.user_id == owner_user_id, Project.user_id == current_user.id),
            Project.is_deleted == False,
        )
    projects = project_query.order_by(Project.update_time.desc()).all()

    result = []
    for proj in projects:
        assets = []

        characters = (
            db.query(ProjectCharacter)
            .filter(ProjectCharacter.project_id == proj.id, ProjectCharacter.is_deleted == False)
            .all()
        )
        for c in characters:
            aid = getattr(c, asset_id_field, None)
            if c.image_url and aid:
                assets.append({
                    "id": c.id,
                    "name": c.name,
                    "asset_type": "image",
                    "image_url": _resolve_url(c.image_url),
                    "thumbnail_url": _resolve_url(c.thumbnail_url),
                    "volc_asset_id": aid,
                })

        locations = (
            db.query(ProjectLocation)
            .filter(ProjectLocation.project_id == proj.id, ProjectLocation.is_deleted == False)
            .all()
        )
        for loc in locations:
            aid = getattr(loc, asset_id_field, None)
            if loc.image_url and aid:
                assets.append({
                    "id": loc.id,
                    "name": loc.name,
                    "asset_type": "image",
                    "image_url": _resolve_url(loc.image_url),
                    "thumbnail_url": _resolve_url(loc.thumbnail_url),
                    "volc_asset_id": aid,
                })

        props = (
            db.query(ProjectProp)
            .filter(ProjectProp.project_id == proj.id, ProjectProp.is_deleted == False)
            .all()
        )
        for p in props:
            aid = getattr(p, asset_id_field, None)
            if p.image_url and aid:
                assets.append({
                    "id": p.id,
                    "name": p.name,
                    "asset_type": "image",
                    "image_url": _resolve_url(p.image_url),
                    "thumbnail_url": _resolve_url(p.thumbnail_url),
                    "volc_asset_id": aid,
                })

        if assets:
            result.append({
                "project_id": proj.id,
                "project_name": proj.title,
                "assets": assets,
            })

    return success_response(data=result)


def _get_owner_user_id(user: User) -> str:
    """子账号返回主账号ID，主账号返回自己的ID"""
    return user.parent_user_id if user.parent_user_id else user.id


def _build_accessible_folder_filter(query, model_class, current_user: User, db: Session, shared_ids=None):
    """根据当前用户身份构建文件夹级别的资产访问过滤条件

    shared_ids: 平台授权资产ID列表，这些资产不受 user_id/folder 归属限制
    """
    conditions = [model_class.user_id == current_user.id]
    if current_user.parent_user_id is not None:
        # 子账号：可看自己创建的 + 共享文件夹下的主账号资产
        accessible_ids = get_accessible_folder_ids(current_user, db)
        if accessible_ids is not None:
            conditions.append(model_class.folder_id.in_(accessible_ids))
    if shared_ids:
        conditions.append(model_class.id.in_(shared_ids))
    return query.filter(or_(*conditions))


@router.get("/asset-center")
def list_asset_center(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取资产中心的有图片或音频的资产，用于资产选择器"""
    from app.crud.asset_share_relation_crud import asset_share_relation_crud

    owner_user_id = _get_owner_user_id(current_user)
    # 按用户区域选资产 ID 字段（前端始终用 volc_asset_id key 接收）
    asset_id_field = "byteplus_asset_id" if current_user.region == UserRegion.OVERSEAS else "volc_private_asset_id"

    # 平台授权资产 ID（按主账号查询，子账号可继承）
    shared_character_ids = asset_share_relation_crud.get_shared_asset_ids(db, owner_user_id, "character")
    shared_location_ids = asset_share_relation_crud.get_shared_asset_ids(db, owner_user_id, "location")
    shared_voice_ids = asset_share_relation_crud.get_shared_asset_ids(db, owner_user_id, "voice")

    # 预加载文件夹名称映射
    folders = (
        db.query(GlobalAssetFolder)
        .filter(GlobalAssetFolder.owner_user_id == owner_user_id, GlobalAssetFolder.is_deleted == False)
        .all()
    )
    folder_map = {f.id: f.name for f in folders}
    assets = []

    # 全局角色（有形象图片的）
    character_query = db.query(GlobalCharacter).filter(GlobalCharacter.is_deleted == False)
    character_query = _build_accessible_folder_filter(
        character_query, GlobalCharacter, current_user, db, shared_ids=shared_character_ids
    )
    characters = character_query.all()

    for c in characters:
        appearances = (
            db.query(GlobalCharacterAppearance)
            .filter(GlobalCharacterAppearance.character_id == c.id, GlobalCharacterAppearance.is_deleted == False)
            .all()
        )
        for app in appearances:
            aid = getattr(app, asset_id_field, None)
            if app.image_url and aid:
                assets.append({
                    "id": app.id,
                    "name": f"{c.name} - 形象{app.appearance_index + 1}",
                    "asset_type": "image",
                    "image_url": _resolve_url(app.image_url),
                    "thumbnail_url": _resolve_url(app.thumbnail_url),
                    "volc_asset_id": aid,
                    "folder_id": c.folder_id,
                    "folder_name": folder_map.get(c.folder_id, ""),
                })

    # 全局场景（有图片的）
    location_query = db.query(GlobalLocation).filter(GlobalLocation.is_deleted == False)
    location_query = _build_accessible_folder_filter(
        location_query, GlobalLocation, current_user, db, shared_ids=shared_location_ids
    )
    locations = location_query.all()

    for loc in locations:
        images = (
            db.query(GlobalLocationImage)
            .filter(GlobalLocationImage.location_id == loc.id, GlobalLocationImage.is_deleted == False)
            .all()
        )
        for img in images:
            aid = getattr(img, asset_id_field, None)
            if img.image_url and aid:
                assets.append({
                    "id": img.id,
                    "name": f"{loc.name} - 图片{img.image_index + 1}",
                    "asset_type": "image",
                    "image_url": _resolve_url(img.image_url),
                    "thumbnail_url": _resolve_url(img.thumbnail_url),
                    "volc_asset_id": aid,
                    "folder_id": loc.folder_id,
                    "folder_name": folder_map.get(loc.folder_id, ""),
                })

    # 全局音色（只返回已同步的）—— 按 region 切换资产 ID 列
    asset_id_col = GlobalVoice.byteplus_asset_id if current_user.region == UserRegion.OVERSEAS else GlobalVoice.volc_private_asset_id
    voice_query = db.query(GlobalVoice).filter(
        GlobalVoice.is_deleted == False, asset_id_col.isnot(None)
    )
    voice_query = _build_accessible_folder_filter(
        voice_query, GlobalVoice, current_user, db, shared_ids=shared_voice_ids
    )
    voices = voice_query.all()

    for v in voices:
        assets.append({
            "id": v.id,
            "name": v.name,
            "asset_type": "audio",
            "image_url": None,
            "audio_url": _resolve_url(v.custom_voice_url),
            "volc_asset_id": getattr(v, asset_id_field, None),
            "duration": v.duration,
            "folder_id": None,
            "folder_name": "",
        })

    return success_response(data=assets)


@router.post("/seedance_callback")
def short_video_callback(body: dict):
    """接收 Seedance SDK 的短视频生成回调，立即返回，业务异步处理"""
    logger.info(f"短视频回调请求: {json.dumps(body, ensure_ascii=False)}")

    process_short_video_callback.delay(body)
    return success_response(data={"received": True})


@router.get("/asset-center/folders")
def list_asset_center_folders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取资产中心的文件夹列表"""
    owner_user_id = _get_owner_user_id(current_user)
    query = db.query(GlobalAssetFolder).filter(
        GlobalAssetFolder.owner_user_id == owner_user_id, GlobalAssetFolder.is_deleted == False
    )
    if current_user.parent_user_id is None:
        # 主账号：只看自己创建的
        query = query.filter(GlobalAssetFolder.user_id == current_user.id)
    else:
        accessible_ids = get_accessible_folder_ids(current_user, db)
        if accessible_ids is not None:
            query = query.filter(
                or_(
                    GlobalAssetFolder.user_id == current_user.id,
                    GlobalAssetFolder.id.in_(accessible_ids),
                )
            )
        else:
            # 子账号无 main_user_asset:read 权限，只能看自己的文件夹
            query = query.filter(GlobalAssetFolder.user_id == current_user.id)
    folders = query.all()
    return success_response(data=[{"id": f.id, "name": f.name} for f in folders])
