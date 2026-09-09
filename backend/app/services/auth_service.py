from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from redis import Redis
from sqlalchemy.orm import Session

from app import crud
from app.core.config import settings
from app.core.logging import logger
from app.core.security import (
    create_access_token,
    decode_token,
    verify_password,
)
from app.models.user import User
from app.schemas.auth import LogoutResponse, TokenResponse


class AuthService:
    """
    认证服务
    """

    @staticmethod
    def authenticate_user(db: Session, username: str, password: str) -> User:
        """
        用户认证
        """
        user = crud.user_crud.get_by_username(username=username, db=db)

        if not user:
            logger.error(f"用户名不存在，用户输入用户名：{username}，密码：{password}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误",
            )

        if user.status != "enable":
            logger.error(f"账户已被禁用，用户输入用户名：{username}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="账户已被禁用",
            )

        if not verify_password(password, user.password_hash):
            logger.error(f"用户名或密码错误，用户输入用户名：{username}，密码：{password}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误",
            )

        return user

    @staticmethod
    def login(db: Session, username: str, password: str, redis_client: Redis) -> TokenResponse:
        user = AuthService.authenticate_user(db, username, password)

        access_token = create_access_token(subject=user.id)

        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        )

        # 初始化 Redis 会话：滑动过期，TTL = SESSION_IDLE_TIMEOUT_MINUTES
        session_key = f"user:{user.id}:session_active"
        redis_client.set(
            session_key,
            "1",
            ex=settings.SESSION_IDLE_TIMEOUT_MINUTES * 60,
        )

        logger.success(f"用户登录成功，用户ID：{user.id}")
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_at=expires_at,
        )

    @staticmethod
    def logout(token: str, redis_client: Redis) -> LogoutResponse:
        try:
            payload = decode_token(token)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的令牌",
            )

        user_id = payload.get("sub")
        if user_id:
            redis_client.delete(f"user:{user_id}:session_active")

        return LogoutResponse()
