from datetime import datetime

from dateutil.relativedelta import relativedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.crud.base_crud import CRUDBase
from app.enums.membership import MembershipStatus
from app.models.membership import MembershipLevel, MembershipLevelPrivilege, UserMembership


class CRUDMembership(CRUDBase):

    def get_enabled_levels(self, db: Session):
        """获取所有启用的会员等级（含权益），按排序排列"""
        levels = db.query(MembershipLevel).filter(
            MembershipLevel.status == 1,
            MembershipLevel.is_deleted == False,
        ).order_by(MembershipLevel.level_order.asc()).all()

        result = []
        for level in levels:
            privileges = db.query(MembershipLevelPrivilege).filter(
                MembershipLevelPrivilege.level_id == level.id,
                MembershipLevelPrivilege.is_deleted == False,
            ).all()

            # 计算月付折扣价和节省百分比
            monthly_discount_price = Decimal("0.00")
            monthly_saved_percent = "0%"
            if level.monthly_price and level.monthly_price > 0:
                monthly_discount_price = (level.monthly_price * level.monthly_discount_rate).quantize(Decimal("0.01"))
                saved = level.monthly_price - monthly_discount_price
                percent = int((saved / level.monthly_price * 100))
                monthly_saved_percent = f"省{percent}%"

            # 计算年付折扣价和节省百分比
            yearly_discount_price = Decimal("0.00")
            yearly_saved_percent = "0%"
            if level.yearly_price and level.yearly_price > 0:
                yearly_discount_price = (level.yearly_price * level.yearly_discount_rate).quantize(Decimal("0.01"))
                saved = level.yearly_price - yearly_discount_price
                percent = int((saved / level.yearly_price * 100))
                yearly_saved_percent = f"省{percent}%"

            result.append({
                "id": level.id,
                "name": level.name,
                "level_order": level.level_order,
                "monthly_price": str(level.monthly_price),
                "monthly_discount_rate": str(level.monthly_discount_rate),
                "monthly_discount_price": str(monthly_discount_price),
                "monthly_saved_percent": monthly_saved_percent,
                "yearly_price": str(level.yearly_price),
                "yearly_discount_rate": str(level.yearly_discount_rate),
                "yearly_discount_price": str(yearly_discount_price),
                "yearly_saved_percent": yearly_saved_percent,
                "can_buy_points": level.can_buy_points,
                "privileges": [
                    {"key": p.privilege_key, "value": p.privilege_value, "remark": p.remark}
                    for p in privileges
                ],
            })
        return result

    def is_active_member(self, db: Session, user_id: str) -> bool:
        """是否为付费会员（有 ACTIVE 会员记录）。

        与 get_current_membership 同口径：status=ACTIVE 即视为付费用户，
        不额外判断 expire_time（过期会员由定时任务置为 EXPIRED）。
        """
        return db.query(UserMembership.id).filter(
            UserMembership.user_id == user_id,
            UserMembership.status == MembershipStatus.ACTIVE,
            UserMembership.is_deleted == False,
        ).first() is not None

    def get_current_membership(self, db: Session, user_id: str) -> Optional[dict]:
        """获取用户当前有效会员信息"""
        membership = db.query(UserMembership).filter(
            UserMembership.user_id == user_id,
            UserMembership.status == MembershipStatus.ACTIVE,
            UserMembership.is_deleted == False,
        ).first()
        if not membership:
            return None

        level = db.query(MembershipLevel).filter(
            MembershipLevel.id == membership.level_id,
            MembershipLevel.is_deleted == False,
        ).first()
        if not level:
            return None

        privileges = db.query(MembershipLevelPrivilege).filter(
            MembershipLevelPrivilege.level_id == level.id,
            MembershipLevelPrivilege.is_deleted == False,
        ).all()

        # 降级预购的目标等级
        next_level = None
        if membership.next_level_id:
            nl = db.query(MembershipLevel).filter(
                MembershipLevel.id == membership.next_level_id,
                MembershipLevel.is_deleted == False,
            ).first()
            if nl:
                next_level = {"id": nl.id, "name": nl.name, "level_order": nl.level_order}

        return {
            "level": {"id": level.id, "name": level.name, "level_order": level.level_order},
            "start_time": membership.start_time,
            "expire_time": membership.expire_time,
            "subscribe_type": membership.subscribe_type,
            "status": membership.status,
            "privileges": [
                {"key": p.privilege_key, "value": p.privilege_value, "remark": p.remark}
                for p in privileges
            ],
            "next_level": next_level,
            "auto_renew": membership.auto_renew,
        }

    def activate_membership(self, db: Session, user_id: str, level_id: str,
                            subscribe_type: str, order_no: str = None):
        """激活会员（仅用于新购/重购，非升降级）"""
        delta = relativedelta(months=1) if subscribe_type == "monthly" else relativedelta(years=1)

        # 不再续费覆盖已有会员；升降级由 membership_change_crud 处理
        now = datetime.now()
        new_membership = UserMembership(
            user_id=user_id,
            level_id=level_id,
            start_time=now,
            expire_time=now + delta,
            subscribe_type=subscribe_type,
            status=MembershipStatus.ACTIVE,
            origin_order_no=order_no,
        )
        db.add(new_membership)

    def get_expired_memberships(self, db: Session):
        """获取所有到期会员（定时任务用）"""
        now = datetime.now()
        return db.query(UserMembership).filter(
            UserMembership.status == MembershipStatus.ACTIVE,
            UserMembership.expire_time <= now,
            UserMembership.is_deleted == False,
        ).all()

    def get_active_memberships(self, db: Session):
        """获取所有有效会员（定时任务用）"""
        return db.query(UserMembership).filter(
            UserMembership.status == MembershipStatus.ACTIVE,
            UserMembership.is_deleted == False,
        ).all()


membership_crud = CRUDMembership(UserMembership)
