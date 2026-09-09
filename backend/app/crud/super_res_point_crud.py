from sqlalchemy.orm import Session
from uuid import uuid4

from app.schemas.super_res_point import SuperResPointCreateSchema, SuperResPointUpdateSchema
from app.crud.base_crud import CRUDBase
from app.models import SuperResPoint
from app.core.logging import logger


class CRUDSuperResPoint(
    CRUDBase[SuperResPoint, SuperResPointCreateSchema, SuperResPointUpdateSchema]
):
    """
    用户API配置 CRUD 操作
    """
    def __init__(self, model: type[SuperResPoint]):
        super().__init__(model)

    def get_by_resolution(self, db:Session, target_video_resolution: str):
        """根据目标分辨率获取超分配置项"""
        super_res_point = db.query(self.model).filter(self.model.target_video_resolution == target_video_resolution).first()
        return super_res_point if super_res_point else None

    def get_point_by_resolution(self, db:Session, target_video_resolution: str):
        """根据目标分辨率获取积分"""
        super_res_point = db.query(self.model).filter(self.model.target_video_resolution == target_video_resolution).first()
        return super_res_point.point if super_res_point else None

    def create(self, db: Session, target_video_resolution: str, point: int):
        """创建超分消耗积分配置项"""
        super_res_point = self.get_by_resolution(db, target_video_resolution)
        if not super_res_point:
            new_super_res_point = self.model(
                id = str(uuid4()),
                target_video_resolution=target_video_resolution,
                point=point
            )
            db.add(new_super_res_point)
            db.commit()
            logger.debug(f"[创建超分消耗积分配置项] 创建成功，分辨率={target_video_resolution}，每秒消耗积分={point}")
            return new_super_res_point
        else:
            logger.debug(f"[创建超分消耗积分配置项] 已存在，跳过创建。分辨率={target_video_resolution}，每秒消耗积分={point}")
            return super_res_point


super_res_point_crud = CRUDSuperResPoint(SuperResPoint)