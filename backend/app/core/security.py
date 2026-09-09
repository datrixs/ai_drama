from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt
from cryptography.fernet import Fernet

from app.core.config import settings

_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    """
    获取Fernet加密对象

    从 SECRET_KEY 通过 SHA256 派生 32 字节密钥，
    再 base64 编码为 Fernet 所需的 url-safe 格式
    """
    global _fernet
    if _fernet is None:
        import base64
        import hashlib
        derived = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
        fernet_key = base64.urlsafe_b64encode(derived)
        _fernet = Fernet(fernet_key)
    return _fernet


def create_access_token(subject: str | Any, expires_delta: timedelta = None) -> str:
    """
    创建访问令牌
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode = {"exp": expire, "sub": str(subject), "type": "access"}

    return jwt.encode(
        payload=to_encode,
        key=settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def create_refresh_token(subject: str | Any, expires_delta: timedelta = None) -> str:
    """
    创建刷新令牌
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.JWT_REFRESH_TOKEN_EXPIRE_MINUTES
        )
    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}

    return jwt.encode(
        payload=to_encode,
        key=settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_token(token: str) -> dict[str, Any]:
    """
    解码JWT令牌
    """
    return jwt.decode(
        jwt=token,
        key=settings.SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )


def verify_password(plain_password: str | bytes, hashed_password: str | bytes) -> bool:
    """
    验证密码是否匹配
    """
    if isinstance(plain_password, str):
        plain_password = plain_password.encode()
    if isinstance(hashed_password, str):
        hashed_password = hashed_password.encode()

    return bcrypt.checkpw(plain_password, hashed_password)


def get_password_hash(plain_password: str | bytes) -> str:
    """
    获取密码的哈希值
    """
    if isinstance(plain_password, str):
        plain_password = plain_password.encode()

    return bcrypt.hashpw(plain_password, bcrypt.gensalt()).decode()


def get_data_encrypt(data) -> str:
    """
    对数据进行加密
    """
    data = _get_fernet().encrypt(data)
    return data.decode()


def get_content(variable: str) -> str:
    """
    对数据进行解密
    """
    return _get_fernet().decrypt(variable.encode()).decode()
