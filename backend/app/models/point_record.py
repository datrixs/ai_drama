from sqlalchemy import Boolean, Column, Integer, Numeric, String

from app.models import BasicModel


class PointRecord(BasicModel):
    """积分变动记录"""
    __tablename__ = "point_record"

    user_id = Column(String(36), nullable=False, index=True, comment="用户ID")
    point_amount = Column(Numeric(10, 2), nullable=False, comment="积分数（正=入账，负=消费）")
    balance_after = Column(Numeric(10, 2), nullable=True, comment="本次变动后的总积分余额（granted + purchased，历史数据为 NULL）")
    record_type = Column(Integer, nullable=False, comment="记录类型：1=会员按月赠送 2=积分购买 3=到期降级 4=积分消费 5=转账 6=赠送清零")
    point_type = Column(Integer, comment="积分类型：1=赠送 2=购买")
    source_id = Column(String(64), comment="来源ID（订单号或关联记录ID）")
    level_id = Column(String(36), comment="触发赠送的会员等级ID")
    grant_month = Column(String(10), comment="赠送周期起始日，如2026-06-05（按月赠送时使用）")
    remark = Column(String(128), comment="备注说明")


class PointPurchasePlan(BasicModel):
    """积分购买方案"""
    __tablename__ = "point_purchase_plan"

    point_amount = Column(Numeric(10, 2), nullable=False, comment="积分数")
    original_price = Column(Numeric(10, 2), nullable=False, comment="原价（划线价）")
    discount_price = Column(Numeric(10, 2), nullable=False, comment="折扣价（实际购买价）")
    is_enabled = Column(Boolean, default=True, comment="是否启用")
    sort_order = Column(Integer, default=0, comment="排序，数值越小越靠前")
