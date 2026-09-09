"""视频超分(火山 AI MediaKit 画质增强)API 端点"""
import json

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.celery_tasks.video_super_res_gen import (
    process_super_res_callback,
    submit_super_res_task,
)
from app.crud.video_super_res_crud import video_super_res_task_crud
from app.enums.video import VideoSuperResTaskStatus
from app.models import User
from app.schemas.video_super_res import (
    VideoSuperResTaskCreate,
    VideoSuperResTaskDetail,
    VideoSuperResTaskItem,
)
from app.utils.response import success_response
from app.utils.tencent_cos_utils import cos_client

router = APIRouter()


# ── 任务管理 ──────────────────────────────────────────

@router.post("/generate")
def generate_task(
    body: VideoSuperResTaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """提交视频超分任务

    入参:
        source_video_url: 源视频 URL
            - is_local_upload=True(本地上传): COS 签名 URL,后端转永久 URL 存储
            - is_local_upload=False(在线 URL): 第三方直链,后端原样保存
        is_local_upload: 是否本地上传(默认 True)
        超分参数(扁平,与火山 API 字段对齐):
            tool_version / scene / resolution / resolution_limit /
            bitrate_level / fps / callback_args / queue_id
    """
    # 保留前端原始请求体快照(转 COS 永久 URL 前),用于审计/回放
    request_payload_snapshot = body.model_dump(exclude_none=True)

    task_data = body.to_task_data()
    task_data["user_id"] = current_user.id
    task_data["create_uid"] = current_user.id
    task_data["status"] = VideoSuperResTaskStatus.PENDING
    task_data["request_payload"] = request_payload_snapshot

    # 仅本地上传(COS 资源)才把签名 URL 转永久 URL;在线 URL 原样存储
    if task_data.get("is_local_upload", True):
        task_data["source_video_url"] = cos_client.to_permanent(task_data["source_video_url"])
        if task_data.get("source_thumbnail_url"):
            task_data["source_thumbnail_url"] = cos_client.to_permanent(task_data["source_thumbnail_url"])

    task = video_super_res_task_crud.create(db, task_data)
    submit_super_res_task.delay(task.id)

    return success_response(data={"task_id": task.id, "status": VideoSuperResTaskStatus.PENDING})


@router.get("/tasks")
def list_tasks(
    cursor: str = None,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取用户视频超分任务列表(游标分页)"""
    limit = min(limit, 50)
    tasks, has_more, next_cursor = video_super_res_task_crud.get_user_tasks_paginated(
        db, current_user.id, cursor=cursor, limit=limit
    )
    return success_response(data={
        "items": [VideoSuperResTaskItem.model_validate(t).model_dump(mode="json") for t in tasks],
        "has_more": has_more,
        "next_cursor": next_cursor,
    })


@router.get("/tasks/{task_id}")
def get_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取视频超分任务详情"""
    task = video_super_res_task_crud.get_task(db, task_id, current_user.id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return success_response(data=VideoSuperResTaskDetail.model_validate(task))


@router.post("/tasks/{task_id}/cancel")
def cancel_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """取消任务(仅 pending/submitted/processing 可取消)"""
    task = video_super_res_task_crud.get_task(db, task_id, current_user.id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if task.status not in (
        VideoSuperResTaskStatus.PENDING,
        VideoSuperResTaskStatus.SUBMITTED,
        VideoSuperResTaskStatus.PROCESSING,
    ):
        raise HTTPException(status_code=400, detail="当前状态不可取消")
    task = video_super_res_task_crud.update_status(db, task_id, VideoSuperResTaskStatus.CANCELLED)
    return success_response(data={"task_id": task.id, "status": VideoSuperResTaskStatus.CANCELLED})


@router.post("/tasks/{task_id}/retry")
def retry_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """重试失败/已取消任务"""
    task = video_super_res_task_crud.get_task(db, task_id, current_user.id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if task.status not in (VideoSuperResTaskStatus.FAILED, VideoSuperResTaskStatus.CANCELLED):
        raise HTTPException(status_code=400, detail="只有失败或已取消的任务可以重试")

    task = video_super_res_task_crud.reset_for_retry(db, task_id)
    submit_super_res_task.delay(task.id)

    return success_response(data={"task_id": task.id, "status": VideoSuperResTaskStatus.PENDING})


@router.delete("/tasks/{task_id}")
def delete_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除任务(软删除)"""
    task = video_super_res_task_crud.get_task(db, task_id, current_user.id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    video_super_res_task_crud.remove(db, task_id)
    return success_response(data={"task_id": task_id})


@router.post("/callback")
def super_res_callback(body: dict):
    """接收火山视频超分回调,立即返回,业务异步处理(无鉴权)"""
    logger.info(f"视频超分回调请求: {json.dumps(body, ensure_ascii=False)}")
    process_super_res_callback.delay(body)
    return success_response(data={"received": True})
