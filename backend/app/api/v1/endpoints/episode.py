"""剧集 API 端点"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.crud.episode_crud import episode_crud
from app.models import User
from app.models.project_asset import Storyboard

logger = logging.getLogger(__name__)
from app.utils.response import success_response
from app.utils.tencent_cos_utils import cos_client

router = APIRouter()


class EpisodeResponse(BaseModel):
    id: str
    project_id: str
    episode_number: int
    title: str = ""
    outline: str = ""
    episode_script: str | None = None
    episode_script_status: str = "pending"
    status: str = "pending"
    video_count: int = 0
    cover_url: str | None = None

    model_config = {"from_attributes": True}

    @field_validator("title", "outline", "episode_script", mode="before")
    @classmethod
    def _none_to_empty(cls, v):
        return v or ""


class EpisodeCreateRequest(BaseModel):
    """新增空剧集请求（导演模式）"""
    title: str = Field(default="", max_length=256, description="剧集标题，可空")
    outline: str = Field(default="", max_length=2000, description="剧情大纲，可空")


class EpisodeUpdateRequest(BaseModel):
    """更新剧集请求（导演模式专属，支持改标题和剧情大纲）"""
    title: str | None = Field(default=None, max_length=256, description="剧集标题，传 null 或不传表示不改")
    outline: str | None = Field(default=None, max_length=2000, description="剧情大纲，传 null 或不传表示不改")


def _resolve_cos_url(v):
    if not v:
        return v
    if not v.startswith("http"):
        return cos_client.key_to_url(v)
    key = cos_client.url_to_key(v)
    if key and not key.startswith("http"):
        return cos_client.key_to_url(key)
    return v


@router.get("/projects/{project_id}/episodes")
def list_episodes(project_id: str, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    episodes = episode_crud.get_by_project(db, project_id)

    episode_ids = [ep.id for ep in episodes]
    if not episode_ids:
        return success_response(data=[])

    # 批量查询每个剧集的视频数量
    video_count_rows = (
        db.query(
            Storyboard.episode_id,
            func.count(Storyboard.id).label("cnt"),
        )
        .filter(
            Storyboard.episode_id.in_(episode_ids),
            Storyboard.is_deleted == False,
            Storyboard.video_url != None,
            Storyboard.video_url != "",
        )
        .group_by(Storyboard.episode_id)
        .all()
    )
    video_count_map = {row.episode_id: row.cnt for row in video_count_rows}

    # 批量查询每个剧集第一个片段的首帧图片
    first_segments = (
        db.query(Storyboard)
        .filter(
            Storyboard.episode_id.in_(episode_ids),
            Storyboard.is_deleted == False,
        )
        .order_by(Storyboard.episode_id, Storyboard.segment_index)
        .all()
    )
    cover_map = {}
    for seg in first_segments:
        if seg.episode_id not in cover_map:
            cover_map[seg.episode_id] = _resolve_cos_url(seg.cover_url)

    items = []
    for ep in episodes:
        resp = EpisodeResponse.model_validate(ep)
        resp.video_count = video_count_map.get(ep.id, 0)
        resp.cover_url = cover_map.get(ep.id)
        items.append(resp.model_dump())

    return success_response(data=items)


@router.get("/projects/{project_id}/episodes/{episode_id}")
def get_episode(project_id: str, episode_id: str, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    episode = episode_crud.get(id=episode_id, db=db)
    if not episode or episode.project_id != project_id:
        raise HTTPException(status_code=404, detail="剧集不存在")
    return success_response(data=EpisodeResponse.model_validate(episode))


@router.post("/projects/{project_id}/episodes")
def create_episode(
    project_id: str,
    body: EpisodeCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """新增一集空剧集（仅导演模式项目可用）"""
    from app.models.project import Project

    proj = db.query(Project).filter(Project.id == project_id, Project.is_deleted == False).first()  # noqa: E712
    if not proj or proj.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="项目不存在")
    if (proj.config or {}).get("mode") != "director":
        raise HTTPException(status_code=400, detail="仅导演模式项目支持手动新增剧集")

    ep = episode_crud.create_empty_episode(
        db, project_id=project_id, user_id=str(current_user.id),
        title=body.title or "", outline=body.outline or "",
    )
    db.commit()
    return success_response(data=EpisodeResponse.model_validate(ep))


@router.delete("/projects/{project_id}/episodes/{episode_id}")
def delete_episode(
    project_id: str,
    episode_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除剧集（软删，同时清理关联分镜）"""
    from app.models.project import Project

    proj = db.query(Project).filter(Project.id == project_id, Project.is_deleted == False).first()  # noqa: E712
    if not proj or proj.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="项目不存在")

    ep = episode_crud.get(id=episode_id, db=db)
    if not ep or ep.project_id != project_id:
        raise HTTPException(status_code=404, detail="剧集不存在")

    episode_crud.delete_episode(db, episode_id=episode_id)
    db.commit()
    return success_response(data={"ok": True, "episode_id": episode_id})


@router.patch("/projects/{project_id}/episodes/{episode_id}")
def update_episode(
    project_id: str,
    episode_id: str,
    body: EpisodeUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新剧集字段（仅导演模式项目支持）"""
    from app.models.project import Project

    proj = db.query(Project).filter(Project.id == project_id, Project.is_deleted == False).first()  # noqa: E712
    if not proj or proj.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="项目不存在")
    if (proj.config or {}).get("mode") != "director":
        raise HTTPException(status_code=400, detail="仅导演模式项目支持修改剧集")

    ep = episode_crud.get(id=episode_id, db=db)
    if not ep or ep.project_id != project_id:
        raise HTTPException(status_code=404, detail="剧集不存在")

    if body.title is not None:
        ep.title = body.title
    if body.outline is not None:
        ep.outline = body.outline

    db.add(ep)
    db.commit()
    db.refresh(ep)
    return success_response(data=EpisodeResponse.model_validate(ep))


@router.post("/projects/{project_id}/episodes/generate_episode_scripts")
def generate_episode_scripts(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """批量生成分集剧本 — 接口层按3集分组，每组触发独立 Celery 任务并发执行"""
    from app.models.project import Project
    from app.services.config_reader import ConfigReader

    proj = db.query(Project).filter(Project.id == project_id).first()
    if not proj or proj.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="项目不存在")

    pending = episode_crud.get_pending_episode_scripts(db, project_id)
    if not pending:
        return success_response(data={"total": 0, "episode_ids": [], "message": "无需生成"})

    # 标记为 generating
    for ep in pending:
        ep.episode_script_status = "generating"
    db.commit()

    # 序列化模型配置快照
    config_reader = ConfigReader(db)
    resolved = config_reader.get_project_config(str(current_user.id), proj.config)
    model_config = resolved.to_dict()

    # 按 3 集一批分组，每批触发独立 Celery 任务
    batch_size = 3
    total = len(pending)
    episode_numbers = [ep.episode_number for ep in pending]
    batch_count = -(-total // batch_size)  # ceil
    logger.info(
        "分集剧本生成调度: project_id=%s, 共 %d 集, 分 %d 批, 集号=%s",
        project_id, total, batch_count, episode_numbers,
    )
    from app.celery_tasks.episode_script import generate_episode_script_batch_task
    for i in range(0, total, batch_size):
        batch = pending[i:i + batch_size]
        batch_items = [
            {"episode_id": ep.id, "episode_number": ep.episode_number}
            for ep in batch
        ]
        generate_episode_script_batch_task.delay(
            project_id=project_id,
            user_id=str(current_user.id),
            batch_items=batch_items,
            batch_total=total,
            batch_index=i // batch_size + 1,
            model_config=model_config,
        )
        batch_count += 1

    return success_response(data={
        "total": total,
        "batch_count": batch_count,
        "episode_ids": [ep.id for ep in pending],
        "episode_numbers": episode_numbers,
    })


@router.post("/projects/{project_id}/episodes/{episode_id}/retry_episode_script")
def retry_episode_script(
    project_id: str,
    episode_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """重试单集剧本生成"""
    from app.models.project import Project
    from app.services.config_reader import ConfigReader

    episode = episode_crud.get(id=episode_id, db=db)
    if not episode or episode.project_id != project_id:
        raise HTTPException(status_code=404, detail="剧集不存在")
    if episode.episode_script_status not in ("failed",):
        raise HTTPException(status_code=400, detail="只能重试失败的剧集")

    episode.episode_script_status = "generating"
    db.commit()

    proj = db.query(Project).filter(Project.id == project_id).first()
    config_reader = ConfigReader(db)
    resolved = config_reader.get_project_config(str(current_user.id), proj.config)
    model_config = resolved.to_dict()

    from app.celery_tasks.episode_script import generate_episode_script_batch_task
    generate_episode_script_batch_task.delay(
        project_id=project_id,
        user_id=str(current_user.id),
        batch_items=[{"episode_id": episode_id, "episode_number": episode.episode_number}],
        batch_total=1,
        batch_index=1,
        model_config=model_config,
    )

    return success_response(data={"episode_id": episode_id, "status": "generating"})
