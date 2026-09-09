from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_serializer, model_validator


class ProviderSchema(BaseModel):
    """
    自定义 OpenAI 兼容提供商

    唯一键合约：providerId::modelId 组合必须唯一
    """
    id: str = Field(..., description="Provider 唯一标识")
    name: str = Field(..., description="Provider 显示名称")
    base_url: Optional[str] = Field("", description="OpenAI 兼容 Base URL")
    api_key: Optional[str] = Field(None, description="API Key（写入时加密存储，读取时脱敏）")
    enabled: bool = Field(default=True, description="是否启用")


class CustomModelSchema(BaseModel):
    """
    自定义模型条目

    唯一键合约：provider_id + model 组合必须唯一
    """
    provider_id: str = Field(..., description="所属 Provider ID")
    model: str = Field(..., description="模型标识符")
    model_name: str = Field(..., description="模型显示名称")
    model_type: str = Field(..., description="模型类型：llm / image / video / audio")
    enabled: bool = Field(default=True, description="是否启用")
    price: Optional[dict] = Field(None, description="模型价格信息（JSON）")

    # 兼容旧数据中的model_id属性
    model_config = {"populate_by_name": True}

    @model_validator(mode="before")
    @classmethod
    def migrate_model_id(cls, values):
        if isinstance(values, dict) and "model" not in values and "model_id" in values:
            values["model"] = values.pop("model_id")
        return values


class DefaultModelsSchema(BaseModel):
    """
    默认模型配置分组
    """
    analysis_model: Optional[str] = Field(None, description="分析模型")
    character_model: Optional[str] = Field(None, description="角色图片模型")
    location_model: Optional[str] = Field(None, description="场景图片模型")
    storyboard_model: Optional[str] = Field(None, description="分镜图片模型")
    edit_model: Optional[str] = Field(None, description="修图模型")
    video_model: Optional[str] = Field(None, description="视频模型")
    audio_model: Optional[str] = Field(None, description="语音模型")


class ConcurrencySchema(BaseModel):
    """
    并发配置分组
    """
    analysis_concurrency: Optional[int] = Field(None, description="分析流程并发上限")
    image_concurrency: Optional[int] = Field(None, description="图像流程并发上限")
    video_concurrency: Optional[int] = Field(None, description="视频流程并发上限")


_API_KEY_FIELDS = (
    "fal_api_key",
    "google_api_key",
    "ark_api_key",
    "qwen_api_key",
    "jd_api_key",
)


def _mask_api_key(value: str | None) -> str | None:
    """
    对 API Key 做脱敏处理，仅保留前4位和后4位
    """
    if not value:
        return value
    if len(value) <= 8:
        return "****"
    return value[:4] + "****" + value[-4:]


class UserApiConfigSchema(BaseModel):
    """
    用户API配置响应模型

    API Key 字段读取时脱敏返回；custom_providers 中的 apiKey 同样脱敏
    """
    id: str = Field(..., description="记录ID")
    user_id: str = Field(..., description="用户ID")

    analysis_model: Optional[str] = Field(None, description="分析模型")
    character_model: Optional[str] = Field(None, description="角色图片模型")
    location_model: Optional[str] = Field(None, description="场景图片模型")
    storyboard_model: Optional[str] = Field(None, description="分镜图片模型")
    edit_model: Optional[str] = Field(None, description="修图模型")
    video_model: Optional[str] = Field(None, description="视频模型")
    audio_model: Optional[str] = Field(None, description="语音模型")

    analysis_concurrency: Optional[int] = Field(None, description="分析流程并发上限")
    image_concurrency: Optional[int] = Field(None, description="图像流程并发上限")
    video_concurrency: Optional[int] = Field(None, description="视频流程并发上限")

    video_ratio: Optional[str] = Field(None, description="屏幕比例")
    video_resolution: Optional[str] = Field(None, description="视频分辨率")
    art_style: Optional[str] = Field(None, description="艺术风格")
    tts_rate: Optional[str] = Field(None, description="TTS语速")
    image_resolution: Optional[str] = Field(None, description="图像清晰度")
    capability_defaults: Optional[str] = Field(None, description="能力默认配置")

    fal_api_key: Optional[str] = Field(None, description="FAL（图片+视频+语音，脱敏）")
    google_api_key: Optional[str] = Field(None, description="Google AI（Gemini 图片，脱敏）")
    ark_api_key: Optional[str] = Field(None, description="火山引擎（Seedream+Seedance，脱敏）")
    qwen_api_key: Optional[str] = Field(None, description="阿里百炼（声音设计，脱敏）")
    jd_api_key: Optional[str] = Field(None, description="京东（脱敏）")

    custom_models: Optional[list[CustomModelSchema]] = Field(None, description="自定义模型列表 + 价格")
    custom_providers: Optional[list[ProviderSchema]] = Field(None, description="自定义 OpenAI 兼容提供商列表")

    ark_video_watermark: Optional[bool] = Field(None, description="开启后所有 ARK 火山视频生成请求强制带水印")
    volc_private_asset_group_id: Optional[str] = Field(None, description="资产中心全局图同步火山私域时的资产组 Id")

    create_time: Optional[datetime] = Field(None, description="创建时间")
    update_time: Optional[datetime] = Field(None, description="更新时间")

    class Config:
        from_attributes = True

    @field_serializer("create_time", "update_time")
    def serialize_datetime(self, v: datetime | None) -> str | None:
        if v is None:
            return None
        return v.strftime("%Y-%m-%d %H:%M:%S")

    @field_serializer(*_API_KEY_FIELDS)
    def serialize_api_key(self, v: str | None) -> str | None:
        return _mask_api_key(v)

    @field_serializer("custom_providers")
    def serialize_providers(self, v: list[ProviderSchema] | None) -> list[dict] | None:
        if v is None:
            return None
        result = []
        for p in v:
            item = p.model_dump()
            item["api_key"] = _mask_api_key(item.get("api_key"))
            result.append(item)
        return result


class UserApiConfigCreateSchema(BaseModel):
    """
    创建用户API配置
    """
    user_id: str = Field(..., description="用户ID")

    analysis_model: Optional[str] = Field(None, description="分析模型")
    character_model: Optional[str] = Field(None, description="角色图片模型")
    location_model: Optional[str] = Field(None, description="场景图片模型")
    storyboard_model: Optional[str] = Field(None, description="分镜图片模型")
    edit_model: Optional[str] = Field(None, description="修图模型")
    video_model: Optional[str] = Field(None, description="视频模型")
    audio_model: Optional[str] = Field(None, description="语音模型")

    analysis_concurrency: Optional[int] = Field(None, description="分析流程并发上限")
    image_concurrency: Optional[int] = Field(None, description="图像流程并发上限")
    video_concurrency: Optional[int] = Field(None, description="视频流程并发上限")

    video_ratio: Optional[str] = Field(None, description="屏幕比例")
    video_resolution: Optional[str] = Field(None, description="视频分辨率")
    art_style: Optional[str] = Field(None, description="艺术风格")
    tts_rate: Optional[str] = Field(None, description="TTS语速")
    image_resolution: Optional[str] = Field(None, description="图像清晰度")
    capability_defaults: Optional[str] = Field(None, description="能力默认配置")

    fal_api_key: Optional[str] = Field(None, description="FAL（图片+视频+语音）")
    google_api_key: Optional[str] = Field(None, description="Google AI（Gemini 图片）")
    ark_api_key: Optional[str] = Field(None, description="火山引擎（Seedream+Seedance）")
    qwen_api_key: Optional[str] = Field(None, description="阿里百炼（声音设计）")
    jd_api_key: Optional[str] = Field(None, description="京东")

    custom_models: Optional[list[CustomModelSchema]] = Field(None, description="自定义模型列表 + 价格")
    custom_providers: Optional[list[ProviderSchema]] = Field(None, description="自定义 OpenAI 兼容提供商列表")

    ark_video_watermark: Optional[bool] = Field(None, description="开启后所有 ARK 火山视频生成请求强制带水印")
    volc_private_asset_group_id: Optional[str] = Field(None, description="资产中心全局图同步火山私域时的资产组 Id")


class UserApiConfigUpdateSchema(BaseModel):
    """
    更新用户API配置

    apiKey 三态更新规则：
    - 字段未传（exclude_unset 中不存在）→ 保留原值
    - 字段传空字符串 "" → 删除（置空）
    - 字段传非空字符串 → 覆盖为新值

    custom_providers 中每个 provider 的 apiKey 同样遵循三态规则
    """
    analysis_model: Optional[str] = Field(None, description="分析模型")
    character_model: Optional[str] = Field(None, description="角色图片模型")
    location_model: Optional[str] = Field(None, description="场景图片模型")
    storyboard_model: Optional[str] = Field(None, description="分镜图片模型")
    edit_model: Optional[str] = Field(None, description="修图模型")
    video_model: Optional[str] = Field(None, description="视频模型")
    audio_model: Optional[str] = Field(None, description="语音模型")

    analysis_concurrency: Optional[int] = Field(None, description="分析流程并发上限")
    image_concurrency: Optional[int] = Field(None, description="图像流程并发上限")
    video_concurrency: Optional[int] = Field(None, description="视频流程并发上限")

    video_ratio: Optional[str] = Field(None, description="屏幕比例")
    video_resolution: Optional[str] = Field(None, description="视频分辨率")
    art_style: Optional[str] = Field(None, description="艺术风格")
    tts_rate: Optional[str] = Field(None, description="TTS语速")
    image_resolution: Optional[str] = Field(None, description="图像清晰度")
    capability_defaults: Optional[str] = Field(None, description="能力默认配置")

    fal_api_key: Optional[str] = Field(None, description="FAL API key（空字符串=删除，不传=保留）")
    google_api_key: Optional[str] = Field(None, description="Google API key（空字符串=删除，不传=保留）")
    ark_api_key: Optional[str] = Field(None, description="火山引擎 API key（空字符串=删除，不传=保留）")
    qwen_api_key: Optional[str] = Field(None, description="阿里百炼 API key（空字符串=删除，不传=保留）")
    jd_api_key: Optional[str] = Field(None, description="京东 API key（空字符串=删除，不传=保留）")

    custom_models: Optional[list[CustomModelSchema]] = Field(None, description="自定义模型列表 + 价格")
    custom_providers: Optional[list[ProviderSchema]] = Field(None, description="自定义提供商列表（apiKey 三态：不传=保留，空串=删除，非空=覆盖）")

    ark_video_watermark: Optional[bool] = Field(None, description="开启后所有 ARK 火山视频生成请求强制带水印")
    volc_private_asset_group_id: Optional[str] = Field(None, description="资产中心全局图同步火山私域时的资产组 Id")


class ConnectModelTestSchema(BaseModel):
    """
    连接模型测试接口
    """
    provider_code: str = Field(description="模型厂商的code")
