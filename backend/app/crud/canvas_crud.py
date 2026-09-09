"""无限画布 CRUD 操作"""
import io
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import HTTPException
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.enums.canvas import CanvasGenerationStatus, CanvasItemRunStatus, CanvasItemType
from app.enums.user import UserRegion
from app.models.canvas import (
    CanvasDocument, CanvasItem, CanvasConnection, CanvasItemGeneration,
)
from app.crud.base_crud import CRUDBase
from app.crud.user_crud import user_crud
from app.schemas.canvas import (
    CanvasDocumentCreate, CanvasDocumentUpdate,
    CanvasItemCreate, CanvasItemUpdate,
    CanvasConnectionCreate,
)
from app.utils.tencent_cos_utils import cos_client


_logger = logging.getLogger(__name__)


# ── 业务规则常量 ─────────────────────────────────────────
# 允许的连线方向：文本→图片 / 文本→视频 / 图片→图片 / 图片→视频 / 音频→视频 / 视频→视频（参考视频，要求源已同步火山）/ 组合→视频（按组内子节点展开）
ALLOWED_CONNECTION_TARGETS: dict[str, set[str]] = {
    "text": {"text", "image", "video"},
    "image": {"image", "video"},
    "audio": {"video"},
    "video": {"video"},
}
# 视频生成参考资产上限（对齐短视频页面 seedance_task_builder.MAX_REFERENCE_IMAGES）
MAX_VIDEO_REFERENCE_IMAGES = 9
MAX_VIDEO_REFERENCE_DURATION_SECONDS = 15

# 上传 MIME 前缀（HEIC 由前端预转 JPEG 后再上传）
IMAGE_MIME_PREFIXES = ("image/jpeg", "image/png", "image/webp", "image/gif", "image/bmp")
VIDEO_MIME_PREFIXES = ("video/mp4", "video/webm", "video/quicktime")
AUDIO_MIME_PREFIXES = (
    "audio/mpeg", "audio/mp3", "audio/wav", "audio/x-wav", "audio/wave",
    "audio/ogg", "audio/m4a", "audio/x-m4a", "audio/aac", "audio/x-aac",
    "audio/mp4", "audio/x-mp4",
)
# 上传大小上限（对齐短视频页面）
MAX_IMAGE_BYTES = 30 * 1024 * 1024  # 30MB
MAX_VIDEO_BYTES = 50 * 1024 * 1024  # 50MB
MAX_AUDIO_BYTES = 15 * 1024 * 1024  # 15MB（与短视频音频一致）
# 音频时长上限（秒）：对齐短视频 audio_url ≤15s
MAX_AUDIO_DURATION_SECONDS = 15
# 图片尺寸约束（对齐短视频页面）
IMAGE_MIN_SIDE = 300
IMAGE_MAX_SIDE = 6000
IMAGE_RATIO_MIN = 0.4
IMAGE_RATIO_MAX = 2.5

# MIME → 扩展名映射（用于生成 COS key）
_MIME_EXT_MAP = {
    "image/jpeg": "jpg", "image/png": "png", "image/webp": "webp",
    "image/gif": "gif", "image/bmp": "bmp",
    "video/mp4": "mp4", "video/webm": "webm", "video/quicktime": "mov",
    "audio/mpeg": "mp3", "audio/mp3": "mp3",
    "audio/wav": "wav", "audio/x-wav": "wav", "audio/wave": "wav",
    "audio/ogg": "ogg", "audio/m4a": "m4a", "audio/x-m4a": "m4a",
    "audio/aac": "aac", "audio/x-aac": "aac",
    "audio/mp4": "m4a", "audio/x-mp4": "m4a",
}


class CRUDCanvasDocument(CRUDBase[CanvasDocument, CanvasDocumentCreate, CanvasDocumentUpdate]):
    """画布 CRUD"""

    def get_user_documents(self, db: Session, user_id: str):
        """获取用户的所有画布，按最近打开时间倒序（无则回退到创建时间）"""
        return (
            self.get_queryset(db)
            .filter(CanvasDocument.user_id == user_id)
            .order_by(
                func.coalesce(
                    CanvasDocument.last_opened_at,
                    CanvasDocument.create_time,
                ).desc()
            )
            .all()
        )

    def get_document(self, db: Session, document_id: str, user_id: str) -> Optional[CanvasDocument]:
        """获取指定用户的画布"""
        return (
            self.get_queryset(db)
            .filter(CanvasDocument.id == document_id, CanvasDocument.user_id == user_id)
            .first()
        )

    def touch_opened(self, db: Session, document_id: str) -> None:
        """更新最近打开时间（用 Core update 单字段，避免触发 onupdate 把 update_time 也刷新）"""
        from sqlalchemy import update as _update
        db.execute(
            _update(CanvasDocument)
            .where(
                CanvasDocument.id == document_id,
                CanvasDocument.is_deleted == False,  # noqa: E712
            )
            .values(last_opened_at=datetime.now())
        )
        db.commit()

    def touch(self, db: Session, document_id: str, uid: Optional[str] = None) -> None:
        """更新画布最近修改时间（用于列表卡片显示）

        节点/连线变动不会自动触发 document 行的 onupdate，需要在 endpoint 层显式调用。
        """
        doc = db.get(CanvasDocument, document_id)
        if doc and not doc.is_deleted:
            doc.update_time = datetime.now()
            if uid:
                doc.update_uid = uid
            db.add(doc)
            db.commit()

    def soft_cascade_delete(self, db: Session, doc: CanvasDocument) -> None:
        """级联软删：画布下所有节点、连线、生成记录一起标记删除"""
        now = datetime.now()
        for item in canvas_item_crud.get_document_items(db, doc.id):
            item.is_deleted = True
            item.delete_time = now
            db.add(item)
        for conn in canvas_connection_crud.get_document_connections(db, doc.id):
            conn.is_deleted = True
            conn.delete_time = now
            db.add(conn)
        doc.is_deleted = True
        doc.delete_time = now
        db.add(doc)
        db.commit()


class CRUDCanvasItem(CRUDBase[CanvasItem, CanvasItemCreate, CanvasItemUpdate]):
    """节点 CRUD"""

    def get_document_items(self, db: Session, canvas_id: str):
        return (
            self.get_queryset(db)
            .filter(CanvasItem.canvas_id == canvas_id)
            .order_by(CanvasItem.create_time.asc())
            .all()
        )

    def get_item(self, db: Session, item_id: str) -> Optional[CanvasItem]:
        return self.get_queryset(db).filter(CanvasItem.id == item_id).first()

    def get_children(self, db: Session, parent_id: str) -> list[CanvasItem]:
        """获取某 group 节点的所有子节点（仅单层）"""
        return (
            self.get_queryset(db)
            .filter(CanvasItem.parent_id == parent_id)
            .all()
        )

    def detach_children(self, db: Session, parent_id: str) -> int:
        """把指向 parent_id 的所有子节点 parent_id 置空（解组）
        返回解组的子节点数量。调用方负责事务提交。
        """
        children = self.get_children(db, parent_id)
        for c in children:
            c.parent_id = None
            db.add(c)
        db.flush()
        return len(children)

    def batch_update_items(self, db: Session, canvas_id: str, updates: list[dict]) -> None:
        """批量更新节点字段（position_x/position_y/parent_id）

        - 校验所有 update.id 属于该 canvas
        - parent_id 非空时，必须指向同 canvas 内 item_type=group 的节点
        - parent_id 不允许指向自己
        - 单层约束：group 节点自身不能再有 parent_id
        """
        if not updates:
            return

        ids = [u["id"] for u in updates if u.get("id")]
        # 批量拉一次该 canvas 的节点，做归属与类型校验
        existing = {it.id: it for it in self.get_document_items(db, canvas_id)}
        for uid in ids:
            if uid not in existing:
                raise HTTPException(status_code=400, detail=f"节点不存在或不属于该画布: {uid}")

        for u in updates:
            item = existing.get(u["id"])
            if not item:
                continue
            new_parent = u.get("parent_id", None)
            # exclude_unset 语义：parent_id 字段不在 dict 里就跳过；空字符串视为解组
            if "parent_id" in u:
                if new_parent:
                    # 空字符串统一规范化为 None
                    if isinstance(new_parent, str) and not new_parent.strip():
                        new_parent = None
                if new_parent:
                    if new_parent == item.id:
                        raise HTTPException(status_code=400, detail="parent_id 不能指向自己")
                    parent_item = existing.get(new_parent)
                    if not parent_item:
                        raise HTTPException(status_code=400, detail=f"父节点不存在或不属于该画布: {new_parent}")
                    if parent_item.item_type != CanvasItemType.GROUP.value:
                        raise HTTPException(status_code=400, detail="parent_id 必须指向 group 类型的节点")
                    if item.item_type == CanvasItemType.GROUP.value:
                        raise HTTPException(status_code=400, detail="不支持嵌套组合（group 节点不能再被打组）")
                item.parent_id = new_parent
            if "position_x" in u and u["position_x"] is not None:
                item.position_x = u["position_x"]
            if "position_y" in u and u["position_y"] is not None:
                item.position_y = u["position_y"]
            db.add(item)
        db.commit()


class CRUDCanvasConnection(CRUDBase[CanvasConnection, CanvasConnectionCreate, dict]):
    """连线 CRUD"""

    def get_document_connections(self, db: Session, canvas_id: str):
        return (
            self.get_queryset(db)
            .filter(CanvasConnection.canvas_id == canvas_id)
            .all()
        )

    def get_connections_by_item(self, db: Session, canvas_id: str, item_id: str):
        """获取与某节点相关的所有未删除连线（源或目标任一命中）"""
        return (
            self.get_queryset(db)
            .filter(
                CanvasConnection.canvas_id == canvas_id,
                or_(
                    CanvasConnection.source_item_id == item_id,
                    CanvasConnection.target_item_id == item_id,
                ),
            )
            .all()
        )

    def soft_delete_by_item(self, db: Session, canvas_id: str, item_id: str) -> None:
        """软删与某节点相关的所有连线（节点删除时调用）"""
        now = datetime.now()
        for conn in self.get_connections_by_item(db, canvas_id, item_id):
            conn.is_deleted = True
            conn.delete_time = now
            db.add(conn)
        db.flush()


class CRUDCanvasItemGeneration(CRUDBase[CanvasItemGeneration, dict, dict]):
    """生成历史 CRUD"""

    def list_by_item(
        self, db: Session, item_id: str, page: int = 1, size: int = 10,
    ) -> Dict[str, Any]:
        """按节点分页查询生成历史（创建时间倒序）"""
        page = max(1, page)
        size = max(1, min(50, size))
        q = (
            self.get_queryset(db)
            .filter(CanvasItemGeneration.item_id == item_id)
            .order_by(CanvasItemGeneration.create_time.desc())
        )
        total = q.count()
        rows = q.offset((page - 1) * size).limit(size).all()
        return {"list": rows, "total": total, "page": page, "size": size}

    def get(self, db: Session, generation_id: str) -> Optional[CanvasItemGeneration]:
        """按 id 查询单条生成记录（含未删除校验）"""
        return self.get_queryset(db).filter(CanvasItemGeneration.id == generation_id).first()


canvas_document_crud = CRUDCanvasDocument(CanvasDocument)
canvas_item_crud = CRUDCanvasItem(CanvasItem)
canvas_connection_crud = CRUDCanvasConnection(CanvasConnection)
canvas_item_generation_crud = CRUDCanvasItemGeneration(CanvasItemGeneration)


# ── 序列化 ─────────────────────────────────────────────

def serialize_document(doc: CanvasDocument) -> dict:
    return {
        "id": doc.id,
        "title": doc.title,
        "description": doc.description,
        "thumbnail_url": doc.thumbnail_url,
        "last_opened_at": doc.last_opened_at.isoformat() if doc.last_opened_at else None,
        "create_time": doc.create_time.isoformat() if doc.create_time else None,
        "update_time": doc.update_time.isoformat() if doc.update_time else None,
    }


def _fill_url_from_source(data: Any) -> Any:
    """视频节点兜底：若 url 为空且 source_url 存在，把 source_url 复制到 url。

    异步上传 COS 完成前 output_json.url / last_output_json.url 为空，此时返回回调源地址
    让前端能立即播放。源地址是外部 URL，sign_urls_in_json 会原样返回不签名。
    """
    if isinstance(data, dict):
        out = dict(data)
        if not out.get("url") and out.get("source_url"):
            out["url"] = out["source_url"]
        return out
    return data


def serialize_item(item: CanvasItem, region: Optional[str] = None) -> dict:
    """节点序列化：last_output_json/content_json 中的 COS 永久 URL 转签名返回前端

    region 非空时一并返回 region / volc_asset_id / byteplus_asset_id / asset_kind_hint，
    供前端按 region 判断「同步火山」按钮显隐。region 由调用方通过 user_crud.get_region 计算后传入。
    """
    item_type = (item.item_type or "").lower()
    asset_kind_hint = {"image": "image", "video": "video", "audio": "audio"}.get(item_type)

    return {
        "id": item.id,
        "canvas_id": item.canvas_id,
        "item_type": item.item_type,
        "title": item.title or "",
        "position_x": item.position_x or 0,
        "position_y": item.position_y or 0,
        "width": item.width or 240,
        "height": item.height or 120,
        "z_index": item.z_index or 0,
        "content_json": cos_client.sign_urls_in_json(item.content_json),
        "generation_config_json": item.generation_config_json,
        "last_output_json": cos_client.sign_urls_in_json(_fill_url_from_source(item.last_output_json)),
        "last_run_status": item.last_run_status or "idle",
        "last_run_error": item.last_run_error,
        "cover_url": cos_client.to_signed(item.cover_url, allow_external=True) or item.cover_url,
        "volc_asset_id": item.volc_asset_id,
        "byteplus_asset_id": item.byteplus_asset_id,
        "asset_tag": item.asset_tag,
        "saved_to_asset_center": bool(item.saved_to_asset_center),
        "voice_url": cos_client.to_signed(item.voice_url, allow_external=True) or item.voice_url,
        "voice_cos_key": item.voice_cos_key,
        "parent_id": item.parent_id,
        "region": region,
        "asset_kind_hint": asset_kind_hint,
        "create_time": item.create_time.isoformat() if item.create_time else None,
        "update_time": item.update_time.isoformat() if item.update_time else None,
    }


def serialize_connection(conn: CanvasConnection) -> dict:
    return {
        "id": conn.id,
        "canvas_id": conn.canvas_id,
        "source_item_id": conn.source_item_id,
        "target_item_id": conn.target_item_id,
        "source_handle": conn.source_handle or "right",
        "target_handle": conn.target_handle or "left",
    }


def serialize_generation(g: CanvasItemGeneration) -> dict:
    """生成记录序列化：output_json 中的 COS 永久 URL 转签名返回前端"""
    return {
        "id": str(g.id),
        "item_id": str(g.item_id),
        "generation_type": g.generation_type,
        "status": g.status,
        "input_json": g.input_json,
        "output_json": cos_client.sign_urls_in_json(_fill_url_from_source(g.output_json)),
        "error_msg": g.error_msg,
        "ark_task_id": g.ark_task_id,
        "model_call_log_id": g.model_call_log_id,
        "started_at": g.started_at.isoformat() if g.started_at else None,
        "finished_at": g.finished_at.isoformat() if g.finished_at else None,
        "create_time": g.create_time.isoformat() if g.create_time else None,
    }


# ── 归属校验 ───────────────────────────────────────────

def get_owned_document_or_404(db: Session, document_id: str, user_id: str) -> CanvasDocument:
    """获取属于当前用户的画布，不存在或归属错误则 404"""
    doc = canvas_document_crud.get_document(db, document_id, user_id)
    if not doc:
        raise HTTPException(status_code=404, detail="画布不存在")
    return doc


def get_owned_item_or_404(db: Session, item_id: str, user_id: str) -> CanvasItem:
    """获取节点并校验画布归属，不存在或不属于该用户则 404/404"""
    item = canvas_item_crud.get_item(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="节点不存在")
    get_owned_document_or_404(db, item.canvas_id, user_id)
    return item


def get_owned_generation_or_404(
    db: Session, item_id: str, generation_id: str, user_id: str,
) -> CanvasItemGeneration:
    """获取生成记录并校验节点 + 画布归属"""
    get_owned_item_or_404(db, item_id, user_id)
    gen = db.get(CanvasItemGeneration, generation_id)
    if not gen or gen.item_id != item_id or gen.is_deleted:
        raise HTTPException(status_code=404, detail="生成记录不存在")
    return gen


# ── 连线方向规则 ───────────────────────────────────────

def validate_connection_direction(
    db: Session, user_id: str, source: CanvasItem, target: CanvasItem,
) -> None:
    """连线方向校验：仅允许 文本→文本 / 文本→图片 / 文本→视频 / 图片→图片 / 图片→视频 / 音频→视频 / 视频→视频

    已生成资产的图片/视频节点连线到视频时，要求 source 已在当前 region 同步至火山资产库；
    未生成资产的节点允许连线（后续生成时可再同步）。
    """
    if source.id == target.id:
        raise HTTPException(status_code=400, detail="不能连接到自己")
    allowed_targets = ALLOWED_CONNECTION_TARGETS.get(source.item_type, set())
    if target.item_type not in allowed_targets:
        raise HTTPException(
            status_code=400,
            detail=f"连线方向不允许：{source.item_type}→{target.item_type}（仅支持 文本→文本 / 文本→图片 / 文本→视频 / 图片→图片 / 图片→视频 / 音频→视频 / 视频→视频）",
        )

    # 图片→视频 / 视频→视频：已生成资产但未同步火山则拒绝
    if target.item_type == CanvasItemType.VIDEO.value and source.item_type in (
        CanvasItemType.IMAGE.value, CanvasItemType.VIDEO.value,
    ):
        out = source.last_output_json or {}
        has_output = bool(out.get("url") or out.get("image_url") or out.get("video_url"))
        if has_output:
            _ensure_video_synced(db, user_id, source)


def _ensure_video_synced(db: Session, user_id: str, video_item: CanvasItem) -> None:
    """视频参考：source 必须已在当前 region 同步至火山资产库"""
    region = user_crud.get_region(user_id=user_id, db=db)
    synced_id = (
        video_item.byteplus_asset_id if region == UserRegion.OVERSEAS.value else video_item.volc_asset_id
    )
    if not synced_id:
        raise HTTPException(status_code=400, detail="请先同步至火山再使用")


# ── 上传校验 ───────────────────────────────────────────

def validate_image_size(raw: bytes) -> None:
    """图片尺寸校验：宽高均 300-6000px，宽高比 0.4-2.5"""
    try:
        from PIL import Image
        with Image.open(io.BytesIO(raw)) as img:
            w, h = img.size
    except Exception:
        raise HTTPException(status_code=400, detail="无法解析图片尺寸，可能不是有效图片")
    if w < IMAGE_MIN_SIDE or h < IMAGE_MIN_SIDE:
        raise HTTPException(
            status_code=400,
            detail=f"图片尺寸过小：{w}x{h}，要求宽高均 ≥ {IMAGE_MIN_SIDE}px",
        )
    if w > IMAGE_MAX_SIDE or h > IMAGE_MAX_SIDE:
        raise HTTPException(
            status_code=400,
            detail=f"图片尺寸过大：{w}x{h}，要求宽高均 ≤ {IMAGE_MAX_SIDE}px",
        )
    ratio = w / h if h else 0
    if ratio < IMAGE_RATIO_MIN or ratio > IMAGE_RATIO_MAX:
        raise HTTPException(
            status_code=400,
            detail=f"图片宽高比 {ratio:.2f} 超出允许范围 [{IMAGE_RATIO_MIN}, {IMAGE_RATIO_MAX}]",
        )


def validate_upload_and_pick_biz(item_type: str, content_type: str, raw: bytes) -> str:
    """按节点类型 + MIME + 大小校验上传文件，返回 biz（image/video/audio）

    HEIC 由前端预转 JPEG 后再上传，后端不接受 image/heic。
    audio 时长 ≤15s 的校验由调用方拿到 duration 后另行执行（见 register_asset / upload_asset）。
    """
    content_type = (content_type or "").lower()
    if item_type == CanvasItemType.IMAGE.value:
        if not content_type.startswith(IMAGE_MIME_PREFIXES):
            raise HTTPException(
                status_code=400,
                detail=f"图片节点仅支持 {IMAGE_MIME_PREFIXES}（HEIC 请先在前端转码）",
            )
        if len(raw) > MAX_IMAGE_BYTES:
            raise HTTPException(status_code=400, detail=f"图片大小超过 {MAX_IMAGE_BYTES // 1024 // 1024}MB")
        validate_image_size(raw)
        return "image"
    if item_type == CanvasItemType.VIDEO.value:
        if not content_type.startswith(VIDEO_MIME_PREFIXES):
            raise HTTPException(status_code=400, detail=f"视频节点仅支持 {VIDEO_MIME_PREFIXES}")
        if len(raw) > MAX_VIDEO_BYTES:
            raise HTTPException(status_code=400, detail=f"视频大小超过 {MAX_VIDEO_BYTES // 1024 // 1024}MB")
        return "video"
    if item_type == CanvasItemType.AUDIO.value:
        if not content_type.startswith(AUDIO_MIME_PREFIXES):
            raise HTTPException(
                status_code=400,
                detail=f"音频节点仅支持 {AUDIO_MIME_PREFIXES}",
            )
        if len(raw) > MAX_AUDIO_BYTES:
            raise HTTPException(status_code=400, detail=f"音频大小超过 {MAX_AUDIO_BYTES // 1024 // 1024}MB")
        return "audio"
    raise HTTPException(status_code=400, detail="仅图片/视频/音频节点支持资产导入")


def infer_ext_by_mime(content_type: str) -> str:
    """根据 MIME 推断扩展名，未命中回退 bin"""
    return _MIME_EXT_MAP.get((content_type or "").lower(), "bin")


# ── 业务：写完成态生成记录 + 资产库同步 ────────────────

def create_completed_generation(
    db: Session,
    item: CanvasItem,
    output_json: dict,
    input_json: dict,
    user_id: str,
    sync_to_volc: bool = True,
) -> CanvasItemGeneration:
    """把外部资产登记为 status=completed 的 generation 记录，
    并把 output_json 回写到 item.content_json / last_output_json。

    用于"上传本地文件 / 从资产中心导入"路径——绕过 LLM 生成，
    直接把已有 URL 当作节点输出。
    sync_to_volc=True 时同步到当前 region 资产库（图片/视频节点）。
    """
    now = datetime.now()
    gen = CanvasItemGeneration(
        item_id=item.id,
        document_id=item.canvas_id,
        user_id=user_id,
        generation_type=item.item_type,
        input_json=input_json,
        output_json=output_json,
        status=CanvasGenerationStatus.COMPLETED.value,
        started_at=now,
        finished_at=now,
    )
    db.add(gen)

    content = dict(item.content_json or {})
    content.update(output_json)
    item.content_json = content
    item.last_output_json = output_json
    item.last_run_status = CanvasItemRunStatus.COMPLETED.value
    item.last_run_error = None
    item.update_uid = user_id
    db.add(item)
    db.commit()

    if sync_to_volc and item.item_type in (
        CanvasItemType.IMAGE.value, CanvasItemType.VIDEO.value, CanvasItemType.AUDIO.value,
    ):
        try:
            from app.utils.user_volc_sync import sync_user_asset_to_volc
            default_name = {
                CanvasItemType.VIDEO.value: "canvas-video",
                CanvasItemType.AUDIO.value: "canvas-audio",
                CanvasItemType.IMAGE.value: "canvas-image",
            }.get(item.item_type, "canvas-asset")
            sync_user_asset_to_volc(db, str(user_id), item, display_name=item.title or default_name)
        except Exception as e:
            # 同步失败不阻塞主流程，仅日志
            _logger.warning(f"[canvas] 资产库同步失败 item={item.id} err={e}")
    db.refresh(gen)
    return gen


def apply_generation_output_to_item(
    db: Session, item: CanvasItem, gen: CanvasItemGeneration, user_id: str,
) -> None:
    """把历史生成的 output_json 回写到节点 content_json / last_output_json

    仅 status=completed 的生成可应用；按节点类型取对应字段。
    """
    if gen.status != CanvasGenerationStatus.COMPLETED.value:
        raise HTTPException(status_code=400, detail="仅可应用已完成的生成")

    output = dict(gen.output_json or {})
    content_patch: dict = {}
    last_output: dict = {}

    if item.item_type == CanvasItemType.TEXT.value:
        text = output.get("text")
        body = output.get("body") or text
        if body is not None:
            content_patch["body"] = body
            last_output["body"] = body
        if text is not None:
            content_patch["text"] = text
            last_output["text"] = text
    elif item.item_type == CanvasItemType.IMAGE.value:
        url = output.get("url")
        if url:
            content_patch["url"] = url
            last_output["url"] = url
            thumb = output.get("thumbnail_url")
            if thumb:
                content_patch["thumbnail_url"] = thumb
                last_output["thumbnail_url"] = thumb
            # 同步封面：优先用 thumbnail，回退到 url 本身
            item.cover_url = thumb or url
    elif item.item_type == CanvasItemType.VIDEO.value:
        url = output.get("url")
        if url:
            content_patch["url"] = url
            last_output["url"] = url
        # 视频封面独立存放在 output.cover_url（生成回调时写入）
        cover = output.get("cover_url")
        if cover:
            item.cover_url = cover

    if content_patch:
        content = dict(item.content_json or {})
        content.update(content_patch)
        item.content_json = content
    if last_output:
        item.last_output_json = last_output

    item.last_run_status = CanvasItemRunStatus.COMPLETED.value
    item.last_run_error = None
    item.update_uid = user_id
    db.add(item)
    db.commit()
