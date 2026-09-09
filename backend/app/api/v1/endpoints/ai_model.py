"""
AI模型相关接口

GET /models           获取所有模型列表（按供应商分组）
GET /models/text      获取文本模型列表
GET /models/image     获取图像模型列表
GET /models/video     获取视频模型列表
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models import User
from app.models.ai_model import AIModel, AIProvider
from app.services.config_reader import ConfigReader
from app.utils.response import success_response

router = APIRouter()


# 系统 provider code → ResolvedConfig 中的 API Key 字段名
# （覆盖 DB 中常见的 provider code 写法）
_PROVIDER_APIKEY_FIELD = {
    "volcengine": "ark_api_key",
    "dashscope": "qwen_api_key",
    "Ali": "qwen_api_key",
    "Google": "google_api_key",
    "FAL": "fal_api_key",
    "chatgpt": "jd_api_key",
    "JD": "jd_api_key",
    "deepseek": "jd_api_key",
}


def _provider_has_api_key(resolved, provider_code: str) -> bool:
    """判断指定 provider 在当前用户配置下是否有可用 API Key

    两条路径任一命中即可：
    1. 系统 provider 走独立字段（ark_api_key / jd_api_key 等）
    2. custom_providers 中存在该 code 且 api_key 非空
    """
    if not provider_code:
        return False
    field = _PROVIDER_APIKEY_FIELD.get(provider_code)
    if field and getattr(resolved, field, None):
        return True
    p = resolved.find_provider_by_code(provider_code)
    if p and p.get("api_key"):
        return True
    return False


@router.get("")
def list_models(
    model_type: str = Query(default=None, description="模型类型筛选：text / image / video"),
    db: Session = Depends(get_db),
):
    """
    获取模型列表，按供应商分组

    返回格式：
    [
        {
            "provider": { "id", "name", "code" },
            "models": [
                { "id", "name", "model_name", "model_type", "base_url" }
            ]
        }
    ]
    """
    query = db.query(AIModel)
    if model_type:
        query = query.filter(AIModel.model_type == model_type)

    models = query.all()
    provider_ids = list(set(m.provider_id for m in models))
    providers = db.query(AIProvider).filter(AIProvider.id.in_(provider_ids)).all()
    provider_map = {p.id: p for p in providers}

    grouped = {}
    for m in models:
        pid = m.provider_id
        if pid not in grouped:
            provider = provider_map.get(pid)
            grouped[pid] = {
                "provider": {
                    "id": provider.id,
                    "name": provider.name,
                    "code": provider.code,
                } if provider else None,
                "models": [],
            }
        grouped[pid]["models"].append({
            "id": m.id,
            "name": m.name,
            "model_name": m.model_name,
            "model_type": m.model_type,
            "base_url": m.base_url,
        })

    return success_response(data=list(grouped.values()))


@router.get("/flat")
def list_models_flat(
    model_type: str = Query(default=None, description="模型类型筛选：text / image / video"),
    model_provider: str = Query(default=None, description="模型供应商筛选"),
    available_only: bool = Query(default=False, description="仅返回当前用户已启用且配置了 API Key 的模型"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取扁平化模型列表（前端下拉选项用）

    available_only=true 时按当前用户过滤：
    - 模型在用户 custom_models 中且 enabled=true
    - 模型所属 provider 已配置 API Key（独立字段或 custom_providers）

    返回格式：
    [
        {
            "id": "model_name",
            "name": "Doubao Seed 2.0 Pro",
            "model_name": "doubao-seed-2-0-pro-260215",
            "model_type": "text",
            "base_url": "https://...",
            "label": "Doubao Seed 2.0 Pro 火山引擎 Ark",
            "provider_name": "火山引擎 Ark"
        }
    ]
    """
    query = db.query(AIModel)
    if model_type:
        query = query.filter(AIModel.model_type == model_type)
    if model_provider:
        provider = db.query(AIProvider).filter(AIProvider.code == model_provider).first()
        if provider:
            query = query.filter(AIModel.provider_id == provider.id)

    models = query.all()
    provider_ids = list(set(m.provider_id for m in models))
    providers = db.query(AIProvider).filter(AIProvider.id.in_(provider_ids)).all()
    provider_map = {p.id: p for p in providers}

    # 用户过滤：已启用 + provider 配过 API Key
    if available_only:
        if not current_user:
            return success_response(data=[])
        resolved = ConfigReader(db).get_config(str(current_user.id))
        # 构建已启用集合：{(provider_code, model_name): True}
        enabled_set = {
            (cm.get("provider_id"), cm.get("model"))
            for cm in (resolved.custom_models or [])
            if cm.get("enabled") and cm.get("model")
        }
        filtered = []
        for m in models:
            provider = provider_map.get(m.provider_id)
            if not provider:
                continue
            if (provider.code, m.model_name) not in enabled_set:
                continue
            if not _provider_has_api_key(resolved, provider.code):
                continue
            filtered.append(m)
        models = filtered

    result = []
    for m in models:
        provider = provider_map.get(m.provider_id)
        provider_name = provider.name if provider else ""

        result.append({
            "id": m.model_name,
            "name": m.name,
            "model_name": m.model_name,
            "model_type": m.model_type,
            "base_url": m.base_url,
            "label": f"{m.name} {provider_name}",
            "provider_name": provider_name,
        })

    return success_response(data=result)
