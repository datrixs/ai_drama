"""Episode CRUD"""
from typing import Optional

from sqlalchemy.orm import Session

from app.crud.base_crud import CRUDBase
from app.enums.video import EpisodeStatus
from app.models.project_asset import Episode, Storyboard


class CRUDEpisode(CRUDBase[Episode, dict, dict]):

    def get_by_project(self, db: Session, project_id: str) -> list[Episode]:
        return (
            self.get_queryset(db)
            .filter(self.model.project_id == project_id)
            .order_by(self.model.episode_number)
            .all()
        )

    def get_by_number(self, db: Session, project_id: str, episode_number: int) -> Optional[Episode]:
        return (
            self.get_queryset(db)
            .filter(self.model.project_id == project_id, self.model.episode_number == episode_number)
            .first()
        )

    def _next_episode_number(self, db: Session, project_id: str) -> int:
        """获取下一个可用的集号（当前最大值 + 1，无记录则从 1 开始）"""
        from sqlalchemy import func
        max_num = (
            db.query(func.max(self.model.episode_number))
            .filter(
                self.model.project_id == project_id,
                self.model.is_deleted == False,  # noqa: E712
            )
            .scalar()
        )
        return (max_num or 0) + 1

    def bulk_create_empty(self, db: Session, project_id: str, count: int, user_id: str = None) -> list[Episode]:
        """批量创建 N 集空剧集（导演模式专用）

        - episode_number 从当前最大值 + 1 开始递增
        - title/outline 留空，由用户后续在 EpisodePage 重命名或进入分镜编辑时补充
        """
        if count <= 0:
            return []
        results = []
        next_num = self._next_episode_number(db, project_id)
        for i in range(count):
            ep = Episode(
                project_id=project_id,
                episode_number=next_num + i,
                title="",
                outline="",
                status=EpisodeStatus.PENDING,
                episode_script_status="pending",
                create_uid=user_id,
            )
            db.add(ep)
            results.append(ep)
        db.flush()
        return results

    def create_empty_episode(self, db: Session, project_id: str, user_id: str = None,
                             episode_number: Optional[int] = None, title: str = "",
                             outline: str = "") -> Episode:
        """新增一集空剧集（导演模式下用户在 EpisodePage 点「新增剧集」）"""
        if episode_number is None:
            episode_number = self._next_episode_number(db, project_id)
        ep = Episode(
            project_id=project_id,
            episode_number=episode_number,
            title=title or "",
            outline=outline or "",
            status=EpisodeStatus.PENDING,
            episode_script_status="pending",
            create_uid=user_id,
        )
        db.add(ep)
        db.flush()
        return ep

    def delete_episode(self, db: Session, episode_id: str) -> Optional[Episode]:
        """删除剧集：同时软删关联的 Storyboard，避免孤儿分镜记录"""
        ep = self.get(id=episode_id, db=db)
        if not ep:
            return None
        ep.is_deleted = True
        db.add(ep)
        # 软删关联分镜
        db.query(Storyboard).filter(
            Storyboard.episode_id == episode_id,
            Storyboard.is_deleted == False,  # noqa: E712
        ).update({Storyboard.is_deleted: True}, synchronize_session=False)
        db.flush()
        return ep

    def sync_from_outlines(self, db: Session, project_id: str, outlines: list[dict], user_id: str = None) -> list[Episode]:
        """根据分析结果批量创建/更新 Episode 记录（幂等）"""
        results = []
        for outline in outlines:
            ep_num = outline.get("episode_number")
            if not ep_num:
                continue

            ep = self.get_by_number(db, project_id, ep_num)
            title = outline.get("title", "")
            text = outline.get("summary") or title

            if ep:
                ep.title = title or ep.title
                ep.outline = text or ep.outline
            else:
                ep = Episode(
                    project_id=project_id,
                    episode_number=ep_num,
                    title=title,
                    outline=text,
                    status=EpisodeStatus.PENDING,
                    create_uid=user_id,
                )
                db.add(ep)
            results.append(ep)

        db.flush()
        return results

    def get_pending_episode_scripts(self, db: Session, project_id: str) -> list[Episode]:
        """获取尚未生成剧本的剧集（pending 或 failed）"""
        return (
            self.get_queryset(db)
            .filter(
                self.model.project_id == project_id,
                self.model.episode_script_status.in_(["pending", "failed"]),
            )
            .order_by(self.model.episode_number)
            .all()
        )

    def update_episode_script(self, db: Session, episode_id: str,
                              status: str, script: str = None) -> Episode:
        """更新剧本内容和状态"""
        ep = self.get(id=episode_id, db=db)
        if ep:
            ep.episode_script_status = status
            if script is not None:
                ep.episode_script = script
            db.add(ep)
        return ep


episode_crud = CRUDEpisode(Episode)
