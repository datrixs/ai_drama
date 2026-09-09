from uuid import uuid4
from decimal import Decimal

from loguru import logger
from sqlalchemy.orm import Session

from app.models import User, UserBalance
from app.models.point_record import PointRecord
from app.enums.membership import PointType, PointRecordType
from app.schemas import UserBalanceCreateSchema, UserBalanceUpdateSchema
from app.crud.base_crud import CRUDBase


class CRUDUserBalance(
    CRUDBase[UserBalance, UserBalanceCreateSchema, UserBalanceUpdateSchema]
):

    def __init__(self, model: type[UserBalance]):
        super().__init__(model)

    def _sync_balance(self, ub: UserBalance):
        """同步冗余总额 balance = granted_balance + purchased_balance"""
        ub.balance = (ub.granted_balance or Decimal("0.00")) + (ub.purchased_balance or Decimal("0.00"))

    def init_user_balance(self, db: Session, user_id: str):
        """初始化用户余额表"""
        user_balance = UserBalance(
            id=str(uuid4()),
            user_id=user_id,
            balance=Decimal("0.00"),
            granted_balance=Decimal("0.00"),
            purchased_balance=Decimal("0.00"),
            frozen_amount=Decimal("0.00"),
            total_spent=Decimal("0.00"),
        )
        db.add(user_balance)

    def get_by_user_id(self, db: Session, user_id: str,
                       for_update: bool = False) -> UserBalance | None:
        """根据用户ID获取用户余额

        for_update=True 时加行锁（SELECT ... FOR UPDATE），用于扣减/退款/划转等
        写操作，防止并发超扣；锁在调用方事务 commit/rollback 后释放。
        只读查询保持默认不加锁。
        """
        query = db.query(UserBalance).filter_by(user_id=user_id)
        if for_update:
            query = query.with_for_update()
        return query.first()

    # ── 双账户入账 ──

    def credit_granted(self, db: Session, user_id: str, amount: Decimal,
                       source_id: str = None, remark: str = "",
                       grant_month: str = None, level_id: str = None) -> None:
        """赠送积分入账（按月赠送/升级补发/首月赠送）"""
        if amount <= 0:
            return
        ub = self.get_by_user_id(db, user_id)
        if not ub:
            return
        ub.granted_balance = (ub.granted_balance or Decimal("0.00")) + amount
        self._sync_balance(ub)
        db.add(ub)
        record = PointRecord(
            user_id=user_id,
            point_amount=amount,
            balance_after=ub.balance,
            record_type=PointRecordType.MONTHLY_GRANT,
            point_type=PointType.GRANTED,
            source_id=source_id,
            level_id=level_id,
            grant_month=grant_month,
            remark=remark or "赠送积分入账",
        )
        db.add(record)

    def credit_purchased(self, db: Session, user_id: str, amount: Decimal,
                         source_id: str = None, remark: str = "") -> None:
        """购买积分入账（积分购买订单到账）"""
        if amount <= 0:
            return
        ub = self.get_by_user_id(db, user_id)
        if not ub:
            return
        ub.purchased_balance = (ub.purchased_balance or Decimal("0.00")) + amount
        self._sync_balance(ub)
        db.add(ub)
        record = PointRecord(
            user_id=user_id,
            point_amount=amount,
            balance_after=ub.balance,
            record_type=PointRecordType.POINT_PURCHASE,
            point_type=PointType.PURCHASED,
            source_id=source_id,
            remark=remark or "购买积分入账",
        )
        db.add(record)

    def _get_sub_user_ids(self, db: Session, user_id: str) -> list[str]:
        """查询某主账号名下所有子账号 id（仅取 id 列，排除软删除，与权限可见口径一致）"""
        return [
            uid for (uid,) in db.query(User.id)
            .filter_by(parent_user_id=user_id, is_deleted=False)
            .all()
        ]

    def clear_granted_balance(self, db: Session, user_id: str,
                              remark: str = "赠送积分清零",
                              cascade_sub_users: bool = True) -> UserBalance | None:
        """清零赠送积分（周期更替/到期/年付发放前）。

        cascade_sub_users=True 时，同步清零该用户名下所有子账号（parent_user_id=user_id）
        的赠送积分；子账号购买积分不动，子账号流水 remark 追加“(级联子账号)”。
        返回主账号余额对象（不存在则为 None），便于调用方取清零后总余额。

        清零由到期/换周期事件触发，与主账号当前余额无关：主账号 granted_balance=0
        时主账号不写流水，但仍级联清零子账号。
        """
        ub = self.get_by_user_id(db, user_id)
        # 主账号存在且有赠送积分时清零、写流水；为 0 也不跳过后续级联
        if ub and (ub.granted_balance or Decimal("0.00")) > 0:
            cleared = ub.granted_balance
            ub.granted_balance = Decimal("0.00")
            self._sync_balance(ub)
            db.add(ub)
            db.add(PointRecord(
                user_id=user_id,
                point_amount=-cleared,
                balance_after=ub.balance,
                record_type=PointRecordType.GRANT_CLEAR,
                point_type=PointType.GRANTED,
                remark=remark,
            ))

        # 无论主账号是否清零，级联清零子账号（递归调用，显式关闭二级级联防误伤）
        if cascade_sub_users:
            for sub_id in self._get_sub_user_ids(db, user_id):
                self.clear_granted_balance(
                    db, sub_id,
                    remark=f"{remark}(级联子账号)",
                    cascade_sub_users=False,
                )
        return ub

    # ── 消费（先赠送后购买） ──

    def deduct_balance(self, db: Session, user_id: str, amount: Decimal,
                       source_id: str = None, remark: str = "积分消费", is_commit=False) -> UserBalance | None:
        """
        消费积分：先扣赠送余额，不足再扣购买余额。
        跨类型时拆两条 PointRecord（point_type 对应）。
        """
        if amount <= 0:
            return None
        ub = self.get_by_user_id(db, user_id, for_update=True)
        if not ub:
            raise ValueError(f"用户余额记录不存在: {user_id}")

        granted = ub.granted_balance or Decimal("0.00")
        purchased = ub.purchased_balance or Decimal("0.00")

        from_granted = min(amount, granted)
        remain = amount - from_granted
        from_purchased = min(remain, purchased)

        if remain - from_purchased > 0:
            raise ValueError(f"积分余额不足: 可用={granted + purchased}, 需要={amount}")

        ub.granted_balance = granted - from_granted
        ub.purchased_balance = purchased - from_purchased
        ub.total_spent = (ub.total_spent or Decimal("0.00")) + amount
        self._sync_balance(ub)
        db.add(ub)

        # 按扣减类型分别写 PointRecord
        if from_granted > 0:
            db.add(PointRecord(
                user_id=user_id,
                point_amount=-from_granted,
                balance_after=ub.balance,
                record_type=PointRecordType.POINT_CONSUME,
                point_type=PointType.GRANTED,
                source_id=source_id,
                remark=f"{remark}(赠送)",
            ))
        if from_purchased > 0:
            db.add(PointRecord(
                user_id=user_id,
                point_amount=-from_purchased,
                balance_after=ub.balance,
                record_type=PointRecordType.POINT_CONSUME,
                point_type=PointType.PURCHASED,
                source_id=source_id,
                remark=f"{remark}(购买)",
            ))

        if is_commit:
            db.commit()

        return ub

    # ── 兼容保留（标记 deprecated，内部转发） ──

    def credit_balance(self, db: Session, user_id: str, amount: Decimal) -> None:
        """积分入账（兼容，默认走赠送积分）"""
        self.credit_granted(db, user_id, amount)

    def _resolve_refund_split(self, db: Session, user_id: str, amount: Decimal,
                              source_id: str = None) -> tuple[Decimal, Decimal]:
        """反查同 source_id 的 POINT_CONSUME 流水，还原退款应回补的购买/赠送分量。

        退款优先回补购买余额（永不过期），超出当初购买扣减部分再回补赠送余额
        （会被周期清零）。无 source_id 或查不到流水时安全退化：全部退回赠送
        （与历史行为兼容），并打 warning 便于排查。
        """
        fallback = (amount, Decimal("0.00"))
        if not source_id:
            logger.warning(f"[积分] 退款无 source_id，退化退回赠送: user_id={user_id} amount={amount}")
            return fallback
        records = db.query(PointRecord).filter(
            PointRecord.user_id == user_id,
            PointRecord.source_id == source_id,
            PointRecord.record_type == PointRecordType.POINT_CONSUME,
        ).all()
        if not records:
            logger.warning(
                f"[积分] 退款未找到预扣流水，退化退回赠送: user_id={user_id} "
                f"source_id={source_id} amount={amount}"
            )
            return fallback

        from_granted = sum(
            (abs(r.point_amount) for r in records if r.point_type == PointType.GRANTED),
            Decimal("0.00"),
        )
        from_purchased = sum(
            (abs(r.point_amount) for r in records if r.point_type == PointType.PURCHASED),
            Decimal("0.00"),
        )
        # 退款优先回补购买余额（永不过期），超出当初购买扣减部分再回补赠送余额。
        purch_part = min(amount, from_purchased)
        grant_part = min(amount - purch_part, from_granted)
        # 退款总量不超过已扣总量（不凭空生成积分）。amount 超出已扣（数据不一致/
        # 重复退款）时仅退实际已扣量并打 warning，避免凭空创造积分。
        refunded = grant_part + purch_part
        if refunded < amount:
            logger.warning(
                f"[积分] 退款超出已扣总量，仅退实际已扣: user_id={user_id} "
                f"source_id={source_id} 请求={amount} 实退={refunded}"
            )
        return grant_part, purch_part

    def refund_balance(self, db: Session, user_id: str, amount: Decimal,
                       source_id: str = None, remark: str = "积分退还") -> None:
        """退还积分：优先回补购买余额，超出部分再回补赠送余额（反查 source_id 预扣构成）。

        无 source_id 或查不到流水时退化退回 granted。跨类型拆两条 REFUND 流水。
        用于模型调用失败退还预扣、结算时退还多扣差额。
        """
        if amount <= 0:
            return
        ub = self.get_by_user_id(db, user_id, for_update=True)
        if not ub:
            return
        grant_part, purch_part = self._resolve_refund_split(db, user_id, amount, source_id)
        refunded = grant_part + purch_part
        ub.granted_balance = (ub.granted_balance or Decimal("0.00")) + grant_part
        ub.purchased_balance = (ub.purchased_balance or Decimal("0.00")) + purch_part
        ub.total_spent = max((ub.total_spent or Decimal("0.00")) - refunded, Decimal("0.00"))
        self._sync_balance(ub)
        db.add(ub)

        if grant_part > 0:
            db.add(PointRecord(
                user_id=user_id,
                point_amount=grant_part,
                balance_after=ub.balance,
                record_type=PointRecordType.REFUND,
                point_type=PointType.GRANTED,
                source_id=source_id,
                remark=f"{remark}(赠送)",
            ))
        if purch_part > 0:
            db.add(PointRecord(
                user_id=user_id,
                point_amount=purch_part,
                balance_after=ub.balance,
                record_type=PointRecordType.REFUND,
                point_type=PointType.PURCHASED,
                source_id=source_id,
                remark=f"{remark}(购买)",
            ))

    def transfer_balance(self, db: Session, from_user_id: str, to_user_id: str,
                         amount: Decimal,
                         source_id: str = None, remark: str = "") -> None:
        """主账号向子账号划拨积分。

        按主账号余额构成拆分（先扣赠送、不足扣购买），子账号按相同分量分别计入
        赠送/购买余额，保持类型一致——避免购买积分（永不清零）被降级为赠送积分
        （会被周期清零），也避免 granted_balance 出现负数。

        按分量写双方 PointRecord 流水（record_type=TRANSFER），转出方为负、
        转入方为正，零额不写。
        """
        if amount <= 0:
            raise ValueError("划拨金额必须大于0")
        from_balance = self.get_by_user_id(db, from_user_id, for_update=True)
        if not from_balance or from_balance.balance < amount:
            raise ValueError("主账号积分余额不足")
        to_balance = self.get_by_user_id(db, to_user_id, for_update=True)
        if not to_balance:
            raise ValueError("子账号余额记录不存在")

        # 余额快照（转账前），供 PointTransferRecord 追溯
        from_before = from_balance.balance
        to_before = to_balance.balance

        from_granted = from_balance.granted_balance or Decimal("0.00")
        from_purchased = from_balance.purchased_balance or Decimal("0.00")
        grant_part = min(amount, from_granted)
        purchase_part = amount - grant_part

        from_balance.granted_balance = from_granted - grant_part
        from_balance.purchased_balance = from_purchased - purchase_part
        self._sync_balance(from_balance)

        to_balance.granted_balance = (to_balance.granted_balance or Decimal("0.00")) + grant_part
        to_balance.purchased_balance = (to_balance.purchased_balance or Decimal("0.00")) + purchase_part
        self._sync_balance(to_balance)

        db.add(from_balance)
        db.add(to_balance)

        action = remark or "积分划拨"
        if grant_part > 0:
            db.add(PointRecord(
                user_id=from_user_id,
                point_amount=-grant_part,
                balance_after=from_balance.balance,
                record_type=PointRecordType.TRANSFER,
                point_type=PointType.GRANTED,
                source_id=source_id,
                remark=f"{action}转出(赠送)→{to_user_id}",
            ))
            db.add(PointRecord(
                user_id=to_user_id,
                point_amount=grant_part,
                balance_after=to_balance.balance,
                record_type=PointRecordType.TRANSFER,
                point_type=PointType.GRANTED,
                source_id=source_id,
                remark=f"{action}收到(赠送)←{from_user_id}",
            ))
        if purchase_part > 0:
            db.add(PointRecord(
                user_id=from_user_id,
                point_amount=-purchase_part,
                balance_after=from_balance.balance,
                record_type=PointRecordType.TRANSFER,
                point_type=PointType.PURCHASED,
                source_id=source_id,
                remark=f"{action}转出(购买)→{to_user_id}",
            ))
            db.add(PointRecord(
                user_id=to_user_id,
                point_amount=purchase_part,
                balance_after=to_balance.balance,
                record_type=PointRecordType.TRANSFER,
                point_type=PointType.PURCHASED,
                source_id=source_id,
                remark=f"{action}收到(购买)←{from_user_id}",
            ))

        return {
            "from_before": from_before,
            "from_after": from_balance.balance,
            "to_before": to_before,
            "to_after": to_balance.balance,
        }

    def reclaim_balance(self, db: Session, from_user_id: str, to_user_id: str,
                        source_id: str = None, remark: str = "") -> dict | None:
        """回收子账号全部积分到主账号。

        按子账号余额构成分别加回主账号对应类型，保持类型一致——子账号的购买
        积分回收后仍是主账号的购买积分（永不清零），不降级为赠送积分。

        按原类型写双方 PointRecord 流水（record_type=TRANSFER），子账号（转出方）
        两类清零、balance_after 恒为 0，主账号（转入方）按原类型入账，零额不写。

        返回包含回收金额与双方余额快照的 dict；无可回收积分返回 None。
        """
        from_balance = self.get_by_user_id(db, from_user_id, for_update=True)
        if not from_balance:
            return None
        # 余额快照（回收前），供 PointTransferRecord 追溯
        from_before = from_balance.balance
        reclaim_granted = from_balance.granted_balance or Decimal("0.00")
        reclaim_purchased = from_balance.purchased_balance or Decimal("0.00")
        reclaim_amount = reclaim_granted + reclaim_purchased
        if reclaim_amount <= 0:
            return None
        to_balance = self.get_by_user_id(db, to_user_id, for_update=True)
        if not to_balance:
            raise ValueError("主账号余额记录不存在")
        to_before = to_balance.balance

        from_balance.granted_balance = Decimal("0.00")
        from_balance.purchased_balance = Decimal("0.00")
        self._sync_balance(from_balance)

        to_balance.granted_balance = (to_balance.granted_balance or Decimal("0.00")) + reclaim_granted
        to_balance.purchased_balance = (to_balance.purchased_balance or Decimal("0.00")) + reclaim_purchased
        self._sync_balance(to_balance)

        db.add(from_balance)
        db.add(to_balance)

        action = remark or "积分回收"
        if reclaim_granted > 0:
            db.add(PointRecord(
                user_id=from_user_id,
                point_amount=-reclaim_granted,
                balance_after=from_balance.balance,
                record_type=PointRecordType.TRANSFER,
                point_type=PointType.GRANTED,
                source_id=source_id,
                remark=f"{action}转出(赠送)→{to_user_id}",
            ))
            db.add(PointRecord(
                user_id=to_user_id,
                point_amount=reclaim_granted,
                balance_after=to_balance.balance,
                record_type=PointRecordType.TRANSFER,
                point_type=PointType.GRANTED,
                source_id=source_id,
                remark=f"{action}收到(赠送)←{from_user_id}",
            ))
        if reclaim_purchased > 0:
            db.add(PointRecord(
                user_id=from_user_id,
                point_amount=-reclaim_purchased,
                balance_after=from_balance.balance,
                record_type=PointRecordType.TRANSFER,
                point_type=PointType.PURCHASED,
                source_id=source_id,
                remark=f"{action}转出(购买)→{to_user_id}",
            ))
            db.add(PointRecord(
                user_id=to_user_id,
                point_amount=reclaim_purchased,
                balance_after=to_balance.balance,
                record_type=PointRecordType.TRANSFER,
                point_type=PointType.PURCHASED,
                source_id=source_id,
                remark=f"{action}收到(购买)←{from_user_id}",
            ))
        return {
            "reclaim_amount": reclaim_amount,
            "from_before": from_before,
            "from_after": from_balance.balance,
            "to_before": to_before,
            "to_after": to_balance.balance,
        }


user_balance_crud = CRUDUserBalance(UserBalance)
