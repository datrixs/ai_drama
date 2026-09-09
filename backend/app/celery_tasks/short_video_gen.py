"""短视频生成 Celery 异步任务（基于 SDK + Callback）

Celery 只负责任务编排，业务逻辑下沉到 VideoGenerationService。
"""
from datetime import datetime
from decimal import Decimal

from app.core.celery import celery
from loguru import logger
from sqlalchemy.orm import Session

from app.core.ws import ws_manager
from app.db.session import SessionLocal
from app.enums.base import WSEventType
from app.enums.video import ShortVideoTaskStatus
from app.models.short_video import ShortVideoTask
from app.models.model_call_log import ModelCallLog
from app.services.point import PointService
from app.services.seedance_client import SeedanceAPIError
from app.services.video_callback_handler import VideoCallbackHandler, extract_video_url
from app.services.video_generation_service import VideoGenerationService
from app.utils.callback_url import CallbackPath, build_callback_url
from app.utils.tencent_cos_utils import cos_client
from app.utils.video_processing import (
    download_video,
    extract_and_upload_video_cover,
    upload_short_video_to_cos,
)


def _notify(user_id: str, data: dict):
    """推送短视频任务状态事件"""
    ws_manager.publish_asset_hub_event(user_id, WSEventType.SHORT_VIDEO_PROGRESS, data)


def _sign_url(url: str) -> str:
    """将永久 URL 转为签名 URL；外部 URL（如方舟 CDN）原样返回"""
    if not url:
        return url
    return cos_client.to_signed(url, allow_external=True) or url


def _handle_task_failure(db: Session, task: ShortVideoTask, error: str):
    """统一失败处理：更新任务状态并推送 WS 通知"""
    if task.status == ShortVideoTaskStatus.CANCELLED:
        return
    task.status = ShortVideoTaskStatus.FAILED
    task.error_message = error[:500]
    task.completed_at = datetime.utcnow()
    db.add(task)
    db.commit()
    _notify(task.user_id, {
        "task_id": task.id,
        "status": ShortVideoTaskStatus.FAILED,
        "error_message": error[:500],
    })


def _get_billing_log(db: Session, ark_task_id: str, task_id: str = None) -> ModelCallLog | None:
    """从 model_call_log 查询本次预扣日志（取最新一条），用于结算/退款的 point 与 source_id"""
    q = db.query(ModelCallLog).filter(ModelCallLog.provider_request_id == ark_task_id)
    if task_id:
        q = q.filter(ModelCallLog.task_id == task_id)
    return q.order_by(ModelCallLog.create_time.desc()).first()


def _update_log_on_failure(db: Session, ark_task_id: str, error_msg: str, task_id: str = None):
    """更新 model_call_log：失败时积分置 0 并记录错误信息（与 dev 分支 wait_for_completion 一致）"""
    q = db.query(ModelCallLog).filter(ModelCallLog.provider_request_id == ark_task_id)
    if task_id:
        q = q.filter(ModelCallLog.task_id == task_id)
    log = q.order_by(ModelCallLog.create_time.desc()).first()
    if log:
        # 先更新剩余积分
        log.remaining_point += log.point
        # 再修改积分为 0
        log.point = 0
        log.error_message = f"视频生成失败: {error_msg}"[:500]
        log.response_status = 402
        db.commit()


@celery.task(bind=True, max_retries=0)
def generate_short_video_task(self, task_id: str):
    """异步执行短视频生成任务：仅提交到方舟，由 callback 接收结果"""
    db = SessionLocal()
    try:
        task = db.get(ShortVideoTask, task_id)
        if not task or task.is_deleted:
            logger.warning(f"短视频任务 {task_id} 不存在或已删除")
            return

        if task.status == ShortVideoTaskStatus.CANCELLED:
            logger.info(f"短视频任务 {task_id} 已取消，跳过执行")
            return

        service = VideoGenerationService(db, task.user_id)

        # 构建请求体
        body = service.build_short_video_body(task)

        # 更新状态为 submitted
        task.status = ShortVideoTaskStatus.SUBMITTED
        task.region = service.region
        task.api_request_params = body
        task.submitted_at = datetime.utcnow()
        db.add(task)
        db.commit()
        _notify(task.user_id, {
            "task_id": task_id, "status": ShortVideoTaskStatus.SUBMITTED, "progress": 0,
        })

        # 调用 SDK 创建任务
        callback_url = build_callback_url(None, CallbackPath.SEEDANCE_SHORT_VIDEO)
        result = service.submit_video_task(body, callback_url=callback_url, task_id=task_id)
        ark_task_id = result["id"]
        task.api_task_id = ark_task_id
        task.api_response_data = result
        # 方舟接受任务后初始状态为 queued；等待 on_running 回调切换到 processing
        task.status = ShortVideoTaskStatus.QUEUED
        db.add(task)
        db.commit()
        _notify(task.user_id, {
            "task_id": task_id, "status": ShortVideoTaskStatus.QUEUED, "progress": 5,
        })

        logger.info(f"短视频任务 {task_id} 已提交到方舟，ark_task_id={ark_task_id}, callback_url={callback_url}")

    except SeedanceAPIError as e:
        task = db.get(ShortVideoTask, task_id)
        if task:
            _handle_task_failure(db, task, e.message)
        logger.error(f"短视频任务 {task_id} SDK 错误: {e.message}")
    except Exception as e:
        task = db.get(ShortVideoTask, task_id)
        if task:
            _handle_task_failure(db, task, str(e))
        logger.error(f"短视频任务 {task_id} 执行异常: {e}")
    finally:
        db.close()


@celery.task(bind=True, max_retries=0)
def process_short_video_callback(self, callback_data: dict):
    """处理短视频生成回调（供 API 回调接口调用）"""
    db = SessionLocal()
    try:
        ark_task_id = callback_data.get("id")
        task = db.query(ShortVideoTask).filter(
            ShortVideoTask.api_task_id == ark_task_id,
            ShortVideoTask.status.in_([
                ShortVideoTaskStatus.QUEUED,
                ShortVideoTaskStatus.PROCESSING,
            ]),
        ).first()
        if not task or task.is_deleted:
            logger.warning(f"短视频回调: 找不到任务, ark_task_id={ark_task_id}")
            return

        if task.status == ShortVideoTaskStatus.CANCELLED:
            logger.info(f"短视频回调: 任务 {task.id} 已取消，忽略回调")
            return

        handler = VideoCallbackHandler()

        def on_success(video_url: str):
            # 立即标记成功并推送 WS（用源地址），COS 上传与首帧提取走异步任务
            task.status = ShortVideoTaskStatus.SUCCEEDED
            task.progress = 100
            task.completed_at = datetime.utcnow()
            task.api_response_data = callback_data
            db.add(task)
            db.commit()

            log = _get_billing_log(db, ark_task_id, task_id=task.id)
            if log and log.point:
                estimated = Decimal(str(log.point))
                PointService.settle(db, task.user_id, estimated, estimated, source_id=log.request_id)
                logger.info(f"[积分] 短视频任务结算成功: user_id={task.user_id}, ark_task_id={ark_task_id}, point={estimated}")

            _notify(task.user_id, {
                "task_id": task.id,
                "status": ShortVideoTaskStatus.SUCCEEDED,
                "progress": 100,
                "api_task_id": ark_task_id,
                "video_url": video_url,
                "thumbnail_url": None,
            })
            logger.info(f"短视频任务 {task.id} 回调成功，source_url={video_url}，触发异步上传 COS")

            # 异步处理：下载视频 → 上传 COS → 提取首帧 → 二次推 WS
            upload_short_video_assets_task.delay(task.id)

        def on_failure(error_msg: str):
            _handle_task_failure(db, task, error_msg)

            log = _get_billing_log(db, ark_task_id, task_id=task.id)
            if log and log.point:
                estimated = Decimal(str(log.point))
                PointService.refund(db, task.user_id, estimated, source_id=log.request_id)
            _update_log_on_failure(db, ark_task_id, error_msg, task_id=task.id)

            logger.error(f"短视频回调: 任务 {task.id} 失败, error={error_msg}")

        def on_queued():
            # generate_short_video_task 提交成功后已置为 QUEUED，回调到达时通常幂等
            if task.status == ShortVideoTaskStatus.QUEUED:
                return
            task.status = ShortVideoTaskStatus.QUEUED
            if not task.progress or task.progress < 5:
                task.progress = 5
            db.add(task)
            db.commit()
            _notify(task.user_id, {
                "task_id": task.id,
                "status": ShortVideoTaskStatus.QUEUED,
                "progress": task.progress,
            })

        def on_running():
            task.status = ShortVideoTaskStatus.PROCESSING
            if not task.started_at:
                task.started_at = datetime.utcnow()
            if not task.progress or task.progress < 10:
                task.progress = 10
            db.add(task)
            db.commit()
            _notify(task.user_id, {
                "task_id": task.id,
                "status": ShortVideoTaskStatus.PROCESSING,
                "progress": task.progress,
            })

        def on_progress():
            # 兜底：未知中间态。极端时序下 progress 可能先于 running 到达，先升 PROCESSING
            if task.status == ShortVideoTaskStatus.QUEUED:
                task.status = ShortVideoTaskStatus.PROCESSING
            task.progress = min(task.progress + 10, 90) if task.progress else 10
            db.add(task)
            db.commit()
            _notify(task.user_id, {
                "task_id": task.id, "status": ShortVideoTaskStatus.PROCESSING, "progress": task.progress,
            })

        handler.dispatch(callback_data, on_success, on_failure, on_progress,
                         on_queued=on_queued, on_running=on_running)

    except Exception as e:
        logger.error(f"短视频回调处理异常: ark_task_id={ark_task_id}, error={e}")
        # 回调处理异常时，将任务标记为失败、退还积分并通知页面
        task = db.query(ShortVideoTask).filter(
            ShortVideoTask.api_task_id == ark_task_id,
            ShortVideoTask.status.in_([
                ShortVideoTaskStatus.QUEUED,
                ShortVideoTaskStatus.PROCESSING,
            ]),
        ).first()
        if task and task.status not in (ShortVideoTaskStatus.SUCCEEDED, ShortVideoTaskStatus.FAILED, ShortVideoTaskStatus.CANCELLED):
            # 退还预扣积分
            log = _get_billing_log(db, ark_task_id, task_id=task.id)
            if log and log.point:
                estimated = Decimal(str(log.point))
                PointService.refund(db, task.user_id, estimated, source_id=log.request_id)
            _update_log_on_failure(db, ark_task_id, f"回调处理异常: {e}", task_id=task.id)

            # 通知
            _handle_task_failure(db, task, f"回调处理异常: {e}")
    finally:
        db.close()


@celery.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    max_retries=3,
)
def upload_short_video_assets_task(self, task_id: str):
    """异步：下载源视频 → 上传 COS → 提取首帧 → 更新 DB → 二次推 WS

    回调到达时已立即推送 WS（用源地址），此任务跑完后再推一次刷新为 COS 永久地址。
    失败时 Celery 自动重试 3 次，最终仍失败仅记录日志，不影响任务已成功状态。
    """
    db = SessionLocal()
    try:
        task = db.get(ShortVideoTask, task_id)
        if not task or task.is_deleted:
            logger.info(f"[assets] 短视频任务 {task_id} 不存在或已删除，跳过")
            return
        # 任务已被取消则不再处理
        if task.status == ShortVideoTaskStatus.CANCELLED:
            logger.info(f"[assets] 短视频任务 {task_id} 已取消，跳过")
            return
        # 幂等：COS 已上传过则跳过
        if task.video_url:
            logger.info(f"[assets] 短视频任务 {task_id} 已有 COS 地址，跳过")
            return

        # 从 api_response_data 解析源地址
        try:
            source_url = extract_video_url(task.api_response_data or {})
        except ValueError as e:
            logger.warning(f"[assets] 短视频任务 {task_id} 解析源地址失败: {e}")
            return

        video_data = download_video(source_url)
        cos_url, _ = upload_short_video_to_cos(video_data, task.user_id)
        cover_url = extract_and_upload_video_cover(video_data, str(task.user_id))

        task.video_url = cos_url or source_url
        if cover_url:
            task.thumbnail_url = cover_url
        db.add(task)
        db.commit()

        # 二次 WS 推送：用 COS 签名地址刷新前端
        _notify(task.user_id, {
            "task_id": task.id,
            "status": ShortVideoTaskStatus.SUCCEEDED,
            "progress": 100,
            "api_task_id": task.api_task_id,
            "video_url": _sign_url(task.video_url),
            "thumbnail_url": _sign_url(task.thumbnail_url),
        })
        logger.info(f"[assets] 短视频任务 {task_id} 异步上传完成，cos_url={task.video_url} cover={'yes' if cover_url else 'no'}")
    except Exception as e:
        logger.error(f"[assets] 短视频任务 {task_id} 异步上传失败（重试中）: {e}")
        raise
    finally:
        db.close()
