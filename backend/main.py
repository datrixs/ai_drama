from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from app.core.config import settings
from app.api.v1.api import api_router
from app.core.logging import logger
from starlette.middleware.cors import CORSMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI生命周期函数
    """
    logger.info("应用启动中...")
    logger.info(f"应用启动成功 - {settings.APP_NAME} v{settings.API_VERSION}")
    yield
    logger.info("应用关闭中...")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.API_VERSION,
    docs_url='/docs',
    lifespan=lifespan,
)


if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix=settings.API_PREFIX)


if __name__ == "__main__":
    uvicorn.run(
        app="main:app",
        host="0.0.0.0",
        reload=True,
        use_colors=True,
    )
