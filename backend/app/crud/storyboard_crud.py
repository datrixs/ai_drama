"""分镜片段 CRUD"""
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud.base_crud import CRUDBase
from app.models.project_asset import Storyboard
from app.schemas.storyboard import StoryboardCreate, StoryboardUpdate


# 处于"生成中"的片段禁止删除（避免 Celery 任务回写脏数据）
DELETING_BLOCKED_STATUSES = {"image_generating", "video_generating"}


class CRUDStoryboard(CRUDBase[Storyboard, StoryboardCreate, StoryboardUpdate]):
    """分镜片段 CRUD 操作"""

    def get_by_episode(self, db: Session, episode_id: str) -> list[Storyboard]:
        """获取剧集下所有片段，按 segment_index 排序"""
        return (
            db.query(self.model)
            .filter(self.model.episode_id == episode_id, self.model.is_deleted == False)
            .order_by(self.model.segment_index)
            .all()
        )

    def get_by_segment_index(
        self, db: Session, episode_id: str, segment_index: int
    ) -> Storyboard | None:
        """按剧集ID和片段序号获取"""
        return (
            db.query(self.model)
            .filter(
                self.model.episode_id == episode_id,
                self.model.segment_index == segment_index,
                self.model.is_deleted == False,
            )
            .first()
        )

    def reorder_segments(
        self, db: Session, episode_id: str, segment_ids: list[str]
    ) -> None:
        """重排片段顺序"""
        for i, seg_id in enumerate(segment_ids):
            segment = db.get(self.model, seg_id)
            if segment and segment.episode_id == episode_id:
                segment.segment_index = i + 1
        db.flush()

    def _lock_and_list(self, db: Session, episode_id: str) -> list[Storyboard]:
        """锁定 episode 下未软删的所有片段（行锁，避免并发插入产生重复序号）"""
        stmt = (
            select(self.model)
            .where(self.model.episode_id == episode_id, self.model.is_deleted == False)
            .with_for_update()
            .order_by(self.model.segment_index)
        )
        return list(db.execute(stmt).scalars().all())

    @staticmethod
    def _reindex(rows: list[Storyboard], skip_id: str | None = None) -> None:
        """按现有顺序把 segment_index 压成 1..N"""
        next_idx = 1
        for r in rows:
            if r.id == skip_id:
                continue
            r.segment_index = next_idx
            next_idx += 1

    def insert_segment(
        self,
        db: Session,
        episode_id: str,
        anchor_segment_id: str,
        position: str,
        create_uid: str,
    ) -> Storyboard:
        """
        在锚点片段前/后插入一条空白片段（status=pending），并维护后续片段的 segment_index。
        position: 'before' 或 'after'
        整个过程依赖 _lock_and_list 取得行锁，调用方需在事务中提交。
        """
        rows = self._lock_and_list(db, episode_id)
        anchor = next((r for r in rows if r.id == anchor_segment_id), None)
        if anchor is None:
            raise ValueError("锚点片段不存在或已删除")

        target_index = anchor.segment_index if position == "before" else anchor.segment_index + 1

        # 把 >= target_index 的全部后移一位
        for r in rows:
            if r.segment_index >= target_index:
                r.segment_index = r.segment_index + 1

        new_segment = self.model(
            id=str(uuid4()),
            episode_id=episode_id,
            segment_index=target_index,
            status="pending",
            create_uid=create_uid,
        )
        db.add(new_segment)
        db.flush()
        return new_segment

    def soft_delete_and_reorder(
        self, db: Session, segment_id: str, update_uid: str
    ) -> Storyboard | None:
        """
        软删除片段，并把剩余片段重排为 1..N。
        若片段处于生成中状态（image_generating/video_generating），抛出 ValueError。
        """
        segment = db.get(self.model, segment_id)
        if segment is None or segment.is_deleted:
            return None
        if segment.status in DELETING_BLOCKED_STATUSES:
            raise ValueError(f"片段正在生成中（{segment.status}），无法删除")

        rows = self._lock_and_list(db, segment.episode_id)
        segment.is_deleted = True
        segment.update_uid = update_uid
        self._reindex(rows, skip_id=segment_id)
        db.flush()
        return segment

    def reindex_episode(self, db: Session, episode_id: str) -> None:
        """把指定 episode 下的剩余片段重排为 1..N"""
        rows = self._lock_and_list(db, episode_id)
        self._reindex(rows)
        db.flush()

    def update_status(self, db: Session, storyboard_id: str, status: str, gen_error: str = None) -> None:
        """更新片段状态"""
        segment = db.get(self.model, storyboard_id)
        if segment:
            segment.status = status
            if gen_error:
                segment.gen_error = gen_error
            db.flush()

    def update_video_url(self, db: Session, storyboard_id: str, video_url: str, duration: float = None) -> None:
        """更新片段视频URL"""
        segment = db.get(self.model, storyboard_id)
        if segment:
            segment.video_url = video_url
            if duration is not None:
                segment.duration = duration
            segment.status = "video_completed"
            db.flush()

    def count_by_episode(self, db: Session, episode_id: str) -> int:
        """统计剧集下片段数量"""
        from sqlalchemy import func
        return (
            db.query(func.count(self.model.id))
            .filter(self.model.episode_id == episode_id, self.model.is_deleted == False)
            .scalar()
        )


storyboard_crud = CRUDStoryboard(Storyboard)
