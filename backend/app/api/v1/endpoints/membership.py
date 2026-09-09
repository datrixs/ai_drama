from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.core.response import success_response
from app.crud.membership_crud import membership_crud
from app.crud.membership_change_crud import membership_change_crud
from app.crud.user_balance_crud import user_balance_crud
from app.models.user import User
from app.schemas.membership import ChangePreviewRequest

router = APIRouter()


@router.get("/levels", summary="获取会员等级列表")
def get_membership_levels(db: Session = Depends(get_db)):
    """获取所有启用的会员等级（含权益和价格计算）"""
    levels = membership_crud.get_enabled_levels(db)
    return success_response(data=levels)


@router.get("/current", summary="获取当前用户会员信息")
def get_current_membership(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取当前登录用户的会员信息（含降级预购、双余额）

    子账号展示主账号会员等级；积分仍走各自账户（双余额用当前用户自己的）。
    """
    membership_user_id = current_user.parent_user_id or current_user.id
    data = membership_crud.get_current_membership(db, membership_user_id)

    # 附加双余额（始终用当前用户自己的）
    ub = user_balance_crud.get_by_user_id(db, current_user.id)
    if ub:
        if data is None:
            data = {}
        data["granted_balance"] = str(ub.granted_balance or "0.00")
        data["purchased_balance"] = str(ub.purchased_balance or "0.00")
    elif data is None:
        data = None

    return success_response(data=data)


@router.post("/change-preview", summary="预览会员变更")
def preview_membership_change(
    req: ChangePreviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """预览升降级：返回 change_type/pay_amount/point_adjust/effective_time/message"""
    try:
        result = membership_change_crud.preview_change(
            db, current_user.id, req.target_level_id, req.subscribe_type,
        )
        return success_response(data=result)
    except ValueError as e:
        return success_response(data=None, msg=str(e), code=1)
