from loguru import logger

from app.core.celery import celery
from app.tasks.helpers import await_sync
from app.services import task as task_service
from app.services.llm import LLMError
from app.graphs.workflows import (
    create_design_character_graph,
    create_modify_character_graph,
    create_reference_to_character_graph,
    create_design_location_graph,
    create_modify_location_graph,
    create_modify_prop_graph,
)
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


@celery.task(bind=True, queue="text", max_retries=3)
def ai_design_character(self, task_id: str):
    graph = create_design_character_graph()
    result = await_sync(graph.ainvoke({"task_id": task_id}))
    _handle_graph_result(task_id, result, self)


@celery.task(bind=True, queue="text", max_retries=3)
def ai_modify_character(self, task_id: str):
    graph = create_modify_character_graph()
    result = await_sync(graph.ainvoke({"task_id": task_id}))
    _handle_graph_result(task_id, result, self)


@celery.task(bind=True, queue="text", max_retries=3)
def reference_to_character(self, task_id: str):
    graph = create_reference_to_character_graph()
    result = await_sync(graph.ainvoke({"task_id": task_id}))
    _handle_graph_result(task_id, result, self)


@celery.task(bind=True, queue="text", max_retries=3)
def ai_design_location(self, task_id: str):
    graph = create_design_location_graph()
    result = await_sync(graph.ainvoke({"task_id": task_id}))
    _handle_graph_result(task_id, result, self)


@celery.task(bind=True, queue="text", max_retries=3)
def ai_modify_location(self, task_id: str):
    graph = create_modify_location_graph()
    result = await_sync(graph.ainvoke({"task_id": task_id}))
    _handle_graph_result(task_id, result, self)


@celery.task(bind=True, queue="text", max_retries=3)
def ai_modify_prop(self, task_id: str):
    graph = create_modify_prop_graph()
    result = await_sync(graph.ainvoke({"task_id": task_id}))
    _handle_graph_result(task_id, result, self)
