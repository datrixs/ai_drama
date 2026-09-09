"""视频生成 API 端点"""
import json

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.celery_tasks.video_generation import (
    batch_generate_scripts_task,
    concat_video_task,
    generate_multimodal_episode_video_task,
    generate_multimodal_script_task,
    generate_segment_video_task,
    generate_single_video_task,
    process_video_callback,
)
from app.crud.episode_crud import episode_crud
from app.crud.episode_concat_record_crud import episode_concat_record_crud
from app.crud.storyboard_crud import storyboard_crud
from app.enums.video import EpisodeStatus, StoryboardStatus
from app.models import User
from app.models.project_asset import Episode, Storyboard
from app.schemas.episode_concat_record import (
    EpisodeConcatRecordListResponse,
    EpisodeConcatRecordResponse,
)
from app.schemas.video_generation import (
    MultimodalVideoGenerateRequest,
    ScriptGenerateRequest,
    ScriptTextResponse,
    ScriptTextUpdateRequest,
    SegmentVideoGenerateRequest,
    VideoConcatRequest,
    VideoGenerateRequest,
)
from app.services.multimodal_script_service import MultimodalScriptService, _get_asset_descriptors
from app.services.script_text_converter import script_text_converter
from app.utils.response import success_response

router = APIRouter()


# ── 单镜头视频生成 ──────────────────────────────────────────

@router.post("/projects/{project_id}/generate")
def generate_video(project_id: str, body: VideoGenerateRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    storyboard = db.query(Storyboard).filter(Storyboard.id == body.storyboard_id, Storyboard.is_deleted == False).first()
    if not storyboard:
        raise HTTPException(status_code=404, detail="分镜片段不存在")

    generation_options = {
        "model": body.model, "resolution": body.resolution, "ratio": body.ratio,
        "duration": body.duration, "generate_audio": body.generate_audio,
        "first_frame_url": body.first_frame_url, "last_frame_url": body.last_frame_url,
    }

    generate_single_video_task.delay(body.storyboard_id, generation_options, body.model)
    return success_response(data={"task_id": body.storyboard_id, "status": StoryboardStatus.VIDEO_GENERATING})


# ── 多片段成片视频生成 ──────────────────────────────────────

@router.post("/projects/{project_id}/episodes/{episode_id}/generate-multimodal")
def generate_multimodal_video(project_id: str, episode_id: str, body: MultimodalVideoGenerateRequest,
                               db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    episode = db.query(Episode).filter(Episode.id == episode_id).first()
    if not episode:
        raise HTTPException(status_code=404, detail="剧集不存在")

    generate_multimodal_episode_video_task.delay(episode_id, body.model)
    return success_response(data={"task_id": episode_id, "status": "submitted"})


# ── 生成多模态脚本 ──────────────────────────────────────────

@router.post("/projects/{project_id}/episodes/{episode_id}/generate-script")
def generate_script(project_id: str, episode_id: str, body: ScriptGenerateRequest,
                     db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    episode = db.query(Episode).filter(Episode.id == episode_id).first()
    if not episode:
        raise HTTPException(status_code=404, detail="剧集不存在")

    episode.status = EpisodeStatus.GENERATING
    db.commit()

    generate_multimodal_script_task.delay(episode_id, project_id, current_user.id)
    return success_response(data={"episode_id": episode_id, "status": EpisodeStatus.GENERATING})


# ── 批量生成脚本 ──────────────────────────────────────────

@router.post("/projects/{project_id}/episodes/batch-generate-scripts")
def batch_generate_scripts(project_id: str, db: Session = Depends(get_db),
                           current_user: User = Depends(get_current_user)):
    episodes = episode_crud.get_by_project(db, project_id)
    pending_eps = [ep for ep in episodes if ep.status == EpisodeStatus.PENDING]
    if not pending_eps:
        return success_response(data={"total": 0, "episode_ids": [], "message": "无需生成"})

    items = []
    for ep in pending_eps:
        ep.status = EpisodeStatus.GENERATING
        items.append({"episode_id": ep.id, "episode_number": ep.episode_number})

    db.commit()

    batch_generate_scripts_task.delay(items, project_id, current_user.id)

    return success_response(data={
        "total": len(items),
        "episode_ids": [i["episode_id"] for i in items],
    })


# ── 按 segment 索引生成视频 ────────────────────────────────

@router.post("/projects/{project_id}/episodes/{episode_id}/generate-segment")
def generate_segment_video(project_id: str, episode_id: str, body: SegmentVideoGenerateRequest,
                            db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    episode = db.query(Episode).filter(Episode.id == episode_id).first()
    if not episode:
        raise HTTPException(status_code=404, detail="剧集不存在")

    storyboard = db.query(Storyboard).filter(
        Storyboard.episode_id == episode_id,
        Storyboard.segment_index == body.segment_index,
        Storyboard.is_deleted == False,
    ).first()
    if not storyboard:
        raise HTTPException(status_code=404, detail="分镜片段不存在")

    generation_options = {
        "segment_index": body.segment_index, "model": body.model,
        "resolution": body.resolution, "ratio": body.ratio, "duration": body.duration,
        "generate_audio": body.generate_audio,
        "first_frame_url": body.first_frame_url, "last_frame_url": body.last_frame_url,
    }

    generate_segment_video_task.delay(episode_id, body.segment_index, generation_options, body.model)
    return success_response(data={"task_id": storyboard.id, "status": StoryboardStatus.VIDEO_GENERATING, "segment_index": body.segment_index})


# ── 脚本纯文本 ──────────────────────────────────────────────

@router.get("/projects/{project_id}/episodes/{episode_id}/script-text")
def get_script_text(project_id: str, episode_id: str, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    episode = db.query(Episode).filter(Episode.id == episode_id).first()
    if not episode:
        raise HTTPException(status_code=404, detail="剧集不存在")

    plain_text = episode.script_plain_text or ""
    if not plain_text:
        # 从 storyboard 的 video_prompt 拼接
        all_storyboards = storyboard_crud.get_by_episode(db, episode_id)
        plain_text = "\n".join(sb.video_prompt for sb in all_storyboards if sb.video_prompt)
        if plain_text:
            episode.script_plain_text = plain_text
            db.commit()

    return success_response(data=ScriptTextResponse(
        episode_id=episode_id, plain_text=plain_text,
        segment_count=len(episode.script_json.get("segments", [])) if episode.script_json else 0,
        has_json=episode.script_json is not None,
    ))


@router.put("/projects/{project_id}/episodes/{episode_id}/script-text")
def update_script_text(project_id: str, episode_id: str, body: ScriptTextUpdateRequest,
                        db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    episode = db.query(Episode).filter(Episode.id == episode_id).first()
    if not episode:
        raise HTTPException(status_code=404, detail="剧集不存在")

    # 每个片段独立解析与更新，无需依赖整段 plain_text 拆分
    for seg_item in body.segments:
        parsed = script_text_converter.plain_text_to_script(seg_item.plain_text)
        if not parsed or not parsed.get("segments"):
            # 自由文本兜底：整段文本作为单个片段的 sceneSummary
            parsed_segment = {
                "segmentIndex": seg_item.segment_index,
                "segmentIntent": "",
                "sceneSummary": seg_item.plain_text.strip(),
                "shotTransition": "",
                "shots": [],
            }
            style_kw = ""
        else:
            parsed_segment = parsed["segments"][0]
            parsed_segment["segmentIndex"] = seg_item.segment_index
            style_kw = (
                parsed.get("styleAndKeywords", "")
                or parsed_segment.get("styleAndKeywords", "")
            )

        MultimodalScriptService(db).update_single_storyboard(
            db, episode_id, seg_item.segment_index,
            segment_plain_text=seg_item.plain_text,
            parsed_segment=parsed_segment,
            style_and_keywords=style_kw,
        )

    # 重建 episode 级数据，保持 script_json / script_plain_text 与 storyboard 表一致
    all_storyboards = storyboard_crud.get_by_episode(db, episode_id)
    segments_json = []
    for sb in all_storyboards:
        try:
            segments_json.append(json.loads(sb.raw_text) if sb.raw_text else {})
        except json.JSONDecodeError:
            segments_json.append({})

    style_kw_top = segments_json[0].get("styleAndKeywords", "") if segments_json else ""
    episode.script_json = {
        "schemaVersion": 2,
        "styleAndKeywords": style_kw_top,
        "sceneSummary": "",
        "segments": segments_json,
    }

    # 直接拼接各片段的 video_prompt（用户编辑的原始文本），避免 round-trip 转换差异
    episode.script_plain_text = "\n".join(
        sb.video_prompt for sb in all_storyboards if sb.video_prompt
    )

    db.commit()

    return success_response(data=ScriptTextResponse(
        episode_id=episode_id,
        plain_text=episode.script_plain_text,
        segment_count=len(all_storyboards),
        has_json=True,
    ))


# ── 视频拼接 ────────────────────────────────────────────────

@router.post("/projects/{project_id}/episodes/{episode_id}/concat-video")
def concat_episode_video(project_id: str, episode_id: str, body: VideoConcatRequest,
                          db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """整集视频合成：严格校验所有片段已完成，固化源视频 URL 后异步执行"""
    # 校验剧集归属
    episode = episode_crud.get(id=episode_id, db=db)
    if not episode or episode.project_id != project_id:
        raise HTTPException(status_code=404, detail="剧集不存在")

    # 严格校验：所有片段必须 status=video_completed 且有 video_url
    segments = storyboard_crud.get_by_episode(db, episode_id)
    if not segments:
        raise HTTPException(status_code=400, detail="该剧集暂无分镜片段，无法合成")
    if len(segments) < 2:
        raise HTTPException(status_code=400, detail="至少需要 2 个片段才能合成整集")

    incomplete = [s for s in segments if s.status != StoryboardStatus.VIDEO_COMPLETED or not s.video_url]
    if incomplete:
        raise HTTPException(
            status_code=400,
            detail=f"还有 {len(incomplete)} 个片段未完成视频生成，无法合成",
        )

    # 阻止并发合成：若已有 pending/processing 任务，拒绝重复触发
    active = episode_concat_record_crud.get_active_by_episode(db, episode_id)
    if active:
        raise HTTPException(status_code=400, detail="已有合成任务进行中，请等待完成后再试")

    # 固化源视频 URL 列表（按 segment_index 排序）
    ordered = sorted(segments, key=lambda s: s.segment_index)
    source_urls = [{"segment_index": s.segment_index, "video_url": s.video_url} for s in ordered]

    # 创建 pending 合成记录
    record = episode_concat_record_crud.create(db, obj_in={
        "user_id": current_user.id,
        "episode_id": episode_id,
        "project_id": project_id,
        "source_video_urls": source_urls,
        "segment_count": len(ordered),
        "status": "pending",
        "create_uid": current_user.id,
    })

    concat_video_task.delay(record.id)
    return success_response(data={
        "task_id": record.id,
        "record_id": record.id,
        "status": "pending",
        "segment_count": len(ordered),
    })


@router.get("/projects/{project_id}/episodes/{episode_id}/concat-records")
def list_concat_records(project_id: str, episode_id: str,
                        db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    """获取剧集的整集合成历史（按时间倒序）"""
    records = episode_concat_record_crud.get_by_episode(db, episode_id)
    items = [EpisodeConcatRecordResponse.model_validate(r) for r in records]
    return success_response(data=EpisodeConcatRecordListResponse(items=items, total=len(items)))


# ── 视频生成回调 ────────────────────────────────────────────

@router.post("/seedance_callback")
def video_callback(body: dict):
    """接收 Seedance SDK 的成片视频生成回调，立即返回，业务异步处理"""
    logger.info(f"成片视频回调请求: {json.dumps(body, ensure_ascii=False)}")

    process_video_callback.delay(body)
    return success_response(data={"received": True})
