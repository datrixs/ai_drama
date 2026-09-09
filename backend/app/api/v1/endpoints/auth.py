from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from redis import Redis
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_redis_client
from app.core.security import create_access_token
from app.schemas.auth import LogoutResponse, TokenResponse, UserCreate
from app.services.auth_service import AuthService
from app.services.user_service import UserService
from app.schemas.user import UserCreateSchema
from app.utils.response import success_response

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


@router.post("/register", status_code=201)
def register(
    user_in: UserCreateSchema,
    db: Session = Depends(get_db),
):
    user = UserService.create_user(db, user_in)
    return success_response(data=user)


@router.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
    redis_client: Redis = Depends(get_redis_client),
):
    data = AuthService.login(db, form_data.username, form_data.password, redis_client)
    return success_response(data=data)


@router.post("/token")
def auth_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
    redis_client: Redis = Depends(get_redis_client),
):
    """
    OAuth2 兼容的 Token 端点

    供 Swagger UI 的 Authorize 功能使用，返回标准 OAuth2 格式。
    与 /login 接口功能相同，仅响应格式不同。
    """
    data = AuthService.login(db, form_data.username, form_data.password, redis_client)
    return {
        "access_token": data.access_token,
        "token_type": data.token_type,
        "expires_at": data.expires_at.isoformat() if data.expires_at else None,
    }


@router.post("/logout")
def logout(
    token: str = Depends(oauth2_scheme),
    redis_client: Redis = Depends(get_redis_client),
):
    AuthService.logout(token, redis_client)
    return success_response()
