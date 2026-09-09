from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_serializer


# === 积分购买方案 ===

class PointPlanItem(BaseModel):
    """积分购买方案列表项"""
    id: str = Field(..., description="方案ID")
    point_amount: str = Field("0", description="积分数")
    original_price: str = Field("0.00", description="原价")
    discount_price: str = Field("0.00", description="折扣价")

    class Config:
        from_attributes = True


# === 积分记录 ===

class PointRecordItem(BaseModel):
    """积分变动记录项"""
    id: str = Field(..., description="记录ID")
    point_amount: str = Field("0", description="积分数")
    balance_after: Optional[str] = Field(None, description="本次变动后的总积分余额（历史数据可能为空）")
    record_type: int = Field(..., description="记录类型")
    source_id: Optional[str] = Field(None, description="来源ID")
    level_id: Optional[str] = Field(None, description="会员等级ID")
    grant_month: Optional[str] = Field(None, description="赠送周期起始日（YYYY-MM-DD）")
    remark: Optional[str] = Field(None, description="备注")
    create_time: Optional[str] = Field(None, description="创建时间")

    class Config:
        from_attributes = True

    @field_serializer("create_time")
    def serialize_datetime(self, v):
        return v.strftime("%Y-%m-%d %H:%M:%S") if isinstance(v, datetime) else v


class PointRecordPageParams(BaseModel):
    """积分记录查询参数"""
    page: int = Field(1, ge=1, description="页码")
    size: int = Field(10, ge=1, le=100, description="每页条数")
    record_type: Optional[int] = Field(None, description="记录类型筛选")
