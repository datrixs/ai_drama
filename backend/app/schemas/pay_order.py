from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_serializer, model_validator


# === 创建订单请求 ===

class MembershipOrderCreate(BaseModel):
    """创建会员购买订单请求"""
    level_id: str = Field(..., description="会员等级ID")
    subscribe_type: str = Field(..., description="订阅类型：monthly/yearly")
    pay_channel: str = Field("unionpay", description="支付渠道：wechat/alipay/unionpay")


class PointOrderCreate(BaseModel):
    """创建积分购买订单请求"""
    plan_id: Optional[str] = Field(None, description="积分购买方案ID（方案购买模式）")
    point_amount: Optional[int] = Field(None, description="自定义购买积分数（自定义充值模式）")
    pay_channel: str = Field("unionpay", description="支付渠道：wechat/alipay/unionpay")

    @model_validator(mode="after")
    def validate_mode(self):
        if not self.plan_id and not self.point_amount:
            raise ValueError("plan_id 和 point_amount 至少提供一个")
        if self.plan_id and self.point_amount:
            raise ValueError("plan_id 和 point_amount 不可同时提供")
        return self


# === 订单创建响应 ===

class OrderCreateInfo(BaseModel):
    """订单创建结果"""
    order_no: str = Field(..., description="订单号")
    original_amount: str = Field("0.00", description="原价")
    pay_amount: str = Field("0.00", description="实付金额")
    qr_code_url: str = Field("", description="支付二维码URL")
    expire_time: Optional[datetime] = Field(None, description="订单超时时间")

    @field_serializer("expire_time")
    def serialize_datetime(self, v):
        return v.strftime("%Y-%m-%d %H:%M:%S") if isinstance(v, datetime) else v


class PointOrderCreateInfo(OrderCreateInfo):
    """积分购买订单创建结果"""
    point_amount: str = Field("0", description="购买积分数")


# === 订单列表/详情 ===

class PayOrderItem(BaseModel):
    """订单列表项"""
    id: str = Field(..., description="订单ID")
    order_no: str = Field(..., description="订单号")
    order_type: Optional[int] = Field(None, description="订单类型")
    amount: Decimal = Field(Decimal("0.00"), description="金额")
    original_amount: Optional[Decimal] = Field(None, description="原价")
    status: int = Field(1, description="状态")
    subscribe_type: Optional[str] = Field(None, description="订阅类型")
    pay_method: Optional[int] = Field(None, description="支付方式")
    finished_time: Optional[datetime] = Field(None, description="完成时间")
    create_time: Optional[datetime] = Field(None, description="创建时间")
    purchased_points: Optional[str] = Field(None, description="购买积分")
    granted_points: Optional[str] = Field(None, description="赠送积分")

    class Config:
        from_attributes = True

    @field_serializer("amount", "original_amount")
    def serialize_decimal(self, v):
        return str(v) if isinstance(v, Decimal) else v

    @field_serializer("finished_time", "create_time")
    def serialize_datetime(self, v):
        return v.strftime("%Y-%m-%d %H:%M:%S") if isinstance(v, datetime) else v


class PayOrderPageParams(BaseModel):
    """订单列表查询参数"""
    page: int = Field(1, ge=1, description="页码")
    size: int = Field(10, ge=1, le=100, description="每页条数")
    order_type: Optional[int] = Field(None, description="订单类型筛选")
    status: Optional[int] = Field(None, description="支付状态筛选")


# === 充值与积分流水合并记录 ===

class CombinedRecordItem(BaseModel):
    """合并记录项（订单事件 + 积分流水事件统一格式）"""
    id: str = Field(..., description="记录ID")
    type: str = Field(..., description="类型：membership/point_purchase/monthly_grant/daily_grant/expire_clear")
    order_no: Optional[str] = Field(None, description="订单号（赠送/清零类为空）")
    amount: Optional[str] = Field(None, description="金额（赠送/清零类为空）")
    points: Optional[str] = Field(None, description="积分数（未成功订单为空）")
    subscribe_type: Optional[str] = Field(None, description="订阅类型（仅会员购买）")
    status: Optional[int] = Field(None, description="订单状态（仅订单事件）")
    remark: Optional[str] = Field(None, description="备注")
    create_time: Optional[str] = Field(None, description="开始时间")
    finished_time: Optional[str] = Field(None, description="结束时间")


class CombinedRecordPageParams(BaseModel):
    """合并记录查询参数"""
    page: int = Field(1, ge=1, description="页码")
    size: int = Field(10, ge=1, le=100, description="每页条数")
    type: Optional[Literal["membership", "point_purchase", "monthly_grant", "daily_grant", "expire_clear", "others"]] = Field(
        None, description="类型筛选：membership/point_purchase/monthly_grant/daily_grant/expire_clear"
    )
    status: Optional[int] = Field(None, ge=1, le=4, description="状态筛选：1待支付/2支付中/3成功/4失败")
