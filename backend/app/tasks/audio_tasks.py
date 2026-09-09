from loguru import logger

from app.core.celery import celery
from app.tasks.helpers import await_sync
from app.services import task as task_service
from app.services.llm import LLMError
from app.graphs.workflows import create_voice_design_graph
from app.enums import TaskStatus


def _handle_graph_result(task_id: str, result: dict, task_fn) -> None:
    errors = result.get("errors", [])
    if not errors:
        return

    last_error = errors[-1]
    if last_error.get("retryable") and task_fn.request.retries < task_fn.max_retries:
        task_service.update_task_status(
            task_id, TaskStatus.PROCESSING, 0,
            error=f"重试中({task_fn.request.retries+1}/{task_fn.max_retries}): {last_error['message']}",
        )
        raise task_fn.retry(
            exc=LLMError(last_error["message"], retryable=True),
            countdown=5 * (2 ** task_fn.request.retries),
        )


@celery.task(bind=True, queue="audio", max_retries=1)
def ai_voice_design(self, task_id: str):
    logger.info(f"[AudioTask] ai_voice_design 开始: task_id={task_id}")
    graph = create_voice_design_graph()
    result = await_sync(graph.ainvoke({"task_id": task_id}))
    _handle_graph_result(task_id, result, self)
    logger.info(f"[AudioTask] ai_voice_design 完成: task_id={task_id}")
