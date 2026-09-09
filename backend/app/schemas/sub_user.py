from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_serializer


class SubUserCreateSchema(BaseModel):
    username: str = Field(..., min_length=2, max_length=128, description="用户名")
    password: str = Field(..., min_length=6, max_length=64, description="密码")
    email: Optional[str] = Field(None, max_length=128, description="邮箱")
    remark: Optional[str] = Field(None, max_length=128, description="备注")


class SubUserUpdateSchema(BaseModel):
    status: Optional[str] = Field(None, description="账户状态：enable-正常，disable-禁用")
    remark: Optional[str] = Field(None, max_length=128, description="备注")
    api_key: Optional[str] = Field(None, max_length=256, description="API Key")
    permissions: Optional[dict] = Field(None, description="权限配置")
    shared_folder_ids: Optional[list[str]] = Field(None, description="共享给子账号的文件夹ID列表")


class SubUserTransferBalanceSchema(BaseModel):
    amount: Decimal = Field(..., gt=0, description="划拨积分数量，必须大于0")


class SubUserResponse(BaseModel):
    id: str = Field(..., description="用户ID")
    username: str = Field(..., description="用户名")
    email: Optional[str] = Field(None, description="邮箱")
    status: str = Field(..., description="账户状态")
    type: Optional[str] = Field(None, description="账号类型")
    parent_user_id: Optional[str] = Field(None, description="主账号ID")
    sub_user_limit: int = Field(default=0, description="子账号数量上限")
    remark: Optional[str] = Field(None, description="备注")
    api_key: Optional[str] = Field(None, description="API Key")
    permissions: Optional[dict] = Field(None, description="权限配置")
    shared_folder_ids: Optional[list[str]] = Field(None, description="共享给子账号的文件夹ID列表")
    balance: Decimal = Field(default=Decimal("0.00"), description="用户余额")
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
