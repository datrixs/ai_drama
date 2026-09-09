from uuid import uuid4
from decimal import Decimal
from typing import Any, Dict

from sqlalchemy.orm import Session

from app.crud.base_crud import CRUDBase
from app.deps.base import PageParams
from app.enums.transfer import PointTransferType, PointTransferStatus
from app.models.point_transfer import PointTransferRecord
from app.schemas.base import PageBase


class CRUDTransferRecord(CRUDBase):
    """积分转账记录 CRUD"""

    def create_record(
        self,
        db: Session,
        user_id: str,
        target_user_id: str,
        point: Decimal,
        transfer_type: PointTransferType,
        status: PointTransferStatus,
        from_before_point: Decimal = None,
        from_after_point: Decimal = None,
        to_before_point: Decimal = None,
        to_after_point: Decimal = None,
    ) -> PointTransferRecord:
        """创建转账记录

        before/after point 为转账双方的余额快照，成功时必填，失败时可不传。
        """
        record = PointTransferRecord(
            id=str(uuid4()),
            user_id=user_id,
            transfer_to_user_id=target_user_id,
            point=point,
            transfer_type=transfer_type,
            status=status,
            transfer_from_user_before_point=from_before_point,
            transfer_from_user_after_point=from_after_point,
            transfer_to_user_before_point=to_before_point,
            transfer_to_user_after_point=to_after_point,
        )
        db.add(record)
        return record

    def get_records_by_user(
        self,
        db: Session,
        user_id: str,
        page_params: PageParams,
    ) -> Dict[str, Any]:
        """获取用户的转账记录（作为转出方或转入方）

        客户端不展示后台分配(ADMIN_ADJUST)类型的记录，仅返回用户间转账。
        """
        query = self.get_queryset(db).filter(
            (PointTransferRecord.user_id == user_id)
            | (PointTransferRecord.transfer_to_user_id == user_id),
            PointTransferRecord.transfer_type != PointTransferType.ADMIN_ADJUST,
        ).order_by(PointTransferRecord.create_time.desc())
        return self.get_multi(page_params, query)


transfer_crud = CRUDTransferRecord(PointTransferRecord)
