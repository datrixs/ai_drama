from enum import Enum, IntEnum


class CodeType(IntEnum):
    """响应状态码"""
    SUCCESS_CODE = 0
    FAIL_CODE = 1
    EXPIRATION_CODE = 2
    EXTERNAL_SERVICE_ERROR = 3
    RESOURCE_NOT_UNLOCKED = 4
    TOKEN_INSUFFICIENT = 5
    VIP_INSUFFICIENT = 6


class DataStatus(IntEnum):
    """数据状态"""
    Normal = 0
    Delete = 1


class TokenType(Enum):
    """Token 类型"""
    ACCESS = "access"
    REFRESH = "refresh"


class WSEventType(str, Enum):
    """WebSocket 推送事件类型"""
    SHORT_VIDEO_PROGRESS = "short_video_progress"
    VIDEO_PROGRESS = "video_progress"
    SCRIPT_PROGRESS = "script_progress"
    PAY_ORDER_STATUS = "pay_order_status"
    EPISODE_SCRIPT_PROGRESS = "episode_script_progress"
    VIDEO_CONCAT = "video_concat"
    SUPER_RESOLUTION_PROGRESS = "super_resolution_progress"
    CANVAS_GENERATION_PROGRESS = "canvas_generation_progress"
