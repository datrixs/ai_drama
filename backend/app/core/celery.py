from celery import Celery
from celery.signals import worker_init

from app.core.config import settings

celery = Celery(
    "async_task",
    broker=settings.CELERY_BROKER,
    backend=settings.CELERY_BACKEND,
    include=[
        "app.celery_tasks.story_analysis",
        "app.celery_tasks.log_flush",
        "app.celery_tasks.project_asset_image",
        "app.celery_tasks.episode_script",
        "app.tasks.text_tasks",
        "app.tasks.image_tasks",
        "app.tasks.audio_tasks",
        "app.celery_tasks.asset_sync",
        "app.celery_tasks.video_generation",
        "app.celery_tasks.short_video_gen",
        "app.celery_tasks.membership_tasks",
        "app.celery_tasks.video_super_res_gen",
        "app.celery_tasks.canvas_generation",
        ],
)

celery.conf.update(
    {
        # --- 数据库 ---
        "beat_dburi": str(settings.SYNC_DATABASE_URI),
        # --- 序列化 ---
        "task_serializer": "json",
        "result_serializer": "json",
        "accept_content": ["json"],
        # --- 时区 ---
        "timezone": "Asia/Shanghai",
        "enable_utc": True,
        # --- 任务执行 ---
        "task_track_started": True,
        "task_acks_late": True,
        "task_reject_on_worker_lost": True,
        "worker_prefetch_multiplier": 1,
        "worker_max_tasks_per_child": 1000,
        # --- 结果过期 ---
        "result_expires": 3600,
        # --- 队列 ---
        "task_default_queue": "default",
        "task_queues": {
            "default": {},
            "text": {},
            "image": {},
            "audio": {},
            "log_llm_call": {},
        },
        # "worker_pool": "solo",
        # --- 重试策略 ---
        # "task_default_max_retries": 5,
        # "task_retry_backoff": True,
        # "task_retry_backoff_max": 600,
        # "task_retry_jitter": True,
        # --- Beat 定时任务 ---
        "beat_schedule": {
            "flush-model-call-log": {
                "task": "log.flush_model_call_log",
                "schedule": settings.LOG_FLUSH_INTERVAL,
                "options": {"expires": settings.LOG_FLUSH_INTERVAL * 2},
            },
            "grant-monthly-points": {
                "task": "membership.grant_monthly_points",
                "schedule": 1200,
                "options": {"expires": 3600},
            },
            "membership-expire-check": {
                "task": "membership.expire_check",
                "schedule": 600,
                "options": {"expires": 1800},
            },
            "pay-order-timeout-check": {
                "task": "pay_order.timeout_check",
                "schedule": 600,
                "options": {"expires": 1800},
            },
        },
    }
)

celery.autodiscover_tasks()


@worker_init.connect
def _patch_psycopg_on_worker_init(**kwargs):
    """worker 启动时把 psycopg2 协程化(仅 gevent 池),消除 FOR UPDATE 等锁阻塞 hub 的自死锁。
       prefork/solo 是进程/线程模型,psycopg2 阻塞不影响其它任务,无需 patch。
    """
    import gevent.monkey
    if not gevent.monkey.is_module_patched("socket"):
        return
        
    from psycogreen.gevent import patch_psycopg
    patch_psycopg()
    print("[celery] gevent 池: psycopg2 已协程化(psycogreen)")


"""
启动命令: 
Windows: celery -A ceelery worker --loglevel=info -E -n worker1.%h
Linux/Mac: celery -A app.celery_tasks.ceelery worker --loglevel=INFO
"""