from enum import Enum, IntEnum


class TaskStatus(str, Enum):
    """任务状态"""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


class TaskType(str, Enum):
    """任务类型"""
    ASSET_HUB_AI_DESIGN_CHARACTER = "asset_hub_ai_design_character"
    ASSET_HUB_AI_MODIFY_CHARACTER = "asset_hub_ai_modify_character"
    ASSET_HUB_REFERENCE_TO_CHARACTER = "asset_hub_reference_to_character"
    ASSET_HUB_IMAGE = "asset_hub_image"
    ASSET_HUB_MODIFY = "asset_hub_modify"
    ASSET_HUB_AI_DESIGN_LOCATION = "asset_hub_ai_design_location"
    ASSET_HUB_AI_MODIFY_LOCATION = "asset_hub_ai_modify_location"
    ASSET_HUB_AI_MODIFY_PROP = "asset_hub_ai_modify_prop"
    PROJECT_ASSET_GENERATE = "project_asset_generate"
    PROJECT_ASSET_BATCH_GENERATE = "project_asset_batch_generate"
    PROJECT_ASSET_MODIFY_IMAGE = "project_asset_modify_image"
    PROJECT_ASSET_REFERENCE_GENERATE = "project_asset_reference_generate"
    ASSET_HUB_VOICE_DESIGN = "asset_hub_voice_design"