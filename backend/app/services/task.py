import json
import uuid
from datetime import datetime

import redis

from app.core.logging import logger
from app.core.config import settings
from app.enums import TaskStatus, TaskType


_redis_client = None


def get_redis():
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD or None,
            db=settings.REDIS_DB,
            decode_responses=True,
        )
    return _redis_client


TASK_KEY_PREFIX = "task:"


def create_task_record(
    task_id: str,
    task_type: str,
    user_id: str,
    target_type: str | None = None,
    target_id: str | None = None,
    payload: dict | None = None,
) -> dict:
    r = get_redis()
    task = {
        "id": task_id,
        "type": task_type,
        "status": TaskStatus.QUEUED,
        "progress": 0,
        "user_id": user_id,
        "target_type": target_type or "",
        "target_id": target_id or "",
        "payload": json.dumps(payload or {}),
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "result": "",
        "error": "",
    }
    r.hset(f"{TASK_KEY_PREFIX}{task_id}", mapping=task)
    return task


def update_task_status(task_id: str, status: str, progress: int = 0, result: str = "", error: str = ""):
    r = get_redis()
    updates = {
        "status": status,
        "progress": progress,
        "updated_at": datetime.now().isoformat(),
    }
    if result:
        updates["result"] = result
    if error:
        updates["error"] = error
    r.hset(f"{TASK_KEY_PREFIX}{task_id}", mapping=updates)


def get_task(task_id: str) -> dict | None:
    r = get_redis()
    data = r.hgetall(f"{TASK_KEY_PREFIX}{task_id}")
    if not data:
        return None
    return data


def submit_task(
    task_type: str,
    user_id: str,
    payload: dict,
    target_type: str | None = None,
    target_id: str | None = None,
    dedupe_key: str | None = None,
) -> dict:
    from app.core.celery import celery

    task_id = str(uuid.uuid4())
    if dedupe_key:
        r = get_redis()
        existing_id = r.get(f"dedupe:{dedupe_key}")
        if existing_id:
            existing_task = get_task(existing_id)
            if existing_task and existing_task["status"] in (TaskStatus.QUEUED, TaskStatus.PROCESSING):
                return {"task_id": existing_id, "status": "deduped", "async": True}
        r.setex(f"dedupe:{dedupe_key}", 3600, task_id)

    create_task_record(
        task_id=task_id,
        task_type=task_type,
        user_id=user_id,
        target_type=target_type,
        target_id=target_id,
        payload=payload,
    )

    queue = _route_queue(task_type)
    task_name = _get_celery_task_name(task_type)
    logger.debug(f"[submit_task] 发送 Celery 任务: task_id={task_id} task_name={task_name} queue={queue} task_type={task_type}")
    celery.send_task(
        task_name,
        kwargs={"task_id": task_id},
        queue=queue,
        task_id=task_id,
    )
    return {"task_id": task_id, "status": TaskStatus.QUEUED, "async": True}


def _route_queue(task_type: str) -> str:
    IMAGE_TYPES = {
        TaskType.ASSET_HUB_IMAGE,
        TaskType.ASSET_HUB_MODIFY,
        TaskType.PROJECT_ASSET_GENERATE,
        TaskType.PROJECT_ASSET_BATCH_GENERATE,
        TaskType.PROJECT_ASSET_MODIFY_IMAGE,
        TaskType.PROJECT_ASSET_REFERENCE_GENERATE,
    }
    AUDIO_TYPES = {
        TaskType.ASSET_HUB_VOICE_DESIGN,
    }
    if task_type in IMAGE_TYPES:
        return "image"
    if task_type in AUDIO_TYPES:
        return "audio"
    return "text"


def _get_celery_task_name(task_type: str) -> str:
    mapping = {
        TaskType.ASSET_HUB_AI_DESIGN_CHARACTER: "app.tasks.text_tasks.ai_design_character",
        TaskType.ASSET_HUB_AI_MODIFY_CHARACTER: "app.tasks.text_tasks.ai_modify_character",
        TaskType.ASSET_HUB_REFERENCE_TO_CHARACTER: "app.tasks.text_tasks.reference_to_character",
        TaskType.ASSET_HUB_IMAGE: "app.tasks.image_tasks.generate_image",
        TaskType.ASSET_HUB_MODIFY: "app.tasks.image_tasks.modify_image",
        TaskType.ASSET_HUB_AI_DESIGN_LOCATION: "app.tasks.text_tasks.ai_design_location",
        TaskType.ASSET_HUB_AI_MODIFY_LOCATION: "app.tasks.text_tasks.ai_modify_location",
        TaskType.ASSET_HUB_AI_MODIFY_PROP: "app.tasks.text_tasks.ai_modify_prop",
        TaskType.PROJECT_ASSET_GENERATE: "app.celery_tasks.project_asset_image.generate_project_asset_image",
        TaskType.PROJECT_ASSET_BATCH_GENERATE: "app.celery_tasks.project_asset_image.batch_generate_project_assets",
        TaskType.PROJECT_ASSET_MODIFY_IMAGE: "app.celery_tasks.project_asset_image.modify_project_asset_image",
        TaskType.PROJECT_ASSET_REFERENCE_GENERATE: "app.celery_tasks.project_asset_image.reference_generate_project_character",
        TaskType.ASSET_HUB_VOICE_DESIGN: "app.tasks.audio_tasks.ai_voice_design",
    }
    if task_type not in mapping:
        raise ValueError(f"未知的任务类型: {task_type}")
    return mapping[task_type]
