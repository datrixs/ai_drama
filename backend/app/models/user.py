from decimal import Decimal

from sqlalchemy import Column, Integer, String, Numeric, DateTime

from app.enums.user import UserRegion
from app.models import BasicModel


class User(BasicModel):
    """用户表"""
    __tablename__ = "user"

    username = Column(String(128), nullable=False, unique=True, comment="用户名")
    password_hash = Column(String(256), nullable=False, comment="用户密码hash值")
    email = Column(String(128), nullable=True, unique=True, comment="邮箱")
    status = Column(String(64), nullable=False, comment="账号状态")
    parent_user_id = Column(String(256), comment="主账号id。如果是主账号，则为None")
    sub_user_limit = Column(Integer, default=0, comment="子账号数量上限")
    type = Column(String(64), nullable=False, comment="账号类型")
    remark = Column(String(128), comment="账号备注")
    region = Column(String(16), default=UserRegion.DOMESTIC, comment="区域: domestic-国内/overseas-国际")

    # 2026-06-17新增字段
    username_cn = Column(String(128), comment="用户昵称")
    contact_name = Column(String(128), comment="联系人姓名")
    last_login_time = Column(DateTime, comment="最后一次登录时间")
    phone = Column(String(128), comment="手机号")

class UserBalance(BasicModel):
    """用户余额表"""
    __tablename__ = "user_balance"

    user_id = Column(String(256), comment="用户ID")
    balance = Column(Numeric(10, 2), default=Decimal(0.0), comment="余额（冗余总额=granted+purchased）")
    granted_balance = Column(Numeric(10, 2), default=Decimal(0.0), comment="赠送积分余额（按规则清零）")
    purchased_balance = Column(Numeric(10, 2), default=Decimal(0.0), comment="购买积分余额（永不清零）")
    frozen_amount = Column(Numeric(10, 2), default=Decimal(0.0), comment="冻结金额")
    total_spent = Column(Numeric(10, 2), default=Decimal(0.0), comment="总花费")
