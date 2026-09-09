from sqlalchemy.orm import Session
from uuid import uuid4

from app.models.user_api_config import UserApiConfig
from app.schemas.user_api_config import (
    UserApiConfigCreateSchema,
    UserApiConfigUpdateSchema,
)
from app.crud.base_crud import CRUDBase


class CRUDUserApiConfig(
    CRUDBase[UserApiConfig, UserApiConfigCreateSchema, UserApiConfigUpdateSchema]
):
    """
    用户API配置 CRUD 操作
    """

    def __init__(self, model: type[UserApiConfig]):
        super().__init__(model)

    def get_by_user_id(
        self, *, user_id: str, db: Session
    ) -> UserApiConfig | None:
        """
        根据用户ID查询API配置
        """
        return db.query(UserApiConfig).filter_by(user_id=user_id).first()

    def get_default_api_config(self, user_id: str) -> UserApiConfig:
        """
        获取默认API配置（硬编码，不从数据库读取）
        """
        config = UserApiConfig()
        config.id = str(uuid4())
        config.user_id = user_id

        config.analysis_model = None
        config.character_model = None
        config.location_model = None
        config.storyboard_model = None
        config.edit_model = None
        config.video_model = None
        config.audio_model = None

        config.analysis_concurrency = 5
        config.image_concurrency = 5
        config.video_concurrency = 5

        config.video_ratio = "9:16"
        config.video_resolution = "720p"
        config.art_style = "american-comic"
        config.tts_rate = "+50%"
        config.image_resolution = "2K"
        config.capability_defaults = None

        config.fal_api_key = None
        config.google_api_key = None
        config.ark_api_key = None
        config.qwen_api_key = None
        config.jd_api_key = None

        config.custom_models = None
        config.custom_providers = None
        config.ark_video_watermark = False
        config.volc_private_asset_group_id = None

        return config


user_api_config_crud = CRUDUserApiConfig(UserApiConfig)
