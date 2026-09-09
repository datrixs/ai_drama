from sqlalchemy import Column, Integer, String, Numeric, Index

from app.models import BasicModel


class SysPermission(BasicModel):
    """系统权限表"""
    __tablename__ = "sys_permission"

    code = Column(String(128), comment="权限代码")
    name = Column(String(128), comment="权限名称")


class SysUserPermission(BasicModel):
    """用户权限"""
    __tablename__ = "sys_user_permission"

    user_id = Column(String(256), comment="用户ID")
    permission_code = Column(String(128), comment="权限代码")
    scope_type = Column(String(128), comment="作用域类型。SELF:自己，ALL:全部")


class SubUserSharedFolder(BasicModel):
    """子账号共享文件夹关联表"""
    __tablename__ = "sub_user_shared_folders"
    __table_args__ = (
        Index("ix_sub_user_shared_folders_sub_user_id", "sub_user_id"),
    )

    sub_user_id = Column(String(256), nullable=False, comment="子账号用户ID")
    folder_id = Column(String(256), nullable=False, comment="共享的文件夹ID")
