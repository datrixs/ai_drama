"""视频超分 Celery 异步任务

职责:编排任务状态机 + 调用火山 API + 处理回调下载上传 COS。
不涉及积分扣费(按需求暂不扣费)。
"""
from datetime import datetime

from loguru import logger
from sqlalchemy.orm import Session

from app.core.celery import celery
from app.core.ws import ws_manager
from app.db.session import SessionLocal
from app.enums.base import WSEventType
from app.enums.video import VideoSuperResTaskStatus
from app.models.video_super_res import VideoSuperResTask
from app.services.video_super_res_client import (
    VideoSuperResAPIError,
    VideoSuperResCallbackHandler,
    VideoSuperResClient,
)
from app.utils.callback_url import CallbackPath, build_callback_url
from app.utils.tencent_cos_utils import cos_client
from app.utils.video_processing import download_video, upload_short_video_to_cos
from app.crud.model_call_log_crud import model_call_log_crud
from app.services.point import PointService


def _notify(user_id: str, data: dict):
    """推送视频超分任务状态事件"""
    ws_manager.publish_asset_hub_event(user_id, WSEventType.SUPER_RESOLUTION_PROGRESS, data)


def _build_ws_payload(task: VideoSuperResTask, **overrides) -> dict:
    """构造 WS 推送载荷

    默认包含任务通用字段(task_id/progress/params/源视频 URL/创建时间),
    通过 kwargs 覆盖或追加字段(如 status/result_video_url/error_message)。
    URL 自动按 is_local_upload 决定是否签名(在线 URL 原样下发)。
    """
    allow_external = not bool(task.is_local_upload)
    payload = {
        "task_id": task.id,
        "progress": task.progress or 0,
        "params": task.params or {},
        "source_video_url": cos_client.to_signed(task.source_video_url, allow_external=allow_external),
        "source_thumbnail_url": cos_client.to_signed(task.source_thumbnail_url, allow_external=allow_external),
        "create_time": task.create_time.isoformat() if task.create_time else None,
    }
    payload.update(overrides)
    return payload


def _handle_task_failure(db: Session, task: VideoSuperResTask, error: str):
    """统一失败处理:更新任务状态并推送 WS 通知"""
    if task.status == VideoSuperResTaskStatus.CANCELLED:
        return
    error_msg = error[:500]
    task.status = VideoSuperResTaskStatus.FAILED
    task.error_message = error_msg
    task.completed_at = datetime.utcnow()
    db.add(task)
    db.commit()
    _notify(task.user_id, _build_ws_payload(task, status=VideoSuperResTaskStatus.FAILED, error_message=error_msg))


@celery.task(bind=True, max_retries=0)
def submit_super_res_task(self, task_id: str):
    """异步执行视频超分任务:构造请求体 -> 提交到火山 API -> 等待回调"""
    db = SessionLocal()
    try:
        task = db.get(VideoSuperResTask, task_id)
        if not task or task.is_deleted:
            logger.warning(f"视频超分任务 {task_id} 不存在或已删除")
            return

        if task.status == VideoSuperResTaskStatus.CANCELLED:
            logger.info(f"视频超分任务 {task_id} 已取消,跳过执行")
            return

        client = VideoSuperResClient()
        callback_url = build_callback_url(None, CallbackPath.SUPER_RESOLUTION)
        body = client.build_request_body(task, callback_url=callback_url)

        task.status = VideoSuperResTaskStatus.SUBMITTED
        task.api_request_params = body
        task.submitted_at = datetime.utcnow()
        db.add(task)
        db.commit()
        _notify(task.user_id, _build_ws_payload(task, status=VideoSuperResTaskStatus.SUBMITTED, progress=0))

        api_task_id, submit_response = client.submit_task(
            body,
            user_id=task.user_id,
            db=db,
            callback_url=callback_url,
            source_video_duration=task.source_video_duration
        )

        task.api_task_id = api_task_id
        task.api_submit_response = submit_response
        task.status = VideoSuperResTaskStatus.PROCESSING
        db.add(task)
        db.commit()
        _notify(task.user_id, _build_ws_payload(task, status=VideoSuperResTaskStatus.PROCESSING, progress=5))

        logger.info(
            f"视频超分任务 {task_id} 已提交到火山, api_task_id={api_task_id}, callback_url={callback_url}"
        )

    except VideoSuperResAPIError as e:
        task = db.get(VideoSuperResTask, task_id)
        if task:
            _handle_task_failure(db, task, e.message)
        logger.error(f"视频超分任务 {task_id} API 错误: {e.message}")
    except Exception as e:
        task = db.get(VideoSuperResTask, task_id)
        if task:
            _handle_task_failure(db, task, str(e))
        logger.error(f"视频超分任务 {task_id} 执行异常: {e}")
    finally:
        db.close()


@celery.task(bind=True, max_retries=0)
def process_super_res_callback(self, callback_data: dict):
    """处理火山超分回调(供 API 回调接口调用)"""
    db = SessionLocal()
    try:
        handler = VideoSuperResCallbackHandler()
        api_task_id = handler.extract_task_id(callback_data)
        if not api_task_id:
            logger.warning(f"视频超分回调缺少 task_id: {callback_data}")
            return

        task = db.query(VideoSuperResTask).filter(
            VideoSuperResTask.api_task_id == api_task_id,
            VideoSuperResTask.status == VideoSuperResTaskStatus.PROCESSING,
        ).first()
        if not task or task.is_deleted or task.status == VideoSuperResTaskStatus.CANCELLED:
            logger.warning(f"视频超分回调: 找不到任务, api_task_id={api_task_id}")
            return

        def on_success(video_url: str):
            video_data = download_video(video_url)
            cos_url, storage_key = upload_short_video_to_cos(video_data, task.user_id)
            task.result_video_url = cos_url or video_url
            task.result_storage_key = storage_key
            task.status = VideoSuperResTaskStatus.SUCCEEDED
            task.progress = 100
            task.completed_at = datetime.utcnow()
            task.api_response_data = callback_data
            db.add(task)
            db.commit()
            if not cos_url:
                logger.warning(f"视频超分任务 {task.id} COS 上传失败,使用原始 URL")

            _notify(task.user_id, _build_ws_payload(
                task,
                status=VideoSuperResTaskStatus.SUCCEEDED,
                progress=100,
                result_video_url=cos_client.to_signed(task.result_video_url),
                result_thumbnail_url=cos_client.to_signed(task.result_thumbnail_url),
            ))
            logger.info(f"视频超分任务 {task.id} 处理成功, result_video_url={task.result_video_url}")

        def on_failure(error_msg: str):
            # 失败时也保存完整回调响应到 api_response_data,与成功路径保持一致
            task.api_response_data = callback_data
            # 在 error_message 前加上火山 RequestId,方便后续问题排查
            request_id = callback_data.get("RequestId") if isinstance(callback_data, dict) else None
            prefixed = f"[request_id={request_id}] {error_msg}" if request_id else error_msg
            _handle_task_failure(db, task, prefixed)
            msg = f"视频超分回调: 任务 {task.id} 失败, request_id={request_id}, error={error_msg}"
            logger.error(msg)
            # 更新调用记录
            model_call_log = model_call_log_crud.get_by_provider_request_id(db=db, provider_request_id=request_id)
            if model_call_log:
                model_call_log_update = {
                    "response_status": 400,
                    "response_body": callback_data,
                    "error_message": msg,
                    "point": 0,
                    "remaining_point": model_call_log.remaining_point + model_call_log.point
                }
                model_call_log_crud.update(db=db, record_id=model_call_log.id, update_data=model_call_log_update)
                # 退还积分
                PointService.refund(db=db, user_id=model_call_log.user_id, estimated_point=model_call_log.point, source_id=model_call_log.request_id)

        def on_progress():
            task.progress = min(task.progress + 10, 90) if task.progress else 10
            db.add(task)
            db.commit()
            _notify(task.user_id, _build_ws_payload(task, status=VideoSuperResTaskStatus.PROCESSING))

        handler.dispatch(callback_data, on_success, on_failure, on_progress)

    except Exception as e:
        error_msg = f"视频超分回调处理异常: {e}"
        logger.error(error_msg)

        # 更新调用记录
        model_call_log = model_call_log_crud.get_by_provider_request_id(db=db, provider_request_id=api_task_id)
        if model_call_log:
            model_call_log_update = {
                "response_status": 400,
                "response_body": callback_data,
                "error_message": error_msg,
                "point": 0,
                "remaining_point": model_call_log.remaining_point + model_call_log.point
            }
            model_call_log_crud.update(db=db, record_id=model_call_log.id, update_data=model_call_log_update)
            # 退还积分
            PointService.refund(db=db, user_id=model_call_log.user_id, estimated_point=model_call_log.point, source_id=model_call_log.request_id)

        # 兜底:能反查到任务就标记失败
        try:
            handler = VideoSuperResCallbackHandler()
            api_task_id = handler.extract_task_id(callback_data)
            if api_task_id:
                task = db.query(VideoSuperResTask).filter(
                    VideoSuperResTask.api_task_id == api_task_id,
                ).first()
                if task and task.status not in (
                    VideoSuperResTaskStatus.SUCCEEDED,
                    VideoSuperResTaskStatus.FAILED,
                    VideoSuperResTaskStatus.CANCELLED,
                ):
                    _handle_task_failure(db, task, f"回调处理异常: {e}")
        except Exception as inner:
            logger.error(f"视频超分回调兜底处理失败: {inner}")
    finally:
        db.close()
