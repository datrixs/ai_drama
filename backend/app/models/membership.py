from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy import Numeric

from app.models import BasicModel


class MembershipChangeLog(BasicModel):
    """会员变更记录"""
    __tablename__ = "membership_change_log"

    user_id = Column(String(36), nullable=False, index=True, comment="用户ID")
    from_level_id = Column(String(36), comment="原等级ID")
    to_level_id = Column(String(36), nullable=False, comment="目标等级ID")
    change_type = Column(Integer, nullable=False, comment="变更类型：1=新购 2=升级 3=降级预购 4=降级兑现 5=到期重购")
    subscribe_type = Column(String(16), comment="订阅类型")
    effective_time = Column(DateTime, comment="生效时间")
    status = Column(Integer, default=1, comment="状态：1=已生效 2=预约中 3=已取消")
    order_no = Column(String(64), comment="关联订单号")
    pay_amount = Column(Numeric(15, 2), comment="本次支付金额")
    point_adjust = Column(Numeric(10, 2), default=0, comment="积分调整数")
    remark = Column(String(255), comment="备注")


class MembershipLevel(BasicModel):
    """会员等级"""
    __tablename__ = "membership_level"

    name = Column(String(64), nullable=False, comment="等级名称")
    level_order = Column(Integer, nullable=False, comment="等级排序，数值越大等级越高")
    monthly_price = Column(Numeric(10, 2), default=0, comment="月付原价")
    monthly_discount_rate = Column(Numeric(3, 2), default=1, comment="月付折扣率，如0.80=八折")
    yearly_price = Column(Numeric(10, 2), default=0, comment="年付原价")
    yearly_discount_rate = Column(Numeric(3, 2), default=1, comment="年付折扣率，如0.80=八折")
    can_buy_points = Column(Boolean, default=False, comment="是否允许单独购买积分")
    status = Column(Integer, default=1, comment="状态：1=启用 0=禁用")


class MembershipLevelPrivilege(BasicModel):
    """会员等级权益（KV键值对，扩展权益只需增行不改表结构）"""
    __tablename__ = "membership_level_privilege"

    level_id = Column(String(36), nullable=False, index=True, comment="关联会员等级ID")
    name = Column(String(64), nullable=True, comment="权益名称")
    privilege_key = Column(String(64), nullable=False, comment="权益键，如monthly_points/project_limit/ai_concurrency")
    privilege_value = Column(String(128), nullable=False, comment="权益值，如1000/10/5")
    remark = Column(String(128), comment="权益说明")


class UserMembership(BasicModel):
    """用户会员"""
    __tablename__ = "user_membership"

    user_id = Column(String(36), nullable=False, index=True, comment="用户ID")
    level_id = Column(String(36), nullable=False, comment="会员等级ID")
    start_time = Column(DateTime, nullable=False, comment="生效时间")
    expire_time = Column(DateTime, nullable=False, index=True, comment="到期时间")
    subscribe_type = Column(String(16), nullable=False, comment="订阅类型：monthly/yearly")
    status = Column(Integer, default=1, index=True, comment="状态：1=有效 0=过期 2=取消")
    next_level_id = Column(String(36), comment="降级预购的目标等级ID")
    next_subscribe_type = Column(String(16), comment="下次续期的订阅类型")
    auto_renew = Column(Boolean, default=False, comment="是否自动续费（预留）")
    origin_order_no = Column(String(64), comment="当前周期原始开通订单号")
