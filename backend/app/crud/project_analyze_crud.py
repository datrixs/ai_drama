import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud.base_crud import CRUDBase
from app.models.project_analyze import AnalysisResult, AnalysisVersion


class CRUDAnalysisResult(CRUDBase[AnalysisResult, dict, dict]):
    def create(self, *, obj_in, created_by_id=None, db: Session) -> AnalysisResult:
        if isinstance(obj_in, dict):
            db_obj = self.model(**obj_in)
        else:
            db_obj = self.model(**obj_in.model_dump(exclude_unset=True))
        db_obj.id = db_obj.id or str(uuid.uuid4())
        if created_by_id:
            db_obj.create_uid = created_by_id
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_by_project(self, db: Session, project_id: str) -> Optional[AnalysisResult]:
        """根据项目ID获取分析结果"""
        stmt = select(AnalysisResult).where(
            AnalysisResult.project_id == project_id,
            AnalysisResult.is_deleted == False,
        )
        return db.execute(stmt).scalar_one_or_none()


class CRUDAnalysisVersion(CRUDBase[AnalysisVersion, dict, dict]):
    def create(self, *, obj_in, created_by_id=None, db: Session) -> AnalysisVersion:
        if isinstance(obj_in, dict):
            db_obj = self.model(**obj_in)
        else:
            db_obj = self.model(**obj_in.model_dump(exclude_unset=True))
        db_obj.id = db_obj.id or str(uuid.uuid4())
        if created_by_id:
            db_obj.create_uid = created_by_id
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_current_version(self, db: Session, analysis_result_id: str) -> Optional[AnalysisVersion]:
        """获取当前版本：优先用 current_version_id，兜底按版本号倒序"""
        result = db.get(AnalysisResult, analysis_result_id)
        if result and result.current_version_id:
            version = db.get(AnalysisVersion, result.current_version_id)
            if version and not version.is_deleted:
                return version
        # 兜底：返回最新版本
        stmt = (
            select(AnalysisVersion)
            .where(
                AnalysisVersion.analysis_result_id == analysis_result_id,
                AnalysisVersion.is_deleted == False,
            )
            .order_by(AnalysisVersion.version_number.desc())
            .limit(1)
        )
        return db.execute(stmt).scalar_one_or_none()

    def get_by_version_number(self, db: Session, analysis_result_id: str, version_number: int) -> Optional[AnalysisVersion]:
        """根据版本号获取版本"""
        stmt = select(AnalysisVersion).where(
            AnalysisVersion.analysis_result_id == analysis_result_id,
            AnalysisVersion.version_number == version_number,
            AnalysisVersion.is_deleted == False,
        )
        return db.execute(stmt).scalar_one_or_none()


analysis_result = CRUDAnalysisResult(AnalysisResult)
analysis_version = CRUDAnalysisVersion(AnalysisVersion)
