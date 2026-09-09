from datetime import timedelta
from typing import Generator

import redis
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt import DecodeError, ExpiredSignatureError, MissingRequiredClaimError
from redis import Redis
from sqlalchemy.orm import Session

from app import crud
from app.core.config import settings
from app.core.security import decode_token
from app.db.session import SessionLocal
from app.models.user import User


reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_PREFIX}/auth/token"
)


def get_db() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session


def get_redis_client() -> Redis:
    """
    获取Redis连接
    """
    redis_client = redis.Redis.from_url(
        f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}",
        max_connections=10,
        decode_responses=True,
    )
    return redis_client


def get_current_user(
    access_token: str = Depends(reusable_oauth2),
    redis_client: Redis = Depends(get_redis_client),
    db: Session = Depends(get_db),
) -> User:
    """
    获取当前登录用户对象（JWT 鉴权 + Redis 会话校验 + 滑动续期 + 用户状态检查）
    """
    try:
        payload = decode_token(access_token)
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="您的Token已过期，请重新登录",
        )
    except DecodeError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token解码错误，请检查请求参数",
        )
    except MissingRequiredClaimError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="您的Token缺少必填字段，请联系管理员",
        )

    user_id = payload["sub"]

    # 会话滑动续期：Redis 中 session_active 作为权威，EXISTS 判活，EXPIRE 续期
    session_key = f"user:{user_id}:session_active"
    if not redis_client.exists(session_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="会话已过期，请重新登录",
        )
    redis_client.expire(
        session_key,
        timedelta(minutes=settings.SESSION_IDLE_TIMEOUT_MINUTES),
    )

    user: User | None = crud.user_crud.get(id=user_id, db=db)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if user.status != "enable":
        raise HTTPException(status_code=400, detail="用户已禁用")

    return user
