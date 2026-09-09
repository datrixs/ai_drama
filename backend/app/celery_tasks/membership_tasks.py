import calendar
from datetime import date, datetime, timedelta
from decimal import Decimal

from app.core.celery import celery
from app.core.config import settings
from app.core.logging import logger
from app.crud.base_crud import CRUDBase
from app.db.session import SessionLocal
from app.enums.membership import MembershipStatus, PayStatus, PointRecordType
from app.models.membership import UserMembership, MembershipLevelPrivilege
from app.models.payment import RechargeOrder
from app.models.point_record import PointRecord
from app.crud.user_balance_crud import user_balance_crud
from app.crud.point_crud import point_record_crud


def _anchor_date(year: int, month: int, day: int) -> date:
    """计算目标月份的锚定日期：尽量保持原始 day，超出则 clamp 到月末。"""
    max_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(day, max_day))


def _calc_next_grant_date(start_time: datetime, now: datetime) -> date:
    """
    基于购买日计算当前周期的应发放日。
    始终以 start_time 的日号作为锚定日，避免 relativedelta 逐次累加导致的月末漂移。

    例：start_time=6月5日, now=7月3日 → 返回 7月5日（未来，跳过）
        start_time=6月5日, now=7月5日 → 返回 7月5日（今天，发放）
        start_time=6月5日, now=7月8日 → 返回 7月5日（已过，补发）
        start_time=1月31日, now=2月15日 → 返回 2月28日（clamp，首月保护触发 → 返回 3月31日）
    """
    start = start_time.date() if isinstance(start_time, datetime) else start_time
    today = now.date() if isinstance(now, datetime) else now
    anchor_day = start.day

    # 用月份差值 O(1) 定位，避免 while 循环
    month_diff = (today.year - start.year) * 12 + (today.month - start.month)

    # 当前周期的锚定日
    current_cycle_year = start.year + (start.month + month_diff - 1) // 12
    current_cycle_month = (start.month + month_diff - 1) % 12 + 1
    current_cycle_date = _anchor_date(current_cycle_year, current_cycle_month, anchor_day)

    if month_diff == 0:
        # 还在首月内，首月积分由购买回调发放，返回下一个周期的发放日（调用方跳过）
        next_year = start.year + (start.month + 1 - 1) // 12
        next_month = (start.month + 1 - 1) % 12 + 1
        return _anchor_date(next_year, next_month, anchor_day)

    # current_cycle_date 是当前所在周期的锚定日
    # 如果它恰好是今天或已过，返回它（可能需要补发）
    # 如果它是未来日期，说明上一个周期的锚定日才是应发日
    if current_cycle_date <= today:
        return current_cycle_date
    else:
        # 回退到上一个周期
        prev_year = start.year + (start.month + month_diff - 2) // 12
        prev_month = (start.month + month_diff - 2) % 12 + 1
        return _anchor_date(prev_year, prev_month, anchor_day)


@celery.task(name="membership.grant_monthly_points")
def grant_monthly_points():
    """按购买日周年月发放积分（幂等）"""
    db = SessionLocal()
    try:
        now = datetime.now()
        today = now.date()

        active_memberships = db.query(UserMembership).filter(
            UserMembership.status == MembershipStatus.ACTIVE,
            UserMembership.subscribe_type != 'monthly',
            UserMembership.is_deleted == False,
            UserMembership.expire_time > now,
        ).all()
        print(f'active_memberships数量: {len(active_memberships)}')
        granted_count = 0
        for membership in active_memberships:
            next_grant_date = _calc_next_grant_date(membership.start_time, now)

            # 还没到发放日，跳过
            if next_grant_date > today:
                continue

            # 发放日必须严格早于到期日期（到期当天不再发放）
            if next_grant_date >= membership.expire_time.date():
                print("到期当天不再发放")
                continue

            grant_date_str = next_grant_date.strftime("%Y-%m-%d")

            # 幂等检查：该周期是否已发放
            if point_record_crud.has_monthly_grant(db, membership.user_id, grant_date_str):
                continue

            # 查询等级的 monthly_points 权益
            privilege = db.query(MembershipLevelPrivilege).filter(
                MembershipLevelPrivilege.level_id == membership.level_id,
                MembershipLevelPrivilege.privilege_key == "monthly_points",
                MembershipLevelPrivilege.is_deleted == False,
            ).first()
            if not privilege:
                continue

            point_amount = Decimal(privilege.privilege_value)
            if point_amount <= 0:
                continue

            # 年付会员：发放前清零上月剩余赠送积分
            if membership.subscribe_type == "yearly":
                user_balance_crud.clear_granted_balance(
                    db, membership.user_id, remark="年付会员按月发放前清零",
                )

            user_balance_crud.credit_granted(
                db, membership.user_id, point_amount,
                remark="会员按月积分赠送",
                grant_month=grant_date_str,
                level_id=membership.level_id,
            )
            granted_count += 1

        db.commit()
        logger.info(f"积分按月赠送完成: 发放用户数={granted_count}")
    except Exception as e:
        db.rollback()
        logger.error(f"积分按月赠送任务异常: {e}")
    finally:
        db.close()


@celery.task(name="membership.expire_check")
def membership_expire_check():
    """每分钟检查到期会员：有降级预购则兑现，否则置过期并清零赠送积分。"""
    db = SessionLocal()
    try:
        # TODO: 降级预购暂不开放，恢复时取消注释
        # from app.crud.membership_change_crud import membership_change_crud

        now = datetime.now()
        expired_memberships = db.query(UserMembership).filter(
            UserMembership.status == MembershipStatus.ACTIVE,
            UserMembership.expire_time <= now,
            UserMembership.is_deleted == False,
        ).all()

        # TODO: 降级预购暂不开放，apply_count 恢复时一并恢复
        expire_count = 0
        for membership in expired_memberships:
            # TODO: 降级预购暂不开放，恢复时取消注释
            # if membership.next_level_id:
            #     membership_change_crud.apply_downgrade(db, membership, now)
            #     apply_count += 1
            # else:
            #     pass

            # 统一走过期流程
            membership.status = MembershipStatus.EXPIRED
            db.add(membership)
            ub = user_balance_crud.clear_granted_balance(
                db, membership.user_id, remark="会员到期清零赠送积分",
            )
            record = PointRecord(
                user_id=membership.user_id,
                point_amount=Decimal("0"),
                balance_after=ub.balance if ub else None,
                record_type=PointRecordType.EXPIRE_DOWNGRADE,
                level_id=membership.level_id,
                remark="会员到期降级",
            )
            db.add(record)
            expire_count += 1

        db.commit()
        if expire_count:
            logger.info(f"会员到期处理完成: 到期过期={expire_count}")
    except Exception as e:
        db.rollback()
        logger.error(f"会员到期检查任务异常: {e}")
    finally:
        db.close()


@celery.task(name="pay_order.timeout_check")
def pay_order_timeout_check():
    """每小时检查超时订单"""
    db = SessionLocal()
    try:
        timeout = datetime.now() - timedelta(seconds=settings.PAY_TIME_OUT)
        timeout_orders = db.query(RechargeOrder).filter(
            RechargeOrder.status.in_([PayStatus.PENDING, PayStatus.PAYING]),
            RechargeOrder.create_time <= timeout,
            RechargeOrder.is_deleted == False,
        ).all()

        for order in timeout_orders:
            order.status = PayStatus.FAILED
            order.failure_reason = "订单超时"
            order.finished_time = datetime.now()

        db.commit()
        if timeout_orders:
            logger.info(f"订单超时处理完成: 超时订单数={len(timeout_orders)}")
    except Exception as e:
        db.rollback()
        logger.error(f"订单超时检查任务异常: {e}")
    finally:
        db.close()
