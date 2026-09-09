"""短视频 CRUD 操作"""
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models.short_video import ShortVideoTask, ShortVideoAsset
from app.crud.base_crud import CRUDBase
from app.schemas.short_video import ShortVideoTaskCreate, ShortVideoAssetUpload


class CRUDShortVideoTask(CRUDBase[ShortVideoTask, ShortVideoTaskCreate, dict]):
    """短视频任务 CRUD"""

    def get_user_tasks(self, db: Session, user_id: str, limit: int = 20):
        """获取用户最近的任务列表"""
        return (
            self.get_queryset(db)
            .filter(ShortVideoTask.user_id == user_id)
            .order_by(ShortVideoTask.create_time.desc())
            .limit(limit)
            .all()
        )

    def get_user_tasks_paginated(self, db: Session, user_id: str, cursor: str = None, limit: int = 20):
        """基于游标的分页查询，cursor 为上一页最后一条记录的 ID"""
        from sqlalchemy import and_

        q = self.get_queryset(db).filter(ShortVideoTask.user_id == user_id)

        if cursor:
            cursor_task = db.get(ShortVideoTask, cursor)
            if cursor_task and cursor_task.create_time:
                q = q.filter(ShortVideoTask.create_time < cursor_task.create_time)

        q = q.order_by(ShortVideoTask.create_time.desc())
        tasks = q.limit(limit + 1).all()

        has_more = len(tasks) > limit
        items = tasks[:limit]
        next_cursor = items[-1].id if has_more and items else None

        return items, has_more, next_cursor

    def get_task(self, db: Session, task_id: str, user_id: str) -> Optional[ShortVideoTask]:
        """获取指定用户的任务"""
        return (
            self.get_queryset(db)
            .filter(ShortVideoTask.id == task_id, ShortVideoTask.user_id == user_id)
            .first()
        )

    def update_status(self, db: Session, task_id: str, status: str, **kwargs) -> Optional[ShortVideoTask]:
        """更新任务状态"""
        task = db.get(ShortVideoTask, task_id)
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


class CRUDShortVideoAsset(CRUDBase[ShortVideoAsset, ShortVideoAssetUpload, dict]):
    """短视频资产 CRUD"""

    def get_user_assets(self, db: Session, user_id: str, asset_type: Optional[str] = None):
        """获取用户资产列表"""
        q = self.get_queryset(db).filter(ShortVideoAsset.user_id == user_id)
        if asset_type:
            q = q.filter(ShortVideoAsset.asset_type == asset_type)
        return q.order_by(ShortVideoAsset.create_time.desc()).all()

    def get_asset(self, db: Session, asset_id: str, user_id: str) -> Optional[ShortVideoAsset]:
        """获取指定用户的资产"""
        return (
            self.get_queryset(db)
            .filter(ShortVideoAsset.id == asset_id, ShortVideoAsset.user_id == user_id)
            .first()
        )


short_video_task_crud = CRUDShortVideoTask(ShortVideoTask)
short_video_asset_crud = CRUDShortVideoAsset(ShortVideoAsset)
