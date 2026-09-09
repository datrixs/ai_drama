from collections import defaultdict

from sqlalchemy import or_, and_
from sqlalchemy.orm import Session

from app import models, schemas
from app.crud.base_crud import CRUDBase
from app.utils.tencent_cos_utils import cos_client



class CRUDGlobalLocation(CRUDBase[models.GlobalLocation, schemas.GlobalLocationCreate, schemas.GlobalLocationUpdate]):
    """场景 CRUD 操作"""

    def get_by_owner(self, db, owner_user_id: str):
        """获取指定主账号的场景查询集"""
        return self.get_queryset(db).filter(
            self.model.owner_user_id == owner_user_id,
        ).order_by(self.model.create_time.desc())


class CRUDGlobalLocationImage(CRUDBase[models.GlobalLocationImage, schemas.GlobalLocationImageCreate, schemas.GlobalLocationImageUpdate]):
    """场景图片 CRUD 操作"""

    def get_by_location(self, db, location_id: str):
        """获取指定场景的图片列表"""
        return self.get_queryset(db).filter(
            self.model.location_id == location_id,
        ).order_by(self.model.image_index.asc())

    def get_batch_by_locations(self, db: Session, location_ids: list[str]) -> dict[str, list]:
        """批量查询多场景的图片，避免 N+1"""
        images = db.query(models.GlobalLocationImage).filter(
            models.GlobalLocationImage.is_deleted == False,
            models.GlobalLocationImage.location_id.in_(location_ids),
        ).order_by(
            models.GlobalLocationImage.location_id,
            models.GlobalLocationImage.image_index.asc(),
        ).all()
        result = defaultdict(list)
        for img in images:
            result[img.location_id].append(img)
        return result

    def resolve_preview_url(self, images: list) -> str | None:
        """从图片列表解析预览图 URL"""
        if not images:
            return None
        selected = next((i for i in images if i.is_selected), images[0])
        if selected and selected.image_url:
            return cos_client.key_to_url(selected.image_url)
        return None

    def resolve_thumbnail_url(self, images: list) -> str | None:
        """从图片列表解析缩略图 URL"""
        if not images:
            return None
        selected = next((i for i in images if i.is_selected), images[0])
        if selected and selected.thumbnail_url:
            return cos_client.key_to_url(selected.thumbnail_url)
        return None


global_location_crud = CRUDGlobalLocation(models.GlobalLocation)
global_location_image_crud = CRUDGlobalLocationImage(models.GlobalLocationImage)