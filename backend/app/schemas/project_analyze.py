"""剧情分析相关 Schema"""
from typing import Optional, List

from pydantic import BaseModel, Field


# ============ 触发/调整分析 ============

class AnalysisRequest(BaseModel):
    """触发/调整分析请求"""
    adjustment: Optional[str] = Field(None, description="调整要求，首次分析时为null")


class AnalysisTriggerResponse(BaseModel):
    """触发分析响应"""
    task_id: str
    project_status: str


# ============ 分析结果 ============

class EpisodeOutlineItem(BaseModel):
    """每集大纲项"""
    episode_number: int
    title: str = ""
    summary: str = ""
    key_events: Optional[List[str]] = None
    key_characters: Optional[List[str]] = None
    hook: Optional[str] = None


class AnalysisResponse(BaseModel):
    """分析结果响应"""
    version_id: str
    version_number: int
    is_confirmed: bool = False
    global_setting: Optional[dict] = None
    episode_outlines: Optional[str] = None
    character_profiles: Optional[str] = None
    scene_descriptions: Optional[str] = None
    prop_descriptions: Optional[str] = None


# # ============ 分镜相关 Schema（暂未开放） ============
#
# class StoryboardScene(BaseModel):
#     """分镜场景"""
#     scene_number: int
#     location: str
#     time: Optional[str] = None
#     characters: Optional[List[str]] = None
#     action: str
#     dialogue: Optional[str] = None
#     camera: Optional[str] = None
#     emotion: Optional[str] = None
#     duration: int = 5
#
#
# class StoryboardData(BaseModel):
#     """分镜数据"""
#     scenes: List[StoryboardScene]
#
#
# class StoryboardSaveRequest(BaseModel):
#     """保存手动编辑的分镜"""
#     storyboard: StoryboardData
#
#
# class StoryboardSaveResponse(BaseModel):
#     """保存分镜响应"""
#     version_id: str
#     updated: bool = True


# ============ AI 故事扩写 ============

class AiStoryExpandRequest(BaseModel):
    """AI 故事扩写请求"""
    prompt: str = Field(..., min_length=1, max_length=5000)


class AiStoryExpandResponse(BaseModel):
    """AI 故事扩写响应"""
    expanded_text: str
