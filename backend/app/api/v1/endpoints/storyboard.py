"""分镜片段 API 端点"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.crud.episode_concat_record_crud import episode_concat_record_crud
from app.crud.storyboard_crud import storyboard_crud
from app.models import User
from app.schemas.storyboard import (
    StoryboardCreate,
    StoryboardUpdate,
    StoryboardShotsUpdate,
    StoryboardReorderRequest,
    StoryboardInsertRequest,
    StoryboardVideoGenerateRequest,
    StoryboardResponse,
    StoryboardListResponse,
)
from app.utils.response import success_response
from app.utils.tencent_cos_utils import cos_client

router = APIRouter()


@router.get("/projects/{project_id}/episodes/{episode_id}/storyboards")
def get_storyboards(
    project_id: str,
    episode_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取剧集的分镜片段列表"""
    segments = storyboard_crud.get_by_episode(db, episode_id)
    items = [StoryboardResponse.model_validate(s) for s in segments]

    # 附带整集成片信息：取最新一条合成记录（不再读 Episode 表）
    episode_video_url = None
    episode_concat_status = None
    latest = episode_concat_record_crud.get_latest_by_episode(db, episode_id)
    if latest:
        episode_concat_status = latest.status
        if latest.result_video_url:
            key = cos_client.url_to_key(latest.result_video_url) or latest.result_video_url
            episode_video_url = cos_client.key_to_url(key)

    return success_response(data=StoryboardListResponse(
        items=items,
        total=len(items),
        episode_video_url=episode_video_url,
        episode_concat_status=episode_concat_status,
    ))


@router.post("/projects/{project_id}/episodes/{episode_id}/storyboards")
def create_storyboard(
    project_id: str,
    episode_id: str,
    body: StoryboardCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建分镜片段"""
    # 检查序号是否冲突
    existing = storyboard_crud.get_by_segment_index(db, episode_id, body.segment_index)
    if existing:
        raise HTTPException(status_code=409, detail=f"片段序号 {body.segment_index} 已存在")

    data = body.model_dump(exclude_unset=True)
    data["episode_id"] = episode_id
    data["create_uid"] = current_user.id
    from app.models.project_asset import Storyboard as StoryboardModel
    from uuid import uuid4
    data["id"] = str(uuid4())
    segment = StoryboardModel(**data)
    db.add(segment)
    db.commit()
    db.refresh(segment)
    return success_response(data=StoryboardResponse.model_validate(segment))


@router.put("/projects/{project_id}/storyboards/{storyboard_id}")
def update_storyboard(
    project_id: str,
    storyboard_id: str,
    body: StoryboardUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新分镜片段"""
    segment = storyboard_crud.get(id=storyboard_id, db=db)
    if not segment or segment.is_deleted:
        raise HTTPException(status_code=404, detail="片段不存在")

    data = body.model_dump(exclude_unset=True, exclude_none=True)
    for key, value in data.items():
        setattr(segment, key, value)
    segment.update_uid = current_user.id
    db.commit()
    db.refresh(segment)
    return success_response(data=StoryboardResponse.model_validate(segment))


@router.delete("/projects/{project_id}/storyboards/{storyboard_id}")
def delete_storyboard(
    project_id: str,
    storyboard_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除分镜片段（软删除），并把剩余片段重排为 1..N"""
    try:
        segment = storyboard_crud.soft_delete_and_reorder(db, storyboard_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if segment is None:
        raise HTTPException(status_code=404, detail="片段不存在")

    db.commit()
    return success_response(msg="删除成功")


@router.put("/projects/{project_id}/storyboards/{storyboard_id}/shots")
def update_storyboard_shots(
    project_id: str,
    storyboard_id: str,
    body: StoryboardShotsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新片段的 shots 数据"""
    segment = storyboard_crud.get(id=storyboard_id, db=db)
    if not segment or segment.is_deleted:
        raise HTTPException(status_code=404, detail="片段不存在")

    segment.shots = [s.model_dump() for s in body.shots]
    segment.update_uid = current_user.id
    db.commit()
    db.refresh(segment)
    return success_response(data=StoryboardResponse.model_validate(segment))


@router.put("/projects/{project_id}/episodes/{episode_id}/storyboards/reorder")
def reorder_storyboards(
    project_id: str,
    episode_id: str,
    body: StoryboardReorderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """重排片段顺序"""
    storyboard_crud.reorder_segments(db, episode_id, body.segment_ids)
    db.commit()
    return success_response(msg="排序成功")


@router.post("/projects/{project_id}/episodes/{episode_id}/storyboards/insert")
def insert_storyboard(
    project_id: str,
    episode_id: str,
    body: StoryboardInsertRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """在锚点片段前/后插入一条空白片段"""
    if body.position not in ("before", "after"):
        raise HTTPException(status_code=400, detail="position 必须为 before 或 after")

    try:
        new_segment = storyboard_crud.insert_segment(
            db,
            episode_id=episode_id,
            anchor_segment_id=body.anchor_segment_id,
            position=body.position,
            create_uid=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    db.commit()
    db.refresh(new_segment)
    return success_response(data=StoryboardResponse.model_validate(new_segment))


@router.post("/projects/{project_id}/storyboards/{storyboard_id}/generate-video")
def generate_storyboard_video(
    project_id: str,
    storyboard_id: str,
    body: StoryboardVideoGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """触发票段视频生成（直接操作 Storyboard，由 Celery 异步执行）"""
    segment = storyboard_crud.get(id=storyboard_id, db=db)
    if not segment or segment.is_deleted:
        raise HTTPException(status_code=404, detail="片段不存在")

    # 将编辑器当前文本保存到 video_prompt（用作 Seedance prompt）
    if body.text_prompt is not None:
        segment.video_prompt = body.text_prompt
        segment.update_uid = current_user.id

    generation_options = {
        "resolution": body.resolution,
        "ratio": body.ratio,
        "duration": body.duration,
        "generate_audio": body.generate_audio,
        "first_frame_url": body.first_frame_url,
        "last_frame_url": body.last_frame_url,
        "video_generation_mode": body.video_generation_mode,
    }

    db.commit()

    # 触发 Celery 任务
    from app.celery_tasks.video_generation import generate_single_video_task
    generate_single_video_task.delay(storyboard_id, generation_options, body.model)

    return success_response(data={"task_id": storyboard_id, "status": "video_generating"})
