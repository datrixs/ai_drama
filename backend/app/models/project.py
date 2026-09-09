from sqlalchemy import Column, DateTime, String, Text, JSON
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import relationship

from app.models.base import BasicModel


class Project(BasicModel):
    """项目表"""
    __tablename__ = "project"

    user_id = Column(String(36), nullable=False, index=True, comment="所属用户ID")
    title = Column(String(256), comment="项目名称")
    description = Column(Text, comment="项目描述")
    novel_text = Column(Text, comment="小说纯文本")
    novel_meta = Column(JSON, comment="小说元信息: {char_count, chapter_count, format, file_name}")
    file_url = Column(String(1024), comment="小说文件云存储路径")
    status = Column(
        String(32), nullable=False, default="draft",
        comment="项目状态: draft/analyzingStory/storyReady/projectCreated/assetsReady/producing/completed",
    )
    phase = Column(String(32), comment="当前阶段: text_analysis/image_generation/video_production")
    config = Column(MutableDict.as_mutable(JSON), default=dict, comment="项目配置: {ratio, style, video_resolution, image_resolution, 各模型配置}")
    last_access_time = Column(DateTime, comment="最近访问时间")
    volc_private_asset_group_id = Column(String(256), comment="火山私域素材库资产组ID")
    byteplus_private_asset_group_id = Column(String(256), nullable=True, comment="BytePlus 资产库资产组ID")

    analysis_result = relationship("AnalysisResult", back_populates="project", uselist=False)
