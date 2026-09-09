"""项目管理相关 Schema"""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


# ============ 创建项目 ============

class ProjectCreate(BaseModel):
    """创建项目请求

    支持两种模式：
    - novel（默认）：粘贴小说正文走剧情分析流程，novel_text 必填且 ≥ 20 字
    - director：跳过剧情分析，直接预生成 N 集空剧集，title/画面比例/风格/预计集数必填
    """
    mode: Literal["novel", "director"] = Field("novel", description="创建模式")
    novel_text: Optional[str] = Field(None, description="小说正文内容（novel 模式必填，≥ 20 字）")
    file_url: Optional[str] = Field(None, description="小说文件云存储路径")
    file_name: Optional[str] = Field(None, description="原始文件名")
    # director 模式专用字段
    title: Optional[str] = Field(None, description="项目名称（director 模式必填）")
    video_ratio: Optional[str] = Field(None, description="画面比例，如 9:16 / 16:9")
    art_style: Optional[str] = Field(None, description="画面风格，如 realistic / american-comic")
    expected_episodes: Optional[int] = Field(None, ge=0, le=50, description="预计集数（director 模式）")


class ProjectCreateResponse(BaseModel):
    """创建项目响应"""
    id: str
    status: str
    create_time: datetime


# ============ 确认项目设置 ============

class ProjectConfirm(BaseModel):
    """确认项目设置请求"""
    title: str = Field(..., description="项目名称")
    ratio: str = Field("9:16", description="画面比例")
    style: str = Field("realistic", description="画面风格")


class ProjectConfigResponse(BaseModel):
    """项目配置响应 - 字段名与 UserApiConfig 列名一致"""
    video_ratio: str = "9:16"
    art_style: str = "realistic"
    video_resolution: str = "1080x1920"
    image_resolution: str = "2K"
    analysis_model: Optional[str] = None
    character_model: Optional[str] = None
    location_model: Optional[str] = None
    storyboard_model: Optional[str] = None
    edit_model: Optional[str] = None
    video_model: Optional[str] = None
    audio_model: Optional[str] = None


class ProjectConfirmResponse(BaseModel):
    """确认项目设置响应"""
    id: str
    status: str
    title: str
    config: ProjectConfigResponse


# ============ 项目配置读写 ============

class ProjectConfigUpdateRequest(BaseModel):
    """更新项目配置请求 - 传 null 清除覆盖，不传不修改"""
    title: Optional[str] = None
    video_ratio: Optional[str] = None
    art_style: Optional[str] = None
    analysis_model: Optional[str] = None
    character_model: Optional[str] = None
    location_model: Optional[str] = None
    storyboard_model: Optional[str] = None
    edit_model: Optional[str] = None
    video_model: Optional[str] = None
    audio_model: Optional[str] = None


class ProjectConfigGetResponse(BaseModel):
    """获取项目配置响应"""
    title: Optional[str] = None
    resolved: ProjectConfigResponse
    defaults: ProjectConfigResponse
    overrides: dict = {}


# ============ 项目详情 ============

class NovelMetaResponse(BaseModel):
    """小说元信息"""
    char_count: int = 0
    chapter_count: int = 0
    format: str = ""
    file_name: str = ""


class ProjectDetailResponse(BaseModel):
    """项目详情响应"""
    id: str
    user_id: str
    title: Optional[str] = None
    status: str
    phase: Optional[str] = None
    config: Optional[dict] = None
    novel_meta: Optional[NovelMetaResponse] = None
    analysis_status: Optional[str] = None
    current_version_number: Optional[int] = None
    create_time: datetime
    update_time: Optional[datetime] = None


# ============ 上传小说 ============

class UploadNovelResponse(BaseModel):
    """上传小说文件响应"""
    file_url: str
    extracted_text: str
    char_count: int
    format: str


# ============ 项目列表 ============

class ProjectStatsResponse(BaseModel):
    """项目资产统计"""
    episodes: int = 0
    images: int = 0
    videos: int = 0


class ProjectListItemResponse(BaseModel):
    """项目列表项"""
    id: str
    title: Optional[str] = None
    description: Optional[str] = None
    status: str
    mode: str = "novel"
    novel_preview: Optional[str] = None
    stats: ProjectStatsResponse
    create_time: datetime
    update_time: Optional[datetime] = None


class PaginationResponse(BaseModel):
    """分页信息"""
    page: int
    page_size: int
    total: int
    total_pages: int


class ProjectListResponse(BaseModel):
    """项目列表响应"""
    projects: list[ProjectListItemResponse]
    pagination: PaginationResponse


class ProjectUpdateRequest(BaseModel):
    """编辑项目请求"""
    title: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
