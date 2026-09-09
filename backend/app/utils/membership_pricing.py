"""会员升降级差价/积分/预购金额计算（纯函数，无副作用）"""

import math
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class UpgradeQuote:
    """同类型升级报价"""
    pay_amount: Decimal       # 需支付的差价
    point_adjust: Decimal     # 需补发的赠送积分
    ratio: Decimal            # 剩余比例
    effective_time: datetime  # 生效时间（= now）


@dataclass(frozen=True)
class CrossTypeUpgradeQuote:
    """跨类型升级报价（信用抵扣模型）"""
    pay_amount: Decimal
    point_adjust: Decimal
    new_expire_time: datetime
    new_subscribe_type: str


def _round_to_hour(dt: datetime) -> datetime:
    """将时间向下取整到小时边界，保证同一小时内定价结果一致"""
    return dt.replace(minute=0, second=0, microsecond=0)


def calc_ratio(cycle_start: datetime, cycle_end: datetime, now: datetime) -> Decimal:
    """计算剩余周期比例（小时级精度）"""
    now = _round_to_hour(now)
    total_seconds = (cycle_end - cycle_start).total_seconds()
    remain_seconds = max((cycle_end - now).total_seconds(), 0)
    if total_seconds <= 0:
        return Decimal("0")
    return Decimal(str(remain_seconds)) / Decimal(str(total_seconds))


def calc_current_month_ratio(start_time: datetime, now: datetime) -> Decimal:
    """
    基于 start_time 计算当前所在月度周期的剩余比例（小时级精度）。
    从 start_time 开始按月划分周期，找到 now 所在的月度区间，计算剩余比例。
    """
    from dateutil.relativedelta import relativedelta

    now = _round_to_hour(now)
    month_start = start_time
    delta_months = relativedelta(months=1)
    while month_start + delta_months <= now:
        month_start += delta_months
    month_end = month_start + delta_months
    return calc_ratio(month_start, month_end, now)


def calc_upgrade(
    old_level, new_level, subscribe_type: str,
    cycle_start: datetime, cycle_end: datetime, now: datetime,
    old_monthly_points: Decimal, new_monthly_points: Decimal,
) -> UpgradeQuote:
    """
    同类型升级补差价 + 按比例补发积分。

    差价 = (新等级现价 - 旧等级现价) × 剩余比例
    积分 = (新monthly_points - 旧monthly_points) × 剩余比例，向下取整，最小0
    """
    ratio = calc_ratio(cycle_start, cycle_end, now)
    month_ratio = calc_current_month_ratio(cycle_start, now)

    if subscribe_type == "yearly":
        old_price = old_level.yearly_price * old_level.yearly_discount_rate
        new_price = new_level.yearly_price * new_level.yearly_discount_rate
    else:
        old_price = old_level.monthly_price * old_level.monthly_discount_rate
        new_price = new_level.monthly_price * new_level.monthly_discount_rate

    pay_amount = max(
        ((new_price - old_price) * ratio).quantize(Decimal("0.01")),
        Decimal("0.00"),
    )

    point_diff = new_monthly_points - old_monthly_points
    point_adjust = max(
        Decimal(math.floor(float(point_diff * month_ratio))),
        Decimal("0"),
    )

    return UpgradeQuote(
        pay_amount=pay_amount,
        point_adjust=point_adjust,
        ratio=ratio,
        effective_time=now,
    )


def calc_cross_type_upgrade(
    old_level, new_level,
    old_subscribe_type: str, new_subscribe_type: str,
    cycle_start: datetime, cycle_end: datetime, now: datetime,
    old_monthly_points: Decimal, new_monthly_points: Decimal,
) -> CrossTypeUpgradeQuote:
    """
    跨类型升级（月→年）：信用抵扣模型。

    仅支持月→年方向。
    差价 = 目标新周期总价 - 当前剩余信用
    新周期从 now 起算目标订阅周期长度
    """
    from dateutil.relativedelta import relativedelta

    ratio = calc_ratio(cycle_start, cycle_end, now)
    month_ratio = calc_current_month_ratio(cycle_start, now)

    # 当前剩余信用
    if old_subscribe_type == "yearly":
        old_price = old_level.yearly_price * old_level.yearly_discount_rate
    else:
        old_price = old_level.monthly_price * old_level.monthly_discount_rate
    credit = (old_price * ratio).quantize(Decimal("0.01"))

    # 目标新订阅总价
    if new_subscribe_type == "yearly":
        target_price = (new_level.yearly_price * new_level.yearly_discount_rate).quantize(Decimal("0.01"))
        target_delta = relativedelta(years=1)
    else:
        target_price = (new_level.monthly_price * new_level.monthly_discount_rate).quantize(Decimal("0.01"))
        target_delta = relativedelta(months=1)

    pay_amount = max(
        (target_price - credit).quantize(Decimal("0.01")),
        Decimal("0.00"),
    )

    # 积分补发：按当月周期剩余比例计算差额
    point_diff = new_monthly_points - old_monthly_points
    point_adjust = max(
        Decimal(math.floor(float(point_diff * month_ratio))),
        Decimal("0"),
    )

    return CrossTypeUpgradeQuote(
        pay_amount=pay_amount,
        point_adjust=point_adjust,
        new_expire_time=cycle_start + target_delta,
        new_subscribe_type=new_subscribe_type,
    )


def calc_downgrade_prepay(new_level, subscribe_type: str) -> Decimal:
    """降级预购金额 = 低等级当前订阅类型现价"""
    if subscribe_type == "yearly":
        price = new_level.yearly_price * new_level.yearly_discount_rate
    else:
        price = new_level.monthly_price * new_level.monthly_discount_rate
    return price.quantize(Decimal("0.01"))


def get_level_price(level, subscribe_type: str) -> Decimal:
    """获取等级指定订阅类型的现价"""
    if subscribe_type == "yearly":
        return (level.yearly_price * level.yearly_discount_rate).quantize(Decimal("0.01"))
    return (level.monthly_price * level.monthly_discount_rate).quantize(Decimal("0.01"))


def get_monthly_points(db, level_id: str) -> Decimal:
    """查询等级的 monthly_points 权益值，无则返回 0"""
    from app.models.membership import MembershipLevelPrivilege

    privilege = db.query(MembershipLevelPrivilege).filter(
        MembershipLevelPrivilege.level_id == level_id,
        MembershipLevelPrivilege.privilege_key == "monthly_points",
        MembershipLevelPrivilege.is_deleted == False,
    ).first()
    if not privilege:
        return Decimal("0")
    val = Decimal(privilege.privilege_value)
    return val if val > 0 else Decimal("0")
