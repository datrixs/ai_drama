"""
AI模型计费配置 Model（行式存储）

一条记录 = 一个模型的一个计费档位。
不同计费维度（分辨率、是否角色图等）通过多条记录 + match_config 区分。
"""
from sqlalchemy import Column, String, Boolean, JSON, Text

from app.models import BasicModel


class AIModelPricing(BasicModel):
    """
    模型计费配置表
    """
    __tablename__ = "ai_model_pricing"

    model_id = Column(String(36), nullable=True, index=True, comment="AIModel表ID；NULL表示全局配置（如超分）")
    rule_type = Column(String(64), nullable=False, index=True, comment="计费规则类型，对应策略类")
    match_config = Column(JSON, nullable=False, default=dict, comment="匹配维度，用于运行时筛选档位（如分辨率、是否角色图）")
    price_config = Column(JSON, nullable=False, default=dict, comment="价格参数，供策略类计算使用")
    is_enabled = Column(Boolean, default=True, comment="是否启用")
    remark = Column(Text, nullable=True, comment="备注")
