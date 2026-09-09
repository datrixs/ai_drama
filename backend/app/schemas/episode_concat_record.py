"""剧集整集合成记录 Schema"""
from typing import Optional, Any
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.utils.tencent_cos_utils import cos_client


def _resolve_cos_url(v):
    """COS key/URL 转签名 URL（复用 storyboard.py 中的同名逻辑）"""
    if not v:
        return v
    if not v.startswith("http"):
        return cos_client.key_to_url(v)
    key = cos_client.url_to_key(v)
    if key and not key.startswith("http"):
        return cos_client.key_to_url(key)
    return v


class SourceVideoItem(BaseModel):
    """合成时使用的单个源视频"""
    segment_index: int = Field(description="片段序号")
    video_url: str = Field(description="源视频 URL")


class EpisodeConcatRecordResponse(BaseModel):
    """合成记录响应"""
    id: str
    episode_id: str
    project_id: str
    user_id: Optional[str] = None
    source_video_urls: list[SourceVideoItem] = []
    segment_count: int = 0
    result_video_url: Optional[str] = None
    result_storage_key: Optional[str] = None
    duration_sec: Optional[float] = None
    status: str = "pending"
    error_message: Optional[str] = None
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None

    model_config = {"from_attributes": True}

    @field_validator("source_video_urls", mode="before")
    @classmethod
    def _coerce_source_urls(cls, v):
        """DB 中存为 list[dict]，转为 SourceVideoItem；None 转为空列表"""
        if v is None:
            return []
        return v

    @field_validator("result_video_url", mode="before")
    @classmethod
    def _resolve_result_url(cls, v):
        return _resolve_cos_url(v)


class EpisodeConcatRecordListResponse(BaseModel):
    """合成记录列表响应"""
    items: list[EpisodeConcatRecordResponse]
    total: int
