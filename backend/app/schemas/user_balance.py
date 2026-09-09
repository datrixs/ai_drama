from datetime import datetime
from typing import Optional
from decimal import Decimal

from pydantic import BaseModel, Field, field_serializer, model_validator


class UserBalanceCreateSchema(BaseModel):
    """创建用户余额"""
    user_id: str = Field(description="用户ID")
    # balance: Optional[Decimal] = Field(default=Decimal(0.0), description="余额")
    # frozen_amount: Optional[Decimal] = Field(default=Decimal(0.0), description="冻结金额")
    # total_spent: Optional[Decimal] = Field(default=Decimal(0.0), description="总花费")


class UserBalanceUpdateSchema(BaseModel):
    """更新用户余额"""
    user_id: str = Field(description="用户ID")
    frozen_amount: Decimal = Field(description="冻结金额")