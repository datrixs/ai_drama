from sqlalchemy import Column, Integer, String, Text

from app.models import BasicModel


class PayApiLog(BasicModel):
    """支付接口调用日志"""
    __tablename__ = "pay_api_log"

    order_no = Column(String(64), index=True, comment="关联订单号")
    api_type = Column(String(16), nullable=False, comment="接口类型：create/query/callback")
    request_data = Column(Text, comment="请求报文（加密后）")
    response_data = Column(Text, comment="响应报文（脱敏后）")
    result = Column(String(16), nullable=False, comment="调用结果：success/fail")
    error_msg = Column(String(512), comment="失败时的错误描述")
    cost_ms = Column(Integer, comment="调用耗时（毫秒）")
