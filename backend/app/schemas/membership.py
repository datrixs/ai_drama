from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field, field_serializer


# === 会员等级 ===

class PrivilegeItem(BaseModel):
    """权益键值对"""
    key: str = Field(..., description="权益键")
    value: str = Field(..., description="权益值")
    remark: Optional[str] = Field(None, description="权益说明")


class MembershipLevelItem(BaseModel):
    """会员等级列表项"""
    id: str = Field(..., description="等级ID")
    name: str = Field(..., description="等级名称")
    level_order: int = Field(..., description="等级排序")
    monthly_price: str = Field("0.00", description="月付原价")
    monthly_discount_rate: str = Field("1.00", description="月付折扣率")
    monthly_discount_price: str = Field("0.00", description="月付折扣价")
    monthly_saved_percent: str = Field("0%", description="月付节省百分比")
    yearly_price: str = Field("0.00", description="年付原价")
    yearly_discount_rate: str = Field("1.00", description="年付折扣率")
    yearly_discount_price: str = Field("0.00", description="年付折扣价")
    yearly_saved_percent: str = Field("0%", description="年付节省百分比")
    can_buy_points: bool = Field(False, description="是否允许单独购买积分")
    privileges: List[PrivilegeItem] = Field(default_factory=list, description="权益列表")

    class Config:
        from_attributes = True


# === 用户会员 ===

class LevelBrief(BaseModel):
    """等级简要信息"""
    id: str = Field(..., description="等级ID")
    name: str = Field(..., description="等级名称")
    level_order: int = Field(..., description="等级排序")


class UserMembershipItem(BaseModel):
    """用户当前会员信息"""
    level: Optional[LevelBrief] = Field(None, description="会员等级")
    start_time: Optional[str] = Field(None, description="生效时间")
    expire_time: Optional[str] = Field(None, description="到期时间")
    subscribe_type: Optional[str] = Field(None, description="订阅类型")
    status: int = Field(0, description="状态")
    privileges: List[PrivilegeItem] = Field(default_factory=list, description="当前权益列表")
    next_level: Optional[LevelBrief] = Field(None, description="降级预购目标等级")
    auto_renew: bool = Field(False, description="是否自动续费")
    granted_balance: str = Field("0.00", description="赠送积分余额")
    purchased_balance: str = Field("0.00", description="购买积分余额")

    class Config:
        from_attributes = True

    @field_serializer("start_time", "expire_time")
    def serialize_datetime(self, v):
        return v.strftime("%Y-%m-%d %H:%M:%S") if isinstance(v, datetime) else v


# === 变更预览 ===

class ChangePreviewRequest(BaseModel):
    """预览会员变更请求"""
    target_level_id: str = Field(..., description="目标等级ID")
    subscribe_type: str = Field("monthly", description="目标订阅类型")


class ChangePreviewResponse(BaseModel):
    """预览会员变更响应"""
    change_type: int = Field(0, description="变更类型：0=拒绝 1=新购 2=升级 3=降级预购 5=到期重购")
    pay_amount: str = Field("0.00", description="需支付金额")
    point_adjust: str = Field("0", description="需补发积分")
    effective_time: Optional[str] = Field(None, description="生效时间")
    expire_time: Optional[str] = Field(None, description="到期时间")
    message: str = Field("", description="提示文案")
