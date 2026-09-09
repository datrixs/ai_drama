from typing import Optional

from fastapi import Query
from pydantic import BaseModel, Field


class Params(BaseModel):
    """查询参数基类"""
    pass


class PageParams(Params):
    """分页查询参数基类"""
    page: int = Field(Query(1, ge=1, description="页码"))
    size: int = Field(Query(20, ge=1, le=99999, description="分页数"))
    is_paginate: Optional[bool] = Field(Query(True, description="是否分页"))