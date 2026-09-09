from typing import Optional

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from app.crud.base_crud import CRUDBase
from app.enums.membership import PointRecordType, PointType
from app.models.point_record import PointRecord, PointPurchasePlan


class CRUDPointRecord(CRUDBase):

    def get_enabled_plans(self, db: Session):
        """获取所有启用的积分购买方案"""
        return db.query(PointPurchasePlan).filter(
            PointPurchasePlan.is_enabled == True,
            PointPurchasePlan.is_deleted == False,
        ).order_by(PointPurchasePlan.sort_order.asc()).all()

    def get_user_records(self, db: Session, user_id: str, page: int = 1, size: int = 10,
                         record_type: Optional[int] = None):
        """查询用户积分记录"""
        query = db.query(PointRecord).filter(
            PointRecord.user_id == user_id,
            PointRecord.is_deleted == False,
        )
        if record_type is not None:
            query = query.filter(PointRecord.record_type == record_type)
        query = query.order_by(PointRecord.create_time.desc())
        total = query.count()
        items = query.offset((page - 1) * size).limit(size).all()
        return {"data": items, "pagination": {"page": page, "size": size, "total_count": total}}

    def has_monthly_grant(self, db: Session, user_id: str, grant_date: str) -> bool:
        """检查某周期是否已发放积分（grant_date 格式: YYYY-MM-DD）"""
        return db.query(PointRecord).filter(
            PointRecord.user_id == user_id,
            PointRecord.record_type == PointRecordType.MONTHLY_GRANT,
            PointRecord.grant_month == grant_date,
        ).first() is not None

    def sum_granted_by_sources(self, db: Session, source_ids: list) -> dict:
        """按来源ID(订单号)聚合赠送积分总额，一次查询避免 N+1

        口径：统计该订单关联的赠送积分正向入账（point_type=GRANTED 且 >0），
        即会员首月赠送等；不含后续周期清零（其 source_id 非订单号）。
        注：source_ids 应由调用方先按用户隔离（当前用户自己的订单号）。
        """
        if not source_ids:
            return {}
        rows = db.query(
            PointRecord.source_id,
            func.sum(PointRecord.point_amount),
        ).filter(
            PointRecord.source_id.in_(source_ids),
            PointRecord.point_type == PointType.GRANTED,
            PointRecord.point_amount > 0,
            PointRecord.is_deleted == False,
        ).group_by(PointRecord.source_id).all()
        return {sid: total for sid, total in rows if sid}

    def sum_points_by_order_sources(self, db: Session, user_id: str, source_ids: list) -> dict:
        """按订单号(source_id)聚合入账积分（首月赠送 MONTHLY_GRANT + 购买到账 POINT_PURCHASE）

        合并记录用：给订单事件补积分。source_id 即订单号；一笔成功订单对应一条入账流水。
        按 user_id 过滤作纵深防御（与 source_id 唯一性双保险），仅聚合正向入账。
        """
        if not source_ids:
            return {}
        rows = db.query(
            PointRecord.source_id,
            func.sum(PointRecord.point_amount),
        ).filter(
            PointRecord.user_id == user_id,
            PointRecord.source_id.in_(source_ids),
            PointRecord.record_type.in_([PointRecordType.MONTHLY_GRANT, PointRecordType.POINT_PURCHASE]),
            PointRecord.point_amount > 0,
            PointRecord.is_deleted == False,
        ).group_by(PointRecord.source_id).all()
        return {sid: total for sid, total in rows if sid}

    def get_grant_clear_records(self, db: Session, user_id: str, record_types: list) -> list:
        """查询纯赠送/清零流水，供合并记录展示。

        record_types 指定要查的 PointRecordType（MONTHLY_GRANT 和/或 GRANT_CLEAR）：
        - MONTHLY_GRANT 仅取 source_id IS NULL（后续周期赠送）；首月赠送 source_id=订单号，
          已并入订单事件，不在此返回（避免重复）。
        - GRANT_CLEAR 取全部（source_id 恒为 None）。
        """
        conds = []
        if PointRecordType.MONTHLY_GRANT in record_types:
            conds.append(and_(
                PointRecord.record_type == PointRecordType.MONTHLY_GRANT,
                PointRecord.source_id.is_(None),
            ))
        if PointRecordType.GRANT_CLEAR in record_types:
            conds.append(PointRecord.record_type == PointRecordType.GRANT_CLEAR)
        if not conds:
            return []
        return db.query(PointRecord).filter(
            PointRecord.user_id == user_id,
            PointRecord.is_deleted == False,
            or_(*conds),
        ).all()


point_record_crud = CRUDPointRecord(PointRecord)
point_plan_crud = CRUDPointRecord(PointPurchasePlan)
