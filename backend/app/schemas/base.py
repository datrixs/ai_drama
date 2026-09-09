from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field

from app.enums.base import CodeType


class Msg(BaseModel):
    """统一响应模型"""
    code: CodeType = CodeType.SUCCESS_CODE
    message: str = "success"
    data: Optional[Any] = None


class PageMsg(Msg):
    """分页响应模型"""
    data: Optional[List[Any]] = None
    pagination: Optional[dict] = None


class PageBase(BaseModel):
    """分页基础信息"""
    page: int = Field(..., description="当前页码")
    size: int = Field(..., description="每页数量")
    total_count: int = Field(..., description="总记录数")


class SchemaBase(BaseModel):
    """Schema 基类，提供时间格式化"""
    create_time: Optional[datetime] = Field(None, description="创建时间")
    update_time: Optional[datetime] = Field(None, description="更新时间")

    class Config:
        json_encoders = {
            datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S") if v else None
        }
