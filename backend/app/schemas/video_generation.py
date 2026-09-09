"""视频生成 Schema"""
from typing import Optional
from datetime import datetime

from pydantic import BaseModel, Field


class VideoGenerateRequest(BaseModel):
    """单镜头视频生成请求"""
    storyboard_id: str = Field(description="分镜片段ID")
    model: Optional[str] = Field(default="doubao-seedance-2-0-260128")
    resolution: Optional[str] = Field(default="720p")
    ratio: Optional[str] = Field(default="16:9")
    duration: Optional[int] = Field(default=None)
    generate_audio: bool = Field(default=True)
    first_frame_url: Optional[str] = None
    last_frame_url: Optional[str] = None


class MultimodalVideoGenerateRequest(BaseModel):
    """多片段成片视频生成请求"""
    episode_id: str = Field(description="剧集ID")
    model: Optional[str] = Field(default="doubao-seedance-2-0-260128")


class ScriptGenerateRequest(BaseModel):
    """多模态脚本生成请求"""
    episode_id: str = Field(description="剧集ID")


class SegmentVideoGenerateRequest(BaseModel):
    """按 segment 索引生成视频请求"""
    segment_index: int = Field(description="片段索引（从0开始）")
    model: Optional[str] = Field(default="doubao-seedance-2-0-260128")
    resolution: Optional[str] = Field(default="720p")
    ratio: Optional[str] = Field(default="16:9")
    duration: Optional[int] = Field(default=None)
    generate_audio: bool = Field(default=True)
    first_frame_url: Optional[str] = None
    last_frame_url: Optional[str] = None


class ScriptTextResponse(BaseModel):
    """脚本纯文本响应"""
    episode_id: str
    plain_text: str
    segment_count: int
    has_json: bool


class SegmentTextItem(BaseModel):
    """单个片段的编辑内容"""
    segment_index: int = Field(..., ge=1, description="片段序号（从1开始）")
    plain_text: str = Field(..., description="该片段的纯文本内容")


class ScriptTextUpdateRequest(BaseModel):
    """脚本纯文本更新请求（每片段独立对象）"""
    segments: list[SegmentTextItem] = Field(default_factory=list, description="需要更新的片段列表")


class VideoConcatRequest(BaseModel):
    """视频拼接请求"""
    episode_id: str = Field(description="剧集ID")
    output_title: Optional[str] = Field(default=None, description="输出视频标题")
