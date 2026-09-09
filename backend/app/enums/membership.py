from enum import IntEnum


class OrderType(IntEnum):
    """订单类型"""
    RECHARGE = 1       # 充值
    VIP_PURCHASE = 2   # 会员购买
    POINT_PURCHASE = 3 # 积分购买


class PayStatus(IntEnum):
    """支付状态（与 RechargeOrder.status 对齐）"""
    PENDING = 1   # 待支付
    PAYING = 2    # 支付中（杉德下单成功，等待用户扫码）
    SUCCESS = 3   # 成功（杉德回调确认支付成功）
    FAILED = 4    # 失败（含超时、取消等）


class MembershipStatus(IntEnum):
    """会员状态"""
    EXPIRED = 0   # 过期
    ACTIVE = 1    # 有效
    CANCELLED = 2 # 取消


class PointRecordType(IntEnum):
    """积分记录类型"""
    MONTHLY_GRANT = 1    # 会员按月赠送
    POINT_PURCHASE = 2   # 积分购买
    EXPIRE_DOWNGRADE = 3 # 到期降级（标记，积分为0）
    POINT_CONSUME = 4    # 积分消费
    TRANSFER = 5         # 转账
    GRANT_CLEAR = 6      # 赠送积分清零
    REFUND = 7           # 积分退还（消费失败/结算差额退回，正数）


class MembershipChangeType(IntEnum):
    """会员变更类型"""
    NEW_PURCHASE = 1     # 新购
    UPGRADE = 2          # 升级
    DOWNGRADE_BOOK = 3   # 降级预购
    DOWNGRADE_APPLY = 4  # 降级到期兑现
    REPURCHASE = 5       # 到期重购


class ChangeLogStatus(IntEnum):
    """变更日志状态"""
    EFFECTIVE = 1  # 已生效
    PENDING = 2    # 预约中
    CANCELLED = 3  # 已取消


class PointType(IntEnum):
    """积分类型"""
    GRANTED = 1    # 赠送积分
    PURCHASED = 2  # 购买积分
