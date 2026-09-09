from sqlalchemy import Column, Integer, String, JSON, Boolean
from sqlalchemy.orm import relationship

from app.models import BasicModel


class UserApiConfig(BasicModel):
    """用户API配置表"""
    __tablename__ = "user_api_config"

    user_id = Column(String(256), comment="用户ID")
    user = relationship("User", primaryjoin="UserApiConfig.user_id == foreign(User.id)")

    analysis_model = Column(String(128), comment="用户配置的分析模型。对应AIModel.model_name")
    character_model = Column(String(128), comment="用户配置的角色图片模型")
    location_model = Column(String(128), comment="用户配置的场景图片模型")
    storyboard_model = Column(String(128), comment="用户配置的分镜图片模型")
    edit_model = Column(String(128), comment="用户配置的修图模型")
    video_model = Column(String(128), comment="用户配置的视频模型")
    audio_model = Column(String(128), comment="用户配置的语音模型")

    # 源系统配置，未使用
    # lip_sync_model = Column(String(128), comment="用户配置的口型同步模型")
    # voice_design_model = Column(String(128), comment="用户配置的音色设计模型")

    # 并发配置
    analysis_concurrency = Column(Integer, default=5, comment="分析流程并发上限")
    image_concurrency = Column(Integer, default=5, comment="图像流程并发上限")
    video_concurrency = Column(Integer, default=5, comment="视频流程并发上限")

    video_ratio = Column(String(128), default="9:16", comment="屏幕比例")
    video_resolution = Column(String(128), default="720p", comment="视频分辨率")

    art_style = Column(String(128), default="american-comic", comment="艺术风格")
    tts_rate = Column(String(128), default="+50%", comment="")
    image_resolution = Column(String(128), default="2K", comment="图像清晰度")
    capability_defaults = Column(String(128), comment="")

    # API key配置
    ark_api_key = Column(String(256), comment="火山引擎（Seedream+Seedance）")
    jd_api_key = Column(String(256), comment="京东API key")

    # 用户模型列表（用户正在使用的模型，以打开开关的模型为准）
    custom_models = Column(JSON, comment="自定义模型列表 + 价格（JSON）")

    # 用户使用的供应商列表
    custom_providers = Column(JSON, comment="自定义 OpenAI 兼容提供商列表（JSON，包含 API Key）")

    # 仅 admin 账号在「系统设置」中可改；开启后所有 ARK 火山视频生成请求强制带水印
    ark_video_watermark = Column(Boolean, default=False, comment="开启后所有 ARK 火山视频生成请求强制带水印")

    # 资产中心全局图同步火山私域时的资产组 Id（与 novel_promotion_projects.volcPrivateAssetGroupId 语义一致，按用户维度）
    volc_private_asset_group_id = Column(String(256), comment="资产中心全局图同步火山私域时的资产组 Id")
    byteplus_private_asset_group_id = Column(String(256), nullable=True, comment="资产中心全局图同步 BytePlus 时的资产组 Id")

    # API 端点
    endpoint = Column(String(128), comment="端点")