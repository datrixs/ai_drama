from app.core.celery import celery
from loguru import logger

from app.core.model_call_log_writer import model_call_log_writer


@celery.task(name="log.flush_model_call_log", queue="log_llm_call")
def flush_model_call_log():
    """定时从 Redis 缓冲区批量写入 model_call_log 表"""
    count = model_call_log_writer.flush_to_db()
    if count > 0:
        logger.info(f"模型调用日志刷写完成 count={count}")
