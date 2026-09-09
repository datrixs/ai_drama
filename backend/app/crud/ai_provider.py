import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud.base_crud import CRUDBase
from app.models import AIProvider
from app.schemas import AIProviderCreateSchema, AIProviderUpdateSchema


class CRUDAIProvider(CRUDBase[AIProvider, AIProviderCreateSchema, AIProviderUpdateSchema]):

    def get_provider_list(self, db: Session):
        """
        获取全部模型供应商列表
        """
        return self.get_queryset(db).order_by(self.model.create_time.desc()).all()


ai_provider_crud = CRUDAIProvider(AIProvider)