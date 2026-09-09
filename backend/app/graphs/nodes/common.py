import json

from loguru import logger

from app.graphs.states import BaseWorkflowState
from app.services import task as task_service
from app.enums import TaskStatus


def validate_task(state: BaseWorkflowState) -> dict:
    task = task_service.get_task(state["task_id"])
    if not task or task["status"] not in (TaskStatus.QUEUED, TaskStatus.PROCESSING):
        logger.debug(f"[Graph/validate_task] 任务无效: task_id={state['task_id']} task={'None' if not task else task.get('status')}")
        return {"status": "canceled"}

    payload = json.loads(task.get("payload", "{}"))
    config_snapshot = payload.get("config_snapshot", {})
    logger.debug(f"[Graph/validate_task] 任务验证通过: task_id={state['task_id']} user_id={task.get('user_id')} config_user_id={config_snapshot.get('user_id')} payload_keys={list(payload.keys())}")
    return {
        "payload": payload,
        "user_id": task.get("user_id", ""),
        "status": TaskStatus.PROCESSING,
        "progress": 10,
        "errors": [],
    }


def report_progress(state: BaseWorkflowState) -> dict:
    task_service.update_task_status(
        state["task_id"],
        state.get("status", TaskStatus.PROCESSING),
        state.get("progress", 0),
    )
    return {}


def handle_error(state: BaseWorkflowState) -> dict:
    errors = state.get("errors", [])
    if not errors:
        return {}

    last_error = errors[-1]
    error_msg = last_error.get("message", "未知错误")

    task_service.update_task_status(
        state["task_id"],
        TaskStatus.FAILED,
        0,
        error=error_msg,
    )

    _mark_entity_failed(state, error_msg)

    return {"status": TaskStatus.FAILED}


def _mark_entity_failed(state: dict, error_msg: str) -> None:
    payload = state.get("payload", {})
    if isinstance(payload, str):
        payload = json.loads(payload)
    asset_type = payload.get("type", "")
    asset_id = state.get("asset_id") or payload.get("id", "")
    user_id = state.get("user_id", "")
    if not asset_id:
        return

    from app.db.session import SessionLocal
    from app.core.ws import ws_manager

    try:
        with SessionLocal() as db:
            if asset_type == "character":
                from app.models.asset import GlobalCharacterAppearance
                appearance_index = state.get("appearance_index", payload.get("appearance_index", 0))
                entity = db.query(GlobalCharacterAppearance).filter(
                    GlobalCharacterAppearance.character_id == asset_id,
                    GlobalCharacterAppearance.appearance_index == appearance_index,
                    GlobalCharacterAppearance.is_deleted == False,
                ).first()
                if entity:
                    entity.gen_status = "failed"
                    db.commit()
                    ws_manager.publish_asset_hub_event(
                        user_id=user_id,
                        event_type="asset_hub_generation_failed",
                        data={"target_type": "appearance", "target_id": entity.id, "asset_type": "character", "error": error_msg},
                    )
            else:
                from app.models.asset import GlobalLocationImage
                generating_images = db.query(GlobalLocationImage).filter(
                    GlobalLocationImage.location_id == asset_id,
                    GlobalLocationImage.gen_status == "generating",
                    GlobalLocationImage.is_deleted == False,
                ).all()
                if generating_images:
                    for img in generating_images:
                        img.gen_status = "failed"
                    db.commit()
                    for img in generating_images:
                        ws_manager.publish_asset_hub_event(
                            user_id=user_id,
                            event_type="asset_hub_generation_failed",
                            data={"target_type": "location_image", "target_id": img.id, "asset_type": asset_type, "error": error_msg},
                        )
    except Exception:
        logger.warning(f"标记实体失败状态异常 asset_id={asset_id}")


def finalize_result(state: BaseWorkflowState) -> dict:
    result_data = state.get("result_data", {})
    task_service.update_task_status(
        state["task_id"],
        TaskStatus.COMPLETED,
        100,
        result=json.dumps(result_data, ensure_ascii=False),
    )
    return {"status": TaskStatus.COMPLETED, "progress": 100}


def human_review_gate(state: BaseWorkflowState) -> dict:
    # 预留：needs_human_review=True 时通过 LangGraph interrupt 暂停
    # 当前实现直接通过
    return {}


def should_finalize(state: BaseWorkflowState) -> str:
    errors = state.get("errors", [])
    if errors:
        last_error = errors[-1]
        if not last_error.get("retryable", False):
            return "handle_error"
    if state.get("status") == TaskStatus.FAILED:
        return "handle_error"
    if state.get("status") == TaskStatus.CANCELED:
        return "__end__"
    return "finalize_result"
