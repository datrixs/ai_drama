import uuid
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud.base_crud import CRUDBase
from app.models.task_record import TaskRecord, OperationRecord


class CRUDTaskRecord(CRUDBase[TaskRecord, dict, dict]):
    def create_task(
        self,
        db: Session,
        *,
        project_id: str,
        task_type: str,
        input_params: dict | None = None,
        parent_task_id: str | None = None,
        timeout_seconds: int = 300,
        max_retries: int = 3,
    ) -> TaskRecord:
        """创建任务记录"""
        task = TaskRecord(
            id=str(uuid.uuid4()),
            project_id=project_id,
            task_type=task_type,
            input_params=input_params,
            parent_task_id=parent_task_id,
            max_retries=max_retries,
            timeout_at=datetime.utcnow() + timedelta(seconds=timeout_seconds),
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        return task

    def start_task(self, db: Session, task_id: str, worker_id: str, celery_task_id: str | None = None) -> TaskRecord:
        """标记任务开始执行"""
        task = self.get(id=task_id, db=db)
        if not task:
            raise ValueError(f"任务 {task_id} 不存在")
        task.status = "running"
        task.worker_id = worker_id
        task.started_at = datetime.utcnow()
        if celery_task_id:
            task.celery_task_id = celery_task_id
        db.add(task)
        db.commit()
        db.refresh(task)
        return task

    def complete_task(self, db: Session, task_id: str, output_result: dict | None = None) -> TaskRecord:
        """标记任务完成"""
        task = self.get(id=task_id, db=db)
        if not task:
            raise ValueError(f"任务 {task_id} 不存在")
        task.status = "success"
        task.output_result = output_result
        task.completed_at = datetime.utcnow()
        db.add(task)
        db.commit()
        db.refresh(task)
        return task

    def fail_task(self, db: Session, task_id: str, error_message: str) -> TaskRecord:
        """标记任务失败"""
        task = self.get(id=task_id, db=db)
        if not task:
            raise ValueError(f"任务 {task_id} 不存在")
        task.retry_count += 1
        if task.retry_count < task.max_retries:
            task.status = "pending"
            task.next_retry_at = datetime.utcnow() + timedelta(
                seconds=2 ** task.retry_count * 30
            )
        else:
            task.status = "failed"
        task.error_message = error_message
        db.add(task)
        db.commit()
        db.refresh(task)
        return task


class CRUDOperationRecord(CRUDBase[OperationRecord, dict, dict]):
    def log_operation(
        self,
        db: Session,
        *,
        project_id: str,
        user_id: str,
        action: str,
        target_type: str | None = None,
        target_id: str | None = None,
        detail: dict | None = None,
    ) -> OperationRecord:
        """记录操作"""
        record = OperationRecord(
            id=str(uuid.uuid4()),
            project_id=project_id,
            user_id=user_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            detail=detail,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record


task_record = CRUDTaskRecord(TaskRecord)
operation_record = CRUDOperationRecord(OperationRecord)
