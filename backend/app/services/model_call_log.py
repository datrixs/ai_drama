from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.crud.model_call_log_crud import model_call_log_crud
from app.models.project import Project
from app.models.user import User
from app.schemas.model_call_log import (
    ModelCallLogDetailItem,
    ModelCallLogItem,
    ModelCallLogSummaryItem,
)


class ModelCallLogService:

    @staticmethod
    def _get_visible_user_ids(db: Session, current_user: User) -> List[str]:
        user_ids = [current_user.id]
        if current_user.parent_user_id is None:
            sub_users = db.query(User).filter(
                User.parent_user_id == current_user.id,
                User.is_deleted == False,
            ).all()
            user_ids.extend([u.id for u in sub_users])
        return user_ids

    @staticmethod
    def get_list(
        db: Session,
        current_user: User,
        page_params: Any,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        task_id: Optional[str] = None,
        model_provider: Optional[str] = None,
        model_name: Optional[str] = None,
        response_status: Optional[int] = None,
        is_retry: Optional[bool] = None,
        call_time_start: Optional[datetime] = None,
        call_time_end: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        user_ids = ModelCallLogService._get_visible_user_ids(db, current_user)
        if user_id:
            user_ids = [uid for uid in user_ids if uid == user_id]
        query = model_call_log_crud.build_query(
            db,
            user_ids=user_ids,
            project_id=project_id,
            task_id=task_id,
            model_provider=model_provider,
            model_name=model_name,
            response_status=response_status,
            is_retry=is_retry,
            call_time_start=call_time_start,
            call_time_end=call_time_end,
        )
        result = model_call_log_crud.get_multi(page_params=page_params, query=query)
        items = result["data"]
        user_id_set = list(set(item.user_id for item in items))
        user_map = {u.id: u.username for u in db.query(User).filter(User.id.in_(user_id_set)).all()}
        project_id_set = list(set(item.project_id for item in items if item.project_id))
        project_map = {p.id: p.title for p in db.query(Project).filter(Project.id.in_(project_id_set)).all()} if project_id_set else {}
        provider_code_set = list(set(item.model_provider for item in items if item.model_provider))
        from app.models.ai_model import AIProvider
        provider_map = {p.code: p.name for p in db.query(AIProvider).filter(AIProvider.code.in_(provider_code_set)).all()} if provider_code_set else {}
        result["data"] = []
        for item in items:
            schema_item = ModelCallLogItem.model_validate(item)
            schema_item.username = user_map.get(item.user_id)
            schema_item.project_title = project_map.get(item.project_id) if item.project_id else None
            schema_item.model_provider_name = provider_map.get(item.model_provider) if item.model_provider else None
            result["data"].append(schema_item)
        return result

    @staticmethod
    def get_detail(db: Session, record_id: str) -> ModelCallLogDetailItem:
        from app.models.ai_model import AIProvider
        record = model_call_log_crud.get(db, record_id)
        if not record:
            raise HTTPException(status_code=404, detail="扣费记录不存在")
        schema_item = ModelCallLogDetailItem.model_validate(record)
        if record.model_provider:
            provider = db.query(AIProvider).filter(AIProvider.code == record.model_provider).first()
            schema_item.model_provider_name = provider.name if provider else None
        return schema_item

    @staticmethod
    def get_summary(
        db: Session,
        current_user: User,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        task_id: Optional[str] = None,
        model_provider: Optional[str] = None,
        model_name: Optional[str] = None,
        call_time_start: Optional[datetime] = None,
        call_time_end: Optional[datetime] = None,
    ) -> ModelCallLogSummaryItem:
        user_ids = ModelCallLogService._get_visible_user_ids(db, current_user)
        if user_id:
            user_ids = [uid for uid in user_ids if uid == user_id]
        query = model_call_log_crud.build_query(
            db,
            user_ids=user_ids,
            project_id=project_id,
            task_id=task_id,
            model_provider=model_provider,
            model_name=model_name,
            call_time_start=call_time_start,
            call_time_end=call_time_end,
        )
        summary = model_call_log_crud.get_summary(query)
        return ModelCallLogSummaryItem(**summary)
