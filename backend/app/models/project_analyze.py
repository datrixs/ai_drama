from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.models.base import BasicModel


class AnalysisResult(BasicModel):
    """分析结果表 - 一个项目一条记录"""
    __tablename__ = "analysis_result"

    project_id = Column(String(36), ForeignKey("project.id"), nullable=False, index=True, comment="项目ID")
    current_version_id = Column(String(36), comment="当前确认的版本ID")
    status = Column(
        String(32), nullable=False, default="pending",
        comment="分析状态: pending/generating/completed",
    )

    project = relationship("Project", back_populates="analysis_result")
    versions = relationship("AnalysisVersion", back_populates="analysis_result", order_by="AnalysisVersion.version_number")


class AnalysisVersion(BasicModel):
    """分析版本表 - 每次生成/调整产生新版本"""
    __tablename__ = "analysis_version"

    analysis_result_id = Column(String(36), ForeignKey("analysis_result.id"), nullable=False, index=True, comment="分析结果ID")
    parent_version_id = Column(String(36), comment="基于哪个版本调整")
    version_number = Column(Integer, nullable=False, default=1, comment="版本号")

    # 全局设定
    global_setting = Column(JSON, comment="全局设定: {novel_summary, world_setting, style_tone, character_relations, suggested_episodes, episode_mapping}")

    # Layer 2: 格式化数据（JSON 数组，每项含 name/description/image_prompt）
    character_profiles = Column(JSON, comment="人物特征列表（Layer 2 格式化 JSON 数组）")
    scene_descriptions = Column(JSON, comment="场景描写列表（Layer 2 格式化 JSON 数组）")
    prop_descriptions = Column(JSON, comment="道具描写列表（Layer 2 格式化 JSON 数组）")

    # Layer 1: 结构化原始数据（JSON 数组，每项含原始提取的详细字段）
    character_details = Column(JSON, comment="人物原始结构化数据（Layer 1）")
    scene_details = Column(JSON, comment="场景原始结构化数据（Layer 1）")
    prop_details = Column(JSON, comment="道具原始结构化数据（Layer 1）")

    episode_outlines = Column(JSON, comment="每集剧本大纲")
    first_ep_storyboard = Column(JSON, comment="第一集分镜")

    # 增量调整上下文
    adjustment_context = Column(JSON, comment="增量调整上下文快照")

    # 模型调用记录
    prompt_snapshot = Column(Text, comment="Prompt快照")
    model_config_data = Column("model_config", JSON, comment="模型配置")
    token_usage = Column(JSON, comment="Token使用量")

    is_confirmed = Column(Boolean, nullable=False, default=False, comment="是否已确认")

    analysis_result = relationship("AnalysisResult", back_populates="versions")
