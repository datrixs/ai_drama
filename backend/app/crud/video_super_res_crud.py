"""视频超分 CRUD 操作"""
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models.video_super_res import VideoSuperResTask
from app.crud.base_crud import CRUDBase
from app.enums.video import VideoSuperResTaskStatus
from app.schemas.video_super_res import VideoSuperResTaskCreate


class CRUDVideoSuperResTask(CRUDBase[VideoSuperResTask, VideoSuperResTaskCreate, dict]):
    """视频超分任务 CRUD"""

    def get_user_tasks_paginated(self, db: Session, user_id: str, cursor: str = None, limit: int = 20):
        """基于游标的分页查询, cursor 为上一页最后一条记录的 ID"""
        q = self.get_queryset(db).filter(VideoSuperResTask.user_id == user_id)

        if cursor:
            cursor_task = db.get(VideoSuperResTask, cursor)
            if cursor_task and cursor_task.create_time:
                q = q.filter(VideoSuperResTask.create_time < cursor_task.create_time)

        q = q.order_by(VideoSuperResTask.create_time.desc())
        tasks = q.limit(limit + 1).all()

        has_more = len(tasks) > limit
        items = tasks[:limit]
        next_cursor = items[-1].id if has_more and items else None

        return items, has_more, next_cursor

    def get_task(self, db: Session, task_id: str, user_id: str) -> Optional[VideoSuperResTask]:
        """获取指定用户的任务"""
        return (
            self.get_queryset(db)
            .filter(VideoSuperResTask.id == task_id, VideoSuperResTask.user_id == user_id)
            .first()
        )

    def update_status(self, db: Session, task_id: str, status: str, **kwargs) -> Optional[VideoSuperResTask]:
        """更新任务状态"""
        task = db.get(VideoSuperResTask, task_id)
        if not task or task.is_deleted:
            return None
        task.status = status
        for key, value in kwargs.items():
            if hasattr(task, key):
                setattr(task, key, value)
        db.add(task)
        db.commit()
        db.refresh(task)
        return task

    def reset_for_retry(self, db: Session, task_id: str) -> Optional[VideoSuperResTask]:
        """重置任务为 pending 状态,清空之前的结果(供 retry 端点使用)"""
        task = db.get(VideoSuperResTask, task_id)
        if not task or task.is_deleted:
            return None
        task.status = VideoSuperResTaskStatus.PENDING
        task.error_message = None
        task.progress = 0
        task.api_task_id = None
        task.api_request_params = None
        task.api_response_data = None
        task.result_video_url = None
        task.result_thumbnail_url = None
        task.result_storage_key = None
        task.submitted_at = None
        task.completed_at = None
        db.add(task)
        db.commit()
        db.refresh(task)
        return task


video_super_res_task_crud = CRUDVideoSuperResTask(VideoSuperResTask)
