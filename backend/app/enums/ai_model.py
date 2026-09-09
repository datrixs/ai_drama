from enum import Enum


class AIModelType(Enum):
    """
    大模型类型
        text: 文本模型
        image: 图片模型
        video: 视频模型
        audio: 音频模型
    """
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"


class VideoResolutionType(Enum):
    """
    视频分辨率
    """
    R_480P = "480P"
    R_720P = "720P"
    R_1080P = "1080P"
    R_2K = "2K"
    R_4K = "4K"


class SuperResResolutionType(Enum):
    """
    视频超分，目标分辨率
    """
    R_720P = "720P"
    R_1080P = "1080P"
    R_2K = "2K"
    R_4K = "4K"