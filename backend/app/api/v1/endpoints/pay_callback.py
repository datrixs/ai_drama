from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.response import success_response
from app.crud.payment import recharge_crud

router = APIRouter()


@router.post("/membership", summary="会员购买支付回调")
async def membership_pay_callback(
    request: Request,
    db: Session = Depends(get_db),
):
    """杉德支付会员购买异步回调（无需登录）"""
    try:
        result = await recharge_crud.membership_pay_callback(db, request)
        return result
    except ValueError as e:
        from app.core.logging import logger
        logger.error(f"会员购买回调处理失败: {e}")
        return dict(respCode="999999", respMsg=str(e))


@router.post("/points", summary="积分购买支付回调")
async def point_pay_callback(
    request: Request,
    db: Session = Depends(get_db),
):
    """杉德支付积分购买异步回调（无需登录）"""
    try:
        result = await recharge_crud.point_pay_callback(db, request)
        return result
    except ValueError as e:
        from app.core.logging import logger
        logger.error(f"积分购买回调处理失败: {e}")
        return dict(respCode="999999", respMsg=str(e))
