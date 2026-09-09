"""回调 URL 构建工具"""
from enum import Enum

from fastapi import Request

from app.core.config import settings


class CallbackPath(str, Enum):
    """Seedance SDK 回调路径枚举"""

    SEEDANCE_VIDEO = "/api/v1/video/seedance_callback"
    SEEDANCE_SHORT_VIDEO = "/api/v1/short-video/seedance_callback"
    SUPER_RESOLUTION = "/api/v1/super-resolution/callback"
    CANVAS_VIDEO = "/api/v1/canvas/seedance_callback"


def build_callback_url(
    request: Request | None = None,
    path: CallbackPath = CallbackPath.SEEDANCE_VIDEO,
) -> str:
    """构建 Seedance SDK 视频生成回调 URL

    Args:
        request: FastAPI 请求对象，用于提取 base_url
        path: 回调路径枚举，默认成片视频回调
    """
    if settings.CALLBACK_BASE_URL:
        return f"{settings.CALLBACK_BASE_URL.rstrip('/')}{path.value}"
    if request is not None:
        return f"{str(request.base_url).rstrip('/')}{path.value}"
    return ""
