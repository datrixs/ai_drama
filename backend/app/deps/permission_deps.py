from functools import wraps
from typing import Callable

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.crud.permission_crud import permission_crud
from app.crud.sub_user_shared_folder_crud import sub_user_shared_folder_crud
from app.models.user import User


def require_permission(permission_code: str) -> Callable:
    """
    FastAPI 依赖：校验当前用户是否拥有指定权限。
    - 主账号默认拥有所有权限
    - 子账号需要在 SysUserPermission 表中配置对应权限
    """

    async def _check(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        if current_user.parent_user_id is None:
            return current_user

        has = permission_crud.has_permission(db, current_user.id, permission_code)
        if not has:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"权限不足，需要 {permission_code} 权限",
            )
        return current_user

    return _check


def get_visible_user_ids(current_user: User, db: Session) -> list[str]:
    """
    获取当前用户可见的用户ID列表（用于数据过滤）。

    - 主账号：返回 [自己id, ...所有子账号id]
    - 子账号：返回 [自己id]，如果勾选了 main_user_asset:read 则追加主账号id
    """
    from app.models.user import User as UserModel

    visible_ids = [current_user.id]

    if current_user.parent_user_id is None:
        sub_users = (
            db.query(UserModel)
            .filter_by(parent_user_id=current_user.id, is_deleted=False)
            .all()
        )
        visible_ids.extend([u.id for u in sub_users])
    else:
        has_main_asset_read = permission_crud.has_permission(
            db, current_user.id, "main_user_asset:read"
        )
        if has_main_asset_read and current_user.parent_user_id:
            visible_ids.append(current_user.parent_user_id)

    return visible_ids


def get_accessible_folder_ids(current_user: User, db: Session) -> list[str] | None:
    """
    获取子账号可访问的主账号文件夹ID列表。

    - 主账号：返回 None（表示无限制，可访问所有文件夹）
    - 子账号且无 main_user_asset:read 权限：返回 None（不会看到主账号数据）
    - 子账号且有 main_user_asset:read 权限：返回共享的文件夹ID列表
    """
    if current_user.parent_user_id is None:
        return None

    has_main_asset_read = permission_crud.has_permission(
        db, current_user.id, "main_user_asset:read"
    )
    if not has_main_asset_read:
        return None

    return sub_user_shared_folder_crud.get_shared_folder_ids(db, current_user.id)
