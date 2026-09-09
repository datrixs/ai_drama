from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import Query
from pydantic import BaseModel, Field, field_serializer

from app.deps.base import PageParams
from app.enums.transfer import PointTransferStatus


class TransferCreateSchema(BaseModel):
    """发起转账请求"""
    target_username: str = Field(..., min_length=1, max_length=128, description="对方用户名")
    amount: Decimal = Field(..., gt=0, description="转账积分数量，必须大于0")
    password: str = Field(..., min_length=1, description="当前用户密码")


class TransferRecordResponse(BaseModel):
    """转账记录响应"""
    id: str = Field(..., description="记录ID")
    user_id: str = Field(..., description="转出用户ID")
    transfer_to_user_id: str = Field(..., description="转入用户ID")
    target_username: Optional[str] = Field(None, description="对方用户名")
    point: Decimal = Field(..., description="转账积分")
    transfer_type: int = Field(..., description="转账类型")
    status: int = Field(..., description="转账状态")
    create_time: Optional[datetime] = Field(None, description="创建时间")

    class Config:
        from_attributes = True

    @field_serializer("create_time")
    def serialize_datetime(self, v: datetime | None) -> str | None:
        if v is None:
            return None
        return v.strftime("%Y-%m-%d %H:%M:%S")

    @field_serializer("point")
    def serialize_point(self, v: Decimal | None) -> str:
        if v is None:
            return "0.00"
        return str(v)


class TransferRecordPageParams(PageParams):
    """转账记录分页查询参数"""
    page: int = Field(Query(1, ge=1, description="页码"))
    size: int = Field(Query(10, ge=1, le=100, description="每页数量"))
