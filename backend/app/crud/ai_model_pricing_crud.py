"""
AI模型计费配置 CRUD
"""
from typing import Optional

from sqlalchemy.orm import Session

from app.crud.base_crud import CRUDBase
from app.models import AIModelPricing
from app.schemas import AIModelPricingCreateSchema, AIModelPricingUpdateSchema


class CRUDAIModelPricing(CRUDBase[AIModelPricing, AIModelPricingCreateSchema, AIModelPricingUpdateSchema]):
    """模型计费配置 CRUD"""

    def get_pricings_by_model(
        self,
        db: Session,
        model_id: Optional[str],
        rule_type: str = None,
    ) -> list[AIModelPricing]:
        """
        根据 model_id + rule_type 查询启用的定价配置列表
        """
        query = self.get_queryset(db).filter(
            self.model.model_id == model_id,
            self.model.is_enabled == True,
        )
        if rule_type:
            query = query.filter(self.model.rule_type == rule_type)
        return query.all()

    def get_rule_types_by_model(self, db: Session, model_id: str) -> list[str]:
        """
        获取某个模型启用的所有 rule_type（用于数据驱动判断模型计费类型）
        """
        rows = db.query(self.model.rule_type).filter(
            self.model.model_id == model_id,
            self.model.is_enabled == True,
            self.model.is_deleted == False,
        ).distinct().all()
        return [row[0] for row in rows]


ai_model_pricing_crud = CRUDAIModelPricing(AIModelPricing)
