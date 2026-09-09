"""
AI模型服务 - 已迁移到 PointService

此文件保留以保持向后兼容性，所有积分计算逻辑已迁移到 app/services/point.py
"""
from decimal import Decimal

from sqlalchemy.orm import Session

from app.services.point import PointService
from app import crud, models


class AIModelService:
    """
    AI模型服务（向后兼容包装）
    
    所有积分计算逻辑已迁移到 PointService，此类提供向后兼容的接口
    """

    @staticmethod
    def calculate_point(
        db: Session,
        model_id: str,
        **kwargs: dict,
    ) -> Decimal:
        """
        根据消耗的token计算积分（向后兼容接口）
        
        参数说明：
        - 文本模型：需要 input_token、output_token
        - 图片模型：需要 is_character（是否是生成角色图）
        - 视频模型：需要 has_reference、video_resolution、video_output_duration、reference_duration
        
        实际实现已委托给 PointService
        """
        return PointService.calculate_point(db, model_id=model_id, **kwargs)

    @staticmethod
    def get_ai_model_by_model_name(db: Session, model_name) -> models.AIModel:
        """
        根据模型名称获取模型对象
        """
        ai_model = crud.ai_model_crud.get_by_model_name(db, model_name)
        return ai_model