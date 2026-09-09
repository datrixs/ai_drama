"""
数据字典 接口
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models import User
from app.services import SysDictService
from app.utils.response import success_response

router = APIRouter()


@router.get("")
def get_user_api_config(
    dict_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取当前用户API配置

    API Key 字段脱敏返回
    """
    data = SysDictService.get_item_list(db=db, dict_name=dict_name)
    return success_response(data=data)
