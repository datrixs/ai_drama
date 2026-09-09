"""无限画布相关枚举"""
from enum import Enum


class CanvasItemType(str, Enum):
    """画布节点类型

    - TEXT：文本节点
    - IMAGE：图片节点
    - VIDEO：视频节点
    - AUDIO：音频节点
    - GROUP：组合节点（容器，仅作视觉与拖动整体，不参与连线）
    """
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    GROUP = "group"


class CanvasItemRunStatus(str, Enum):
    """节点最近一次生成的运行状态（与 AICON 对齐）"""
    IDLE = "idle"
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class CanvasGenerationStatus(str, Enum):
    """单次生成历史的状态（与 AICON 对齐）"""
    IDLE = "idle"
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"
