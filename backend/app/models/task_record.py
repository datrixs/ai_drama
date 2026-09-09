from datetime import datetime, timedelta

from sqlalchemy import Column, String, Integer, DateTime, JSON, Boolean, Text

from app.models.base import BasicModel


class TaskRecord(BasicModel):
    """任务记录表"""
    __tablename__ = "task_record"

    project_id = Column(String(36), nullable=False, index=True, comment="项目ID")
    task_type = Column(String(64), nullable=False, comment="任务类型: novel_preprocess/comprehensive_extraction/character_gen/...")
    celery_task_id = Column(String(256), comment="Celery任务ID")
    parent_task_id = Column(String(36), comment="父任务ID")

    status = Column(
        String(32), nullable=False, default="pending",
        comment="任务状态: pending/running/success/failed/timeout/cancelled",
    )
    worker_id = Column(String(256), comment="执行任务的Worker ID")

    input_params = Column(JSON, comment="输入参数")
    output_result = Column(JSON, comment="输出结果")

    retry_count = Column(Integer, nullable=False, default=0, comment="已重试次数")
    max_retries = Column(Integer, nullable=False, default=3, comment="最大重试次数")
    next_retry_at = Column(DateTime, comment="下次重试时间")

    started_at = Column(DateTime, comment="开始执行时间")
    completed_at = Column(DateTime, comment="完成时间")
    timeout_at = Column(DateTime, comment="超时时间")

    error_message = Column(Text, comment="错误信息")


class OperationRecord(BasicModel):
    """操作记录表"""
    __tablename__ = "operation_record"

    project_id = Column(String(36), nullable=False, index=True, comment="项目ID")
    user_id = Column(String(36), nullable=False, comment="操作用户ID")
    action = Column(String(64), nullable=False, comment="操作类型: create_project/upload_novel/start_analysis/adjust/confirm/...")
    target_type = Column(String(32), comment="目标类型: project/analysis_version/asset/episode/...")
    target_id = Column(String(36), comment="目标ID")
    detail = Column(JSON, comment="操作详情")
