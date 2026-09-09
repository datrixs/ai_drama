"""对话记录 Schema"""
from typing import Optional
from datetime import datetime

from pydantic import BaseModel, Field


class MessageCreate(BaseModel):
    """发送消息"""
    role: str = Field(description="角色: user/assistant/system")
    content: str = Field(description="消息内容")
    attachments: list[dict] = Field(default_factory=list, description="附件列表")


class ConversationCreate(BaseModel):
    """创建对话"""
    conversation_type: str = Field(default="general", description="对话类型")
    title: Optional[str] = None
    episode_id: Optional[str] = None
    initial_message: Optional[str] = Field(default=None, description="初始消息")


class ConversationResponse(BaseModel):
    """对话响应"""
    id: str
    project_id: Optional[str] = None
    episode_id: Optional[str] = None
    conversation_type: str = "general"
    title: Optional[str] = None
    messages: list[dict] = []
    result_video_url: Optional[str] = None
    result_image_urls: list = []
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None

    model_config = {"from_attributes": True}
