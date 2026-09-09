from datetime import datetime
from typing import Any, Dict, Generic, TypeVar, Union
from uuid import uuid4

from fastapi import HTTPException
from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import exc, func
from sqlalchemy.orm import DeclarativeBase, Session

from app.deps.base import PageParams
from app.schemas.base import PageBase

ModelType = TypeVar("ModelType", bound=DeclarativeBase)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)
SchemaType = TypeVar("SchemaType", bound=BaseModel)
T = TypeVar("T", bound=DeclarativeBase)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """同步 CRUD 基类，所有资产 CRUD 继承此类"""

    def __init__(self, model: type[ModelType]):
        """
        CRUD object with default methods to Create, Read, Update, Delete (CRUD).
        **Parameters**
        * `model`: A SQLAlchemy DeclarativeBase model class
        * `schema`: A Pydantic model (schema) class
        """
        self.model = model

    def get(
        self, *, id: UUID | str, db: Session
    ) -> ModelType | None:
        return db.get(self.model, id)

    def get_queryset(self, db: Session):
        return db.query(self.model).filter(self.model.is_deleted == False)

    def receive(self, db: Session, primary_id: str) -> ModelType:
        obj = self.get(id=primary_id, db=db)
        if not obj:
            name = self.model.__doc__ or self.model.__name__
            raise HTTPException(status_code=400, detail=f"{name}不存在")
        return obj

    def get_by_ids(
        self,
        *,
        list_ids: list[UUID | str],
        db: Session,
    ) -> list[ModelType] | None:
        return db.query(self.model).filter(self.model.id.in_(list_ids)).all()

    def get_count(
        self, db: Session
    ) -> int:
        return db.query(func.count()).select_from(self.model).scalar()

    def get_multi(self, page_params: PageParams, query) -> Dict[str, Any]:
        total_count = query.count()
        if page_params.is_paginate:
            offset = (page_params.page - 1) * page_params.size
            items = query.offset(offset).limit(page_params.size).all()
        else:
            items = query.all()
        pagination = PageBase(
            page=page_params.page, size=page_params.size, total_count=total_count,
        )
        return {"data": items, "pagination": pagination.model_dump()}


    # TODO: 以下方法依赖 fastapi_pagination 包，安装后取消注释
    #
    # def get_multi_paginated(
    #     self,
    #     *,
    #     params: Params | None = Params(),
    #     query: T | SelectStatement | None = None,
    #     db: Session,
    # ) -> Page[ModelType]:
    #     if query is None:
    #         return paginate(db, self.model, params)
    #     return paginate(db, query, params)
    #
    # def get_multi_paginated_ordered(
    #     self,
    #     *,
    #     params: Params | None = Params(),
    #     order_by: str | None = None,
    #     order: IOrderEnum | None = IOrderEnum.ascendent,
    #     query: T | SelectStatement | None = None,
    #     db: Session,
    # ) -> Page[ModelType]:
    #     columns = self.model.__table__.columns
    #
    #     if order_by is None or order_by not in columns:
    #         order_by = "id"
    #
    #     if query is None:
    #         if order == IOrderEnum.ascendent:
    #             query = select(self.model).order_by(columns[order_by].asc())
    #         else:
    #             query = select(self.model).order_by(columns[order_by].desc())
    #
    #     return paginate(db, query, params)
    #
    # def get_multi_ordered(
    #     self,
    #     *,
    #     skip: int = 0,
    #     limit: int = 100,
    #     order_by: str | None = None,
    #     order: IOrderEnum | None = IOrderEnum.ascendent,
    #     db: Session,
    # ) -> list[ModelType]:
    #     columns = self.model.__table__.columns
    #
    #     if order_by is None or order_by not in columns:
    #         order_by = "id"
    #
    #     q = db.query(self.model).offset(skip).limit(limit)
    #
    #     if order == IOrderEnum.ascendent:
    #         return q.order_by(columns[order_by].asc()).all()
    #     return q.order_by(columns[order_by].desc()).all()


    def create(self, db: Session, obj_in: Union[BaseModel, Dict[str, Any]]) -> ModelType:
        obj_data = obj_in.model_dump() if isinstance(obj_in, BaseModel) else obj_in
        if "id" not in obj_data or not obj_data["id"]:
            obj_data["id"] = str(uuid4())
        db_obj = self.model(**obj_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, db_obj: ModelType, obj_in: Union[BaseModel, Dict[str, Any]]) -> ModelType:
        update_data = obj_in if isinstance(obj_in, dict) else obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj


    def remove(self, db: Session, primary_id: str) -> ModelType:
        obj = self.receive(db, primary_id)
        obj.is_deleted = True
        obj.delete_time = datetime.now()
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj