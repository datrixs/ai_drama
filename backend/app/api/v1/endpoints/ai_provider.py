"""
AI供应商相关接口

GET /ai-providers           获取所有供应商列表
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.crud.ai_provider import ai_provider_crud
from app.utils.response import success_response

router = APIRouter()


@router.get("")
def list_ai_providers(
    db: Session = Depends(get_db),
):
    """
    获取所有模型供应商列表

    返回格式：
    [
        {
            "id": "provider_id",
            "name": "供应商名称",
            "code": "供应商编码",
            "label": "供应商名称（用于前端显示）",
            "value": "供应商编码（用于前端选项值）"
        }
    ]
    """
    providers = ai_provider_crud.get_provider_list(db)
    result = []
    for p in providers:
        result.append({
            "id": p.id,
            "name": p.name,
            "code": p.code,
            "label": p.name,
            "value": p.code,
        })
    return success_response(data=result)
