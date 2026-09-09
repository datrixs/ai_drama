from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.core.response import success_response
from app.crud.point_crud import point_record_crud
from app.models.user import User
from app.schemas.point import PointRecordPageParams

router = APIRouter()


@router.get("/plans", summary="获取积分购买方案")
def get_point_plans(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取所有启用的积分购买方案"""
    plans = point_record_crud.get_enabled_plans(db)
    return success_response(data=plans)


@router.get("/records", summary="查询积分记录")
def get_point_records(
    page_params: PointRecordPageParams = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """查询当前用户的积分变动记录"""
    result = point_record_crud.get_user_records(
        db, current_user.id,
        page=page_params.page, size=page_params.size,
        record_type=page_params.record_type,
    )
    return success_response(data=result["data"], pagination=result["pagination"])
