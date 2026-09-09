"""
用户API配置接口

GET  /           获取当前用户的API配置
PUT  /           更新当前用户的API配置
POST /           创建用户API配置
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models import User
from app.schemas.user_api_config import (
    UserApiConfigCreateSchema,
    UserApiConfigUpdateSchema,
    ConnectModelTestSchema,
)
from app.services.user_api_config_service import UserApiConfigService
from app.utils.response import success_response, error_response

router = APIRouter()


@router.get("")
def get_user_api_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取当前用户API配置

    API Key 字段脱敏返回
    """
    data = UserApiConfigService.get_by_user_id(db, current_user.id)
    return success_response(data=data)


@router.put("")
def update_user_api_config(
    config_in: UserApiConfigUpdateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    更新当前用户API配置

    apiKey 三态更新：
    - 不传 → 保留原值
    - 空字符串 → 删除
    - 非空字符串 → 加密覆盖
    """
    data = UserApiConfigService.update(db, current_user.id, config_in)
    return success_response(data=data)


@router.post("/connect")
def connect_model_test(
    param_in: ConnectModelTestSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    连接模型测试接口

    发送最小化请求验证指定厂商的 API Key 和网络连通性。
    provider_code 必须为 ai_provider 表中预定义的供应商编号。
    """
    result = UserApiConfigService.connect_to_provider(
        db, current_user.id, param_in.provider_code
    )
    if result["success"]:
        return success_response(data=result)
    return error_response(msg="连接测试失败", data=result)