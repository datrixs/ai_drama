from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.core.response import success_response
from app.crud.payment import recharge_crud
from app.models.user import User
from app.schemas.pay_order import (
    MembershipOrderCreate,
    PointOrderCreate,
    PayOrderPageParams,
    CombinedRecordPageParams,
)

router = APIRouter()


@router.post("/membership", summary="创建会员购买订单")
def create_membership_order(
    order_in: MembershipOrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建会员购买订单，返回支付二维码"""
    try:
        result = recharge_crud.create_membership_order(db, order_in, current_user)
        return success_response(data=result.model_dump())
    except ValueError as e:
        return success_response(data=None, msg=str(e), code=1)


@router.post("/points", summary="创建积分购买订单")
def create_point_order(
    order_in: PointOrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建积分购买订单，返回支付二维码"""
    try:
        result = recharge_crud.create_point_order(db, order_in, current_user)
        return success_response(data=result.model_dump())
    except ValueError as e:
        return success_response(data=None, msg=str(e), code=1)


@router.get("", summary="查询订单列表")
def get_orders(
    page_params: PayOrderPageParams = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """查询当前用户的订单列表"""
    result = recharge_crud.get_user_orders(
        db, current_user.id,
        page=page_params.page, size=page_params.size,
        order_type=page_params.order_type,
        status=page_params.status,
    )
    return success_response(data=result["data"], pagination=result["pagination"])


@router.get("/combined-records", summary="充值与积分流水合并记录")
def get_combined_records(
    page_params: CombinedRecordPageParams = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """查询当前用户的充值订单与积分流水合并记录（按时间混排）

    类型：会员购买/积分购买（含待支付/支付中/失败）、每月赠送、过期清零（每日赠送预留）。
    仅返回当前用户自己的记录。
    """
    result = recharge_crud.get_combined_records(
        db, current_user.id,
        page=page_params.page, size=page_params.size,
        type=page_params.type,
        status=page_params.status,
    )
    return success_response(data=result["data"], pagination=result["pagination"])


@router.get("/{order_no}", summary="查询订单详情")
def get_order_detail(
    order_no: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """查询指定订单详情"""
    try:
        order = recharge_crud.query_order_status(db, order_no, current_user)
        return success_response(data=order)
    except ValueError as e:
        return success_response(data=None, msg=str(e), code=1)
