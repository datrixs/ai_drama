from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.core.response import success_response
from app.models.user import User
from app.schemas.model_call_log import ModelCallLogPageParams
from app.services.model_call_log import ModelCallLogService

router = APIRouter()


@router.get("", summary="获取扣费记录列表")
def get_model_call_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page_params: ModelCallLogPageParams = Depends(),
) -> Any:
    result = ModelCallLogService.get_list(
        db,
        current_user=current_user,
        page_params=page_params,
        user_id=page_params.user_id,
        project_id=page_params.project_id,
        task_id=page_params.task_id,
        model_provider=page_params.model_provider,
        model_name=page_params.model_name,
        response_status=page_params.response_status,
        is_retry=page_params.is_retry,
        call_time_start=page_params.call_time_start,
        call_time_end=page_params.call_time_end,
    )
    data = [item.model_dump(mode="json") for item in result["data"]]
    return success_response(data=data, pagination=result["pagination"])


@router.get("/summary", summary="获取扣费记录统计摘要")
def get_model_call_log_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    user_id: str = Query(None, description="用户ID"),
    project_id: str = Query(None, description="项目ID"),
    task_id: str = Query(None, description="任务ID"),
    model_provider: str = Query(None, description="模型供应商"),
    model_name: str = Query(None, description="模型名称"),
    call_time_start: datetime = Query(None, description="调用开始时间"),
    call_time_end: datetime = Query(None, description="调用结束时间"),
) -> Any:
    data = ModelCallLogService.get_summary(
        db,
        current_user=current_user,
        user_id=user_id,
        project_id=project_id,
        task_id=task_id,
        model_provider=model_provider,
        model_name=model_name,
        call_time_start=call_time_start,
        call_time_end=call_time_end,
    )
    return success_response(data=data.model_dump(mode="json"))


@router.get("/{record_id}", summary="获取扣费记录详情")
def get_model_call_log_detail(
    record_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    data = ModelCallLogService.get_detail(db, record_id)
    return success_response(data=data.model_dump(mode="json"))
