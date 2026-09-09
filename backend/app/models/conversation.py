"""
对话记录模型
"""
from sqlalchemy import Column, String, Text, JSON
from sqlalchemy.orm import relationship

from app.models.base import BasicModel


class ConversationRecord(BasicModel):
    """用户与AI的对话记录"""
    __tablename__ = "conversation_record"

    project_id = Column(String(36), comment="项目ID（可选）")
    episode_id = Column(String(36), comment="剧集ID（可选）")
    user_id = Column(String(36), nullable=False, index=True, comment="用户ID")

    conversation_type = Column(
        String(32), nullable=False, default="general",
        comment="对话类型: storyboard_edit/video_generation/asset_design/general",
    )
    title = Column(String(256), comment="对话标题")

    messages = Column(JSON, comment="消息列表: [{role: user/assistant/system, content, timestamp, attachments: [{type, url, name}]}]")

    result_video_url = Column(String(1024), comment="对话产生的结果视频URL")
    result_image_urls = Column(JSON, comment="对话产生的结果图片URL列表")
    result_data = Column(JSON, comment="其他结构化结果数据")

    metadata_ = Column("metadata", JSON, comment="元数据: {model_used, token_usage, generation_params}")
