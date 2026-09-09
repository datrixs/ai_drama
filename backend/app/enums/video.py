from enum import Enum


class ShortVideoTaskStatus(str, Enum):
    """短视频生成任务状态"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    QUEUED = "queued"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class VideoSuperResTaskStatus(str, Enum):
    """视频超分任务状态"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class EpisodeStatus(str, Enum):
    """剧集状态（分镜生成阶段）"""
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class StoryboardStatus(str, Enum):
    """分镜状态"""
    PENDING = "pending"
    IMAGE_GENERATING = "image_generating"
    IMAGE_COMPLETED = "image_completed"
    VIDEO_GENERATING = "video_generating"
    VIDEO_COMPLETED = "video_completed"
    FAILED = "failed"
