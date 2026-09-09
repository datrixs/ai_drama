from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.sys_permission import SysPermission, SysUserPermission


class PermissionCRUD:

    @staticmethod
    def get_all_permissions(db: Session) -> list[SysPermission]:
        return db.query(SysPermission).filter(SysPermission.is_deleted == False).all()

    @staticmethod
    def get_permission_by_code(db: Session, code: str) -> SysPermission | None:
        return db.query(SysPermission).filter_by(code=code, is_deleted=False).first()

    @staticmethod
    def get_user_permissions(db: Session, user_id: str) -> list[SysUserPermission]:
        return (
            db.query(SysUserPermission)
            .filter_by(user_id=user_id, is_deleted=False)
            .all()
        )

    @staticmethod
    def get_user_permission_codes(db: Session, user_id: str) -> list[str]:
        rows = (
            db.query(SysUserPermission.permission_code)
            .filter_by(user_id=user_id, is_deleted=False)
            .all()
        )
        return [r.permission_code for r in rows]

    @staticmethod
    def has_permission(db: Session, user_id: str, permission_code: str) -> bool:
        return (
            db.query(SysUserPermission)
            .filter_by(
                user_id=user_id,
                permission_code=permission_code,
                is_deleted=False,
            )
            .first()
            is not None
        )

    @staticmethod
    def set_user_permissions(
        db: Session, user_id: str, permission_codes: list[str]
    ) -> list[SysUserPermission]:
        db.query(SysUserPermission).filter_by(user_id=user_id).delete(
            synchronize_session=False
        )

        results = []
        for code in permission_codes:
            perm = SysUserPermission(
                id=str(uuid4()),
                user_id=user_id,
                permission_code=code,
                scope_type="SELF",
            )
            db.add(perm)
            results.append(perm)

        db.flush()
        return results

    @staticmethod
    def build_permission_map(db: Session, user_id: str) -> dict[str, bool]:
        codes = PermissionCRUD.get_user_permission_codes(db, user_id)
        return {code: True for code in codes}


permission_crud = PermissionCRUD()
