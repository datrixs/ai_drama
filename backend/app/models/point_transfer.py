"""
积分转账记录 Model
"""
from sqlalchemy import Column, Integer, String, Numeric, Boolean
from sqlalchemy.sql import column

from app.models import BasicModel
from app.enums import PointTransferType, PointTransferStatus


class PointTransferRecord(BasicModel):
    """积分转账记录"""
    __tablename__ = "point_transfer_record"

    user_id = Column(String(128), comment="用户ID")
    transfer_from_user_before_point = Column(Numeric(10, 2), comment="转出账号-转账前可用积分余额")
    transfer_from_user_after_point= Column(Numeric(10, 2), comment="转出账号-转账后可用积分余额")
    transfer_to_user_id = Column(String(128), comment="转账目标用户ID")
    transfer_to_user_before_point = Column(Numeric(10, 2), comment="转入账号-转账前可用积分余额")
    transfer_to_user_after_point= Column(Numeric(10, 2), comment="转入账号-转账后可用积分余额")
    point = Column(Numeric(10, 2), comment="转账积分")
    transfer_type = Column(Integer, comment="转账类型" + PointTransferType.__doc__)
    status = Column(Integer, comment="转账状态" + PointTransferStatus.__doc__)
