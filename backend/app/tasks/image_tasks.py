from app.core.celery import celery
from app.tasks.helpers import await_sync
from app.services import task as task_service
from app.services.llm import LLMError
from app.graphs.workflows import create_generate_image_graph, create_modify_image_graph
from app.enums import TaskStatus

from app.core.logging import logger


@celery.task(bind=True, queue="image", max_retries=3)
def generate_image(self, task_id: str):
    logger.debug(f"[Celery/generate_image] 任务开始: task_id={task_id}")
    graph = create_generate_image_graph()
    result = await_sync(graph.ainvoke({"task_id": task_id}))
    logger.debug(f"[Celery/generate_image] 任务完成: task_id={task_id} result_keys={list(result.keys()) if result else 'None'}")

    errors = result.get("errors", [])
    if errors:
        last_error = errors[-1]
        if last_error.get("retryable") and self.request.retries < self.max_retries:
            task_service.update_task_status(
                task_id, TaskStatus.PROCESSING, 0,
                error=f"重试中({self.request.retries+1}/{self.max_retries}): {last_error['message']}",
            )
            raise self.retry(
                exc=LLMError(last_error["message"], retryable=True),
                countdown=5 * (2 ** self.request.retries),
            )


@celery.task(bind=True, queue="image", max_retries=3)
def modify_image(self, task_id: str):
    graph = create_modify_image_graph()
    result = await_sync(graph.ainvoke({"task_id": task_id}))

    errors = result.get("errors", [])
    if errors:
        last_error = errors[-1]
        if last_error.get("retryable") and self.request.retries < self.max_retries:
            task_service.update_task_status(
                task_id, TaskStatus.PROCESSING, 0,
                error=f"重试中({self.request.retries+1}/{self.max_retries}): {last_error['message']}",
            )
            raise self.retry(
                exc=LLMError(last_error["message"], retryable=True),
                countdown=5 * (2 ** self.request.retries),
            )
