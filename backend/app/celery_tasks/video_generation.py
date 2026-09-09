"""
视频生成 Celery 任务（基于 SDK + Callback）

Celery 只负责任务编排（状态流转、异常捕获、调用 Service），
业务逻辑下沉到 VideoGenerationService。
"""
import os
import shutil
import subprocess
import tempfile
from decimal import Decimal

import httpx
from app.core.celery import celery
from loguru import logger
from sqlalchemy.orm import Session

from app.core.ws import ws_manager
from app.db.session import SessionLocal
from app.enums.base import WSEventType
from app.enums.video import EpisodeStatus, StoryboardStatus
from app.models.model_call_log import ModelCallLog
from app.models.project import Project
from app.models.project_asset import Episode, Storyboard, EpisodeConcatRecord
from app.services.multimodal_script_service import MultimodalScriptService, _get_asset_descriptors
from app.services.point import PointService
from app.services.script_text_converter import script_text_converter
from app.services.seedance_client import SeedanceAPIError
from app.services.video_callback_handler import VideoCallbackHandler
from app.services.video_generation_service import VideoGenerationService
from app.utils.callback_url import CallbackPath, build_callback_url
from app.utils.tencent_cos_utils import cos_client


# ── 公共辅助 ────────────────────────────────────────────────

def _resolve_project_and_user(db: Session, episode_id: str = None, project_id: str = None):
    """通过 Episode 或 project_id 解析 project_id 和 user_id"""
    if not project_id and episode_id:
        episode = db.query(Episode).filter(Episode.id == episode_id).first()
        project_id = episode.project_id if episode else None
    project = db.query(Project).filter(Project.id == project_id).first() if project_id else None
    return project_id, (project.user_id if project else "")


def _notify(user_id: str, project_id: str, event_type: str, data: dict = None):
    ws_manager.publish_project_event(user_id, project_id, event_type, data or {})


def _fail_storyboard(db: Session, storyboard: Storyboard, error: str):
    """标记分镜失败并保存错误信息"""
    if storyboard:
        storyboard.status = StoryboardStatus.FAILED
        storyboard.gen_error = error[:500]
        db.add(storyboard)
        db.commit()


# ── Callback 处理 ───────────────────────────────────────────

@celery.task(bind=True, max_retries=0)
def process_video_callback(self, callback_data: dict):
    """处理成片视频生成回调"""
    db = SessionLocal()
    try:
        ark_task_id = callback_data.get("id")
        storyboard = db.query(Storyboard).filter(
            Storyboard.ark_task_id == ark_task_id,
            Storyboard.status == StoryboardStatus.VIDEO_GENERATING,
        ).first()
        if not storyboard:
            logger.warning(f"视频回调: 找不到对应分镜, ark_task_id={ark_task_id}")
            return

        if storyboard.status in (StoryboardStatus.FAILED, StoryboardStatus.VIDEO_COMPLETED):
            logger.info(f"视频回调: 分镜 {storyboard.id} 已是终态({storyboard.status})，忽略回调")
            return

        pid, uid = _resolve_project_and_user(db, episode_id=storyboard.episode_id)
        if not uid:
            logger.warning(f"视频回调: 无法解析用户ID, storyboard_id={storyboard.id}, episode_id={storyboard.episode_id}")
        service = VideoGenerationService(db, uid or "", pid)
        handler = VideoCallbackHandler()

        logger.info(
            f"视频回调: ark_task_id={ark_task_id}, "
            f"segment_index={storyboard.segment_index}, status={callback_data.get('status')}"
        )

        current_ark_id = ark_task_id
        current_callback_data = callback_data
        handler.dispatch(
            callback_data,
            on_success=lambda video_url: service.handle_callback_success(
                storyboard, video_url, current_ark_id, callback_data=current_callback_data,
            ),
            on_failure=lambda error_msg: service.handle_callback_failure(storyboard, error_msg, current_ark_id),
            on_progress=lambda: service.handle_callback_progress(storyboard),
        )

    except Exception as e:
        logger.error(f"视频回调处理异常: ark_task_id={ark_task_id}, error={e}")
        # 回调处理异常时，将 storyboard 标记为失败、退还积分并通知页面
        try:
            sb = db.query(Storyboard).filter(
                Storyboard.ark_task_id == ark_task_id,
                Storyboard.status == StoryboardStatus.VIDEO_GENERATING,
            ).first()
            if sb and sb.status not in (StoryboardStatus.FAILED, StoryboardStatus.VIDEO_COMPLETED):
                pid, uid = _resolve_project_and_user(db, episode_id=sb.episode_id)
                _fail_storyboard(db, sb, f"回调处理异常: {e}")
                # 退还预扣积分
                if uid and ark_task_id:
                    log = db.query(ModelCallLog).filter(ModelCallLog.provider_request_id == ark_task_id).first()
                    if log:
                        if log.point and log.point > 0:
                            PointService.refund(db, uid, Decimal(str(log.point)), source_id=log.request_id)
                        log.point = 0
                        log.error_message = f"回调处理异常: {e}"[:500]
                        db.commit()
                if uid and pid:
                    _notify(uid, pid, WSEventType.VIDEO_PROGRESS, {
                        "task_id": sb.id, "status": StoryboardStatus.FAILED,
                        "error": f"回调处理异常: {e}", "segment_index": sb.segment_index,
                    })
        except Exception as inner_e:
            logger.error(f"视频回调异常兜底处理失败: ark_task_id={ark_task_id}, error={inner_e}")
    finally:
        db.close()


@celery.task(
    bind=True,
    name="video.upload_storyboard_assets",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    max_retries=3,
)
def upload_storyboard_video_assets_task(self, storyboard_id: str):
    """异步：下载成片源视频 → 上传 COS → 提取首尾帧 → 二次推 WS

    回调到达时 storyboard 状态已被改为 VIDEO_COMPLETED 并推过一次 WS（用源地址），
    本任务跑完后再推一次刷新为 COS 永久地址。失败时 Celery 自动重试 3 次。
    """
    db = SessionLocal()
    try:
        storyboard = db.query(Storyboard).filter(Storyboard.id == storyboard_id).first()
        if not storyboard:
            logger.warning(f"[storyboard-assets] 分镜 {storyboard_id} 不存在")
            return
        # 幂等：已有 COS video_url 直接跳过
        if storyboard.video_url:
            logger.info(f"[storyboard-assets] 分镜 {storyboard_id} 已有 video_url，跳过")
            return
        pid, uid = _resolve_project_and_user(db, episode_id=storyboard.episode_id)
        if not uid or not pid:
            logger.warning(f"[storyboard-assets] 无法解析 user/project, storyboard_id={storyboard_id}")
            return
        service = VideoGenerationService(db, uid, pid)
        service.finalize_storyboard_video_assets(storyboard)
    except Exception as e:
        logger.error(f"[storyboard-assets] 分镜 {storyboard_id} 异步上传失败（重试中）: {e}")
        raise
    finally:
        db.close()


# ── 单镜头视频生成 ──────────────────────────────────────────

@celery.task(bind=True, max_retries=0)
def generate_single_video_task(self, storyboard_id: str, generation_options: dict = None, model: str = None):
    """单镜头视频生成：直接操作 Storyboard"""
    db = SessionLocal()
    pid, uid = None, None
    try:
        storyboard = db.query(Storyboard).filter(Storyboard.id == storyboard_id).first()
        if not storyboard:
            raise ValueError(f"分镜片段不存在: {storyboard_id}")

        pid, uid = _resolve_project_and_user(db, episode_id=storyboard.episode_id)
        service = VideoGenerationService(db, uid, pid)

        storyboard.status = StoryboardStatus.VIDEO_GENERATING
        if generation_options and "video_prompt" in generation_options:
            storyboard.video_prompt = generation_options["video_prompt"]
        db.commit()

        _notify(uid, pid, WSEventType.VIDEO_PROGRESS, {"task_id": storyboard_id, "status": StoryboardStatus.VIDEO_GENERATING, "progress": 10, "segment_index": storyboard.segment_index})

        opts = {**(generation_options or {})}
        body = service.build_single_shot_body(storyboard, opts, default_model=model)
        db.commit()
        _notify(uid, pid, WSEventType.VIDEO_PROGRESS, {"task_id": storyboard_id, "status": StoryboardStatus.VIDEO_GENERATING, "progress": 20, "segment_index": storyboard.segment_index})

        callback_url = build_callback_url(None, CallbackPath.SEEDANCE_VIDEO)
        result = service.submit_video_task(body, callback_url=callback_url, task_id=storyboard_id)
        ark_task_id = result["id"]
        storyboard.ark_task_id = ark_task_id
        db.commit()
        _notify(uid, pid, WSEventType.VIDEO_PROGRESS, {"task_id": storyboard_id, "status": "submitted", "progress": 30, "segment_index": storyboard.segment_index})
        logger.info(f"单镜头视频任务 {storyboard_id} 已提交，ark_task_id={ark_task_id}, callback_url={callback_url}")

    except SeedanceAPIError as e:
        logger.error(f"单镜头视频生成失败: storyboard_id={storyboard_id}, error={e.message}")
        db.rollback()
        sb = db.query(Storyboard).filter(Storyboard.id == storyboard_id).first()
        if sb:
            _fail_storyboard(db, sb, e.message)
            if uid and pid:
                _notify(uid, pid, WSEventType.VIDEO_PROGRESS, {"task_id": storyboard_id, "status": StoryboardStatus.FAILED, "error": e.message, "segment_index": sb.segment_index})
    except Exception as e:
        logger.error(f"单镜头视频生成失败: storyboard_id={storyboard_id}, error={e}")
        db.rollback()
        sb = db.query(Storyboard).filter(Storyboard.id == storyboard_id).first()
        if sb:
            _fail_storyboard(db, sb, str(e))
            if uid and pid:
                _notify(uid, pid, WSEventType.VIDEO_PROGRESS, {"task_id": storyboard_id, "status": StoryboardStatus.FAILED, "error": str(e), "segment_index": sb.segment_index})
    finally:
        db.close()


# ── 多片段成片视频生成 ──────────────────────────────────────

@celery.task(bind=True, max_retries=0)
def generate_multimodal_episode_video_task(self, episode_id: str, model: str = None):
    """多片段成片视频生成：直接操作 Storyboard，不再创建协调器任务"""
    db = SessionLocal()
    pid, uid = None, None
    try:
        pid, uid = _resolve_project_and_user(db, episode_id=episode_id)
        episode = db.query(Episode).filter(Episode.id == episode_id).first()
        if not episode or not episode.script_json:
            raise ValueError("剧集不存在或未生成脚本")

        service = VideoGenerationService(db, uid, pid)

        segments = episode.script_json["segments"]
        submitted_segments = {}

        for i, seg_data in enumerate(segments):
            seg_idx = seg_data.get("segmentIndex", i)
            sb = db.query(Storyboard).filter(
                Storyboard.episode_id == episode_id, Storyboard.segment_index == seg_idx,
            ).first()
            if not sb:
                logger.warning(f"多片段成片: 找不到 storyboard, episode_id={episode_id}, segment_index={seg_idx}, 跳过")
                continue

            try:
                body = service.build_segment_body(episode, seg_idx, {}, default_model=model)
                callback_url = build_callback_url(None, CallbackPath.SEEDANCE_VIDEO)
                result = service.submit_video_task(body, callback_url=callback_url, task_id=sb.id)
                ark_task_id = result["id"]
                submitted_segments[seg_idx] = ark_task_id

                sb.ark_task_id = ark_task_id
                sb.status = StoryboardStatus.VIDEO_GENERATING
                db.add(sb)
                db.commit()
                logger.info(f"多片段成片: segment {seg_idx} 已提交, ark_task_id={ark_task_id}")
            except SeedanceAPIError as e:
                logger.error(f"多片段成片: segment {seg_idx} 提交失败, error={e.message}")
                db.rollback()
                _fail_storyboard(db, sb, e.message)
                if uid and pid:
                    _notify(uid, pid, WSEventType.VIDEO_PROGRESS, {
                        "task_id": sb.id, "status": StoryboardStatus.FAILED,
                        "error": e.message, "segment_index": seg_idx,
                    })
                # 单 segment 失败不中断整体流程，继续下一个

        _notify(uid, pid, WSEventType.VIDEO_PROGRESS, {
            "task_id": episode_id, "status": "submitted",
            "progress": 30, "total_segments": len(segments),
            "submitted_count": len(submitted_segments),
        })
        logger.info(f"多片段成片任务 {episode_id} 已提交，共 {len(submitted_segments)}/{len(segments)} 个片段")

    except Exception as e:
        logger.error(f"多片段视频生成失败: episode_id={episode_id}, error={e}")
        if uid and pid:
            _notify(uid, pid, WSEventType.VIDEO_PROGRESS, {"task_id": episode_id, "status": StoryboardStatus.FAILED, "error": str(e)})
    finally:
        db.close()


# ── 脚本生成（保持不变）─────────────────────────────────────

def _generate_single_script(db, episode_id: str, project_id: str, user_id: str = None,
                            batch_total: int = 0, batch_current: int = 0):
    """单集脚本生成核心逻辑，供单集任务和批量任务复用"""
    episode = db.query(Episode).filter(Episode.id == episode_id).first()
    if not episode:
        raise ValueError(f"剧集不存在: {episode_id}")

    if not user_id:
        project = db.query(Project).filter(Project.id == project_id).first()
        user_id = project.user_id if project else ""

    episode.status = EpisodeStatus.GENERATING
    db.commit()

    notify_data = {"task_id": episode_id, "status": EpisodeStatus.GENERATING, "episode_id": episode_id, "episode_number": episode.episode_number}
    if batch_total:
        notify_data.update({"batch_total": batch_total, "batch_current": batch_current})
    _notify(user_id, project_id, WSEventType.SCRIPT_PROGRESS, notify_data)

    script = MultimodalScriptService(db).generate_script(episode_id, project_id)
    asset_descriptors = _get_asset_descriptors(db, project_id)
    script = script_text_converter.enrich_cross_segment_consistency(script, asset_descriptors)

    # 构建 asset_id→{name, kind} 映射
    asset_name_map = {d["assetId"]: {"name": d["name"], "kind": d["kind"]} for d in asset_descriptors if d.get("assetId") and d.get("name")}

    episode.script_json = script
    episode.script_plain_text = script_text_converter.script_to_plain_text(script, asset_map=asset_name_map)
    episode.status = EpisodeStatus.COMPLETED
    db.commit()

    # 创建 Storyboard
    MultimodalScriptService(db).create_storyboard_from_script(
        db, episode_id, script, plain_text=episode.script_plain_text,
    )
    db.commit()

    success_data = {
        "task_id": episode_id, "status": EpisodeStatus.COMPLETED, "episode_id": episode_id,
        "episode_number": episode.episode_number,
        "segment_count": len(script.get("segments", [])),
    }
    if batch_total:
        success_data.update({"batch_total": batch_total, "batch_current": batch_current})
    _notify(user_id, project_id, WSEventType.SCRIPT_PROGRESS, success_data)


@celery.task(bind=True, max_retries=0)
def generate_multimodal_script_task(self, episode_id: str, project_id: str, user_id: str):
    db = SessionLocal()
    try:
        _generate_single_script(db, episode_id, project_id, user_id)
    except Exception as e:
        logger.error(f"脚本生成失败: episode_id={episode_id}, error={e}")
        ep = db.query(Episode).filter(Episode.id == episode_id).first()
        if ep:
            ep.status = EpisodeStatus.FAILED
            db.commit()
        _notify(user_id, project_id, WSEventType.SCRIPT_PROGRESS, {
            "task_id": episode_id, "status": EpisodeStatus.FAILED, "error": str(e),
            "episode_id": episode_id, "episode_number": ep.episode_number if ep else None,
        })
    finally:
        db.close()


@celery.task(bind=True, max_retries=0)
def batch_generate_scripts_task(self, items: list[dict], project_id: str, user_id: str):
    """按剧集顺序串行生成脚本，items: [{episode_id, episode_number}, ...]"""
    total = len(items)
    for idx, item in enumerate(items, 1):
        episode_id = item["episode_id"]
        ep_number = item.get("episode_number", idx)
        db = SessionLocal()
        try:
            _generate_single_script(
                db, episode_id, project_id, user_id,
                batch_total=total, batch_current=idx,
            )
        except Exception as e:
            logger.error(f"批量脚本生成失败: episode={ep_number}, error={e}")
            ep = db.query(Episode).filter(Episode.id == episode_id).first()
            if ep:
                ep.status = EpisodeStatus.FAILED
                db.commit()
            _notify(user_id, project_id, WSEventType.SCRIPT_PROGRESS, {
                "task_id": episode_id, "status": EpisodeStatus.FAILED, "error": str(e),
                "episode_id": episode_id, "episode_number": ep_number,
                "batch_total": total, "batch_current": idx,
            })
            # 失败不中断，继续下一集
        finally:
            db.close()


# ── 按 segment 索引生成视频 ────────────────────────────────

@celery.task(bind=True, max_retries=0)
def generate_segment_video_task(self, episode_id: str, segment_index: int, generation_options: dict = None, model: str = None):
    """按 segment 索引生成视频：直接操作 Storyboard"""
    db = SessionLocal()
    pid, uid = None, None
    try:
        pid, uid = _resolve_project_and_user(db, episode_id=episode_id)
        episode = db.query(Episode).filter(Episode.id == episode_id).first()
        if not episode or not episode.script_json:
            raise ValueError(f"剧集不存在或未生成脚本: {episode_id}")

        service = VideoGenerationService(db, uid, pid)

        storyboard = db.query(Storyboard).filter(
            Storyboard.episode_id == episode_id, Storyboard.segment_index == segment_index,
        ).first()
        if not storyboard:
            raise ValueError(f"分镜片段不存在: episode_id={episode_id}, segment_index={segment_index}")

        storyboard.status = StoryboardStatus.VIDEO_GENERATING
        db.commit()
        _notify(uid, pid, WSEventType.VIDEO_PROGRESS, {"task_id": storyboard.id, "status": StoryboardStatus.VIDEO_GENERATING, "progress": 10, "segment_index": segment_index})

        opts = {**(generation_options or {})}
        body = service.build_segment_body(episode, segment_index, opts, default_model=model)
        db.commit()
        _notify(uid, pid, WSEventType.VIDEO_PROGRESS, {"task_id": storyboard.id, "status": StoryboardStatus.VIDEO_GENERATING, "progress": 20, "segment_index": segment_index})

        callback_url = build_callback_url(None, CallbackPath.SEEDANCE_VIDEO)
        result = service.submit_video_task(body, callback_url=callback_url, task_id=storyboard.id)
        ark_task_id = result["id"]
        storyboard.ark_task_id = ark_task_id
        db.commit()
        _notify(uid, pid, WSEventType.VIDEO_PROGRESS, {"task_id": storyboard.id, "status": "submitted", "progress": 30, "segment_index": segment_index})
        logger.info(f"片段视频任务 {storyboard.id} 已提交，segment_index={segment_index}, ark_task_id={ark_task_id}, callback_url={callback_url}")

    except SeedanceAPIError as e:
        logger.error(f"片段视频生成失败: episode_id={episode_id}, segment_index={segment_index}, error={e.message}")
        db.rollback()
        sb = db.query(Storyboard).filter(
            Storyboard.episode_id == episode_id, Storyboard.segment_index == segment_index,
        ).first()
        if sb:
            _fail_storyboard(db, sb, e.message)
            if uid and pid:
                _notify(uid, pid, WSEventType.VIDEO_PROGRESS, {"task_id": sb.id, "status": StoryboardStatus.FAILED, "error": e.message, "segment_index": segment_index})
    except Exception as e:
        logger.error(f"片段视频生成失败: episode_id={episode_id}, segment_index={segment_index}, error={e}")
        db.rollback()
        sb = db.query(Storyboard).filter(
            Storyboard.episode_id == episode_id, Storyboard.segment_index == segment_index,
        ).first()
        if sb:
            _fail_storyboard(db, sb, str(e))
            if uid and pid:
                _notify(uid, pid, WSEventType.VIDEO_PROGRESS, {"task_id": sb.id, "status": StoryboardStatus.FAILED, "error": str(e), "segment_index": segment_index})
    finally:
        db.close()


# ── 视频拼接（结果写入 EpisodeConcatRecord）─────────────────

@celery.task(bind=True, max_retries=0)
def concat_video_task(self, record_id: str):
    """视频拼接：结果写入 EpisodeConcatRecord（不再写 Episode 表）"""
    db = SessionLocal()
    try:
        record = db.query(EpisodeConcatRecord).filter(EpisodeConcatRecord.id == record_id).first()
        if not record:
            raise ValueError(f"合成记录不存在: {record_id}")

        pid = record.project_id
        uid = record.user_id
        episode_id = record.episode_id

        record.status = "processing"
        db.commit()

        # 推送「开始合成」事件
        _notify(uid, pid, WSEventType.VIDEO_CONCAT, {
            "task_id": record_id, "record_id": record_id, "episode_id": episode_id,
            "status": "processing",
        })

        # 直接使用记录创建时固化的源视频 URL 列表，保证合成内容与历史记录一致
        source_urls = record.source_video_urls or []
        if not source_urls:
            raise ValueError("源视频列表为空")

        tmp_dir = tempfile.mkdtemp(prefix="pipixia_concat_")
        try:
            total = len(source_urls)
            for i, item in enumerate(source_urls):
                url = item.get("video_url") if isinstance(item, dict) else getattr(item, "video_url", None)
                if not url:
                    raise ValueError(f"第 {i + 1} 个源视频 URL 缺失")
                # DB 中存的是 COS 永久 URL 或 key，私有桶需转签名 URL 才能下载
                key = cos_client.url_to_key(url) or url
                signed_url = cos_client.key_to_url(key)
                tmp_path = os.path.join(tmp_dir, f"seg_{i:03d}.mp4")
                with httpx.Client(timeout=180) as client:
                    resp = client.get(signed_url)
                    resp.raise_for_status()
                    with open(tmp_path, "wb") as f:
                        f.write(resp.content)

            concat_file = os.path.join(tmp_dir, "concat.txt")
            with open(concat_file, "w", encoding="utf-8") as f:
                for i in range(total):
                    f.write(f"file '{os.path.join(tmp_dir, f'seg_{i:03d}.mp4')}'\n")

            output_path = os.path.join(tmp_dir, "output.mp4")
            r = subprocess.run(
                ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_file, "-c", "copy", output_path],
                capture_output=True, text=True, timeout=300,
            )
            if r.returncode != 0:
                raise ValueError(f"ffmpeg 拼接失败: {r.stderr}")

            with open(output_path, "rb") as f:
                video_data = f.read()

            key = cos_client.generate_unique_key(f"pipixia-drama/projects/{pid}/videos", "mp4", user_id=uid)
            cos_client.upload_object(video_data, key, content_type="video/mp4")
            cos_url = cos_client.get_file_url(cos_client.bucket, key)

            record.result_video_url = cos_url
            record.result_storage_key = key
            record.status = "completed"
            db.commit()

            signed_url = cos_client.get_signed_url(cos_client.url_to_key(cos_url) or cos_url)
            # 推送「合成完成」事件
            _notify(uid, pid, WSEventType.VIDEO_CONCAT, {
                "task_id": record_id, "record_id": record_id, "episode_id": episode_id,
                "status": "completed", "video_url": signed_url,
            })
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)
    except Exception as e:
        logger.error(f"视频拼接失败: record_id={record_id}, error={e}")
        try:
            record = db.query(EpisodeConcatRecord).filter(EpisodeConcatRecord.id == record_id).first()
            if record:
                record.status = "failed"
                record.error_message = str(e)[:2000]
                db.commit()
                if record.user_id and record.project_id:
                    # 推送「合成失败」事件
                    _notify(record.user_id, record.project_id, WSEventType.VIDEO_CONCAT, {
                        "task_id": record_id, "record_id": record_id, "episode_id": record.episode_id,
                        "status": "failed", "error": str(e),
                    })
        except Exception as inner:
            logger.error(f"标记合成失败状态时出错: record_id={record_id}, error={inner}")
    finally:
        db.close()
