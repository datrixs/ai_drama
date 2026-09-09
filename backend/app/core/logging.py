import logging
import os
import sys

from loguru import logger

from app.core.config import settings


# backend目录
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# 日志存放目录
LOG_DIR = os.path.join(BACKEND_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# 移除默认配置
logger.remove()

HUMAN_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{module}.{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)

# 识别当前进程是否为 Celery Worker
is_celery = any("celery" in arg for arg in sys.argv)

# 协程模式下必须为 False 避开死锁；非 Celery 进程保持 True
use_enqueue = False if is_celery else True

# 控制台输出
logger.add(
    sys.stderr,
    format=HUMAN_FORMAT,
    level=settings.LOG_LEVEL,
    backtrace=True,
    diagnose=True,
)

# 公共应用日志
logger.add(
    os.path.join(LOG_DIR, "app_{time:YYYY-MM-DD}.log"),
    format=HUMAN_FORMAT,
    rotation="00:00",
    retention=settings.LOG_FILE_RETENTION,
    enqueue=use_enqueue,
    level=settings.LOG_LEVEL,
    backtrace=True,
    diagnose=True,
)

# 公共错误日志
logger.add(
    os.path.join(LOG_DIR, "error_{time:YYYY-MM-DD}.log"),
    format=HUMAN_FORMAT,
    rotation="00:00",
    retention=settings.LOG_FILE_RETENTION,
    enqueue=use_enqueue,
    level="ERROR",
    backtrace=True,
    diagnose=True,
)


# uvicorn 的标准 logging logger（access / websockets 协议层）不走 loguru，
# 需要单独加 filter，屏蔽 WebSocket 鉴权拒绝这类频繁但无价值的 INFO 日志。
class _WsAccessRejectFilter(logging.Filter):
    """过滤 uvicorn.access 中 WebSocket 鉴权失败（401/403）的请求日志。"""

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        if '"WebSocket ' in msg and msg.rstrip().endswith(("401", "403")):
            return False
        return True


class _WsProtocolRejectFilter(logging.Filter):
    """过滤 uvicorn websockets 协议层拒绝/关闭的 INFO 日志。"""

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        if msg.startswith("connection rejected") or msg == "connection closed":
            return False
        return True


# WebSocket 升级被拒（403/401）的日志走 uvicorn.error 而非 uvicorn.access：
# - uvicorn/protocols/websockets/{websockets_impl,wsproto_impl}.py 中
#   self.logger = logging.getLogger("uvicorn.error")，握手失败时打 `... "WebSocket ..." 403`
# - websockets 库的 `connection rejected` / `connection closed` 也通过该 logger 输出
# 因此 filter 必须挂到 uvicorn.error 才能生效。uvicorn.access 一并挂上以兼容普通 HTTP 路径。
logging.getLogger("uvicorn.access").addFilter(_WsAccessRejectFilter())
logging.getLogger("uvicorn.error").addFilter(_WsAccessRejectFilter())
logging.getLogger("uvicorn.error").addFilter(_WsProtocolRejectFilter())

__all__ = ["logger"]
