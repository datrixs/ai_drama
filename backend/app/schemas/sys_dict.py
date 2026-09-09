from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_serializer


class SysDictResponse(BaseModel):
    """每一条数据字典"""
    dict_name: str = Field(description="数据字典名称")
    key: str = Field(description="键名")
    value: str = Field(description="键值")
    sort: Optional[int] = Field(default=1, description="排序")
    remark: Optional[str] = Field(default='', description="备注")


class SysDictCreateSchema(BaseModel):
    """创建数据字典"""
    dict_name: str = Field(description="数据字典名称")
    key: str = Field(description="键名")
    value: str = Field(description="键值")
    sort: Optional[int] = Field(default=1, description="排序")
    remark: Optional[str] =  Field(default='', description="备注")


class SysDictUpdateSchema(BaseModel):
    pass