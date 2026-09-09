import json
import os
import sys
from typing import Optional

from loguru import logger

from app.core.config import settings
from app.core.logging import LOG_DIR, HUMAN_FORMAT

_project_sinks: dict[str, list[int]] = {}

# 识别当前进程是否为 Celery Worker
is_celery = any("celery" in arg for arg in sys.argv)

# 协程模式下必须为 False 避开死锁；非 Celery 进程保持 True
use_enqueue = False if is_celery else True


def get_project_logger(project_id: str) -> "ProjectLogger":
    return ProjectLogger(project_id)


class ProjectLogger:
    """项目日志管理器"""

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.project_dir = os.path.join(LOG_DIR, "projects", project_id)
        os.makedirs(self.project_dir, exist_ok=True)

        if project_id not in _project_sinks:
            self._register_sinks()

    def _register_sinks(self):
        prefix = f"[project:{self.project_id}]"
        sink_ids = []

        # project.log
        sink_id = logger.add(
            os.path.join(self.project_dir, "project.log"),
            format=HUMAN_FORMAT,
            rotation=settings.LOG_FILE_MAX_SIZE,
            retention=settings.LOG_FILE_RETENTION,
            compression="zip",
            enqueue=use_enqueue,
            level="INFO",
            filter=lambda record: prefix in record["message"],
        )
        sink_ids.append(sink_id)

        # task.log
        sink_id = logger.add(
            os.path.join(self.project_dir, "task.log"),
            format=HUMAN_FORMAT,
            rotation=settings.LOG_FILE_MAX_SIZE,
            retention=settings.LOG_FILE_RETENTION,
            compression="zip",
            enqueue=use_enqueue,
            level="INFO",
            filter=lambda record: f"[task:" in record["message"] and prefix in record["message"],
        )
        sink_ids.append(sink_id)

        # model_call.log
        sink_id = logger.add(
            os.path.join(self.project_dir, "model_call.log"),
            format=HUMAN_FORMAT,
            rotation=settings.LOG_FILE_MAX_SIZE,
            retention=settings.LOG_FILE_RETENTION,
            compression="zip",
            enqueue=use_enqueue,
            level="INFO",
            filter=lambda record: record["extra"].get("log_type") == "model_call"
                                  and prefix in record["message"],
        )
        sink_ids.append(sink_id)

        _project_sinks[self.project_id] = sink_ids

    def info(self, msg: str, **kwargs):
        logger.bind(**kwargs).info(f"[project:{self.project_id}] {msg}")

    def error(self, msg: str, **kwargs):
        logger.bind(**kwargs).error(f"[project:{self.project_id}] {msg}")

    def warning(self, msg: str, **kwargs):
        logger.bind(**kwargs).warning(f"[project:{self.project_id}] {msg}")

    def task_log(self, task_id: str, task_type: str, msg: str, **kwargs):
        logger.bind(**kwargs).info(
            f"[project:{self.project_id}] [task:{task_id}] [{task_type}] {msg}"
        )

    def model_call(self, msg: str, detail: dict):
        """记录模型调用日志（人类可读，详细JSON在message字段）"""
        detail_json = json.dumps(detail, ensure_ascii=False, default=str)
        logger.bind(log_type="model_call").info(
            f"[project:{self.project_id}] {msg} detail={detail_json}"
        )
