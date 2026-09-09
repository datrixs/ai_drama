from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.crud.permission_crud import permission_crud
from app.enums.user import UserRegion
from app.models import User
from app.schemas.user import ChangePasswordSchema, UserCreateSchema, UserResponse, UserUpdateSchema
from app.services.user_service import UserService, _attach_balance
from app.utils.response import success_response

router = APIRouter()


class UpdateRegionRequest(BaseModel):
    region: str = Field(..., description="区域类型: domestic-国内 / overseas-国际")


@router.get("/me")
def get_current_user_info(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取当前登录用户信息。
    子账号额外返回权限列表。
    """
    _attach_balance(db, current_user)

    user_data = UserResponse.model_validate(current_user).model_dump()

    if current_user.parent_user_id is not None:
        perm_map = permission_crud.build_permission_map(db, current_user.id)
        user_data["permissions"] = perm_map

    return success_response(data=user_data)


@router.put("/region")
def update_my_region(
    body: UpdateRegionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """切换当前用户的区域类型（domestic/overseas）。主账号与子账号均可调用。"""
    if not UserRegion.is_valid(body.region):
        raise HTTPException(status_code=400, detail="区域类型非法，仅支持 domestic 或 overseas")

    data = UserService.update_region(db, str(current_user.id), body.region)
    return success_response(data=data)


@router.put("/password")
def change_my_password(
    body: ChangePasswordSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """修改当前登录用户的密码，需校验原密码。"""
    UserService.change_password(
        db, str(current_user.id), body.old_password, body.new_password
    )
    return success_response(msg="密码修改成功")


@router.get("")
def list_users(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = UserService.get_user_list(db, skip=skip, limit=limit)
    return success_response(data=data)


@router.get("/{user_id}")
def get_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = UserService.get_user(db, user_id)
    return success_response(data=data)


@router.post("", status_code=201)
def create_user(
    user_in: UserCreateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = UserService.create_user(db, user_in)
    return success_response(data=data)


@router.put("/{user_id}")
def update_user(
    user_id: str,
    user_in: UserUpdateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = UserService.update_user(db, user_id, user_in)
    return success_response(data=data)


@router.delete("/{user_id}", status_code=200)
def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    UserService.delete_user(db, user_id)
    return success_response(msg="删除成功")
