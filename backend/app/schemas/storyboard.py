"""分镜片段相关 Schema"""
from typing import Any, Optional
from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator

from app.utils.tencent_cos_utils import cos_client


def _resolve_cos_url(v):
    if not v:
        return v
    if not v.startswith("http"):
        return cos_client.key_to_url(v)
    # CDN URL 也转成签名临时地址
    key = cos_client.url_to_key(v)
    if key and not key.startswith("http"):
        return cos_client.key_to_url(key)
    return v


def _extract_source_video_url(api_response_data: Any) -> Optional[str]:
    """从方舟回调原始数据中解析视频源地址（content.video_url），失败返回 None"""
    if not isinstance(api_response_data, dict):
        return None
    try:
        return api_response_data.get("content", {}).get("video_url")
    except (AttributeError, TypeError):
        return None


# === 镜头（Shot）===

class ShotItem(BaseModel):
    """单个分镜镜头"""
    index: int = Field(description="镜头序号")
    durationHintSec: Optional[float] = Field(default=3.0, description="时长提示（秒）")
    timeOfDay: Optional[str] = Field(default=None, description="时间段: 白天/黄昏/夜晚等")
    sceneAssetId: Optional[str] = Field(default=None, description="场景资产ID")
    characterAssetIds: list[str] = Field(default_factory=list, description="角色资产ID列表")
    camera: Optional[str] = Field(default=None, description="镜头运动: 推/拉/摇/移/跟/固定等")
    dialogue: Optional[str] = Field(default=None, description="对白")
    action: Optional[str] = Field(default=None, description="动作描述")
    soundEffect: Optional[str] = Field(default=None, description="音效")


# === 参考图 ===

class ReferenceImage(BaseModel):
    """参考图"""
    url: str = Field(description="图片URL")
    assetId: Optional[str] = Field(default=None, description="资产ID")
    label: Optional[str] = Field(default=None, description="标签")


# === 资产引用 ===

class AssetRef(BaseModel):
    """资产引用"""
    assetId: str = Field(description="资产ID")
    kind: str = Field(description="资产类型: character/location/prop")
    name: str = Field(description="资产名称")


# === 创建片段 ===

class StoryboardCreate(BaseModel):
    """创建分镜片段"""
    segment_index: int = Field(description="片段序号（从1开始）")
    segment_intent: Optional[str] = Field(default=None, description="片段意图描述")
    scene_summary: Optional[str] = Field(default=None, description="场景总述")
    shots: list[ShotItem] = Field(default_factory=list, description="镜头列表")
    style_and_keywords: Optional[str] = Field(default=None, description="风格和关键词")
    image_prompt: Optional[str] = Field(default=None, description="图片生成提示词")
    image_url: Optional[str] = Field(default=None, description="参考图URL")
    video_prompt: Optional[str] = Field(default=None, description="视频生成提示词")
    reference_images: list[ReferenceImage] = Field(default_factory=list, description="参考图列表")
    asset_refs: list[AssetRef] = Field(default_factory=list, description="资产引用")
    raw_text: Optional[str] = Field(default=None, description="LLM生成的原始文本")


# === 更新片段 ===

class StoryboardUpdate(BaseModel):
    """更新分镜片段（部分更新，只传需要修改的字段）"""
    segment_index: Optional[int] = None
    segment_intent: Optional[str] = None
    scene_summary: Optional[str] = None
    shots: Optional[list[ShotItem]] = None
    style_and_keywords: Optional[str] = None
    image_prompt: Optional[str] = None
    image_url: Optional[str] = None
    video_prompt: Optional[str] = None
    reference_images: Optional[list[ReferenceImage]] = None
    asset_refs: Optional[list[AssetRef]] = None


# === 更新片段 shots ===

class StoryboardShotsUpdate(BaseModel):
    """更新片段的 shots 数据"""
    shots: list[ShotItem] = Field(description="镜头列表")


# === 片段排序 ===

class StoryboardReorderRequest(BaseModel):
    """片段排序请求"""
    segment_ids: list[str] = Field(description="按新顺序排列的片段ID列表")


# === 片段插入 ===

class StoryboardInsertRequest(BaseModel):
    """片段插入请求：在锚点片段前/后插入一条空白片段"""
    anchor_segment_id: str = Field(description="锚点片段ID")
    position: str = Field(default="after", description="插入位置: before/after")


# === 视频生成请求 ===

class StoryboardVideoGenerateRequest(BaseModel):
    """分镜视频生成请求"""
    model: Optional[str] = Field(default="doubao-seedance-2-0-260128", description="模型名称")
    resolution: Optional[str] = Field(default="720p", description="分辨率: 480p/720p/1080p")
    ratio: Optional[str] = Field(default="16:9", description="画面比例")
    duration: Optional[int] = Field(default=None, description="指定时长（秒），None则自动计算")
    generate_audio: bool = Field(default=True, description="是否生成音频")
    first_frame_url: Optional[str] = Field(default=None, description="首帧图片URL")
    last_frame_url: Optional[str] = Field(default=None, description="尾帧图片URL")
    video_generation_mode: Optional[str] = Field(default="normal", description="视频生成方式")
    text_prompt: Optional[str] = Field(default=None, description="编辑器当前文本内容，用作视频生成 prompt")


# === 片段响应 ===

class StoryboardResponse(BaseModel):
    """分镜片段响应"""
    id: str
    episode_id: str
    segment_index: int
    segment_intent: Optional[str] = None
    scene_summary: Optional[str] = None
    shots: list[ShotItem] = []
    style_and_keywords: Optional[str] = None
    image_prompt: Optional[str] = None
    image_url: Optional[str] = None
    video_prompt: Optional[str] = None
    video_url: Optional[str] = None
    cover_url: Optional[str] = None
    duration: Optional[float] = None
    resolution: Optional[str] = None
    first_frame_url: Optional[str] = None
    last_frame_url: Optional[str] = None
    reference_images: Optional[list[ReferenceImage]] = None
    status: str = "pending"
    gen_error: Optional[str] = None
    api_response_data: Optional[dict] = None
    raw_text: Optional[str] = None
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None

    model_config = {"from_attributes": True}

    @field_validator("shots", "reference_images", mode="before")
    @classmethod
    def _none_to_empty_list(cls, v):
        return v if v is not None else []

    @field_validator("image_url", "video_url", "cover_url", "first_frame_url", "last_frame_url", mode="before")
    @classmethod
    def _resolve_urls(cls, v):
        return _resolve_cos_url(v)

    @model_validator(mode="after")
    def _fallback_video_url(self):
        """COS 上传未完成时（video_url 空），从 api_response_data 解析源地址供前端立即播放。

        源地址是方舟/Seedance 外部 CDN URL，原样返回不签名。
        """
        if not self.video_url and self.api_response_data:
            source = _extract_source_video_url(self.api_response_data)
            if source:
                self.video_url = source
        # 不对外暴露回调原文
        self.api_response_data = None
        return self


# === 片段列表响应 ===

class StoryboardListResponse(BaseModel):
    """分镜片段列表响应"""
    items: list[StoryboardResponse]
    total: int
    # 整集成片（VIDEO_CONCAT 产出物）— 便于前端刷新页面后展示已有合成结果
    episode_video_url: Optional[str] = None
    episode_concat_status: Optional[str] = None
