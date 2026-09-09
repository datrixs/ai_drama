"""无限画布 Celery 任务

每个 generate_canvas_* 任务接 generation_id + 用户 model_config 快照，
调用 services/canvas_generation.py 里的 process_* 函数实际跑生成。
"""
from app.core.celery import celery
from app.core.logging import logger
from app.db.session import SessionLocal
from app.services.canvas_generation import (
    dispatch_canvas_video_callback,
    finalize_canvas_video_assets,
    process_image_generation,
    process_text_generation,
    submit_canvas_video_task,
)


@celery.task(bind=True, name="canvas.generate_text", max_retries=0)
def generate_canvas_text(self, generation_id: str, model_config: dict):
    """文本节点生成任务"""
    db = SessionLocal()
    try:
        logger.info(f"[canvas-task] generate_text start gen={generation_id}")
        result = process_text_generation(db, generation_id, model_config)
        logger.info(f"[canvas-task] generate_text done gen={generation_id}")
        return result
    finally:
        db.close()


@celery.task(bind=True, name="canvas.generate_image", max_retries=0)
def generate_canvas_image(self, generation_id: str, model_config: dict):
    """图片节点生成任务"""
    db = SessionLocal()
    try:
        logger.info(f"[canvas-task] generate_image start gen={generation_id}")
        result = process_image_generation(db, generation_id, model_config)
        logger.info(f"[canvas-task] generate_image done gen={generation_id}")
        return result
    finally:
        db.close()


@celery.task(bind=True, name="canvas.generate_video", max_retries=0)
def generate_canvas_video(self, generation_id: str, model_config: dict):
    """视频节点生成任务：提交到 Seedance，结果由回调更新"""
    db = SessionLocal()
    try:
        logger.info(f"[canvas-task] generate_video submit start gen={generation_id}")
        result = submit_canvas_video_task(db, generation_id, model_config)
        logger.info(f"[canvas-task] generate_video submitted gen={generation_id}")
        return result
    finally:
        db.close()


@celery.task(bind=True, name="canvas.video_callback", max_retries=0)
def process_canvas_video_callback(self, callback_data: dict):
    """处理 Seedance 视频生成回调"""
    db = SessionLocal()
    try:
        logger.info(f"[canvas-task] video_callback: ark_task_id={callback_data.get('id')}")
        dispatch_canvas_video_callback(db, callback_data)
    finally:
        db.close()


@celery.task(
    bind=True,
    name="canvas.upload_video_assets",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    max_retries=3,
)
def upload_canvas_video_assets_task(self, generation_id: str):
    """异步：下载 canvas 源视频 → 上传 COS → 提取首帧 → 回写 → 二次推 WS"""
    db = SessionLocal()
    try:
        logger.info(f"[canvas-task] upload_assets start gen={generation_id}")
        finalize_canvas_video_assets(db, generation_id)
        logger.info(f"[canvas-task] upload_assets done gen={generation_id}")
    except Exception as e:
        logger.error(f"[canvas-task] upload_assets failed gen={generation_id}: {e}")
        raise
    finally:
        db.close()
