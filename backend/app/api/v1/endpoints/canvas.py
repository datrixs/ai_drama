"""无限画布 API 端点

仅负责：路由声明、登录态/参数解析、调度 Celery、调用 crud 层做业务处理、
把结果用 success_response 包回 HTTP 响应。

请求模型在 app/schemas/canvas.py；
业务规则、序列化、归属校验、上传校验、资产同步等在 app/crud/canvas_crud.py。
"""
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.crud.global_asset_folder import global_asset_folder_crud
from app.crud.global_character import global_character_crud, global_character_appearance_crud
from app.crud.global_location import global_location_crud, global_location_image_crud
from app.crud.global_voice import global_voice_crud
from app.utils.tencent_cos_utils import cos_client
from app.celery_tasks.canvas_generation import (
    generate_canvas_image,
    generate_canvas_text,
    generate_canvas_video,
    process_canvas_video_callback,
)
from app.crud.canvas_crud import (
    apply_generation_output_to_item,
    canvas_connection_crud,
    canvas_document_crud,
    canvas_item_crud,
    canvas_item_generation_crud,
    create_completed_generation,
    get_owned_document_or_404,
    get_owned_generation_or_404,
    get_owned_item_or_404,
    infer_ext_by_mime,
    MAX_AUDIO_DURATION_SECONDS,
    serialize_connection,
    serialize_document,
    serialize_generation,
    serialize_item,
    validate_connection_direction,
    validate_upload_and_pick_biz,
)
from app.enums.canvas import CanvasItemType
from app.models import User
from app.models.canvas import CanvasConnection
from app.crud.user_crud import user_crud
from app.schemas.canvas import (
    CanvasConnectionCreate,
    CanvasDocumentCreate,
    CanvasDocumentUpdate,
    CanvasGenerateImageRequest,
    CanvasGenerateTextRequest,
    CanvasGenerateVideoRequest,
    CanvasItemBatchUpdate,
    CanvasItemCreate,
    CanvasItemUpdate,
    RegisterAssetRequest,
    SaveToAssetCenterRequest,
    BatchSaveToAssetCenterRequest,
)
from app.services.canvas_generation import (
    extract_and_upload_video_cover,
    prepare_image_generation,
    prepare_text_generation,
    prepare_video_generation,
)
from app.services.config_reader import ConfigReader
from app.utils.response import success_response

router = APIRouter()


def _owner_user_id(user: User) -> str:
    """主账号 id（参考 asset_hub._get_owner_user_id）"""
    return str(user.parent_user_id) if user.parent_user_id else str(user.id)


# ── 画布 CRUD ──────────────────────────────────────────

@router.post("/documents")
def create_document(
    body: CanvasDocumentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建画布"""
    data = body.model_dump()
    data["user_id"] = current_user.id
    data["create_uid"] = current_user.id
    doc = canvas_document_crud.create(db, data)
    return success_response(data=serialize_document(doc))


@router.get("/documents")
def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """列出我的画布（按最近打开时间倒序）"""
    docs = canvas_document_crud.get_user_documents(db, current_user.id)
    return success_response(data=[serialize_document(d) for d in docs])


@router.get("/documents/{document_id}")
def get_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取画布详情（含所有节点和连线，一次性返回）"""
    doc = get_owned_document_or_404(db, document_id, current_user.id)
    items = canvas_item_crud.get_document_items(db, doc.id)
    connections = canvas_connection_crud.get_document_connections(db, doc.id)
    canvas_document_crud.touch_opened(db, doc.id)
    region = user_crud.get_region(user_id=str(current_user.id), db=db)
    return success_response(data={
        **serialize_document(doc),
        "items": [serialize_item(i, region=region) for i in items],
        "connections": [serialize_connection(c) for c in connections],
    })


@router.put("/documents/{document_id}")
def update_document(
    document_id: str,
    body: CanvasDocumentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新画布（标题/描述/缩略图）"""
    doc = get_owned_document_or_404(db, document_id, current_user.id)
    update_data = body.model_dump(exclude_unset=True)
    if not update_data:
        return success_response(data=serialize_document(doc))
    update_data["update_uid"] = current_user.id
    doc = canvas_document_crud.update(db, doc, update_data)
    return success_response(data=serialize_document(doc))


@router.delete("/documents/{document_id}")
def delete_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除画布（软删，级联软删其下所有节点和连线）"""
    doc = get_owned_document_or_404(db, document_id, current_user.id)
    canvas_document_crud.soft_cascade_delete(db, doc)
    return success_response(data={"id": doc.id})


# ── 节点 ──────────────────────────────────────────

@router.post("/documents/{document_id}/items")
def create_item(
    document_id: str,
    body: CanvasItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """新增节点"""
    doc = get_owned_document_or_404(db, document_id, current_user.id)
    try:
        CanvasItemType(body.item_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"不支持的节点类型: {body.item_type}")
    data = body.model_dump()
    data["canvas_id"] = doc.id
    data["create_uid"] = current_user.id
    data["last_run_status"] = "idle"
    item = canvas_item_crud.create(db, data)
    canvas_document_crud.touch(db, doc.id, str(current_user.id))
    region = user_crud.get_region(user_id=str(current_user.id), db=db)
    return success_response(data=serialize_item(item, region=region))


@router.put("/items/{item_id}")
def update_item(
    item_id: str,
    body: CanvasItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新节点（位置/大小/内容等）"""
    item = get_owned_item_or_404(db, item_id, current_user.id)
    region = user_crud.get_region(user_id=str(current_user.id), db=db)
    update_data = body.model_dump(exclude_unset=True)
    if not update_data:
        return success_response(data=serialize_item(item, region=region))
    update_data["update_uid"] = current_user.id
    item = canvas_item_crud.update(db, item, update_data)
    canvas_document_crud.touch(db, item.canvas_id, str(current_user.id))
    return success_response(data=serialize_item(item, region=region))


@router.delete("/items/{item_id}")
def delete_item(
    item_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除节点（同时软删与之相关的连线）

    若节点为 group 类型，先解组（子节点 parent_id 置空并保留），再软删组本身。
    """
    item = get_owned_item_or_404(db, item_id, current_user.id)
    if item.item_type == CanvasItemType.GROUP.value:
        canvas_item_crud.detach_children(db, item.id)
        db.commit()
    canvas_connection_crud.soft_delete_by_item(db, item.canvas_id, item.id)
    canvas_item_crud.remove(db, item.id)
    canvas_document_crud.touch(db, item.canvas_id, str(current_user.id))
    return success_response(data={"id": item.id})


@router.post("/documents/{document_id}/items/batch")
def batch_update_items(
    document_id: str,
    body: CanvasItemBatchUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """批量更新节点（用于打组/解组/组拖动一次性保存位置与父子关系）"""
    doc = get_owned_document_or_404(db, document_id, current_user.id)
    updates = [
        u.model_dump(exclude_unset=True) for u in body.updates if u.id
    ]
    canvas_item_crud.batch_update_items(db, doc.id, updates)
    canvas_document_crud.touch(db, doc.id, str(current_user.id))
    return success_response(data={"updated": len(updates)})


# ── 连线 ──────────────────────────────────────────

@router.post("/documents/{document_id}/connections")
def create_connection(
    document_id: str,
    body: CanvasConnectionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """新增连线"""
    doc = get_owned_document_or_404(db, document_id, current_user.id)
    source = canvas_item_crud.get_item(db, body.source_item_id)
    target = canvas_item_crud.get_item(db, body.target_item_id)
    if not source or source.canvas_id != doc.id:
        raise HTTPException(status_code=400, detail="上游节点不存在或不属于该画布")
    if not target or target.canvas_id != doc.id:
        raise HTTPException(status_code=400, detail="下游节点不存在或不属于该画布")
    validate_connection_direction(db, str(current_user.id), source, target)
    data = body.model_dump()
    data["canvas_id"] = doc.id
    data["create_uid"] = current_user.id
    conn = canvas_connection_crud.create(db, data)
    canvas_document_crud.touch(db, doc.id, str(current_user.id))
    return success_response(data=serialize_connection(conn))


@router.delete("/connections/{connection_id}")
def delete_connection(
    connection_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除连线"""
    conn = db.get(CanvasConnection, connection_id)
    if not conn or conn.is_deleted:
        raise HTTPException(status_code=404, detail="连线不存在")
    get_owned_document_or_404(db, conn.canvas_id, current_user.id)
    canvas_connection_crud.remove(db, conn.id)
    canvas_document_crud.touch(db, conn.canvas_id, str(current_user.id))
    return success_response(data={"id": conn.id})


# ── 节点生成（异步 Celery 任务） ─────────────────────────

def _resolve_prompt(item, prompt: Optional[str], prompt_tokens: Optional[list[dict]]) -> str:
    """优先用入参 prompt，回退到节点 content_json.prompt"""
    p = (prompt or "").strip()
    if not p:
        p = ((item.content_json or {}).get("prompt") or "").strip()
    return p


def _ensure_prompt_or_tokens(
    item, prompt: Optional[str], prompt_tokens: Optional[list[dict]],
) -> None:
    """prompt 与 prompt_tokens 都为空则 400"""
    has_tokens = bool(prompt_tokens) or bool((item.content_json or {}).get("prompt_tokens"))
    if not prompt and not has_tokens:
        raise HTTPException(status_code=400, detail="prompt 不能为空")


def _resolved_model_config(db: Session, user_id: str) -> dict:
    """读取用户当前模型配置快照（Celery 任务内重建 ModelCaller 用）"""
    return ConfigReader(db).get_config(user_id).to_dict()


@router.post("/items/{item_id}/generate-text")
def generate_text(
    item_id: str,
    body: CanvasGenerateTextRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """触发文本节点生成（异步 Celery 任务）"""
    item = get_owned_item_or_404(db, item_id, current_user.id)
    if item.item_type != CanvasItemType.TEXT.value:
        raise HTTPException(status_code=400, detail="该节点不是文本节点")

    prompt = _resolve_prompt(item, body.prompt, body.prompt_tokens)
    _ensure_prompt_or_tokens(item, prompt, body.prompt_tokens)

    model_config = _resolved_model_config(db, str(current_user.id))
    _, gen = prepare_text_generation(
        db,
        item_id=item_id,
        user_id=str(current_user.id),
        request_payload={
            "prompt": prompt,
            "prompt_tokens": body.prompt_tokens,
            "prompt_plain_text": body.prompt_plain_text,
            "model": body.model,
        },
    )
    task = generate_canvas_text.delay(str(gen.id), model_config)
    canvas_document_crud.touch(db, item.canvas_id, str(current_user.id))
    return success_response(data={
        "generation_id": str(gen.id),
        "item_id": item_id,
        "task_id": task.id,
        "status": gen.status,
        "last_run_status": item.last_run_status,
    })


@router.post("/items/{item_id}/generate-image")
def generate_image(
    item_id: str,
    body: CanvasGenerateImageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """触发图片节点生成（异步 Celery 任务）"""
    item = get_owned_item_or_404(db, item_id, current_user.id)
    if item.item_type != CanvasItemType.IMAGE.value:
        raise HTTPException(status_code=400, detail="该节点不是图片节点")

    prompt = _resolve_prompt(item, body.prompt, body.prompt_tokens)
    _ensure_prompt_or_tokens(item, prompt, body.prompt_tokens)

    model_config = _resolved_model_config(db, str(current_user.id))
    _, gen = prepare_image_generation(
        db,
        item_id=item_id,
        user_id=str(current_user.id),
        request_payload={
            "prompt": prompt,
            "prompt_tokens": body.prompt_tokens,
            "prompt_plain_text": body.prompt_plain_text,
            "model": body.model,
            "ratio": body.ratio,
            "model_key": body.model_key,
            "reference_image_urls": body.reference_image_urls,
            "image_style": body.image_style,
        },
    )
    task = generate_canvas_image.delay(str(gen.id), model_config)
    canvas_document_crud.touch(db, item.canvas_id, str(current_user.id))
    return success_response(data={
        "generation_id": str(gen.id),
        "item_id": item_id,
        "task_id": task.id,
        "status": gen.status,
        "last_run_status": item.last_run_status,
    })


@router.post("/items/{item_id}/generate-video")
def generate_video(
    item_id: str,
    body: CanvasGenerateVideoRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """触发视频节点生成（异步 Celery + 回调）"""
    item = get_owned_item_or_404(db, item_id, current_user.id)
    if item.item_type != CanvasItemType.VIDEO.value:
        raise HTTPException(status_code=400, detail="该节点不是视频节点")

    prompt = _resolve_prompt(item, body.prompt, body.prompt_tokens)
    _ensure_prompt_or_tokens(item, prompt, body.prompt_tokens)

    resolved = ConfigReader(db).get_config(str(current_user.id))
    if not getattr(resolved, "video_model", None):
        raise HTTPException(status_code=400, detail="当前暂无视频生成模型，请先在设置中心配置")
    model_config = resolved.to_dict()

    _, gen = prepare_video_generation(
        db,
        item_id=item_id,
        user_id=str(current_user.id),
        request_payload={
            "prompt": prompt,
            "prompt_tokens": body.prompt_tokens,
            "prompt_plain_text": body.prompt_plain_text,
            "model": body.model,
            "ratio": body.ratio,
            "resolution": body.resolution,
            "duration": body.duration,
            "first_frame_url": body.first_frame_url,
            "last_frame_url": body.last_frame_url,
            "reference_image_urls": body.reference_image_urls,
        },
    )
    task = generate_canvas_video.delay(str(gen.id), model_config)
    canvas_document_crud.touch(db, item.canvas_id, str(current_user.id))
    return success_response(data={
        "generation_id": str(gen.id),
        "item_id": item_id,
        "task_id": task.id,
        "status": gen.status,
        "last_run_status": item.last_run_status,
    })


@router.post("/seedance_callback")
def canvas_video_callback(body: dict):
    """Seedance 视频生成回调入口（无需登录态）"""
    process_canvas_video_callback.delay(body)
    return success_response(data={"received": True})


# ── 节点生成历史 ───────────────────────────────────────

@router.get("/items/{item_id}/generations/{generation_id}")
def get_generation(
    item_id: str,
    generation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """查询单条生成结果（前端轮询用）"""
    gen = get_owned_generation_or_404(db, item_id, generation_id, current_user.id)
    return success_response(data=serialize_generation(gen))


@router.get("/items/{item_id}/generations")
def list_generations(
    item_id: str,
    page: int = 1,
    size: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """分页查询节点的生成历史（按创建时间倒序）"""
    get_owned_item_or_404(db, item_id, current_user.id)
    result = canvas_item_generation_crud.list_by_item(db, item_id, page=page, size=size)
    return success_response(data={
        "list": [serialize_generation(g) for g in result["list"]],
        "total": result["total"],
        "page": result["page"],
        "size": result["size"],
    })


@router.post("/items/{item_id}/generations/{generation_id}/apply")
def apply_generation(
    item_id: str,
    generation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """应用某次历史生成（把 output_json 回写到节点 content_json 和 last_output_json）"""
    item = get_owned_item_or_404(db, item_id, current_user.id)
    gen = get_owned_generation_or_404(db, item_id, generation_id, current_user.id)
    apply_generation_output_to_item(db, item, gen, user_id=current_user.id)
    canvas_document_crud.touch(db, item.canvas_id, str(current_user.id))
    region = user_crud.get_region(user_id=str(current_user.id), db=db)
    return success_response(data=serialize_item(item, region=region))


@router.get("/items/{item_id}/generations/{generation_id}/model-call")
def get_generation_model_call(
    item_id: str,
    generation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """查询某次生成关联的模型调用日志详情（model_call_log）"""
    from app.services.model_call_log import ModelCallLogService

    gen = get_owned_generation_or_404(db, item_id, generation_id, current_user.id)
    if not gen.model_call_log_id:
        return success_response(data=None)
    detail = ModelCallLogService.get_detail(db, gen.model_call_log_id)
    return success_response(data=detail.model_dump(mode="json"))


# ── 资产导入（上传 / 资产中心） ─────────────────────────

@router.post("/items/{item_id}/register-asset")
def register_asset(
    item_id: str,
    body: RegisterAssetRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """把上传 / 资产中心的二进制资产登记到节点

    前端已直传 COS 拿到 url，这里只做：建一条 status=completed 的 generation 记录 +
    把 url 写到 item.content_json 和 last_output_json。
    """
    item = get_owned_item_or_404(db, item_id, current_user.id)
    if item.item_type not in (
        CanvasItemType.IMAGE.value, CanvasItemType.VIDEO.value, CanvasItemType.AUDIO.value,
    ):
        raise HTTPException(status_code=400, detail="仅图片/视频/音频节点支持资产导入")
    if not body.url:
        raise HTTPException(status_code=400, detail="url 不能为空")

    # audio 时长 ≤15s 校验（对齐短视频 audio_url 限制）
    if item.item_type == CanvasItemType.AUDIO.value:
        duration = body.duration
        if duration is None:
            raise HTTPException(status_code=400, detail="音频缺少 duration 字段")
        if duration > MAX_AUDIO_DURATION_SECONDS:
            raise HTTPException(
                status_code=400,
                detail=f"音频时长超过 {MAX_AUDIO_DURATION_SECONDS}s 限制",
            )

    # 统一存永久 URL + cos_key，响应前端时再转签名
    permanent_url = cos_client.to_permanent(body.url)
    cos_key = body.cos_key or cos_client.url_to_key(body.url)
    output_json = {"url": permanent_url}
    if body.thumbnail_url:
        output_json["thumbnail_url"] = cos_client.to_permanent(body.thumbnail_url)
    if cos_key:
        output_json["image_key"] = cos_key
        output_json["cos_key"] = cos_key
    if item.item_type == CanvasItemType.AUDIO.value and body.duration is not None:
        output_json["duration"] = body.duration

    # 上传来源（source=upload）才同步火山；资产中心导入（source=asset_center）跳过
    sync_to_volc = (body.source or "upload") == "upload"

    input_json = {
        "source": body.source or "upload",
        "filename": body.filename,
        "size": body.size,
        "asset_id": body.asset_id,
    }

    gen = create_completed_generation(
        db, item, output_json, input_json,
        user_id=str(current_user.id),
        sync_to_volc=sync_to_volc,
    )

    # 生成封面：图片复用 thumbnail_url（无则回退到 url 本身）；视频下载后提取首帧；音频无封面
    cover_url: Optional[str] = None
    try:
        if item.item_type == CanvasItemType.IMAGE.value:
            cover_url = output_json.get("thumbnail_url") or permanent_url
        elif item.item_type == CanvasItemType.VIDEO.value:
            from app.utils.video_processing import download_video
            video_data = download_video(permanent_url)
            cover_url = extract_and_upload_video_cover(video_data, str(current_user.id))
    except Exception as e:
        # 封面生成失败不阻塞主流程
        from app.core.logging import logger
        logger.warning(f"[canvas] register-asset 封面生成失败 item={item.id} err={e}")
    if cover_url:
        item.cover_url = cover_url
        db.add(item)
        db.commit()
        db.refresh(item)

    canvas_document_crud.touch(db, item.canvas_id, str(current_user.id))
    region = user_crud.get_region(user_id=str(current_user.id), db=db)
    return success_response(data={
        "generation_id": str(gen.id),
        "url": cos_client.to_signed(permanent_url, allow_external=True) or permanent_url,
        "thumbnail_url": cos_client.to_signed(output_json.get("thumbnail_url"), allow_external=True) or output_json.get("thumbnail_url"),
        "cover_url": cos_client.to_signed(cover_url, allow_external=True) or cover_url,
        "item": serialize_item(item, region=region),
    })


@router.post("/items/{item_id}/upload-asset")
async def upload_asset(
    item_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """接收 multipart 文件，后端转存到 COS 后写一条 completed generation 记录

    用于绕开浏览器直传 COS 的 CORS 限制。
    HEIC 由前端预先转码为 JPEG 后再上传（与短视频页面一致），后端不接受 image/heic。
    音频时长 ≤15s 校验由前端 getMediaMetadata 预检，后端不解析音频本身（与短视频一致）。
    """
    item = get_owned_item_or_404(db, item_id, current_user.id)
    if item.item_type not in (
        CanvasItemType.IMAGE.value, CanvasItemType.VIDEO.value, CanvasItemType.AUDIO.value,
    ):
        raise HTTPException(status_code=400, detail="仅图片/视频/音频节点支持资产导入")

    content_type = (file.content_type or "").lower()
    filename = file.filename or "upload.bin"
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="文件内容为空")

    biz = validate_upload_and_pick_biz(item.item_type, content_type, raw)
    ext = infer_ext_by_mime(content_type)

    cos_key = cos_client.generate_unique_key(
        category="canvas", biz=biz, user_id=str(current_user.id), ext=ext,
    )
    ok = cos_client.upload_object(raw, cos_key, content_type=content_type or "application/octet-stream")
    if not ok:
        raise HTTPException(status_code=500, detail="COS 上传失败")
    permanent_url = cos_client.get_permanent_url(cos_key)

    output_json = {"url": permanent_url, "image_key": cos_key, "cos_key": cos_key}
    input_json = {
        "source": "upload",
        "filename": filename,
        "size": len(raw),
        "content_type": content_type,
    }

    gen = create_completed_generation(
        db, item, output_json, input_json,
        user_id=str(current_user.id),
    )

    # 生成封面：图片用 PIL 压缩成缩略图；视频用 ffmpeg 提取首帧；音频无封面。失败不阻塞主流程。
    cover_url: Optional[str] = None
    try:
        if item.item_type == CanvasItemType.IMAGE.value:
            from app.utils.thumbnail import generate_thumbnail_bytes
            thumb_bytes = generate_thumbnail_bytes(raw)
            thumb_key = cos_client.generate_unique_key(
                category="canvas", biz="cover", user_id=str(current_user.id), ext="jpg",
            )
            if cos_client.upload_object(thumb_bytes, thumb_key, content_type="image/jpeg"):
                cover_url = cos_client.get_permanent_url(thumb_key)
        elif item.item_type == CanvasItemType.VIDEO.value:
            cover_url = extract_and_upload_video_cover(raw, str(current_user.id))
    except Exception as e:
        from app.core.logging import logger
        logger.warning(f"[canvas] upload-asset 封面生成失败 item={item.id} err={e}")
    if cover_url:
        item.cover_url = cover_url
        db.add(item)
        db.commit()
        db.refresh(item)

    canvas_document_crud.touch(db, item.canvas_id, str(current_user.id))
    region = user_crud.get_region(user_id=str(current_user.id), db=db)
    return success_response(data={
        "generation_id": str(gen.id),
        "url": cos_client.to_signed(permanent_url, allow_external=True) or permanent_url,
        "thumbnail_url": None,
        "cover_url": cos_client.to_signed(cover_url, allow_external=True) or cover_url,
        "item": serialize_item(item, region=region),
    })


# ── 同步火山 / 保存到资产中心 ────────────────────────────

@router.post("/items/{item_id}/sync-volcano")
def sync_item_volcano(
    item_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """把节点已生成的资产同步到当前 region 的火山/BytePlus 私域资产库（幂等）

    返回 {volc_asset_id, byteplus_asset_id, region, asset_type}，供前端按 region 判断「已同步」状态。
    """
    from app.utils.user_volc_sync import sync_user_asset_to_volc

    item = get_owned_item_or_404(db, item_id, current_user.id)
    if item.item_type not in (
        CanvasItemType.IMAGE.value, CanvasItemType.VIDEO.value, CanvasItemType.AUDIO.value,
    ):
        raise HTTPException(status_code=400, detail="仅图片/视频/音频节点支持同步火山")

    # 没有输出 url 直接拒绝
    out = item.last_output_json or {}
    if not (out.get("url") or out.get("image_url") or out.get("video_url") or out.get("audio_url")):
        raise HTTPException(status_code=400, detail="节点尚无可同步的资产")

    default_name = {
        CanvasItemType.IMAGE.value: "canvas-image",
        CanvasItemType.VIDEO.value: "canvas-video",
        CanvasItemType.AUDIO.value: "canvas-audio",
    }.get(item.item_type, "canvas-asset")
    try:
        sync_user_asset_to_volc(
            db, str(current_user.id), item,
            display_name=item.title or default_name,
            raise_on_error=True,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"同步火山失败：{e}")

    db.refresh(item)
    canvas_document_crud.touch(db, item.canvas_id, str(current_user.id))
    region = user_crud.get_region(user_id=str(current_user.id), db=db)
    return success_response(data={
        "volc_asset_id": item.volc_asset_id,
        "byteplus_asset_id": item.byteplus_asset_id,
        "region": region,
        "asset_type": item.asset_type,
        "item": serialize_item(item, region=region),
    })


@router.post("/items/{item_id}/save-to-asset-center")
def save_item_to_asset_center(
    item_id: str,
    body: SaveToAssetCenterRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """把节点资产保存到资产中心（角色 / 场景 / 道具 / 音色）

    - image 节点 + asset_kind=character/location/prop
    - audio 节点（asset_kind 强制为 voice）

    folder_id 与 new_folder_name 二选一，都为空则不分组。新建分组归属当前用户。

    节点已沉淀了永久 URL / 封面 / 火山资产 ID，这里直接复用：
    - 资产 image_url / custom_voice_url 直接存 COS key（与 asset_hub 一致）
    - 资产 thumbnail_url 取节点 cover_url 的 cos_key
    - 资产 volc_private_asset_id / byteplus_asset_id 直接复制节点的对应字段
      （节点未同步火山时为空，资产中心首次使用时按需触发同步）
    故本接口不再调用 sync_user_asset_to_volc，避免重复入库。

    保存成功后将 canvas_item.saved_to_asset_center 置 True（避免重复入库）。
    """
    item = get_owned_item_or_404(db, item_id, current_user.id)
    if item.item_type not in (CanvasItemType.IMAGE.value, CanvasItemType.AUDIO.value):
        raise HTTPException(status_code=400, detail="仅图片/音频节点支持保存到资产中心")
    out = item.last_output_json or {}
    asset_url = (
        out.get("url") or out.get("image_url")
        or out.get("video_url") or out.get("audio_url")
    )
    if not asset_url:
        raise HTTPException(status_code=400, detail="节点尚无可保存的资产")

    # 解析资产组（folder_id 优先；new_folder_name 时新建）
    folder_id = _resolve_folder_id(db, current_user, body.folder_id, body.new_folder_name)

    created = _persist_item_asset(
        db, item,
        asset_kind=body.asset_kind,
        folder_id=folder_id,
        asset_name=body.name,
        current_user=current_user,
    )

    # 标记节点已入库资产中心，避免重复保存
    item.saved_to_asset_center = True
    db.add(item)
    db.commit()
    db.refresh(item)

    canvas_document_crud.touch(db, item.canvas_id, str(current_user.id))
    return success_response(data={**created, "saved_to_asset_center": True})


@router.post("/documents/{document_id}/batch-save-to-asset-center")
def batch_save_items_to_asset_center(
    document_id: str,
    body: BatchSaveToAssetCenterRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """批量保存到资产中心：按节点自身 asset_tag / item_type 自动归类

    候选过滤：
      - image 节点 + asset_tag∈{character/location/prop}
      - audio 节点
      - saved_to_asset_center=False
      - last_output_json 含可保存 url
    folder_id / new_folder_name 由调用方提供，组在批量入库开始前解析（一次性创建或校验）。
    """
    doc = get_owned_document_or_404(db, document_id, current_user.id)
    items = canvas_item_crud.get_document_items(db, doc.id)

    def _has_asset_url(it):
        out = it.last_output_json or {}
        return bool(out.get("url") or out.get("image_url") or out.get("video_url") or out.get("audio_url"))

    candidates = [
        it for it in items
        if not bool(it.saved_to_asset_center)
        and (
            (it.item_type == CanvasItemType.IMAGE.value and it.asset_tag in ("character", "location", "prop"))
            or it.item_type == CanvasItemType.AUDIO.value
        )
        and _has_asset_url(it)
    ]

    # 一次性解析资产组（新建或校验），后续循环复用同一 folder_id
    folder_id = _resolve_folder_id(db, current_user, body.folder_id, body.new_folder_name)

    saved: list[dict] = []
    skipped: list[dict] = []
    for it in candidates:
        try:
            _persist_item_asset(
                db, it,
                asset_kind=it.asset_tag or "voice",
                folder_id=folder_id,
                asset_name=it.title,
                current_user=current_user,
            )
            it.saved_to_asset_center = True
            saved.append({"id": it.id, "item_type": it.item_type, "kind": it.asset_tag or "voice"})
        except HTTPException as e:
            skipped.append({"id": it.id, "reason": e.detail or str(e)})
        except Exception as e:  # noqa: BLE001
            skipped.append({"id": it.id, "reason": str(e)})

    db.commit()
    if saved:
        canvas_document_crud.touch(db, doc.id, str(current_user.id))

    return success_response(data={
        "saved": saved,
        "skipped": skipped,
        "folder_id": folder_id,
        "candidate_total": len(candidates),
    })


def _resolve_folder_id(
    db: Session, current_user: User,
    folder_id: Optional[str], new_folder_name: Optional[str],
) -> Optional[str]:
    """保存到资产中心：解析资产组（folder_id 优先；new_folder_name 时新建；都为空则不分组）"""
    import uuid

    if not folder_id and new_folder_name:
        new_folder = global_asset_folder_crud.create(db=db, obj_in={
            "id": str(uuid.uuid4()),
            "user_id": str(current_user.id),
            "owner_user_id": _owner_user_id(current_user),
            "name": new_folder_name.strip(),
        })
        return str(new_folder.id)
    if folder_id:
        folder = global_asset_folder_crud.get(db=db, id=folder_id)
        if not folder or str(folder.user_id) != str(current_user.id):
            raise HTTPException(status_code=400, detail="资产组不存在或无权访问")
        return str(folder.id)
    return None


def _persist_item_asset(
    db: Session, item,
    *,
    asset_kind: str,
    folder_id: Optional[str],
    asset_name: Optional[str],
    current_user: User,
) -> dict:
    """单节点资产入库核心逻辑（无 folder 解析、无 HTTP 校验，仅按 item_type 写入全局资产）。

    被 save_item_to_asset_center（单节点）和 batch_save_items_to_asset_center（批量）复用。
    """
    import uuid

    out = item.last_output_json or {}
    asset_url = (
        out.get("url") or out.get("image_url")
        or out.get("video_url") or out.get("audio_url")
    )
    if not asset_url:
        raise HTTPException(status_code=400, detail="节点尚无可保存的资产")

    name = (asset_name or item.title or "").strip() or "未命名资产"
    owner_user_id = _owner_user_id(current_user)
    # 资产中心约定存 cos_key（而非完整 URL），与 asset_hub 现有写入路径一致
    cos_key = cos_client.url_to_key(asset_url) or asset_url
    # 复用节点已生成的封面图（图片=压缩缩略图；视频=ffmpeg 首帧）作为资产缩略图
    cover_cos_key = cos_client.url_to_key(item.cover_url) if item.cover_url else None
    # 复用节点已同步的火山/BytePlus 资产 ID，避免资产中心再次入库
    src_volc_id = item.volc_asset_id
    src_byteplus_id = item.byteplus_asset_id
    duration_value = out.get("duration")

    if item.item_type == CanvasItemType.AUDIO.value:
        voice = global_voice_crud.create(db=db, obj_in={
            "id": str(uuid.uuid4()),
            "user_id": str(current_user.id),
            "owner_user_id": owner_user_id,
            "folder_id": folder_id,
            "name": name,
            "voice_type": "uploaded",
            "custom_voice_url": cos_key,
            "duration": int(duration_value) if duration_value is not None else None,
            "volc_private_asset_id": src_volc_id,
            "byteplus_asset_id": src_byteplus_id,
        })
        return {"kind": "voice", "voice": {"id": str(voice.id), "name": voice.name}}

    if item.item_type == CanvasItemType.IMAGE.value:
        kind = (asset_kind or "character").strip().lower()
        if kind not in ("character", "location", "prop"):
            raise HTTPException(status_code=400, detail="asset_kind 仅支持 character/location/prop")
        if kind == "character":
            character = global_character_crud.create(db=db, obj_in={
                "id": str(uuid.uuid4()),
                "user_id": str(current_user.id),
                "owner_user_id": owner_user_id,
                "folder_id": folder_id,
                "name": name,
            })
            appearance = global_character_appearance_crud.create(db=db, obj_in={
                "id": str(uuid.uuid4()),
                "character_id": str(character.id),
                "appearance_index": 0,
                "change_reason": "画布导入",
                "image_url": cos_key,
                "thumbnail_url": cover_cos_key,
                "descriptions": "[]",
                "image_urls": "[]",
                "previous_image_urls": "[]",
                "volc_private_asset_id": src_volc_id,
                "byteplus_asset_id": src_byteplus_id,
                "gen_status": "completed",
            })
            return {
                "kind": "character",
                "character": {"id": str(character.id), "name": character.name},
                "appearance": {"id": str(appearance.id)},
            }
        # location / prop 走 GlobalLocation
        location = global_location_crud.create(db=db, obj_in={
            "id": str(uuid.uuid4()),
            "user_id": str(current_user.id),
            "owner_user_id": owner_user_id,
            "folder_id": folder_id,
            "name": name,
            "asset_kind": kind,
        })
        location_image = global_location_image_crud.create(db=db, obj_in={
            "id": str(uuid.uuid4()),
            "location_id": str(location.id),
            "image_index": 0,
            "image_url": cos_key,
            "thumbnail_url": cover_cos_key,
            "is_selected": True,
            "volc_private_asset_id": src_volc_id,
            "byteplus_asset_id": src_byteplus_id,
            "gen_status": "completed",
        })
        return {
            "kind": kind,
            "location": {"id": str(location.id), "name": location.name},
            "image": {"id": str(location_image.id)},
        }

    raise HTTPException(status_code=400, detail="仅图片/音频节点支持保存到资产中心")
