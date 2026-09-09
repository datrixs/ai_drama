from sqlalchemy import or_, and_

from app import models, schemas
from app.crud.base_crud import CRUDBase


class CRUDGlobalVoice(CRUDBase[models.GlobalVoice, schemas.GlobalVoiceCreate, schemas.GlobalVoiceUpdate]):
    """音色 CRUD 操作"""

    def get_by_owner(self, db, owner_user_id: str):
        """获取指定主账号的音色查询集"""
        return self.get_queryset(db).filter(
            self.model.owner_user_id == owner_user_id,
        ).order_by(self.model.create_time.desc())



global_voice_crud = CRUDGlobalVoice(models.GlobalVoice)