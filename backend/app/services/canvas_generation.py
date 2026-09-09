"""无限画布节点生成 service

参考 AICON 的 prepare/process 流程：
- prepare_xxx_generation：写一条 generation 记录（status=pending），并标记 item 进入 processing
- process_xxx_generation：Celery 任务里实际调用 provider，结果回写 item + generation

阶段 3.1：文本节点（LLM）
阶段 3.2：图片节点（ModelCaller.generate_image + COS）
阶段 3.3：视频节点（SeedanceClient + 回调）
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.core.logging import logger
from app.core.model_provider import ModelCaller
from app.enums.canvas import (
    CanvasGenerationStatus, CanvasItemRunStatus, CanvasItemType,
)
from app.models.canvas import CanvasItem, CanvasItemGeneration
from app.services.config_reader import ConfigReader
from app.services.image_processor import download_and_store_image, ratio_to_size
from app.services.llm import LLMError
from app.services.seedance_client import SeedanceClient
from app.services.seedance_task_builder import build_single_shot_task
from app.services.video_callback_handler import VideoCallbackHandler
from app.prompts.constants import get_art_style_prompt
from app.utils.callback_url import build_callback_url, CallbackPath
from app.utils.canvas_prompt import (
    build_prompt_for_llm,
    build_video_prompt_with_labels,
    collect_media_refs_by_role,
)
from app.utils.tencent_cos_utils import cos_client
from app.utils.video_processing import (
    download_video,
    extract_and_upload_video_cover,
    extract_first_frame,
    save_video_local,
    upload_short_video_to_cos,
)


CANVAS_TEXT_SYSTEM_PROMPT = "你是一个专业的中文创作助手。请直接输出适合写入画布节点的正文内容。"

# 默认图片生成参数（可被 generation_config_json 覆盖）
DEFAULT_IMAGE_MODEL_KEY = "character_model"
DEFAULT_IMAGE_RATIO = "1:1"

# 默认视频生成参数
DEFAULT_VIDEO_RATIO = "16:9"
DEFAULT_VIDEO_RESOLUTION = "720p"
DEFAULT_VIDEO_DURATION = 5


def _build_generation_record(
    db: Session,
    item: CanvasItem,
    user_id: str,
    generation_type: str,
    request_payload: dict,
) -> CanvasItemGeneration:
    """新建一条 pending 状态的生成记录，并把节点置为 pending"""
    gen = CanvasItemGeneration(
        item_id=item.id,
        document_id=item.canvas_id,
        user_id=user_id,
        generation_type=generation_type,
        input_json=request_payload,
        output_json={},
        status=CanvasGenerationStatus.PENDING.value,
    )
    db.add(gen)
    item.last_run_status = CanvasItemRunStatus.PENDING.value
    item.last_run_error = None
    db.add(item)
    db.flush()
    return gen


def _mark_processing(db: Session, item: CanvasItem, gen: CanvasItemGeneration) -> None:
    item.last_run_status = CanvasItemRunStatus.PROCESSING.value
    gen.status = CanvasGenerationStatus.PROCESSING.value
    gen.started_at = datetime.now()
    db.add(item)
    db.add(gen)
    db.flush()


def _attach_model_call_log_id(db: Session, gen: CanvasItemGeneration, task_id: str) -> None:
    """按 task_id 反查最近一条 model_call_log，把 id 冗余写入 generation.

    文/图生成走 ModelCaller（内部已写日志，task_id=generation_id）；
    视频走 SeedanceClient.last_log_id 直接拿，不走这里。
    """
    if not task_id:
        return
    if gen.model_call_log_id:
        return
    from app.models.model_call_log import ModelCallLog
    log = (
        db.query(ModelCallLog)
        .filter(ModelCallLog.task_id == task_id)
        .order_by(ModelCallLog.call_time.desc())
        .first()
    )
    if log:
        gen.model_call_log_id = log.id
        db.add(gen)
        db.flush()


def _sync_item_asset_to_volc(db: Session, item: CanvasItem, user_id: str, display_name: str = "") -> None:
    """把图片节点同步到当前 region 对应的火山/BytePlus 资产库。

    幂等：已同步（volc_asset_id 或 byteplus_asset_id 已存在对应 region）则直接返回。
    失败不抛异常，仅日志告警，不影响主流程。
    """
    try:
        from app.utils.user_volc_sync import sync_user_asset_to_volc
        sync_user_asset_to_volc(db, str(user_id), item, display_name=display_name or "")
    except Exception as e:
        logger.warning(f"[canvas] 资产库同步失败 item={item.id} err={e}")


def _mark_completed(
    db: Session,
    item: CanvasItem,
    gen: CanvasItemGeneration,
    *,
    output: dict,
    item_content_patch: Optional[dict] = None,
    item_last_output: Optional[dict] = None,
) -> None:
    gen.status = CanvasGenerationStatus.COMPLETED.value
    gen.finished_at = datetime.now()
    # 合并 model_call_log_id（若已设置），便于历史审计直接读 output_json
    merged_output = dict(output or {})
    if gen.model_call_log_id and not merged_output.get("model_call_log_id"):
        merged_output["model_call_log_id"] = gen.model_call_log_id
    gen.output_json = merged_output
    item.last_run_status = CanvasItemRunStatus.COMPLETED.value
    item.last_run_error = None
    if item_content_patch is not None:
        content = dict(item.content_json or {})
        content.update(item_content_patch)
        item.content_json = content
    if item_last_output is not None:
        item.last_output_json = item_last_output
    db.add(item)
    db.add(gen)
    db.flush()
    _publish_generation_event(gen, item, CanvasGenerationStatus.COMPLETED.value)


def _mark_failed(
    db: Session, item: CanvasItem, gen: CanvasItemGeneration, error_msg: str
) -> None:
    gen.status = CanvasGenerationStatus.FAILED.value
    gen.finished_at = datetime.now()
    gen.error_msg = error_msg
    item.last_run_status = CanvasItemRunStatus.FAILED.value
    item.last_run_error = error_msg
    db.add(item)
    db.add(gen)
    db.flush()
    _publish_generation_event(gen, item, CanvasGenerationStatus.FAILED.value, error_msg)


def _publish_generation_event(
    gen: CanvasItemGeneration,
    item: CanvasItem,
    status: str,
    error_msg: Optional[str] = None,
) -> None:
    """生成状态变更 → 推 WS 事件，前端订阅后可直接 patch 节点

    载荷结构对齐前端 useCanvasGeneration.applyFromWsEvent 期望。
    推送前把图片 URL 转签名 URL（DB 中存的是永久 URL，前端访问需临时签名）。
    """
    try:
        from app.core.ws import ws_manager
        from app.enums.base import WSEventType
        from app.utils.tencent_cos_utils import cos_client

        ws_manager.publish_asset_hub_event(
            str(gen.user_id),
            WSEventType.CANVAS_GENERATION_PROGRESS,
            {
                "document_id": str(gen.document_id),
                "item_id": str(gen.item_id),
                "generation_id": str(gen.id),
                "generation_type": gen.generation_type,
                "status": status,
                "error_msg": error_msg,
                "item_patch": {
                    "content_json": cos_client.sign_urls_in_json(item.content_json or {}),
                    "last_output_json": cos_client.sign_urls_in_json(item.last_output_json or {}),
                    "last_run_status": item.last_run_status,
                    "last_run_error": item.last_run_error or None,
                    "cover_url": cos_client.to_signed(item.cover_url, allow_external=True) or item.cover_url,
                    # 同步状态一并下发，前端无需轮询/重拉即可正确展示"已同步火山"角标
                    "volc_asset_id": item.volc_asset_id,
                    "byteplus_asset_id": item.byteplus_asset_id,
                },
            },
        )
    except Exception as e:
        logger.warning(f"[canvas] WS 推送失败 gen={gen.id} status={status} err={e}")


# ── 文本节点 ──────────────────────────────────────────

def prepare_text_generation(
    db: Session,
    item_id: str,
    user_id: str,
    request_payload: dict,
) -> tuple[CanvasItem, CanvasItemGeneration]:
    """API 层调用：写 pending 记录，返回 (item, generation) 给上层 dispatch 任务"""
    item = db.get(CanvasItem, item_id)
    if not item:
        raise ValueError(f"节点 {item_id} 不存在")
    if item.item_type != CanvasItemType.TEXT.value:
        raise ValueError(f"节点 {item_id} 不是文本节点")

    prompt_tokens = request_payload.get("prompt_tokens") or []
    prompt_plain_text = (request_payload.get("prompt_plain_text") or "").strip()
    raw_prompt = (request_payload.get("prompt") or "").strip()

    # prompt 解析优先级：
    # 1) 传了 prompt_tokens → 用 build_prompt_for_llm 解析（mention 内联展开）
    # 2) 传了 raw prompt → 直接用
    # 3) 都没传 → 回退到节点 content_json.prompt_tokens / prompt
    if prompt_tokens:
        resolved_prompt = build_prompt_for_llm(db, prompt_tokens, current_item_id=item_id)
        if not resolved_prompt:
            # mention 全部失效或为空，回退到 raw
            resolved_prompt = raw_prompt
    else:
        resolved_prompt = raw_prompt

    if not resolved_prompt:
        node_cj = item.content_json or {}
        node_tokens = node_cj.get("prompt_tokens") or []
        if node_tokens:
            resolved_prompt = build_prompt_for_llm(db, node_tokens, current_item_id=item_id)
        if not resolved_prompt:
            resolved_prompt = (node_cj.get("prompt") or "").strip()

    if not resolved_prompt:
        raise ValueError("prompt 不能为空")

    payload = {
        "prompt": resolved_prompt,
        "prompt_tokens": prompt_tokens or (item.content_json or {}).get("prompt_tokens") or [],
        "prompt_plain_text": prompt_plain_text,
        "model": request_payload.get("model"),
        "body_snapshot": (item.content_json or {}).get("body"),
        "content_snapshot": dict(item.content_json or {}),
    }

    gen = _build_generation_record(db, item, user_id, "text", payload)
    db.commit()
    return item, gen


def process_text_generation(
    db: Session,
    generation_id: str,
    model_config: dict,
) -> dict[str, Any]:
    """Celery 任务里调用：实际调 LLM，回写结果"""
    gen = db.get(CanvasItemGeneration, generation_id)
    if not gen:
        raise ValueError(f"生成记录 {generation_id} 不存在")
    item = db.get(CanvasItem, gen.item_id)
    if not item:
        raise ValueError(f"节点 {gen.item_id} 不存在")

    _mark_processing(db, item, gen)
    db.commit()

    request_payload = gen.input_json or {}
    prompt = request_payload.get("prompt") or ""

    try:
        caller = ModelCaller.from_config_snapshot(model_config, db=db)
        result = caller.call(
            model_key="analysis_model",
            prompt=prompt,
            system_prompt=CANVAS_TEXT_SYSTEM_PROMPT,
            temperature=0.7,
            max_tokens=4096,
            timeout=180,
            task_id=generation_id,
        )
        text = (result.content or "").strip()
        if not text:
            raise LLMError("LLM 返回内容为空")

        _attach_model_call_log_id(db, gen, task_id=generation_id)
        _mark_completed(
            db, item, gen,
            output={
                "text": text,
                "body": text,
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
                "total_tokens": result.total_tokens,
                "model": request_payload.get("model"),
            },
            item_content_patch={"body": text},
            item_last_output={"body": text, "text": text},
        )
        db.commit()
        logger.info(f"[canvas] text generation completed gen={generation_id} item={item.id} len={len(text)}")
        return {"generation_id": generation_id, "status": "completed", "text": text}

    except Exception as exc:
        _mark_failed(db, item, gen, str(exc))
        db.commit()
        logger.exception(f"[canvas] text generation failed gen={generation_id}")
        raise


# ── 图片节点 ──────────────────────────────────────────

def prepare_image_generation(
    db: Session,
    item_id: str,
    user_id: str,
    request_payload: dict,
) -> tuple[CanvasItem, CanvasItemGeneration]:
    """API 层调用：写 pending 记录，返回 (item, generation)"""
    item = db.get(CanvasItem, item_id)
    if not item:
        raise ValueError(f"节点 {item_id} 不存在")
    if item.item_type != CanvasItemType.IMAGE.value:
        raise ValueError(f"节点 {item_id} 不是图片节点")

    # 解析 prompt：优先 prompt_tokens（mention 内联展开），回退到 raw prompt，再回退到节点
    prompt_tokens = request_payload.get("prompt_tokens") or []
    if prompt_tokens:
        prompt = build_prompt_for_llm(db, prompt_tokens, current_item_id=item_id)
        # 收集上游图片作为图生图参考（图片生成模型只接受 HTTP(S) URL，关闭 Asset://）
        media_refs = collect_media_refs_by_role(
            db, prompt_tokens, current_item_id=item_id, user_id=user_id,
            prefer_asset_protocol=False,
        )
    else:
        prompt = (request_payload.get("prompt") or "").strip()
        media_refs = {
            "reference_image_urls": list(request_payload.get("reference_image_urls") or []),
        }
    if not prompt:
        prompt = ((item.content_json or {}).get("prompt") or "").strip()
    if not prompt:
        raise ValueError("prompt 不能为空")

    prompt_plain_text = (request_payload.get("prompt_plain_text") or "").strip()

    # 合并生成参数：节点 generation_config_json 为底，request 覆盖
    cfg = dict(item.generation_config_json or {})
    cfg.update({
        k: v for k, v in (request_payload or {}).items()
        if k not in {"prompt", "reference_image_urls"} and v is not None
    })
    ratio = (cfg.get("ratio") or DEFAULT_IMAGE_RATIO).strip()
    cfg["ratio"] = ratio
    size = ratio_to_size(ratio)

    # 图片风格注入：预设风格（american-comic/chinese-comic/japanese-anime/realistic）
    # 对应一段风格描述，作为前缀拼到 prompt；custom 或未知风格 → get_art_style_prompt 返回空串，不注入，
    # 即"不限制风格"，完全由用户 prompt 自由控制画风。
    image_style = (request_payload.get("image_style") or "").strip()
    style_desc = get_art_style_prompt(image_style) if image_style else ""
    if style_desc and style_desc not in prompt:
        prompt = f"{style_desc}，{prompt}"

    payload = {
        "prompt": prompt,
        "prompt_tokens": prompt_tokens or (item.content_json or {}).get("prompt_tokens") or [],
        "prompt_plain_text": prompt_plain_text,
        "model": cfg.get("model"),
        "model_key": cfg.get("model_key") or DEFAULT_IMAGE_MODEL_KEY,
        "ratio": ratio,
        "size": size,
        "n": int(cfg.get("n") or 1),
        "image_style": image_style or None,
        "reference_image_urls": media_refs["reference_image_urls"],
        "content_snapshot": dict(item.content_json or {}),
    }

    gen = _build_generation_record(db, item, user_id, "image", payload)
    db.commit()
    return item, gen


def _extract_image_url(result: dict) -> Optional[str]:
    """从 generate_image 结果中取 URL 或 b64_json"""
    data = result.get("data") or []
    if not data:
        return None
    first = data[0] if isinstance(data, list) else {}
    return first.get("url") or first.get("b64_json")


def process_image_generation(
    db: Session,
    generation_id: str,
    model_config: dict,
) -> dict[str, Any]:
    """Celery 任务里调用：调文生图 → 下载并上传 COS → 回写"""
    gen = db.get(CanvasItemGeneration, generation_id)
    if not gen:
        raise ValueError(f"生成记录 {generation_id} 不存在")
    item = db.get(CanvasItem, gen.item_id)
    if not item:
        raise ValueError(f"节点 {gen.item_id} 不存在")

    _mark_processing(db, item, gen)
    db.commit()

    request_payload = gen.input_json or {}
    prompt = request_payload.get("prompt") or ""
    model_key = request_payload.get("model_key") or DEFAULT_IMAGE_MODEL_KEY
    # 页面选了具体模型名（如 seeddream）时优先使用，否则回退到 model_key 解析用户配置
    model_name_override = (request_payload.get("model") or "").strip() or None
    size = request_payload.get("size") or "2048x2048"
    n = int(request_payload.get("n") or 1)
    reference_image_urls = list(request_payload.get("reference_image_urls") or [])

    try:
        caller = ModelCaller.from_config_snapshot(model_config, db=db)
        if reference_image_urls:
            # 图生图：参考图走 edit_image（gpt-image-2 / Gemini / litellm 通用路径）
            # DB 存的是永久 URL（私有 bucket），外部模型拉不到，需在调用前追加临时签名（2h TTL）
            signed_refs = [cos_client.to_signed(u, allow_external=True) or u for u in reference_image_urls]
            result = caller.edit_image(
                model_key=model_key,
                prompt=prompt,
                image_urls=signed_refs,
                size=size,
                n=n,
                timeout=300,
                task_id=generation_id,
                model_name_override=model_name_override,
            )
        else:
            # 文生图：保持原行为
            result = caller.generate_image(
                model_key=model_key,
                asset_type="canvas",
                prompt=prompt,
                size=size,
                n=n,
                timeout=300,
                task_id=generation_id,
                model_name_override=model_name_override,
            )
        image_url = _extract_image_url(result)
        if not image_url:
            raise LLMError("图片生成返回为空")

        # 下载并存储到 COS（返回 image_key, thumbnail_key）
        image_key, thumb_key = download_and_store_image(
            image_url, gen.user_id, key_prefix="canvas-image",
        )
        # DB 存永久 URL + image_key；响应前端时再转签名 URL
        permanent_url = cos_client.get_permanent_url(image_key)
        permanent_thumb = cos_client.get_permanent_url(thumb_key) if thumb_key else None

        output = {
            "url": permanent_url,
            "thumbnail_url": permanent_thumb,
            "image_key": image_key,
            "thumbnail_key": thumb_key,
            "size": size,
            "model": request_payload.get("model"),
        }
        last_output = {
            "url": permanent_url,
            "thumbnail_url": permanent_thumb,
            "image_key": image_key,
        }

        _attach_model_call_log_id(db, gen, task_id=generation_id)
        # 先把 last_output / cover_url 落到 item，再同步资产库（sync 反射读取 item.image_url），
        # 最后 _mark_completed：内部 publish WS——保证推送时 volc_asset_id 已就位，
        # 前端收到完成事件即可正确展示"已同步火山"角标。
        item.last_output_json = last_output
        if permanent_thumb:
            item.cover_url = permanent_thumb
        db.add(item)
        db.flush()
        # 同步到当前 region 资产库（火山/BytePlus），写回 volc_asset_id / byteplus_asset_id
        _sync_item_asset_to_volc(db, item, gen.user_id, display_name=item.title or "canvas-image")
        _mark_completed(
            db, item, gen,
            output=output,
            item_content_patch={"prompt": prompt},
            item_last_output=last_output,
        )
        db.commit()
        logger.info(f"[canvas] image generation completed gen={generation_id} item={item.id} key={image_key}")
        return {"generation_id": generation_id, "status": "completed", "url": permanent_url}

    except Exception as exc:
        _mark_failed(db, item, gen, str(exc))
        db.commit()
        logger.exception(f"[canvas] image generation failed gen={generation_id}")
        raise


# ── 视频节点（Seedance + 回调） ──────────────────────────────────────────

def prepare_video_generation(
    db: Session,
    item_id: str,
    user_id: str,
    request_payload: dict,
) -> tuple[CanvasItem, CanvasItemGeneration]:
    """API 层调用：写 pending 记录，返回 (item, generation)"""
    item = db.get(CanvasItem, item_id)
    if not item:
        raise ValueError(f"节点 {item_id} 不存在")
    if item.item_type != CanvasItemType.VIDEO.value:
        raise ValueError(f"节点 {item_id} 不是视频节点")

    prompt_tokens = request_payload.get("prompt_tokens") or []
    if prompt_tokens:
        # 视频节点：mention 替换为 @图片N / @视频N / @音频N 占位符，配合 reference_xxx_urls 数组
        # 让 Seedance 通过编号对齐参考素材（与成品页一致）
        prompt = build_video_prompt_with_labels(db, prompt_tokens, current_item_id=item_id)
        media_refs = collect_media_refs_by_role(db, prompt_tokens, current_item_id=item_id, user_id=user_id)
    else:
        prompt = (request_payload.get("prompt") or "").strip()
        media_refs = {
            "first_frame_url": request_payload.get("first_frame_url"),
            "last_frame_url": request_payload.get("last_frame_url"),
            "reference_image_urls": list(request_payload.get("reference_image_urls") or []),
            "reference_video_urls": list(request_payload.get("reference_video_urls") or []),
            "reference_audio_urls": list(request_payload.get("reference_audio_urls") or []),
        }
    if not prompt:
        prompt = ((item.content_json or {}).get("prompt") or "").strip()
    if not prompt:
        raise ValueError("prompt 不能为空")

    prompt_plain_text = (request_payload.get("prompt_plain_text") or "").strip()

    cfg = dict(item.generation_config_json or {})
    cfg.update({
        k: v for k, v in (request_payload or {}).items()
        if k not in {"prompt", "prompt_tokens", "prompt_plain_text",
                      "reference_image_urls", "reference_video_urls", "reference_audio_urls",
                      "first_frame_url", "last_frame_url"} and v is not None
    })

    payload = {
        "prompt": prompt,
        "prompt_tokens": prompt_tokens or (item.content_json or {}).get("prompt_tokens") or [],
        "prompt_plain_text": prompt_plain_text,
        "model": cfg.get("model"),  # None 时由 ResolvedConfig.video_model 兜底
        "ratio": (cfg.get("ratio") or DEFAULT_VIDEO_RATIO).strip(),
        "resolution": (cfg.get("resolution") or DEFAULT_VIDEO_RESOLUTION).strip(),
        "duration": int(cfg.get("duration") or DEFAULT_VIDEO_DURATION),
        "reference_image_urls": media_refs["reference_image_urls"],
        "reference_video_urls": media_refs["reference_video_urls"],
        "reference_audio_urls": media_refs["reference_audio_urls"],
        "first_frame_url": media_refs["first_frame_url"],
        "last_frame_url": media_refs["last_frame_url"],
        "content_snapshot": dict(item.content_json or {}),
    }

    gen = _build_generation_record(db, item, user_id, "video", payload)
    db.commit()
    return item, gen


def _build_video_body(payload: dict, default_model: str) -> dict:
    """构建 Seedance 请求体（单镜头模式）"""
    return build_single_shot_task(
        text_prompt=payload["prompt"],
        reference_image_urls=payload.get("reference_image_urls") or [],
        model=payload.get("model") or default_model,
        resolution=payload.get("resolution") or DEFAULT_VIDEO_RESOLUTION,
        ratio=payload.get("ratio") or DEFAULT_VIDEO_RATIO,
        duration=int(payload.get("duration") or DEFAULT_VIDEO_DURATION),
        first_frame_url=payload.get("first_frame_url"),
        last_frame_url=payload.get("last_frame_url"),
        generate_audio=True,
        reference_video_urls=payload.get("reference_video_urls") or [],
        reference_audio_urls=payload.get("reference_audio_urls") or [],
    )


def submit_canvas_video_task(
    db: Session,
    generation_id: str,
    model_config: dict,
) -> dict[str, Any]:
    """Celery 任务调用：解析用户配置 → 构建 body → 提交到 Seedance

    成功：写 ark_task_id 到 output_json，保持 status=processing，等待回调。
    失败：标记 failed。
    """
    gen = db.get(CanvasItemGeneration, generation_id)
    if not gen:
        raise ValueError(f"生成记录 {generation_id} 不存在")
    item = db.get(CanvasItem, gen.item_id)
    if not item:
        raise ValueError(f"节点 {gen.item_id} 不存在")

    # 先标 processing（如果还没标）
    if gen.status != CanvasGenerationStatus.PROCESSING.value:
        _mark_processing(db, item, gen)
        db.commit()

    request_payload = gen.input_json or {}

    try:
        config_reader = ConfigReader(db)
        resolved = config_reader.get_config(str(gen.user_id))
        default_video_model = getattr(resolved, "video_model", None) or ""
        # 页面传入 model 优先；页面与默认都为空才报错
        request_model = (request_payload.get("model") or "").strip()
        if not request_model and not default_video_model:
            raise ValueError("当前暂无视频生成模型，请先在设置中心配置或在节点上指定模型")

        body = _build_video_body(request_payload, default_video_model)

        # 解析 api_key / base_url（参考 VideoGenerationService.get_ark_api_key）
        from app.services.video_generation_service import VideoGenerationService
        service = VideoGenerationService(db, str(gen.user_id))
        api_key = service.get_ark_api_key(model_name=body.get("model"))
        base_url = service._resolve_base_url(body.get("model"))

        callback_url = build_callback_url(None, CallbackPath.CANVAS_VIDEO)
        with SeedanceClient(
            api_key,
            user_id=str(gen.user_id),
            project_id=None,
            task_id=generation_id,
            region=service.region,
            base_url=base_url,
        ) as client:
            result = client.create_video_task(body, callback_url=callback_url)

        ark_task_id = result.get("id")
        if not ark_task_id:
            raise ValueError("Seedance 未返回任务 ID")

        # 写入 ark_task_id 到 output_json（供回调匹配），状态保持 processing
        output = dict(gen.output_json or {})
        output.update({
            "ark_task_id": ark_task_id,
            "provider_response": result,
            "callback_url": callback_url,
        })
        gen.output_json = output
        gen.ark_task_id = ark_task_id  # 冗余索引列，回调反查走 SQL
        # 关联模型调用日志（SeedanceClient 内部已写日志，last_log_id 即 model_call_log.id）
        if getattr(client, "last_log_id", None):
            gen.model_call_log_id = client.last_log_id
        db.add(gen)
        db.commit()

        logger.info(f"[canvas] video task submitted gen={generation_id} ark_task_id={ark_task_id}")
        return {
            "generation_id": generation_id,
            "status": "processing",
            "ark_task_id": ark_task_id,
        }

    except Exception as exc:
        _mark_failed(db, item, gen, str(exc))
        db.commit()
        logger.exception(f"[canvas] video submit failed gen={generation_id}")
        raise


def complete_canvas_video_generation(
    db: Session,
    generation_id: str,
    video_url: str,
) -> dict[str, Any]:
    """回调成功时调用：仅更新状态、把源地址写到 last_output/source_url，立即推 WS。

    视频下载、COS 上传、首帧提取、资产库同步放到异步任务 finalize_canvas_video_assets 中处理，
    完成后再次推 WS 刷新为 COS 永久地址。源地址由前端直接播放（外部 URL 不签名）。
    """
    gen = db.get(CanvasItemGeneration, generation_id)
    if not gen:
        raise ValueError(f"生成记录 {generation_id} 不存在")
    item = db.get(CanvasItem, gen.item_id)
    if not item:
        raise ValueError(f"节点 {gen.item_id} 不存在")

    try:
        output = dict(gen.output_json or {})
        output.update({
            "url": "",  # 占位，等异步任务填充 COS 地址
            "source_url": video_url,
        })

        # last_output_json 用源地址，前端回调到达后立即可播放；
        # 清空上一次生成的封面和资产库同步标记（COS 地址变了，旧的 volc_asset_id 不再适用）
        item.last_output_json = {"url": video_url}
        item.cover_url = None
        item.volc_asset_id = None
        item.byteplus_asset_id = None
        db.add(item)
        db.flush()
        _mark_completed(
            db, item, gen,
            output=output,
            item_content_patch={"prompt": (gen.input_json or {}).get("prompt", "")},
            item_last_output={"url": video_url},
        )
        db.commit()
        logger.info(f"[canvas] video callback received gen={generation_id} source_url={video_url}")
    except Exception as exc:
        _mark_failed(db, item, gen, f"视频回调处理失败: {exc}")
        db.commit()
        logger.exception(f"[canvas] video callback handling failed gen={generation_id}")
        raise

    # delay 放到 try 外：Redis 异常不应把已成功的回调标记失败
    from app.celery_tasks.canvas_generation import upload_canvas_video_assets_task
    upload_canvas_video_assets_task.delay(str(gen.id))

    return {"generation_id": generation_id, "status": "completed", "url": video_url}


def finalize_canvas_video_assets(db: Session, generation_id: str) -> dict[str, Any] | None:
    """异步：下载源视频 → 上传 COS → 提取首帧 → 回写 output_json/item → 同步资产库 → 二次推 WS

    幂等：若 output_json.url 已是 COS 地址则直接跳过。失败由 Celery 重试 3 次。
    """
    gen = db.get(CanvasItemGeneration, generation_id)
    if not gen:
        logger.warning(f"[canvas] finalize: gen {generation_id} 不存在")
        return None
    item = db.get(CanvasItem, gen.item_id)
    if not item:
        logger.warning(f"[canvas] finalize: item 不存在 gen={generation_id}")
        return None

    output = dict(gen.output_json or {})
    existing_url = output.get("url")
    # 幂等：已有 COS 地址则跳过
    if existing_url:
        logger.info(f"[canvas] finalize: gen {generation_id} 已有 url={existing_url}，跳过")
        return None

    source_url = output.get("source_url")
    if not source_url:
        logger.warning(f"[canvas] finalize: gen {generation_id} output_json 中无 source_url")
        return None

    video_data = download_video(source_url)
    cos_url, storage_key = upload_short_video_to_cos(video_data, gen.user_id)
    final_url = cos_url or source_url

    cover_url = extract_and_upload_video_cover(video_data, str(gen.user_id))

    output.update({
        "url": final_url,
        "storage_key": storage_key,
    })
    if cover_url:
        output["cover_url"] = cover_url
    gen.output_json = output

    item.last_output_json = {"url": final_url}
    if cover_url:
        item.cover_url = cover_url
    db.add(item)
    db.add(gen)
    db.flush()

    # COS 地址就位后同步资产库（之前 source_url 同步会失败，此处真正生效）
    _sync_item_asset_to_volc(db, item, gen.user_id, display_name=item.title or "canvas-video")

    # 先 commit 再推 WS：避免崩溃重试时重复推送
    db.commit()

    # 二次推 WS：让前端把源地址刷新为 COS 永久地址
    _publish_generation_event(gen, item, CanvasGenerationStatus.COMPLETED.value)

    logger.info(f"[canvas] video assets uploaded gen={generation_id} url={final_url} cover={'yes' if cover_url else 'no'}")
    return {"generation_id": generation_id, "url": final_url, "cover_url": cover_url}


def fail_canvas_video_generation(
    db: Session,
    generation_id: str,
    error_msg: str,
) -> None:
    """回调失败时调用：标记 failed"""
    gen = db.get(CanvasItemGeneration, generation_id)
    if not gen:
        logger.warning(f"[canvas] fail_canvas_video_generation: gen {generation_id} 不存在")
        return
    item = db.get(CanvasItem, gen.item_id)
    if not item:
        logger.warning(f"[canvas] fail_canvas_video_generation: item 不存在 gen={generation_id}")
        return
    _mark_failed(db, item, gen, error_msg)
    db.commit()


def find_generation_by_ark_task_id(db: Session, ark_task_id: str) -> CanvasItemGeneration | None:
    """回调时通过 ark_task_id 找到对应的 generation 记录"""
    if not ark_task_id:
        return None
    return (
        db.query(CanvasItemGeneration)
        .filter(CanvasItemGeneration.ark_task_id == ark_task_id)
        .filter(CanvasItemGeneration.generation_type == "video")
        .filter(CanvasItemGeneration.is_deleted == False)
        .first()
    )


def dispatch_canvas_video_callback(db: Session, callback_data: dict) -> None:
    """处理 Seedance 回调（在 Celery 任务里调用）

    按 VideoCallbackHandler 分派：成功→下载/存储/标记完成；失败→标记失败。
    """
    ark_task_id = callback_data.get("id")
    gen = find_generation_by_ark_task_id(db, ark_task_id)
    if not gen:
        logger.warning(f"[canvas-callback] 找不到 generation: ark_task_id={ark_task_id}")
        return

    # 已是终态：忽略重复回调
    if gen.status in (
        CanvasGenerationStatus.COMPLETED.value,
        CanvasGenerationStatus.FAILED.value,
    ):
        logger.info(f"[canvas-callback] gen {gen.id} 已是终态({gen.status})，忽略")
        return

    handler = VideoCallbackHandler()
    handler.dispatch(
        callback_data,
        on_success=lambda video_url: complete_canvas_video_generation(db, str(gen.id), video_url),
        on_failure=lambda error_msg: fail_canvas_video_generation(db, str(gen.id), error_msg),
        on_progress=lambda: None,
    )
