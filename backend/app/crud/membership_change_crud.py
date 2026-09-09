"""会员变更服务层：场景识别、升级执行、降级预购/兑现、变更日志"""

from datetime import datetime
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session

from app.crud.base_crud import CRUDBase
from app.crud.user_balance_crud import user_balance_crud
from app.enums.membership import (
    MembershipChangeType, MembershipStatus, ChangeLogStatus,
)
from app.models.membership import (
    MembershipChangeLog, MembershipLevel, UserMembership,
)
from app.utils.membership_pricing import (
    UpgradeQuote, CrossTypeUpgradeQuote,
    calc_upgrade, calc_cross_type_upgrade, calc_downgrade_prepay,
    get_monthly_points, get_level_price,
)


# 场景类型
SCENE_REPURCHASE = "repurchase"   # 到期重购（已有过期会员记录）
SCENE_NEW_PURCHASE = "new"        # 全新购买（无任何会员）
SCENE_UPGRADE_SAME = "upgrade_same"
SCENE_UPGRADE_CROSS = "upgrade_cross"
SCENE_DOWNGRADE = "downgrade"
SCENE_REJECT_SAME = "reject_same"          # 同等级
SCENE_REJECT_DOWNGRADE_BOOKED = "reject_booked"  # 已有降级预购
SCENE_REJECT_CROSS_YEAR_TO_MONTH = "reject_year_to_month"
SCENE_REJECT_CROSS_TYPE = "reject_cross_type"       # 暂不支持：跨类型升级（月→年）
SCENE_REJECT_DOWNGRADE = "reject_downgrade"          # 暂不支持：降级


class CRUDMembershipChange(CRUDBase):

    # ── 场景识别 ──

    def identify_change(self, db: Session, membership: UserMembership | None,
                        target_level: MembershipLevel,
                        target_subscribe_type: str) -> dict:
        """
        识别变更场景。返回 dict: {scene, old_level_id, ...}
        membership 为 None 表示无有效会员。
        """
        # 无有效会员
        if not membership:
            return {"scene": SCENE_NEW_PURCHASE}

        # 已有降级预购 → 拒绝
        if membership.next_level_id:
            return {"scene": SCENE_REJECT_DOWNGRADE_BOOKED}

        old_level = db.query(MembershipLevel).filter(
            MembershipLevel.id == membership.level_id,
            MembershipLevel.is_deleted == False,
        ).first()

        # 同等级 → 拒绝
        if old_level and old_level.id == target_level.id:
            return {"scene": SCENE_REJECT_SAME}

        # 比较 level_order 判断升降级
        if old_level and target_level.level_order > old_level.level_order:
            # 升级
            if membership.subscribe_type == target_subscribe_type:
                return {"scene": SCENE_UPGRADE_SAME, "old_level": old_level}
            # 跨类型（暂不支持）
            if membership.subscribe_type == "monthly" and target_subscribe_type == "yearly":
                return {"scene": SCENE_REJECT_CROSS_TYPE, "old_level": old_level}
            # 年→月 不支持
            return {"scene": SCENE_REJECT_CROSS_YEAR_TO_MONTH, "old_level": old_level}

        # 降级（暂不支持）
        return {"scene": SCENE_REJECT_DOWNGRADE, "old_level": old_level}

    # ── 报价计算 ──

    def quote_upgrade_same(self, db: Session, membership: UserMembership,
                           old_level: MembershipLevel, new_level: MembershipLevel,
                           now: datetime) -> UpgradeQuote:
        old_pts = get_monthly_points(db, old_level.id)
        new_pts = get_monthly_points(db, new_level.id)
        return calc_upgrade(
            old_level, new_level, membership.subscribe_type,
            membership.start_time, membership.expire_time, now,
            old_pts, new_pts,
        )

    # TODO: 跨类型升级暂不开放，恢复时取消注释
    # def quote_upgrade_cross(self, db: Session, membership: UserMembership,
    #                         old_level: MembershipLevel, new_level: MembershipLevel,
    #                         target_subscribe_type: str, now: datetime) -> CrossTypeUpgradeQuote:
    #     old_pts = get_monthly_points(db, old_level.id)
    #     new_pts = get_monthly_points(db, new_level.id)
    #     return calc_cross_type_upgrade(
    #         old_level, new_level,
    #         membership.subscribe_type, target_subscribe_type,
    #         membership.start_time, membership.expire_time, now,
    #         old_pts, new_pts,
    #     )

    # TODO: 降级暂不开放，恢复时取消注释
    # def quote_downgrade(self, new_level: MembershipLevel, subscribe_type: str) -> Decimal:
    #     return calc_downgrade_prepay(new_level, subscribe_type)

    # ── 升级执行（回调成功后调用） ──

    def execute_upgrade(self, db: Session, membership: UserMembership,
                        order, now: datetime) -> None:
        """
        升级：切换 level_id。同类型不延长 expire_time，跨类型重算周期。
        积分补发使用订单创建时确定的 order.point_adjust（确定性，不重算）。
        幂等：membership.origin_order_no 已等于 order.order_no 则跳过。
        """
        if membership.origin_order_no == order.order_no:
            return  # 已处理过此订单，幂等

        old_level_id = membership.level_id
        membership.level_id = order.product_id
        membership.origin_order_no = order.order_no

        is_cross = membership.subscribe_type != order.subscribe_type
        if is_cross:
            membership.subscribe_type = order.subscribe_type
            delta = relativedelta(years=1) if order.subscribe_type == "yearly" else relativedelta(months=1)
            # start_time 保持不变，expire_time = start_time + 目标周期长度
            membership.expire_time = membership.start_time + delta

        db.add(membership)

        # 补发赠送积分：用订单创建时确定的 point_adjust
        point_adjust = order.point_adjust or Decimal("0")
        if point_adjust > 0:
            user_balance_crud.credit_granted(
                db, membership.user_id, point_adjust,
                source_id=order.order_no, remark="升级补发赠送积分",
            )

        # 写 ChangeLog
        db.add(MembershipChangeLog(
            user_id=membership.user_id,
            from_level_id=old_level_id,
            to_level_id=order.product_id,
            change_type=MembershipChangeType.UPGRADE,
            subscribe_type=membership.subscribe_type,
            effective_time=now,
            status=ChangeLogStatus.EFFECTIVE,
            order_no=order.order_no,
            pay_amount=order.amount,
            point_adjust=point_adjust,
            remark="跨类型升级" if is_cross else "同类型升级",
        ))

    # ── 降级预购记录（回调成功后调用） ──
    # TODO: 降级暂不开放，恢复时取消注释
    # def book_downgrade(self, db: Session, membership: UserMembership,
    #                    order, now: datetime) -> None:
    #     """设置 next_level_id，当前周期不变，写 ChangeLog(预约中)。幂等：已有预约则跳过。"""
    #     if membership.next_level_id:
    #         return  # 已有降级预约，幂等
    #
    #     old_level_id = membership.level_id
    #     membership.next_level_id = order.product_id
    #     membership.next_subscribe_type = order.subscribe_type
    #     db.add(membership)
    #
    #     db.add(MembershipChangeLog(
    #         user_id=membership.user_id,
    #         from_level_id=old_level_id,
    #         to_level_id=order.product_id,
    #         change_type=MembershipChangeType.DOWNGRADE_BOOK,
    #         subscribe_type=order.subscribe_type,
    #         effective_time=membership.expire_time,
    #         status=ChangeLogStatus.PENDING,
    #         order_no=order.order_no,
    #         pay_amount=order.amount,
    #         remark="降级预购，到期兑现",
    #     ))

    # ── 降级兑现（expire_check 定时任务调用） ──
    # TODO: 降级暂不开放，恢复时取消注释
    # def apply_downgrade(self, db: Session, membership: UserMembership, now: datetime) -> None:
    #     """兑现降级：切换 level_id、续期、清零赠送积分、发首月积分"""
    #     old_level_id = membership.level_id
    #     target_level_id = membership.next_level_id
    #     target_sub = membership.next_subscribe_type or membership.subscribe_type
    #
    #     membership.level_id = target_level_id
    #     membership.subscribe_type = target_sub
    #     membership.next_level_id = None
    #     membership.next_subscribe_type = None
    #     membership.start_time = now
    #     delta = relativedelta(years=1) if target_sub == "yearly" else relativedelta(months=1)
    #     membership.expire_time = now + delta
    #     membership.status = MembershipStatus.ACTIVE
    #     db.add(membership)
    #
    #     # 清零赠送积分（周期更替）
    #     user_balance_crud.clear_granted_balance(db, membership.user_id, remark="降级兑现，周期更替清零")
    #
    #     # 发首月赠送积分
    #     self._grant_first_month_points(db, membership.user_id, target_level_id)
    #
    #     db.add(MembershipChangeLog(
    #         user_id=membership.user_id,
    #         from_level_id=old_level_id,
    #         to_level_id=target_level_id,
    #         change_type=MembershipChangeType.DOWNGRADE_APPLY,
    #         subscribe_type=target_sub,
    #         effective_time=now,
    #         status=ChangeLogStatus.EFFECTIVE,
    #         remark="降级到期兑现",
    #     ))
    #
    # def _grant_first_month_points(self, db: Session, user_id: str, level_id: str) -> None:
    #     """发放首月赠送积分"""
    #     from app.models.point_record import PointRecord
    #     from app.enums.membership import PointRecordType, PointType
    #
    #     point_amount = get_monthly_points(db, level_id)
    #     if point_amount <= 0:
    #         return
    #     user_balance_crud.credit_granted(
    #         db, user_id, point_amount, remark="首月赠送积分",
    #     )

    # ── 预览 ──

    def preview_change(self, db: Session, user_id: str,
                       target_level_id: str, target_subscribe_type: str) -> dict:
        """预览变更：返回 change_type/pay_amount/point_adjust/effective_time/message"""
        target_level = db.query(MembershipLevel).filter(
            MembershipLevel.id == target_level_id,
            MembershipLevel.status == 1,
            MembershipLevel.is_deleted == False,
        ).first()
        if not target_level:
            raise ValueError("目标会员等级不存在或已禁用")

        now = datetime.now()
        membership = db.query(UserMembership).filter(
            UserMembership.user_id == user_id,
            UserMembership.status == MembershipStatus.ACTIVE,
            UserMembership.is_deleted == False,
        ).first()

        scene = self.identify_change(db, membership, target_level, target_subscribe_type)

        if scene["scene"] in (SCENE_REJECT_SAME,):
            return {"change_type": 0, "message": "暂不支持当前类型的调整"}
        if scene["scene"] == SCENE_REJECT_DOWNGRADE_BOOKED:
            return {"change_type": 0, "message": "暂不支持当前类型的调整"}
        if scene["scene"] == SCENE_REJECT_CROSS_YEAR_TO_MONTH:
            return {"change_type": 0, "message": "暂不支持当前类型的调整"}
        if scene["scene"] == SCENE_REJECT_CROSS_TYPE:
            return {"change_type": 0, "message": "暂不支持当前类型的调整"}
        if scene["scene"] == SCENE_REJECT_DOWNGRADE:
            return {"change_type": 0, "message": "暂不支持当前类型的调整"}

        # 新购/重购
        if scene["scene"] in (SCENE_NEW_PURCHASE, SCENE_REPURCHASE):
            return {
                "change_type": MembershipChangeType.NEW_PURCHASE,
                "pay_amount": str(get_level_price(target_level, target_subscribe_type)),
                "point_adjust": "0",
                "effective_time": now.strftime("%Y-%m-%d %H:%M:%S"),
                "expire_time": None,
                "message": "新购立即生效",
            }

        # 升级（同类型）
        if scene["scene"] == SCENE_UPGRADE_SAME:
            old_level = scene["old_level"]
            quote = self.quote_upgrade_same(db, membership, old_level, target_level, now)
            return {
                "change_type": MembershipChangeType.UPGRADE,
                "pay_amount": str(quote.pay_amount),
                "point_adjust": str(quote.point_adjust),
                "effective_time": now.strftime("%Y-%m-%d %H:%M:%S"),
                "expire_time": membership.expire_time.strftime("%Y-%m-%d %H:%M:%S"),
                "message": f"升级立即生效，补差价{quote.pay_amount}元，补发积分{quote.point_adjust}",
            }

        # TODO: 跨类型升级（月→年）暂不开放，恢复时取消注释
        # if scene["scene"] == SCENE_UPGRADE_CROSS:
        #     old_level = scene["old_level"]
        #     quote = self.quote_upgrade_cross(db, membership, old_level, target_level, target_subscribe_type, now)
        #     return {
        #         "change_type": MembershipChangeType.UPGRADE,
        #         "pay_amount": str(quote.pay_amount),
        #         "point_adjust": str(quote.point_adjust),
        #         "effective_time": now.strftime("%Y-%m-%d %H:%M:%S"),
        #         "expire_time": quote.new_expire_time.strftime("%Y-%m-%d %H:%M:%S"),
        #         "message": f"跨类型升级，补差价{quote.pay_amount}元，新周期至{quote.new_expire_time.strftime('%Y-%m-%d')}",
        #     }

        # TODO: 降级预购暂不开放，恢复时取消注释
        # if scene["scene"] == SCENE_DOWNGRADE:
        #     prepay = self.quote_downgrade(target_level, membership.subscribe_type)
        #     return {
        #         "change_type": MembershipChangeType.DOWNGRADE_BOOK,
        #         "pay_amount": str(prepay),
        #         "point_adjust": "0",
        #         "effective_time": membership.expire_time.strftime("%Y-%m-%d %H:%M:%S"),
        #         "expire_time": membership.expire_time.strftime("%Y-%m-%d %H:%M:%S"),
        #         "message": f"降级将在当前周期到期后生效，需预付{prepay}元",
        #     }

        return {"change_type": 0, "message": "无法变更"}


membership_change_crud = CRUDMembershipChange(MembershipChangeLog)
