"""
运行时配置读取器

供 AI 服务调用，获取解密后的用户 API 配置。
包括 API Key、模型选择、并发限制等。

使用示例：
    reader = ConfigReader(db)
    config = reader.get_config(user_id="xxx")

    api_key = config.get_api_key_for("ark")  # 已解密的 API Key
    model = config.analysis_model             # 分析模型名称
    concurrency = config.analysis_concurrency # 并发上限
"""
from dataclasses import asdict, dataclass, field
from typing import Optional

from sqlalchemy.orm import Session

from app.core.logging import logger
from app.core.security import get_content
from app.models.user_api_config import UserApiConfig


@dataclass
class ResolvedConfig:
    """
    解密后的运行时配置（供 AI 服务直接使用）

    所有 API Key 字段已解密为明文
    """
    user_id: str = ""

    analysis_model: Optional[str] = None
    character_model: Optional[str] = None
    location_model: Optional[str] = None
    storyboard_model: Optional[str] = None
    edit_model: Optional[str] = None
    video_model: Optional[str] = None
    audio_model: Optional[str] = None

    analysis_concurrency: int = 5
    image_concurrency: int = 5
    video_concurrency: int = 5

    video_ratio: str = "9:16"
    video_resolution: str = "720p"
    art_style: str = "american-comic"
    tts_rate: str = "+50%"
    image_resolution: str = "2K"
    capability_defaults: Optional[str] = None

    fal_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    ark_api_key: Optional[str] = None
    qwen_api_key: Optional[str] = None
    jd_api_key: Optional[str] = None

    custom_models: Optional[list[dict]] = field(default=None)
    custom_providers: Optional[list[dict]] = field(default=None)

    # 从数据库预加载的 base_url 映射
    model_base_urls: Optional[dict[str, str]] = field(default=None)      # {model_name: base_url} AIModel 级（已含 provider 级回退）
    provider_base_urls: Optional[dict[str, str]] = field(default=None)   # {code: base_url} AIProvider 级
    model_provider_map: Optional[dict[str, str]] = field(default=None)   # {model_name: provider_code} 模型→供应商映射

    ark_video_watermark: bool = False
    volc_private_asset_group_id: Optional[str] = None

    def get_api_key_for(self, provider: str) -> Optional[str]:
        """
        根据 provider 名称获取对应的 API Key

        Args:
            provider: 提供商标识，支持 fal / google / ark / qwen / jd

        Returns:
            解密后的 API Key 明文，未配置时返回 None
        """
        mapping = {
            "fal": self.fal_api_key,
            "google": self.google_api_key,
            "ark": self.ark_api_key,
            "qwen": self.qwen_api_key,
            "jd": self.jd_api_key,
        }
        return mapping.get(provider)

    def get_model_for(self, model_type: str) -> Optional[str]:
        """
        根据模型类型获取用户配置的模型名称

        Args:
            model_type: 模型类型，支持 analysis / character / location / storyboard / edit / video / audio

        Returns:
            模型名称，未配置时返回 None
        """
        mapping = {
            "analysis": self.analysis_model,
            "character": self.character_model,
            "location": self.location_model,
            "storyboard": self.storyboard_model,
            "edit": self.edit_model,
            "video": self.video_model,
            "audio": self.audio_model,
        }
        return mapping.get(model_type)

    def get_concurrency_for(self, task_type: str) -> int:
        """
        根据任务类型获取并发上限

        Args:
            task_type: 任务类型，支持 analysis / image / video

        Returns:
            并发上限，默认 5
        """
        mapping = {
            "analysis": self.analysis_concurrency,
            "image": self.image_concurrency,
            "video": self.video_concurrency,
        }
        return mapping.get(task_type, 5)

    def find_provider_by_id(self, provider_id: str) -> Optional[dict]:
        """
        在 custom_providers 中查找指定 ID 的 provider

        Args:
            provider_id: Provider 唯一标识

        Returns:
            Provider 字典（含解密后的 apiKey），未找到返回 None
        """
        if not self.custom_providers:
            return None
        for p in self.custom_providers:
            if p.get("id") == provider_id:
                return p
        return None

    def find_provider_by_code(self, code: str) -> Optional[dict]:
        """
        在 custom_providers 中按 code 查找 provider（大小写不敏感）

        用于 model_provider 按厂商前缀查找对应的 API Key 和 base_url

        Args:
            code: 厂商标识（如 deepseek / openai / JD）

        Returns:
            Provider 字典（含解密后的 apiKey），未找到返回 None
        """
        if not self.custom_providers:
            return None
        code_lower = code.lower()
        for p in self.custom_providers:
            if (p.get("id") or "").lower() == code_lower:
                return p
        return None

    def find_models_by_provider(self, provider_id: str) -> list[dict]:
        """
        在 custom_models 中查找属于指定 provider 的所有模型

        Args:
            provider_id: Provider 唯一标识

        Returns:
            模型列表，仅包含 enabled=True 的模型
        """
        if not self.custom_models:
            return []
        return [
            m for m in self.custom_models
            if m.get("provider_id") == provider_id and m.get("enabled", True)
        ]

    def to_dict(self) -> dict:
        """
        序列化为字典（供 Celery 任务传递配置快照）

        过滤掉 None 值，减少序列化体积
        """
        return {k: v for k, v in asdict(self).items() if v is not None}


class ConfigReader:
    """
    运行时配置读取器

    从数据库读取用户 API 配置，解密 API Key 后返回 ResolvedConfig 对象。
    供 AI 服务调用以获取模型、密钥、并发等配置。
    支持项目级配置覆盖：project.config > UserApiConfig > 系统默认值。
    """

    # 可被项目配置覆盖的键
    _PROJECT_OVERRIDABLE_KEYS = (
        "analysis_model", "character_model", "location_model",
        "storyboard_model", "edit_model", "video_model", "audio_model",
        "video_ratio", "art_style",
    )

    _ENCRYPTED_FIELDS = (
        "fal_api_key",
        "google_api_key",
        "ark_api_key",
        "qwen_api_key",
        "jd_api_key",
    )

    def __init__(self, db: Session):
        self.db = db

    def get_config(self, user_id: str) -> ResolvedConfig:
        """
        获取用户的解密运行时配置

        子账号在 API Key 等字段为空时，自动回退到主账号的配置。

        Args:
            user_id: 用户ID

        Returns:
            ResolvedConfig 实例，所有 API Key 已解密为明文

        Raises:
            无异常抛出，配置不存在时返回默认值
        """
        config = (
            self.db.query(UserApiConfig)
            .filter_by(user_id=user_id)
            .first()
        )

        if not config:
            logger.warning(f"用户 {user_id} 无API配置，返回默认值")
            return ResolvedConfig(user_id=user_id)

        resolved = ResolvedConfig(user_id=user_id)

        parent_config = self._get_parent_config(config)

        self._resolve_simple_fields(config, resolved, parent_config)
        self._resolve_encrypted_fields(config, resolved, parent_config)
        self._resolve_json_fields(config, resolved, parent_config)
        self._resolve_base_urls(resolved)

        return resolved

    def _get_parent_config(self, config: UserApiConfig) -> UserApiConfig | None:
        """
        获取主账号的 API 配置（仅子账号需要）
        """
        from app.models.user import User

        user = self.db.query(User).filter_by(id=config.user_id).first()
        if not user or not user.parent_user_id:
            return None

        return (
            self.db.query(UserApiConfig)
            .filter_by(user_id=user.parent_user_id)
            .first()
        )

    def _resolve_simple_fields(
        self, config: UserApiConfig, resolved: ResolvedConfig,
        parent_config: UserApiConfig | None = None,
    ) -> None:
        """
        解析普通字段（模型名、并发、视频参数等）
        子账号字段为空时回退到主账号
        """
        simple_fields = (
            "analysis_model", "character_model", "location_model",
            "storyboard_model", "edit_model", "video_model", "audio_model",
            "analysis_concurrency", "image_concurrency", "video_concurrency",
            "video_ratio", "video_resolution", "art_style", "tts_rate",
            "image_resolution", "capability_defaults",
            "ark_video_watermark",
            "volc_private_asset_group_id",
        )
        for f in simple_fields:
            value = getattr(config, f, None)
            if value is None and parent_config:
                value = getattr(parent_config, f, None)
            if value is not None:
                setattr(resolved, f, value)

    def _resolve_encrypted_fields(
        self, config: UserApiConfig, resolved: ResolvedConfig,
        parent_config: UserApiConfig | None = None,
    ) -> None:
        """
        解密 API Key 字段
        子账号字段为空时回退到主账号的密钥
        """
        for f in self._ENCRYPTED_FIELDS:
            value = getattr(config, f, None)
            if not value and parent_config:
                value = getattr(parent_config, f, None)
            if value:
                try:
                    setattr(resolved, f, get_content(value) if isinstance(value, str) else value)
                except Exception as e:
                    logger.warning(f"用户 {config.user_id} 的 {f} 解密失败，使用原始值，错误={e}。")
                    setattr(resolved, f, value)

    def _resolve_json_fields(
        self, config: UserApiConfig, resolved: ResolvedConfig,
        parent_config: UserApiConfig | None = None,
    ) -> None:
        """
        解析 JSON 字段（custom_models, custom_providers），并解密 provider 中的 apiKey
        子账号字段为空时回退到主账号
        """
        custom_models = getattr(config, "custom_models", None)
        if not custom_models and parent_config:
            custom_models = getattr(parent_config, "custom_models", None)
        if custom_models:
            if isinstance(custom_models, list):
                resolved.custom_models = custom_models

        custom_providers = getattr(config, "custom_providers", None)
        if not custom_providers and parent_config:
            custom_providers = getattr(parent_config, "custom_providers", None)
        if custom_providers:
            if isinstance(custom_providers, list):
                resolved.custom_providers = self._decrypt_provider_keys(custom_providers)

    def _decrypt_provider_keys(self, providers: list[dict]) -> list[dict]:
        """
        解密 custom_providers 中每个 provider 的 apiKey
        兼容明文存储的 api_key（解密失败时视为明文直接使用）
        """
        result = []
        for p in providers:
            item = dict(p)
            api_key = item.get("api_key")
            if api_key and isinstance(api_key, str):
                # Fernet 加密后的字符串以 "gAAAA" 开头，仅对加密值尝试解密
                if api_key.startswith("gAAAA"):
                    try:
                        item["api_key"] = get_content(api_key)
                    except Exception as e:
                        logger.warning(f"Provider {item.get('id')} 的 apiKey 解密失败，错误={e}。")
            result.append(item)
        return result

    def _resolve_base_urls(self, resolved: ResolvedConfig) -> None:
        """从 AIModel / AIProvider 表预加载 base_url 和模型→供应商映射"""
        from app.models.ai_model import AIModel, AIProvider

        # 加载所有供应商
        all_providers = self.db.query(AIProvider).all()
        provider_map = {}       # {provider_id: base_url}（仅非空）
        provider_code_map = {}  # {provider_id: code}（所有供应商）
        for p in all_providers:
            provider_code_map[p.id] = p.code
            if p.base_url:
                provider_map[p.id] = p.base_url

        if provider_map:
            resolved.provider_base_urls = {
                p.code: p.base_url for p in all_providers if p.base_url
            }

        # 加载所有模型，构建 model_base_urls 和 model_provider_map
        models = self.db.query(AIModel).all()
        if models:
            resolved.model_base_urls = {}
            resolved.model_provider_map = {}
            for m in models:
                # model_name → provider_code（所有模型都映射）
                if m.provider_id and m.provider_id in provider_code_map:
                    resolved.model_provider_map[m.model_name] = provider_code_map[m.provider_id]

                # model_name → base_url（模型级优先，回退到供应商级）
                url = m.base_url
                if not url and m.provider_id and m.provider_id in provider_map:
                    url = provider_map[m.provider_id]
                if url:
                    resolved.model_base_urls[m.model_name] = url

    def get_project_config(self, user_id: str, project_config: dict | None) -> ResolvedConfig:
        """
        获取项目级合并配置

        优先级: project.config > UserApiConfig > 系统默认值

        Args:
            user_id: 用户ID
            project_config: 项目 config JSONB 字典 (可能为 None 或 {})

        Returns:
            ResolvedConfig 实例，project.config 的值覆盖全局配置
        """
        resolved = self.get_config(user_id)

        if not project_config:
            return resolved

        for key in self._PROJECT_OVERRIDABLE_KEYS:
            # 兼容旧 key
            config_key = key
            if key == "video_ratio" and key not in project_config and "ratio" in project_config:
                config_key = "ratio"
            elif key == "art_style" and key not in project_config and "style" in project_config:
                config_key = "style"

            if config_key in project_config and project_config[config_key] is not None:
                setattr(resolved, key, project_config[config_key])

        return resolved
