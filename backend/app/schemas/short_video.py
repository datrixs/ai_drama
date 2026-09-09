"""短视频生成 Schema"""
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field

from app.schemas.base import SchemaBase


# ===== 短视频生成任务 =====

class ShortVideoTaskCreate(BaseModel):
    """创建短视频生成任务请求"""
    generation_type: str = Field(default="reference", description="生成类型: reference/first_last_frame")
    prompt_text: str = Field(description="用户输入的提示词")
    ratio: str = Field(default="16:9", description="视频比例")
    resolution: str = Field(default="720p", description="分辨率")
    duration: int = Field(default=5, ge=4, le=15, description="视频时长(秒)")
    generate_audio: bool = Field(default=True, description="是否生成音频")
    first_frame_url: Optional[str] = Field(default=None, description="首帧图片URL(首尾帧模式)")
    first_frame_volc_id: Optional[str] = Field(default=None, description="首帧图片火山资产ID")
    last_frame_url: Optional[str] = Field(default=None, description="尾帧图片URL(首尾帧模式)")
    last_frame_volc_id: Optional[str] = Field(default=None, description="尾帧图片火山资产ID")
    reference_media_json: Optional[str] = Field(default=None, description="参考媒体JSON")


class ShortVideoTaskItem(SchemaBase):
    """短视频任务列表项"""
    id: str
    generation_type: str
    prompt_text: Optional[str] = None
    ratio: Optional[str] = None
    resolution: Optional[str] = None
    duration: Optional[int] = None
    generate_audio: Optional[bool] = None
    status: str
    progress: int = 0
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    first_frame_url: Optional[str] = None
    last_frame_url: Optional[str] = None
    error_message: Optional[str] = None
    reference_media_json: Optional[str] = None
    submitted_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ShortVideoTaskDetail(ShortVideoTaskItem):
    """短视频任务详情"""
    api_request_params: Optional[dict] = None
    api_response_data: Optional[dict] = None
    api_task_id: Optional[str] = None
    first_frame_volc_id: Optional[str] = None
    last_frame_volc_id: Optional[str] = None


# ===== 短视频资产 =====

class ShortVideoAssetUpload(BaseModel):
    """上传短视频资产请求"""
    asset_name: str = Field(description="资源名称", max_length=64)
    asset_type: str = Field(description="资源类型: image/video/audio")
    asset_url: str = Field(description="资源地址")
    asset_key: Optional[str] = Field(default=None, description="COS key，用于存储永久地址")
    asset_size: Optional[int] = Field(default=None, description="文件大小(字节)")
    mime_type: Optional[str] = Field(default=None, description="MIME类型")
    source: str = Field(default="upload", description="来源: upload/project_asset/asset_center")
    source_asset_id: Optional[str] = Field(default=None, description="来源资产ID")
    thumbnail_url: Optional[str] = Field(default=None, description="缩略图URL")
    thumbnail_key: Optional[str] = Field(default=None, description="缩略图 COS key（优先于 thumbnail_url）")
    duration: Optional[int] = Field(default=None, description="视频/音频时长(秒)")
    project_id: Optional[str] = Field(default=None, description="关联项目ID")


class ShortVideoAssetItem(SchemaBase):
    """短视频资产列表项"""
    id: str
    user_id: str
    project_id: Optional[str] = None
    asset_name: Optional[str] = None
    asset_type: str
    asset_url: Optional[str] = None
    asset_size: Optional[int] = None
    mime_type: Optional[str] = None
    volc_asset_id: Optional[str] = None
    thumbnail_url: Optional[str] = None
    duration: Optional[int] = None
    source: Optional[str] = None
    source_asset_id: Optional[str] = None

    model_config = {"from_attributes": True}


# ===== 资产选择器 =====

class AssetPickerItem(BaseModel):
    """资产选择器项"""
    id: str
    name: str
    asset_type: str = Field(description="image/video/audio")
    image_url: Optional[str] = None
    project_id: Optional[str] = None
    project_name: Optional[str] = None
    folder_id: Optional[str] = None
    folder_name: Optional[str] = None


class ProjectAssetGroup(BaseModel):
    """项目资产分组"""
    project_id: str
    project_name: str
    assets: List[AssetPickerItem] = []
