from enum import IntEnum


class PointTransferType(IntEnum):
    """
    积分转账类型
    0: 内部转账（主账号 -> 主账号）
    1: 子账号转账（主账号 <-> 主账号下的子账号）
    2: 后台分配（管理后台手动增减积分，系统 <-> 用户）
    """
    INNER_TRANSFER = 0
    SUBACCOUNT_TRANSFER = 1
    ADMIN_ADJUST = 2


class PointTransferStatus(IntEnum):
    """积分转账状态"""
    SUCCESS = 1
    FAILED = 2