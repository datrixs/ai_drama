from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

from app.core.config import settings


# 数据库连接池配置
engine_setting: dict = {
    "url": settings.SYNC_DATABASE_URI,
    "pool_pre_ping": True,
    "echo": False,
    "echo_pool": False,
    "poolclass": QueuePool,
    "pool_size": settings.DB_POOL_SIZE,
    "pool_recycle": 360,
    "pool_timeout": 60,
    "max_overflow": settings.DB_MAX_OVERFLOW,
    "pool_reset_on_return": "rollback",
}

engine = create_engine(**engine_setting)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)
