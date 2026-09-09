import copy
import uuid

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import crud
from app.core.logging import logger
from app.core.security import get_data_encrypt, get_content
from app.models.user_api_config import UserApiConfig
from app.crud import ai_provider_crud
from app.schemas.user_api_config import (
    ProviderSchema,
    UserApiConfigCreateSchema,
    UserApiConfigSchema,
    UserApiConfigUpdateSchema,
)
from app.enums import AIModelType

_API_KEY_FIELDS = (
    "fal_api_key",
    "google_api_key",
    "ark_api_key",
    "qwen_api_key",
    "jd_api_key",
)


def _encrypt_api_keys(data: dict) -> dict:
    """
    对 API Key 字段进行加密

    仅对非空字符串进行加密，None 和空字符串保持原样
    """
    result = copy.deepcopy(data)
    for field in _API_KEY_FIELDS:
        value = result.get(field)
        if value and isinstance(value, str) and value.strip():
            result[field] = get_data_encrypt(value.encode()).decode() if isinstance(get_data_encrypt(value.encode()), bytes) else get_data_encrypt(value.encode())
    return result


def _decrypt_api_keys(config: UserApiConfig) -> dict:
    """
    对 API Key 字段进行解密，返回可序列化的字典

    解密失败时返回原始密文
    """
    result = {}
    for field in _API_KEY_FIELDS:
        value = getattr(config, field, None)
        if value:
            try:
                result[field] = get_content(value) if isinstance(value, str) else value
            except Exception:
                result[field] = value
        else:
            result[field] = value
    return result


def _encrypt_providers(providers: list[dict]) -> list[dict]:
    """
    对 custom_providers 列表中每个 provider 的 apiKey 进行加密
    """
    result = []
    for p in providers:
        item = copy.deepcopy(p)
        api_key = item.get("api_key")
        if api_key and isinstance(api_key, str) and api_key.strip():
            encrypted = get_data_encrypt(api_key.encode())
            item["api_key"] = encrypted.decode() if isinstance(encrypted, bytes) else encrypted
        result.append(item)
    return result


def _merge_provider_api_keys(
    old_providers: list[dict] | None,
    new_providers: list[dict] | None,
) -> list[dict] | None:
    """
    合并 custom_providers 的 apiKey，遵循三态规则：
    - 不传（字段未出现在 new_providers 中）→ 保留原值
    - 空字符串 "" → 删除（置空）
    - 非空字符串 → 加密后覆盖

    同时保证 provider::modelId 唯一键合约
    """
    if new_providers is None:
        return old_providers

    if not old_providers:
        return _encrypt_providers(new_providers)

    old_map = {p.get("id"): p for p in old_providers}
    result = []

    for new_p in new_providers:
        pid = new_p.get("id")
        old_p = old_map.get(pid)

        if old_p and "api_key" in new_p:
            new_key = new_p["api_key"]
            if new_key == "" or new_key is None:
                new_p = {**new_p, "api_key": None}
            elif isinstance(new_key, str) and new_key.strip():
                encrypted = get_data_encrypt(new_key.encode())
                new_p = {**new_p, "api_key": encrypted.decode() if isinstance(encrypted, bytes) else encrypted}
            else:
                new_p = {**new_p, "api_key": old_p.get("api_key")}
        elif old_p:
            new_p = {**new_p, "api_key": old_p.get("api_key")}

        result.append(new_p)

    return result


def _validate_model_uniqueness(custom_models: list[dict] | None) -> None:
    """
    验证 custom_models 中 provider_id + model 唯一键合约
    """
    if not custom_models:
        return
    seen = set()
    for m in custom_models:
        key = f"{m.get('provider_id', '')}::{m.get('model', '')}"
        if key in seen:
            raise HTTPException(
                status_code=400,
                detail=f"模型唯一键冲突：{key}，provider_id + model 组合必须唯一",
            )
        seen.add(key)


class UserApiConfigService:
    """
    用户API配置服务

    核心业务规则：
    1. 模型唯一键合约：provider_id::model 组合必须唯一
    2. Provider 多实例支持
    3. apiKey 三态更新：保留 / 删除 / 覆盖
    4. 默认模型与模型启用联动
    """

    @staticmethod
    def get_by_user_id(db: Session, user_id: str) -> UserApiConfigSchema:
        """
        获取用户API配置（API Key 脱敏返回）
        子账号 API Key 为空时回退到主账号
        """
        config = crud.user_api_config_crud.get_by_user_id(user_id=user_id, db=db)
        if not config:
            raise HTTPException(status_code=404, detail="用户API配置不存在")

        config_dict = _decrypt_api_keys(config)

        from app.models.user import User
        user = db.query(User).filter_by(id=user_id).first()
        if user and user.parent_user_id:
            parent_config = crud.user_api_config_crud.get_by_user_id(
                user_id=user.parent_user_id, db=db
            )
            if parent_config:
                parent_dict = _decrypt_api_keys(parent_config)
                for field in _API_KEY_FIELDS:
                    if not config_dict.get(field) and parent_dict.get(field):
                        config_dict[field] = parent_dict[field]

        return UserApiConfigSchema.model_validate(config).model_copy(
            update={
                "fal_api_key": config_dict.get("fal_api_key"),
                "google_api_key": config_dict.get("google_api_key"),
                "ark_api_key": config_dict.get("ark_api_key"),
                "qwen_api_key": config_dict.get("qwen_api_key"),
                "jd_api_key": config_dict.get("jd_api_key"),
            }
        )

    @staticmethod
    def create(
        db: Session, config_in: UserApiConfigCreateSchema
    ) -> UserApiConfigSchema:
        """
        创建用户API配置

        API Key 写入前加密，custom_models 校验唯一键
        """
        _validate_model_uniqueness(
            [m.model_dump() for m in config_in.custom_models]
            if config_in.custom_models
            else None
        )

        data = config_in.model_dump()

        data = _encrypt_api_keys(data)

        if data.get("custom_providers"):
            data["custom_providers"] = _encrypt_providers(data["custom_providers"])

        config = UserApiConfig(id=str(uuid.uuid4()), **data)
        db.add(config)
        db.commit()
        db.refresh(config)

        logger.success(f"用户API配置创建成功，用户ID：{config.user_id}")
        return UserApiConfigService.get_by_user_id(db, config.user_id)

    @staticmethod
    def update(
        db: Session, user_id: str, config_in: UserApiConfigUpdateSchema
    ) -> UserApiConfigSchema:
        """
        更新用户API配置

        核心逻辑：
        1. apiKey 三态更新：exclude_unset 中不存在=保留，""=删除，非空=覆盖加密
        2. custom_providers 的 apiKey 同样三态
        3. custom_models 校验 provider_id::model 唯一键
        """
        config = crud.user_api_config_crud.get_by_user_id(user_id=user_id, db=db)
        if not config:
            config = UserApiConfig(id=str(uuid.uuid4()), user_id=user_id)
            db.add(config)
            db.flush()

        update_data = config_in.model_dump(exclude_unset=True)

        _validate_model_uniqueness(update_data.get("custom_models"))

        for field in _API_KEY_FIELDS:
            if field in update_data:
                value = update_data[field]
                if value and isinstance(value, str) and value.strip():
                    encrypted = get_data_encrypt(value.encode())
                    update_data[field] = (
                        encrypted.decode()
                        if isinstance(encrypted, bytes)
                        else encrypted
                    )
                elif value == "":
                    update_data[field] = None
                else:
                    del update_data[field]

        if "custom_providers" in update_data:
            old_providers = getattr(config, "custom_providers", None)
            if isinstance(old_providers, str):
                import json
                try:
                    old_providers = json.loads(old_providers)
                except (json.JSONDecodeError, TypeError):
                    old_providers = None

            new_providers_raw = update_data["custom_providers"]
            if isinstance(new_providers_raw, list):
                new_providers = []
                for p in new_providers_raw:
                    if isinstance(p, dict):
                        new_providers.append(p)
                    else:
                        new_providers.append(p)
                update_data["custom_providers"] = _merge_provider_api_keys(
                    old_providers, new_providers
                )

                for p in update_data["custom_providers"]:
                    if not isinstance(p, dict):
                        continue
                    p_base = p.get("base_url")
                    if p_base and isinstance(p_base, str) and p_base.strip():
                        continue
                    provider_id = p.get("id", "")
                    sys_provider = ai_provider_crud.get_queryset(db).filter(
                        ai_provider_crud.model.code == provider_id
                    ).first()
                    if sys_provider and sys_provider.base_url:
                        p["base_url"] = sys_provider.base_url

        changes = []
        for field, value in update_data.items():
            old_value = getattr(config, field, None)
            if field in _API_KEY_FIELDS:
                display_old = "***" if old_value else old_value
                display_new = "***" if value else value
            else:
                display_old = old_value
                display_new = value
            changes.append(f"{field}: {display_old!r} -> {display_new!r}")
            setattr(config, field, value)

        db.add(config)
        db.commit()
        db.refresh(config)

        logger.success(
            f"用户API配置更新成功，用户ID：{user_id}，变更字段：{'; '.join(changes)}"
        )
        return UserApiConfigService.get_by_user_id(db, user_id)

    @staticmethod
    def connect_to_provider(
        db: Session, user_id: str, provider_code: str
    ) -> dict:
        """
        测试连接模型厂商

        通过发送一个最小化的 completion 请求来验证 API Key 和网络连通性。
        流程：
        1. 校验 provider_code 在 ai_provider 表中存在
        2. 从用户 custom_providers 中获取该供应商的 api_key 和 base_url
        3. 从 ai_model 表中查找该供应商的第一个模型用于测试

        Args:
            db: 数据库会话
            user_id: 用户ID
            provider_code: 模型厂商标识（ai_provider.code）

        Returns:
            dict: {"success": bool, "latency_ms": int, "model_name": str, "error": str | None}

        Raises:
            HTTPException: 400 - 不支持的厂商或未配置 API Key
        """
        from app.core.model_provider import ModelCaller
        from app.models.ai_model import AIModel
        from app.services.config_reader import ConfigReader
        from app.core.llm_config_manager import LLMConfigManager

        sys_provider = ai_provider_crud.get_queryset(db).filter(
            ai_provider_crud.model.code == provider_code
        ).first()
        if not sys_provider:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的模型供应商: {provider_code}，请从预定义的供应商列表中选择",
            )

        reader = ConfigReader(db)
        config = reader.get_config(user_id)

        custom_provider = config.find_provider_by_id(provider_code)
        if not custom_provider:
            raise HTTPException(
                status_code=400,
                detail=f"未配置 {sys_provider.name} 的 API Key，请先在厂商资源池中设置",
            )

        api_key = custom_provider.get("api_key")
        if not api_key:
            raise HTTPException(
                status_code=400,
                detail=f"未配置 {sys_provider.name} 的 API Key，请先在厂商资源池中设置",
            )

        api_base = custom_provider.get("base_url") or sys_provider.base_url or None

        test_model = db.query(AIModel).filter(
            AIModel.provider_id == sys_provider.id
        ).first()
        if test_model:
            model_name = test_model.model_name
            model_type = AIModelType(test_model.model_type)

            # 对京东特殊处理，使用文本模型做连接测试
            # 如果使用图片模型会导致前端超时
            if test_model.provider.code in ["chatgpt", "deepseek", "Google"]:
                llm_model_name = f"openai/{model_name}"
            else:
                # litellm调用其他厂商（除京东以外）模型API时
                llm_model_name = f"{provider_code}/{model_name}"
        else:
            raise HTTPException(
                status_code=400,
                detail=f"供应商 {sys_provider.name} 暂无可用的测试模型",
            )

        return ModelCaller.test_connection(
            model_name=llm_model_name,
            model_type=model_type,
            api_key=api_key,
            api_base=api_base,
        )
