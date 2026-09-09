from datetime import datetime
from typing import Any, Dict, Union

from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app import models, schemas
from app.deps.base import PageParams
from app.crud.base_crud import CRUDBase
from app.schemas.base import PageBase


class CRUDGlobalAssetFolder(CRUDBase[models.GlobalAssetFolder, schemas.GlobalAssetFolderCreate, schemas.GlobalAssetFolderUpdate]):
    """文件夹 CRUD 操作"""

    def __init__(self, model: type[models.GlobalAssetFolder]):
        self.model = model

    def get_queryset(self, db: Session):
        """构建基础查询（过滤软删除）"""
        return db.query(self.model).filter(self.model.is_deleted == False)

    def get_by_owner(self, db: Session, user_id: str, owner_user_id: str):
        """获取指定用户的文件夹查询"""
        return self.get_queryset(db).filter(
            or_(
                self.model.owner_user_id == owner_user_id,
                and_(self.model.owner_user_id.is_(None), self.model.user_id == user_id),
            )
        ).order_by(self.model.name.asc())

    def get_multi(self, page_params: PageParams, query) -> Dict[str, Any]:
        """分页查询，返回 dict(data, pagination)"""
        total_count = query.count()
        if page_params.is_paginate:
            offset = (page_params.page - 1) * page_params.size
            items = query.offset(offset).limit(page_params.size).all()
        else:
            items = query.all()

        pagination = PageBase(
            page=page_params.page,
            size=page_params.size,
            total_count=total_count,
        )
        return {
            "data": items,
            "pagination": pagination.dict(),
        }

    def create(self, db: Session, obj_in: Union[BaseModel, Dict[str, Any]]) -> models.GlobalAssetFolder:
        """创建记录"""
        if isinstance(obj_in, BaseModel):
            obj_data = obj_in.dict()
        else:
            obj_data = obj_in
        db_obj = self.model(**obj_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def receive(self, db: Session, primary_id: str) -> models.GlobalAssetFolder:
        """按 ID 查询，不存在则抛出 400"""
        obj = self.get_queryset(db).filter(self.model.id == primary_id).first()
        if not obj:
            model_name = self.model.__doc__ or self.model.__name__
            raise HTTPException(status_code=400, detail=f"{model_name}不存在")
        return obj

    def update(
        self,
        db: Session,
        db_obj: models.GlobalAssetFolder,
        obj_in: Union[BaseModel, Dict[str, Any]],
    ) -> models.GlobalAssetFolder:
        """更新记录"""
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)
        for field in update_data:
            setattr(db_obj, field, update_data[field])
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, primary_id: str) -> models.GlobalAssetFolder:
        """软删除记录"""
        obj = self.receive(db, primary_id)
        obj.is_deleted = True
        obj.delete_time = datetime.now()
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def clear_folder_references(self, db: Session, folder_id: str) -> None:
        """将文件夹内资产的 folder_id 置 NULL"""
        for entity_model in [models.GlobalCharacter, models.GlobalLocation, models.GlobalVoice]:
            db.query(entity_model).filter(
                and_(
                    entity_model.folder_id == folder_id,
                    entity_model.is_deleted == False,
                )
            ).update({entity_model.folder_id: None})
        db.flush()


global_asset_folder_crud = CRUDGlobalAssetFolder(models.GlobalAssetFolder)
