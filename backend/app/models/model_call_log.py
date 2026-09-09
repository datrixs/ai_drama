import uuid
from datetime import datetime

from sqlalchemy import Column, String, Integer, DateTime, Boolean, Text, JSON, PrimaryKeyConstraint, Numeric

from app.models.base import Base


class ModelCallLog(Base):
    """模型调用日志（按月分区）"""
    __tablename__ = "model_call_log"
    __table_args__ = (
        PrimaryKeyConstraint("id", "call_time"),
    )

    id = Column(String(36), default=lambda: str(uuid.uuid4()))

    # 调用上下文
    user_id = Column(String(36), nullable=False, comment="调用用户")
    project_id = Column(String(36), comment="关联项目")
    task_id = Column(String(36), comment="关联任务")

    # 请求标识
    request_id = Column(String(128), nullable=False, comment="唯一请求ID")
    provider_request_id = Column(String(256), comment="模型厂商请求ID")

    # 模型信息
    model_provider = Column(String(64), nullable=False, comment="供应商")
    model_name = Column(String(128), nullable=False, comment="模型名")
    endpoint = Column(String(512), nullable=False, comment="API端点")
    api_key_masked = Column(String(64), comment="脱敏API Key")

    # 请求/响应
    request_body = Column(JSON, comment="请求体")
    response_status = Column(Integer, comment="HTTP状态码")
    response_body = Column(JSON, comment="响应体摘要")

    # 通用 Usage
    input_tokens = Column(Integer, default=0, comment="输入token数")
    output_tokens = Column(Integer, default=0, comment="输出token数")
    total_tokens = Column(Integer, default=0, comment="总token数")
    latency_ms = Column(Integer, comment="调用耗时(毫秒)")

    # 供应商特有 Usage
    usage_details = Column(JSON, comment="供应商特有usage字段")

    # 媒体信息（图片/视频输入输出）
    media_type = Column(String(32), comment="调用类型: text_text/text_image/image_text/image_image/video")
    input_media = Column(JSON, comment="输入媒体信息 [{type, url, width, height, size_bytes, duration}]")
    output_media = Column(JSON, comment="输出媒体信息 [{type, url, width, height, size_bytes, duration}]")

    # 重试
    is_retry = Column(Boolean, nullable=False, default=False)
    retry_count = Column(Integer, nullable=False, default=0)
    max_retries = Column(Integer, nullable=False, default=3)
    error_message = Column(Text, comment="错误信息")

    # 时间
    call_time = Column(DateTime, nullable=False, comment="模型实际调用时间")
    create_time = Column(DateTime, nullable=False, default=datetime.now, comment="记录入库时间")

    # 本次调用消耗的积分
    point = Column(Numeric(10, 2), default=0, comment="消耗积分")
    remaining_point = Column(Numeric(10, 2), default=0, comment="扣除后剩余积分")
