"""EpisodeConcatRecord CRUD — 整集视频合成记录"""
from typing import Optional

from sqlalchemy.orm import Session

from app.crud.base_crud import CRUDBase
from app.models.project_asset import EpisodeConcatRecord


class CRUDEpisodeConcatRecord(CRUDBase[EpisodeConcatRecord, dict, dict]):
    """整集合成记录 CRUD"""

    def get_by_episode(self, db: Session, episode_id: str, limit: int = 50) -> list[EpisodeConcatRecord]:
        """按剧集查询合成历史（按创建时间倒序）"""
        return (
            self.get_queryset(db)
            .filter(self.model.episode_id == episode_id)
            .order_by(self.model.create_time.desc())
            .limit(limit)
            .all()
        )

    def get_latest_by_episode(self, db: Session, episode_id: str) -> Optional[EpisodeConcatRecord]:
        """获取剧集最新一条合成记录（任意状态）"""
        return (
            self.get_queryset(db)
            .filter(self.model.episode_id == episode_id)
            .order_by(self.model.create_time.desc())
            .first()
        )

    def get_active_by_episode(self, db: Session, episode_id: str) -> Optional[EpisodeConcatRecord]:
        """获取剧集当前进行中的合成记录（pending/processing），用于阻止并发合成"""
        return (
            self.get_queryset(db)
            .filter(
                self.model.episode_id == episode_id,
                self.model.status.in_(["pending", "processing"]),
            )
            .order_by(self.model.create_time.desc())
            .first()
        )


episode_concat_record_crud = CRUDEpisodeConcatRecord(EpisodeConcatRecord)
