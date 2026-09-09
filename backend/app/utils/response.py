"""
封装API响应格式

响应格式：
{
    "code": 0,
    "msg": "success",
    "data": {}
}
"""
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Any


def _serialize(data: Any) -> Any:
    if isinstance(data, BaseModel):
        return data.model_dump(mode="json")
    if isinstance(data, list):
        return [_serialize(item) for item in data]
    return data


def success_response(
    msg: str = "success",
    data: Optional[Any] = None
) -> JSONResponse:
    """
    成功响应，自动处理 Pydantic 对象序列化
    """
    return JSONResponse(
        content={"code": 0, "msg": msg, "data": _serialize(data)},
        status_code=200,
    )


def error_response(
    code: int = -1,
    msg: str = "error",
    data: Optional[Any] = None
) -> JSONResponse:
    """
    错误响应
    """
    return JSONResponse(
        content={"code": code, "msg": msg, "data": data},
        status_code=400,
    )
