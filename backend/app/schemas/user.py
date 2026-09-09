from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_serializer

from app.enums.user import UserRegion


class UserCreateSchema(BaseModel):
    username: str = Field(..., min_length=2, max_length=128, description="用户名")
    password: str = Field(..., min_length=6, max_length=64, description="密码")
    email: Optional[str] = Field(None, max_length=128, description="邮箱")
    status: str = Field(default="enable", description="账户状态：enable-正常，disable-禁用")
    type: str = Field(default="normal", description="账号类型：normal-普通版，lite-轻量版，pro-专业版")
    parent_user_id: Optional[str] = Field(None, description="主账号ID")
    sub_user_limit: int = Field(default=0, description="子账号数量上限")
    remark: Optional[str] = Field(None, max_length=128, description="备注")
    region: Optional[str] = Field(None, description="区域: domestic-国内/overseas-国际")


class UserUpdateSchema(BaseModel):
    email: Optional[str] = Field(None, max_length=128, description="邮箱")
    status: Optional[str] = Field(None, description="账户状态：enable-正常，disable-禁用")
    password: Optional[str] = Field(None, min_length=6, max_length=64, description="密码")
    type: Optional[str] = Field(None, description="账号类型：normal-普通版，lite-轻量版，pro-专业版")
    remark: Optional[str] = Field(None, max_length=128, description="备注")
    region: Optional[str] = Field(None, description="区域: domestic-国内/overseas-国际")


class ChangePasswordSchema(BaseModel):
    old_password: str = Field(..., description="原密码")
    new_password: str = Field(..., min_length=6, max_length=64, description="新密码")


class UserResponse(BaseModel):
    id: str = Field(..., description="用户ID")
    username: str = Field(..., description="用户名")
    email: Optional[str] = Field(None, description="邮箱")
    status: str = Field(..., description="账户状态")
    type: Optional[str] = Field(None, description="账号类型")
    parent_user_id: Optional[str] = Field(None, description="主账号ID")
    sub_user_limit: int = Field(default=0, description="子账号数量上限")
    remark: Optional[str] = Field(None, description="备注")
    region: str = Field(default=UserRegion.DOMESTIC, description="区域: domestic-国内/overseas-国际")
    balance: Decimal = Field(default=Decimal("0.00"), description="用户余额")
    permissions: Optional[dict] = Field(None, description="权限配置（仅子账号返回）")
    create_time: Optional[datetime] = Field(None, description="创建时间")
    update_time: Optional[datetime] = Field(None, description="更新时间")

    class Config:
        from_attributes = True

    @field_serializer("create_time", "update_time")
    def serialize_datetime(self, v: datetime | None) -> str | None:
        if v is None:
            return None
        return v.strftime("%Y-%m-%d %H:%M:%S")

    @field_serializer("balance")
    def serialize_balance(self, v: Decimal | None) -> str:
        if v is None:
            return "0.00"
        return str(v)
