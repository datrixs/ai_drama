from decimal import Decimal

from sqlalchemy import Column, DateTime, Integer, Numeric, String, Text

from app.models import BasicModel


class RechargeOrder(BasicModel):
    """充值订单"""
    __tablename__ = "recharge_order"

    order_no = Column(String(64), nullable=False, unique=True, comment="订单号")
    user_id = Column(String(36), nullable=False, index=True, comment="用户ID")
    pay_serial_number = Column(String(64), comment="支付方支付流水号")
    channel_order_no = Column(String(64), comment="渠道订单号")
    channel_pay_serial_no = Column(String(100), comment="渠道流水号")
    channel_finish_time = Column(DateTime, comment="渠道订单完成时间")
    amount = Column(Numeric(15, 2), nullable=False, default=Decimal("0.00"), comment="充值金额")
    actual_pay_amount = Column(Numeric(15, 2), comment="支付方实际支付金额")
    fee_amount = Column(Numeric(15, 2), comment="商户手续费金额")
    extra_fee_amount = Column(Numeric(15, 2), comment="商户额外手续费金额")
    holiday_fee_amount = Column(Numeric(15, 2), comment="商户节假日手续费金额")
    platform_fee_amount = Column(Numeric(15, 2), comment="商户平台手续费金额")
    pay_method = Column(Integer, nullable=False, default=1, comment="支付方式: 1=杉德扫码")
    pay_mode = Column(String(32), comment="支付方式细节：如扫码、条码支付")
    pay_url = Column(Text, comment="支付链接/二维码URL")
    status = Column(Integer, nullable=False, default=1, comment="状态: 1=待支付, 2=支付中, 3=成功, 4=失败")
    failure_reason = Column(String(255), comment="失败原因")
    finished_time = Column(DateTime, comment="订单完成时间")

    # 会员/积分购买扩展字段
    order_type = Column(Integer, comment="订单类型：1=充值 2=会员购买 3=积分购买")
    product_id = Column(String(36), comment="商品ID（会员等级ID或积分购买方案ID）")
    original_amount = Column(Numeric(15, 2), comment="原价（划线价展示用）")
    subscribe_type = Column(String(16), comment="订阅类型：monthly/yearly（会员购买时使用）")
    change_type = Column(Integer, comment="变更类型：1=新购 2=升级 3=降级预购 5=到期重购")
    from_level_id = Column(String(36), comment="升级时的原等级ID")
    point_adjust = Column(Numeric(10, 2), comment="升级需补发的赠送积分数")
    point_amount = Column(Numeric(10, 2), comment="购买积分数（积分购买订单专用）")
