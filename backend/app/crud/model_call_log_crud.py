from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy import case, func, or_
from sqlalchemy.orm import Session

from app.deps.base import PageParams
from app.models.model_call_log import ModelCallLog
from app.schemas.base import PageBase


class CRUDModelCallLog:

    def __init__(self, model: type[ModelCallLog]):
        self.model = model

    def get(self, db: Session, record_id: str) -> Optional[ModelCallLog]:
        return db.query(self.model).filter(
            self.model.id == record_id,
        ).first()

    def get_by_provider_request_id(self, db: Session, provider_request_id: str):
        return db.query(self.model).filter(
            self.model.provider_request_id == provider_request_id,
        ).first()

    def create(self, db: Session, create_data: Dict[str, Any]):
        if "id" not in create_data or not create_data["id"]:
            create_data["id"] = str(uuid4())
        db_obj = self.model(**create_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, record_id: str, update_data: dict) -> Optional[ModelCallLog]:
        record = self.get(db, record_id)
        if not record:
            return None
        for key, value in update_data.items():
            setattr(record, key, value)
        db.commit()
        db.refresh(record)
        return record

    def get_queryset(self, db: Session):
        return db.query(self.model)

    def build_query(
        self,
        db: Session,
        user_ids: Optional[List[str]] = None,
        project_id: Optional[str] = None,
        task_id: Optional[str] = None,
        model_provider: Optional[str] = None,
        model_name: Optional[str] = None,
        response_status: Optional[int] = None,
        is_retry: Optional[bool] = None,
        call_time_start: Optional[datetime] = None,
        call_time_end: Optional[datetime] = None,
    ):
        query = self.get_queryset(db)
        if user_ids:
            query = query.filter(self.model.user_id.in_(user_ids))
        if project_id:
            query = query.filter(self.model.project_id == project_id)
        if task_id:
            query = query.filter(self.model.task_id == task_id)
        if model_provider:
            query = query.filter(self.model.model_provider == model_provider)
        if model_name:
            query = query.filter(self.model.model_name.like(f"%{model_name}%"))
        if response_status is not None:
            if response_status == 0:
                query = query.filter(or_(
                    self.model.response_status != 200,
                    self.model.response_status.is_(None)
                ))
            else:
                query = query.filter(self.model.response_status == response_status)
        if is_retry is not None:
            query = query.filter(self.model.is_retry == is_retry)
        if call_time_start:
            query = query.filter(self.model.call_time >= call_time_start)
        if call_time_end:
            query = query.filter(self.model.call_time <= call_time_end)
        return query

    def get_multi(self, page_params: PageParams, query) -> Dict[str, Any]:
        query = query.order_by(self.model.call_time.desc())
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

    def get_summary(self, query) -> Dict[str, Any]:
        result = query.with_entities(
            func.count(self.model.id).label("total_calls"),
            func.coalesce(func.sum(
                case((self.model.response_status == 200, 1), else_=0)
            ), 0).label("success_calls"),
            func.coalesce(func.sum(
                case((or_(
                    self.model.response_status != 200,
                    self.model.response_status.is_(None)
                ), 1), else_=0)
            ), 0).label("failed_calls"),
            func.coalesce(func.sum(self.model.input_tokens), 0).label("total_input_tokens"),
            func.coalesce(func.sum(self.model.output_tokens), 0).label("total_output_tokens"),
            func.coalesce(func.sum(self.model.total_tokens), 0).label("total_tokens"),
            func.coalesce(func.sum(self.model.point), 0).label("total_point"),
            func.avg(self.model.latency_ms).label("avg_latency_ms"),
        ).first()
        return {
            "total_calls": result.total_calls or 0,
            "success_calls": int(result.success_calls or 0),
            "failed_calls": int(result.failed_calls or 0),
            "total_input_tokens": int(result.total_input_tokens or 0),
            "total_output_tokens": int(result.total_output_tokens or 0),
            "total_tokens": int(result.total_tokens or 0),
            "total_point": float(result.total_point) if result.total_point else None,
            "avg_latency_ms": round(float(result.avg_latency_ms), 2) if result.avg_latency_ms else None,
        }


model_call_log_crud = CRUDModelCallLog(ModelCallLog)
