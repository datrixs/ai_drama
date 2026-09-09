from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field

from app import schemas
from app.deps.base import PageParams


class ModelCallLogPageParams(PageParams):
    """扣费记录列表查询参数"""
    user_id: Optional[str] = Field(Query(None, description="用户ID"))
    project_id: Optional[str] = Field(Query(None, description="项目ID"))
    task_id: Optional[str] = Field(Query(None, description="任务ID"))
    model_provider: Optional[str] = Field(Query(None, description="模型供应商"))
    model_name: Optional[str] = Field(Query(None, description="模型名称"))
    response_status: Optional[int] = Field(Query(None, description="HTTP状态码"))
    is_retry: Optional[bool] = Field(Query(None, description="是否重试"))
    call_time_start: Optional[datetime] = Field(Query(None, description="调用开始时间"))
    call_time_end: Optional[datetime] = Field(Query(None, description="调用结束时间"))


class ModelCallLogItem(BaseModel):
    """扣费记录列表项"""
    model_config = ConfigDict(from_attributes=True, json_encoders={
        datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S") if v else None
    })

    id: str = Field(..., description="记录ID")
    user_id: str = Field(..., description="调用用户ID")
    username: Optional[str] = Field(None, description="调用用户名")
    project_id: Optional[str] = Field(None, description="关联项目ID")
    project_title: Optional[str] = Field(None, description="关联项目名称")
    task_id: Optional[str] = Field(None, description="关联任务ID")
    request_id: str = Field(..., description="唯一请求ID")
    provider_request_id: Optional[str] = Field(None, description="模型厂商请求ID")
    model_provider: str = Field(..., description="供应商")
    model_provider_name: Optional[str] = Field(None, description="供应商名称")
    model_name: str = Field(..., description="模型名")
    endpoint: Optional[str] = Field(None, description="API端点")
    api_key_masked: Optional[str] = Field(None, description="脱敏API Key")
    response_status: Optional[int] = Field(None, description="HTTP状态码")
    input_tokens: int = Field(0, description="输入token数")
    output_tokens: int = Field(0, description="输出token数")
    total_tokens: int = Field(0, description="总token数")
    latency_ms: Optional[int] = Field(None, description="调用耗时(毫秒)")
    point: Optional[Decimal] = Field(None, description="消耗积分")
    remaining_point: Optional[Decimal] = Field(None, description="扣除后剩余积分")
    is_retry: bool = Field(False, description="是否重试")
    retry_count: int = Field(0, description="重试次数")
    error_message: Optional[str] = Field(None, description="错误信息")
    call_time: Optional[datetime] = Field(None, description="模型实际调用时间")
    create_time: Optional[datetime] = Field(None, description="记录入库时间")
    media_type: Optional[str] = Field(None, description="调用类型: text_text/text_image/image_text/image_image/video")


class ModelCallLogDetailItem(ModelCallLogItem):
    """扣费记录详情项（含请求/响应体）"""
    request_body: Optional[Dict[str, Any]] = Field(None, description="请求体")
    response_body: Optional[Dict[str, Any]] = Field(None, description="响应体摘要")
    usage_details: Optional[Dict[str, Any]] = Field(None, description="供应商特有usage字段")
    max_retries: int = Field(3, description="最大重试次数")
    media_type: Optional[str] = Field(None, description="调用类型: text_text/text_image/image_text/image_image/video")
    input_media: Optional[List[Dict[str, Any]]] = Field(None, description="输入媒体信息")
    output_media: Optional[List[Dict[str, Any]]] = Field(None, description="输出媒体信息")


class ModelCallLogMsg(schemas.Msg):
    """单条扣费记录响应"""
    data: Optional[ModelCallLogDetailItem] = Field(None, description="数据")


class ModelCallLogPageMsg(schemas.PageMsg):
    """扣费记录列表响应"""
    data: Optional[List[ModelCallLogItem]] = Field(None, description="数据")


class ModelCallLogSummaryItem(BaseModel):
    """扣费记录统计摘要"""
    total_calls: int = Field(0, description="总调用次数")
    success_calls: int = Field(0, description="成功次数")
    failed_calls: int = Field(0, description="失败次数")
    total_input_tokens: int = Field(0, description="总输入token数")
    total_output_tokens: int = Field(0, description="总输出token数")
    total_tokens: int = Field(0, description="总token数")
    total_point: Optional[Decimal] = Field(None, description="总消耗积分")
    avg_latency_ms: Optional[float] = Field(None, description="平均耗时(毫秒)")


class ModelCallLogSummaryMsg(schemas.Msg):
    """扣费记录统计响应"""
    data: Optional[ModelCallLogSummaryItem] = Field(None, description="数据")
