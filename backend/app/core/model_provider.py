"""
模型调用抽象层 - 基于 LiteLLM 的统一模型调用器

替换原 TextModelProvider 全局单例，支持：
- 多 Provider 路由（百炼/火山/智谱/DeepSeek/OpenAI 等）
- 配置驱动的模型选择（系统默认 < 设置中心 < 项目配置）
- 统一日志双写（Redis 缓冲 + 项目日志）
"""
import asyncio
import json
import math
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional

os.environ.setdefault("LITELLM_LOG", "WARNING")

import httpx
import litellm

from app.core.config import settings
from app.core.logging import logger
from app.core.model_call_log_writer import model_call_log_writer
from app.enums import AIModelType


# Gemini 图片模型集合（小写形式，用于 _is_gemini_image_model 判断）
_GEMINI_IMAGE_MODELS = {"gemini-2-5-flash-image", "gemini-3-pro-image-preview"}

# aspectRatio → 像素尺寸（flash 模型像素固定；3-pro 也用此表推断 aspectRatio）
_GEMINI_ASPECT_RATIOS = {
    "1:1": (1024, 1024), "2:3": (832, 1248), "3:2": (1248, 832),
    "3:4": (864, 1184), "4:3": (1184, 864), "4:5": (896, 1152),
    "5:4": (1152, 896), "9:16": (768, 1344), "16:9": (1344, 768),
    "21:9": (1536, 672),
}

# URL 后缀 → mimeType（图生图 fileData 用）
_URL_EXT_TO_MIME = {
    "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
    "webp": "image/webp", "gif": "image/gif", "bmp": "image/bmp",
}


@dataclass
class ResolvedModel:
    """模型解析结果：封装 litellm 调用所需的全部参数信息

    调用方使用模式：
        m = self._resolve_model(model_key)
        # 日志：m.api_base / m.api_key / m.provider_code / m.model_name
        # 调用：litellm.xxx(model=m.model_name, api_key=m.api_key, api_base=m.api_base,
        #                  custom_llm_provider=m.custom_llm_provider)
    """
    model_name: str
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    custom_llm_provider: Optional[str] = None
    provider_code: str = "openai"


class ModelResult:
    """模型调用结果"""
    def __init__(self, content: str, input_tokens: int = 0, output_tokens: int = 0, total_tokens: int = 0):
        self.content = content
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.total_tokens = total_tokens

    def parse_json(self) -> dict | list:
        """尝试解析 JSON 格式的返回内容"""
        text = self.content.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1])
        return json.loads(text)


class ModelCaller:
    """
    配置驱动的模型调用器，替换 TextModelProvider

    使用方式：
        # 从用户配置创建（API 端点中）
        config_reader = ConfigReader(db)
        resolved = config_reader.get_project_config(user_id, project.config)
        caller = ModelCaller(resolved)

        # 从配置快照创建（Celery Worker 中）
        caller = ModelCaller.from_config_snapshot(model_config)

        # 从系统默认创建（无用户上下文）
        caller = ModelCaller.from_system_defaults()
    """

    # model_key → ResolvedConfig 字段名
    _MODEL_KEY_MAP = {
        "analysis_model": "analysis_model",
        "character_model": "character_model",
        "location_model": "location_model",
        "storyboard_model": "storyboard_model",
        "edit_model": "edit_model",
        "video_model": "video_model",
        "audio_model": "audio_model",
    }

    # LiteLLM provider 前缀 → ResolvedConfig API Key 字段名（仅含独立字段的厂商）
    _PROVIDER_KEY_MAP = {
        "dashscope": "qwen_api_key",
        "volcengine": "ark_api_key",
        "chatgpt": "jd_api_key",
        "deepseek": "ark_api_key",
    }

    def __init__(self, resolved_config, db=None):
        """
        初始化 ModelCaller

        Args:
            resolved_config: ResolvedConfig 实例，包含解密后的 API Key 和模型配置
            db: 可选的数据库会话，传入时启用积分预扣机制
        """
        self.config = resolved_config
        self.db = db

    @classmethod
    def from_config_snapshot(cls, config_dict: dict, db=None) -> "ModelCaller":
        """从序列化的配置快照创建实例（供 Celery Worker 使用）"""
        from app.services.config_reader import ResolvedConfig
        resolved = ResolvedConfig(**config_dict)
        logger.debug(f"[ModelCaller/from_config_snapshot] user_id={resolved.user_id} db={'有' if db else 'None'}")
        return cls(resolved, db=db)

    @classmethod
    def from_system_defaults(cls) -> "ModelCaller":
        """从系统默认配置创建实例（供无用户上下文的场景使用）"""
        from app.services.config_reader import ResolvedConfig
        resolved = ResolvedConfig(
            analysis_model=getattr(settings, "LLM_MODEL_NAME", None),
        )
        return cls(resolved)

    # 走 litellm 原生 provider 路由的厂商（保留 provider/ 前缀）
    # 其余厂商统一走 openai/ 前缀 + api_base 路由（中转站）
    _LITELLM_NATIVE_PROVIDERS = {"volcengine"}

    def _resolve_model(
        self,
        model_key: str,
        model_name_override: Optional[str] = None,
    ) -> ResolvedModel:
        """
        解析 model_key → ResolvedModel

        - 中转站路由：模型名加 openai/ 前缀；custom_llm_provider="openai"
        - 原生 provider（如 volcengine）：保留 provider/ 前缀；custom_llm_provider=None
        - api_key / api_base / custom_llm_provider 全部由调用方显式传给 litellm

        model_name_override 非空时直接用作模型名（跳过 _get_model_name 的配置字段查找），
        用于"页面选了具体模型名"覆盖默认 model_key 解析的场景。
        """
        if model_name_override:
            model_name = model_name_override
        else:
            model_name = self._get_model_name(model_key)
            if not model_name:
                raise ValueError(f"未配置模型: {model_key}，且无系统默认模型")

        call_kwargs = self._get_provider_kwargs(model_name)

        actual_model_name = model_name.split("/", 1)[1] if "/" in model_name else model_name

        # 获取实际 provider code（用于日志和特殊路由）
        model_provider_map = getattr(self.config, "model_provider_map", None) or {}
        provider_code = model_provider_map.get(actual_model_name, "openai")

        # volcengine 等原生厂商保留 provider/ 前缀；其余统一走 openai/ 前缀（中转站）
        if provider_code in self._LITELLM_NATIVE_PROVIDERS:
            litellm_name = f"{provider_code}/{actual_model_name}"
            custom_llm_provider = None
        else:
            litellm_name = f"openai/{actual_model_name}"
            custom_llm_provider = "openai"

        return ResolvedModel(
            model_name=litellm_name,
            api_key=call_kwargs.get("api_key"),
            api_base=call_kwargs.get("api_base"),
            custom_llm_provider=custom_llm_provider,
            provider_code=provider_code,
        )

    def _get_model_name(self, model_key: str) -> Optional[str]:
        """从配置获取模型名，带回退链：指定字段 → analysis_model → 系统默认"""
        config_field = self._MODEL_KEY_MAP.get(model_key)
        if config_field:
            name = getattr(self.config, config_field, None)
            if name:
                return name

        if self.config.analysis_model:
            return self.config.analysis_model

        return getattr(settings, "LLM_MODEL_NAME", None)

    def _get_provider_kwargs(self, model_name: str) -> dict:
        """根据模型名获取 API Key 和 api_base，统一通过 openai/ + api_base 路由"""
        actual_model_name = model_name.split("/", 1)[1] if "/" in model_name else model_name

        # 从数据库映射获取模型实际所属的 provider code
        model_provider_map = getattr(self.config, "model_provider_map", None) or {}
        provider_code = model_provider_map.get(actual_model_name)

        # 系统模型（在 ai_model 表中）→ 走数据库驱动路径，不经过 custom_providers
        if provider_code:
            return self._get_system_provider_kwargs(actual_model_name, provider_code)

        # 自定义模型（不在 ai_model 表中）→ 走 custom_providers 路径
        custom_kwargs = self._check_custom_provider(model_name)
        if custom_kwargs is not None:
            return custom_kwargs

        # 兜底：系统默认
        api_key = getattr(settings, "LLM_API_KEY", None)
        base_url = getattr(settings, "LLM_BASE_URL", None)
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["api_base"] = base_url
        return kwargs

    def _get_system_provider_kwargs(self, actual_model_name: str, provider_code: str) -> dict:
        """系统模型（在 ai_model 表中）的 api_key 和 api_base 获取"""
        provider_info = self.config.find_provider_by_code(provider_code)

        # API Key：独立字段 → custom_providers
        api_key = None
        key_field = self._PROVIDER_KEY_MAP.get(provider_code)
        if key_field:
            api_key = getattr(self.config, key_field, None)

        if not api_key and provider_info:
            api_key = provider_info.get("api_key")

        kwargs = {"api_key": api_key}

        # base_url：custom_providers → model_base_urls → provider_base_urls → 系统环境变量
        base_url = provider_info.get("base_url") if provider_info else None

        if not base_url:
            model_base_urls = getattr(self.config, "model_base_urls", None) or {}
            base_url = model_base_urls.get(actual_model_name)

        if not base_url:
            provider_base_urls = getattr(self.config, "provider_base_urls", None) or {}
            base_url = provider_base_urls.get(provider_code)

        if base_url:
            kwargs["api_base"] = base_url

        return kwargs

    def _check_custom_provider(self, model_name: str) -> Optional[dict]:
        """检查是否为自定义 Provider 的模型"""
        custom_models = getattr(self.config, "custom_models", None)
        if not custom_models:
            return None

        for m in custom_models:
            if m.get("model_name") == model_name or m.get("litellm_name") == model_name:
                provider_id = m.get("provider_id")
                if not provider_id:
                    continue
                provider = self.config.find_provider_by_id(provider_id)
                if not provider:
                    continue

                kwargs = {"api_key": provider.get("api_key")}

                # base_url：优先 custom_provider → 兜底 model_base_urls（数据库）
                base_url = provider.get("api_base") or provider.get("base_url")
                if not base_url:
                    actual_name = model_name.split("/", 1)[1] if "/" in model_name else model_name
                    model_base_urls = getattr(self.config, "model_base_urls", None) or {}
                    base_url = model_base_urls.get(actual_name)
                if base_url:
                    kwargs["api_base"] = base_url

                return kwargs
        return None

    @staticmethod
    def _mask_api_key(api_key: str) -> str:
        """脱敏 API Key: sk-***abc"""
        if not api_key or len(api_key) < 8:
            return "***"
        return f"{api_key[:3]}***{api_key[-3:]}"

    def _is_semantic_key(self, model_key: str) -> bool:
        """判断 model_key 是否为语义 key（如 analysis_model），而非直接模型名"""
        return model_key in self._MODEL_KEY_MAP

    # ==================== 积分预扣机制 ====================

    def _get_billing_user_id(self) -> str | None:
        """获取需要计费的用户ID，无需计费时返回 None"""
        if not self.db:
            logger.debug(f"[积分] 跳过计费: db=None")
            return None
        user_id = getattr(self.config, "user_id", None)
        if not user_id or user_id == "system":
            logger.debug(f"[积分] 跳过计费: user_id={user_id}")
            return None
        logger.debug(f"[积分] 计费用户: user_id={user_id}")
        return user_id

    def _is_token_billing_image_model(self, model_name: str) -> bool:
        """
        是否为按token计费的图片模型（数据驱动，不再硬编码模型名）

        通过查询 ai_model_pricing 表中该模型的 rule_type 是否以 image_token 开头来判断。
        """
        if not self.db:
            return False

        from app.crud import ai_model_pricing_crud, ai_model_crud

        clean_name = model_name.split("/", 1)[1] if "/" in model_name else model_name
        ai_model = ai_model_crud.get_by_model_name(db=self.db, model_name=clean_name)
        if not ai_model:
            return False

        rule_types = ai_model_pricing_crud.get_rule_types_by_model(db=self.db, model_id=ai_model.id)
        return any(rt.startswith("image_token") for rt in rule_types)

    def _estimate_points(self, model_name: str, **kwargs) -> Decimal:
        """按模型类别预估积分 - 委托给 PointService"""
        from app.services.point import PointService
        return PointService.estimate_point(self.db, model_name, **kwargs)

    def _calculate_actual_points(self, model_name: str, input_tokens: int, output_tokens: int) -> Decimal:
        """调用完成后计算实际文本积分 - 委托给 PointService"""
        from app.services.point import PointService
        return PointService.calculate_actual_point(self.db, model_name, input_tokens, output_tokens)

    def _calculate_actual_points_for_image2(self, model_name: str, input_text_tokens: int, input_image_tokens: int, output_tokens: int) -> Decimal:
        """调用完成后计算实际积分，仅gpt-image2可用"""
        from app.services.point import PointService
        return PointService.calculate_actual_point_for_image2(self.db, model_name, input_text_tokens, input_image_tokens, output_tokens)

    def _calculate_actual_points_for_banana(self, model_name: str, output_tokens: int) -> Decimal:
        from app.services.point import PointService
        return PointService.calculate_actual_point_for_banana(self.db, model_name, output_tokens)

    def _pre_deduct(self, user_id: str, estimated_point: Decimal,
                    source_id: str = None) -> Decimal:
        """预扣积分 - 委托给 PointService（source_id 用于退款反查构成）"""
        from app.services.point import PointService
        return PointService.pre_deduct(self.db, user_id, estimated_point, source_id=source_id)

    def _settle(self, user_id: str, estimated_point: Decimal, actual_point: Decimal,
                source_id: str = None) -> None:
        """结算差额 - 委托给 PointService"""
        from app.services.point import PointService
        PointService.settle(self.db, user_id, estimated_point, actual_point, source_id=source_id)

    def _refund(self, user_id: str, estimated_point: Decimal, source_id: str = None) -> None:
        """退还预扣积分 - 委托给 PointService"""
        from app.services.point import PointService
        PointService.refund(self.db, user_id, estimated_point, source_id=source_id)

    @staticmethod
    def test_connection(
        model_name: str,
        model_type: AIModelType,
        api_key: str,
        api_base: str | None = None,
        timeout: int = 30,
    ) -> dict:
        """
        测试模型连接是否可用

        发送一个最小化的 completion 请求验证 API Key 和网络连通性

        Args:
            model_name: litellm 格式的模型名（含 provider 前缀，如 "deepseek/deepseek-chat"）
            api_key: API Key 明文
            api_base: 自定义 API 端点（仅 OpenAI-compatible provider 需要）
            timeout: 超时时间（秒），默认 30s

        Returns:
            dict: {"success": bool, "latency_ms": int, "model_name": str, "error": str | None}
        """
        start = time.monotonic()
        try:
            custom_llm_provider = "openai" if model_name.startswith("openai/") else None

            logger.debug(f"[模型连接测试] model_name={model_name}, model_type={model_type}")
            logger.debug(f"[模型连接测试] api_key={api_key}, api_base={api_base}")

            if model_type == AIModelType.TEXT:
                litellm.completion(
                    model=model_name,
                    messages=[{"role": "user", "content": "Hi"}],
                    max_tokens=5,
                    temperature=0,
                    timeout=timeout,
                    api_key=api_key,
                    api_base=api_base,
                    custom_llm_provider=custom_llm_provider,
                    max_retries=0,
                )
            elif model_type == AIModelType.IMAGE:
                litellm.image_generation(
                    model=model_name,
                    prompt="hi",
                    size="1024x1024",
                    n=1,
                    api_key=api_key,
                    api_base=api_base,
                    custom_llm_provider=custom_llm_provider,
                )
            else:
                logger.error(f"[模型连接测试] 不支持的模型类型，model_type={model_type}")
                raise ValueError(f"不支持的模型类型，model_type={model_type}")

            logger.success(f"[模型连接测试] 模型={model_name}，连接成功")
            latency_ms = int((time.monotonic() - start) * 1000)
            return {
                "success": True,
                "latency_ms": latency_ms,
                "model_name": model_name,
                "error": None,
            }
        except Exception as e:
            logger.error(f"[模型连接测试] 连接失败报错：{e}")
            latency_ms = int((time.monotonic() - start) * 1000)
            return {
                "success": False,
                "latency_ms": latency_ms,
                "model_name": model_name,
                "error": str(e),
            }

    def call(
        self,
        model_key: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = 8192,
        timeout: int = 180,
        project_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> ModelResult:
        """
        根据配置调用对应模型

        Args:
            model_key: 模型标识，如 "analysis_model" / "character_model"
            prompt: 用户提示词
            system_prompt: 系统提示词
            temperature: 生成温度
            max_tokens: 最大 token 数
            timeout: 超时时间（秒）
            project_id: 项目 ID（用于项目日志）
            task_id: 任务 ID（用于日志关联）

        Returns:
            ModelResult 统一结果
        """
        request_id = str(uuid.uuid4())
        m = self._resolve_model(model_key)

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        log_record = {
            "id": str(uuid.uuid4()),
            "user_id": getattr(self.config, "user_id", "system"),
            "project_id": project_id,
            "task_id": task_id,
            "request_id": request_id,
            "model_provider": m.provider_code,
            "model_name": m.model_name,
            "endpoint": m.api_base or f"litellm:///{m.provider_code}",
            "api_key_masked": self._mask_api_key(m.api_key or ""),
            "media_type": "text_text",
            "request_body": {
                "prompt_preview": prompt[:2000],
                "prompt_len": len(prompt),
                "messages_count": len(messages),
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
        }

        plog = None
        if project_id:
            from app.core.project_logger import get_project_logger
            plog = get_project_logger(project_id)
            plog.model_call(
                f"模型调用开始 request_id={request_id} model={m.model_name}",
                {
                    "request_id": request_id,
                    "model_name": m.model_name,
                    "prompt_preview": prompt[:200],
                    "prompt_len": len(prompt),
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )

        billing_user_id = self._get_billing_user_id()
        estimated_point = Decimal("0")

        if billing_user_id:
            try:
                estimated_point = self._estimate_points(
                    m.model_name, prompt=prompt, system_prompt=system_prompt, max_tokens=max_tokens,
                )
                self._pre_deduct(billing_user_id, estimated_point, source_id=request_id)
            except Exception as e:
                call_time = datetime.now()
                log_record.update({
                    "call_time": call_time.isoformat(),
                    "latency_ms": 0,
                    "error_message": str(e),
                    "point": 0,
                })
                model_call_log_writer.write(log_record)
                raise

        call_time = datetime.now()
        start = time.monotonic()
        try:
            logger.info(f"[调用前检查] api_base={m.api_base}")
            logger.info(f"[调用前检查] api_key={m.api_key}")
            response = litellm.completion(
                model=m.model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
                api_key=m.api_key,
                api_base=m.api_base,
                custom_llm_provider=m.custom_llm_provider,
                max_retries=0,
            )

            content = response.choices[0].message.content
            usage = response.usage
            latency_ms = int((time.monotonic() - start) * 1000)

            input_tokens = usage.prompt_tokens if usage else 0
            output_tokens = usage.completion_tokens if usage else 0
            total_tokens = usage.total_tokens if usage else 0

            usage_details = {}
            if usage:
                for attr in ("prompt_tokens_details", "completion_tokens_details"):
                    val = getattr(usage, attr, None)
                    if val:
                        usage_details[attr] = str(val)

            actual_point = estimated_point
            if billing_user_id and usage and (input_tokens or output_tokens):
                actual_point = self._calculate_actual_points(m.model_name, input_tokens, output_tokens)
                self._settle(billing_user_id, estimated_point, actual_point, source_id=request_id)

            log_record.update({
                "call_time": call_time.isoformat(),
                "provider_request_id": getattr(response, "id", None),
                "response_status": 200,
                "response_body": {"result_preview": content[:2000], "result_full": content},
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
                "latency_ms": latency_ms,
                "usage_details": usage_details,
                "point": float(actual_point),
                "_skip_auto_billing": True,
            })

            model_call_log_writer.write(log_record)

            if plog:
                plog.model_call(
                    f"模型调用完成 request_id={request_id} model={m.model_name} "
                    f"status=200 input_tokens={input_tokens} output_tokens={output_tokens} "
                    f"total_tokens={total_tokens} latency={latency_ms}ms",
                    {
                        "request_id": request_id,
                        "action": "model_call_end",
                        "response_status": 200,
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "total_tokens": total_tokens,
                        "latency_ms": latency_ms,
                        "usage_details": usage_details,
                        "response_preview": content[:200],
                        "response_full": content,
                        "finish_reason": response.choices[0].finish_reason if response.choices else None,
                    },
                )

            return ModelResult(
                content=content,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
            )
        except Exception as e:
            if billing_user_id and estimated_point > 0:
                try:
                    self._refund(billing_user_id, estimated_point, source_id=request_id)
                except Exception as refund_err:
                    logger.warning(f"退还预扣积分失败 error={refund_err} user_id={billing_user_id}")

            latency_ms = int((time.monotonic() - start) * 1000)
            log_record.update({
                "call_time": call_time.isoformat(),
                "latency_ms": latency_ms,
                "error_message": str(e),
            })
            model_call_log_writer.write(log_record)

            if plog:
                plog.error(
                    f"模型调用失败 request_id={request_id} model={m.model_name} "
                    f"latency={latency_ms}ms error={str(e)}"
                )
            raise

    def generate_image(
        self,
        model_key: str,
        asset_type: str,
        prompt: str,
        size: str = "2048x2048",
        n: int = 1,
        timeout: int = 300,
        project_id: Optional[str] = None,
        task_id: Optional[str] = None,
        model_name_override: Optional[str] = None,
    ) -> dict:
        """文生图"""
        request_id = str(uuid.uuid4())
        m = self._resolve_model(model_key, model_name_override=model_name_override)

        logger.debug(f"[文生图] generate_image 开始: request_id={request_id} model_key={model_key} asset_type={asset_type} model_name={m.model_name} db={'有' if self.db else 'None'}")

        is_gpt_image_2 = self._is_gpt_image_2_model(m.model_name)
        is_gemini_image = self._is_gemini_image_model(m.model_name)

        log_record = {
            "id": str(uuid.uuid4()),
            "user_id": getattr(self.config, "user_id", "system"),
            "project_id": project_id,
            "task_id": task_id,
            "request_id": request_id,
            "model_provider": m.provider_code,
            "model_name": m.model_name,
            "endpoint": m.api_base or f"litellm:///{m.provider_code}",
            "api_key_masked": self._mask_api_key(m.api_key or ""),
            "media_type": "text_image",
            "request_body": {
                "prompt_preview": prompt[:2000],
                "size": size,
                "n": n,
            },
        }

        billing_user_id = self._get_billing_user_id()
        estimated_point = Decimal("0")

        logger.debug(f"[文生图] billing_user_id={billing_user_id}")

        if billing_user_id:
            try:
                # 判断图片类型，角色三视图，is_character应该为True
                is_character = True if asset_type == "character" else False

                # gpt-image-2 按token计费，需根据prompt预估；其它图片模型按张数计费
                if self._is_token_billing_image_model(m.model_name):
                    estimated_point = self._estimate_points(m.model_name, prompt=prompt)
                else:
                    estimated_point = self._estimate_points(m.model_name, n=n, is_character=is_character, size=size)

                logger.debug(f"[文生图] estimated_point={estimated_point}")
                self._pre_deduct(billing_user_id, estimated_point, source_id=request_id)
            except Exception as e:
                logger.warning(f"[文生图] 积分预扣失败: {e}")
                call_time = datetime.now()
                log_record.update({
                    "call_time": call_time.isoformat(),
                    "latency_ms": 0,
                    "error_message": str(e),
                    "point": 0,
                })
                model_call_log_writer.write(log_record)
                raise

        call_time = datetime.now()
        start = time.monotonic()
        try:
            if is_gpt_image_2:
                result = self._call_jd_gpt_image_2_gen_sync(
                    prompt=prompt,
                    size=size,
                    n=n,
                    api_key=m.api_key,
                    api_base=m.api_base,
                    timeout=timeout,
                )
            elif is_gemini_image:
                actual = m.model_name.split("/", 1)[-1]
                aspect_ratio, image_size = self._gemini_resolve_size(actual, size)
                payload = self._build_jd_gemini_payload(
                    prompt=prompt,
                    image_urls=None,
                    aspect_ratio=aspect_ratio,
                    image_size=image_size,
                )
                raw = self._call_jd_gemini_image_sync(
                    payload=payload,
                    api_key=m.api_key,
                    api_base=m.api_base,
                    timeout=timeout,
                )
                result = self._normalize_gemini_response(raw, actual)
            else:
                response = litellm.image_generation(
                    model=m.model_name,
                    prompt=prompt,
                    size=size,
                    n=n,
                    timeout=timeout,
                    api_key=m.api_key,
                    api_base=m.api_base,
                    custom_llm_provider=m.custom_llm_provider,
                )
                result = response.model_dump()
            # logger.info(f"[同步文生图] result={self._build_image_response_body(result)}")
            data_count = len(result.get("data") or [])
            latency_ms = int((time.monotonic() - start) * 1000)

            # 提取输出图片元信息
            from app.utils.media_info_utils import parse_image_gen_output
            output_media = parse_image_gen_output(result.get("data") or [], size)

            # 提取 usage（gpt-image-2 走 result["usage_metadata"]，litellm 走 result["usage"]）
            input_tokens, output_tokens, total_tokens, usage_dict = self._extract_image_usage(result)

            logger.info(f"[同步文生图] usage_dict={usage_dict}")
            logger.debug(f"[同步文生图] input_tokens={input_tokens}, output_tokens={output_tokens}, total_tokens={total_tokens}")

            # 从usage_dict中提取计算积分所需字段
            input_text_tokens = usage_dict.get("input_tokens_details").get("text_tokens")
            input_image_tokens = usage_dict.get("input_tokens_details").get("image_tokens")

            # gpt-image-2 按实际token结算（多退少补）；其它图片模型预扣即最终
            actual_point = estimated_point
            if self._is_token_billing_image_model(m.model_name) and billing_user_id:
                if is_gpt_image_2:
                    actual_point = self._calculate_actual_points_for_image2(m.model_name, input_text_tokens, input_image_tokens, output_tokens)
                elif is_gemini_image:
                    actual_point = self._calculate_actual_points_for_banana(m.model_name, output_tokens)
                else:
                    logger.warning(f"[文生图] 模型判断错误，没有计算实际积分消耗。")

                try:
                    self._settle(billing_user_id, estimated_point, actual_point, source_id=request_id)
                except Exception as settle_err:
                    logger.warning(f"[同步文生图] 积分结算失败 error={settle_err} user_id={billing_user_id}")

            log_record.update({
                "call_time": call_time.isoformat(),
                "provider_request_id": self._extract_image_request_id(result),
                "response_status": 200,
                "response_body": self._build_image_response_body(result),
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
                "usage_details": usage_dict,
                "latency_ms": latency_ms,
                "output_media": output_media,
                "point": float(actual_point),
                "_skip_auto_billing": True,
            })
            logger.debug(f"[同步文生图] 写入 model_call_log: request_id={request_id} point={actual_point} estimated={estimated_point}")
            model_call_log_writer.write(log_record)

            logger.info(f"文生图完成 model={m.model_name} 生成图片数={data_count}")
            return result
        except Exception as e:
            if billing_user_id and estimated_point > 0:
                try:
                    self._refund(billing_user_id, estimated_point, source_id=request_id)
                except Exception as refund_err:
                    logger.warning(f"退还预扣积分失败 error={refund_err} user_id={billing_user_id}")

            latency_ms = int((time.monotonic() - start) * 1000)
            log_record.update({
                "call_time": call_time.isoformat(),
                "latency_ms": latency_ms,
                "error_message": str(e),
            })
            model_call_log_writer.write(log_record)
            raise

    @staticmethod
    def _is_gpt_image_2_model(model_name: str) -> bool:
        """判断是否为 gpt-image-2 模型（兼容 openai/ 前缀）"""
        actual = model_name.split("/", 1)[1] if "/" in model_name else model_name
        return actual == "gpt-image-2"

    @staticmethod
    def _jd_gpt_image_2_endpoint(api_base: str, kind: str) -> str:
        """拼接 gpt-image-2 JD 端点 URL。

        api_base 为 DB 配置的京东基础地址（如 https://agentrs.jd.com/api/saas/plugin-u/v1）。
        kind: "gen" → 文生图，"edit" → 图生图。
        """
        suffix = "images-generations-G" if kind == "gen" else "image-edits-G"
        return f"{api_base.rstrip('/')}/exec/{suffix}"

    @staticmethod
    def _build_jd_gpt_image_2_edit_payload(
        prompt: str, image_urls: list[str], size: str, n: int,
    ) -> dict:
        """构造 gpt-image-2 图生图请求体"""
        return {
            "model": "gpt-image-2",
            "prompt": prompt,
            "images": [{"image_url": u} for u in image_urls],
            "size": size,
            "n": str(n),
            "output_format": "png",
            "logo_add": 0,
        }

    @staticmethod
    def _build_jd_gpt_image_2_gen_payload(prompt: str, size: str, n: int) -> dict:
        """构造 gpt-image-2 文生图请求体"""
        return {
            "model": "gpt-image-2",
            "prompt": prompt,
            "size": size,
            "n": n,
        }

    @staticmethod
    def _call_jd_gpt_image_2_edit_sync(
        prompt: str, image_urls: list[str], size: str, n: int,
        api_key: str, api_base: str, timeout: int,
    ) -> dict:
        """同步调用 gpt-image-2 图生图 API"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        payload = ModelCaller._build_jd_gpt_image_2_edit_payload(prompt, image_urls, size, n)
        url = ModelCaller._jd_gpt_image_2_endpoint(api_base, "edit")
        logger.info(f"[图生图同步请求] request={payload}")
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(url, headers=headers, json=payload)
            if resp.status_code != 200:
                raise RuntimeError(
                    f"gpt-image-2 图生图调用失败 HTTP {resp.status_code}: {resp.text}"
                )
            return resp.json()

    @staticmethod
    async def _acall_jd_gpt_image_2_edit(
        prompt: str, image_urls: list[str], size: str, n: int,
        api_key: str, api_base: str, timeout: int,
    ) -> dict:
        """异步调用 gpt-image-2 图生图 API"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        payload = ModelCaller._build_jd_gpt_image_2_edit_payload(prompt, image_urls, size, n)
        url = ModelCaller._jd_gpt_image_2_endpoint(api_base, "edit")
        logger.info(f"[图生图异步请求] request={payload}")
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code != 200:
                raise RuntimeError(
                    f"gpt-image-2 图生图调用失败 HTTP {resp.status_code}: {resp.text}"
                )
            return resp.json()

    @staticmethod
    def _call_jd_gpt_image_2_gen_sync(
        prompt: str, size: str, n: int,
        api_key: str, api_base: str, timeout: int,
    ) -> dict:
        """同步调用 gpt-image-2 文生图 API"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        payload = ModelCaller._build_jd_gpt_image_2_gen_payload(prompt, size, n)
        url = ModelCaller._jd_gpt_image_2_endpoint(api_base, "gen")
        logger.info(f"[文生图同步请求] request={payload}")
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(url, headers=headers, json=payload)
            logger.debug(f"[同步文生图] resp={resp.text}")

            if resp.status_code != 200:
                raise RuntimeError(
                    f"gpt-image-2 文生图调用失败 HTTP {resp.status_code}: {resp.text}"
                )
            return resp.json()

    @staticmethod
    async def _acall_jd_gpt_image_2_gen(
        prompt: str, size: str, n: int,
        api_key: str, api_base: str, timeout: int,
    ) -> dict:
        """异步调用 gpt-image-2 文生图 API"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        payload = ModelCaller._build_jd_gpt_image_2_gen_payload(prompt, size, n)
        url = ModelCaller._jd_gpt_image_2_endpoint(api_base, "gen")

        logger.debug(f"[调用京东image2] headers={headers}")
        logger.info(f"[文生图异步请求] request={payload}")
        logger.debug(f"[调用京东image2] url={url}")
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, headers=headers, json=payload)
            logger.debug(f"[异步文生图] resp={resp.text}")
            if resp.status_code != 200:
                raise RuntimeError(
                    f"gpt-image-2 文生图调用失败 HTTP {resp.status_code}: {resp.text}"
                )
            logger.debug(f"[调用京东image2] resp.json()={resp.json()}")
            return resp.json()

    @staticmethod
    def _extract_image_usage(result: dict) -> tuple[int, int, int, dict]:
        """从图片生成响应提取 token usage。

        JD HTTP 响应：result["usage_metadata"]，字段名 input_tokens / output_tokens。
        litellm ImageResponse.model_dump()：result["usage"]，字段名 prompt_tokens /
        completion_tokens（litellm Usage 也保留 input_tokens / output_tokens 别名）。
        两种键名和两种字段命名都兼容。

        Returns: (input_tokens, output_tokens, total_tokens, usage_dict)
        """
        usage_dict: dict = {}

        if isinstance(result, dict):
            for key in ("usage", "usage_metadata"):
                raw = result.get(key)
                if isinstance(raw, dict):
                    usage_dict = raw
                    break
                if raw is not None and hasattr(raw, "model_dump"):
                    usage_dict = raw.model_dump() or {}
                    break

        input_tokens = usage_dict.get("input_tokens") or usage_dict.get("prompt_tokens") or 0
        output_tokens = usage_dict.get("output_tokens") or usage_dict.get("completion_tokens") or 0
        total_tokens = usage_dict.get("total_tokens") or (input_tokens + output_tokens)

        return input_tokens, output_tokens, total_tokens, usage_dict

    @staticmethod
    def _extract_image_request_id(result: dict) -> Optional[str]:
        """从图片生成响应提取 provider request_id。

        JD HTTP 响应在 result["request_id"]；litellm ImageResponse.model_dump()
        在 result["id"]。两种键名都兼容。
        """
        if not isinstance(result, dict):
            return None
        for key in ("request_id", "id"):
            val = result.get(key)
            if val:
                return val
        return None

    @staticmethod
    def _build_image_response_body(result: dict) -> dict:
        """构造图片生成的 response_body：保留所有顶层字段（含 usage / created / size 等），
        data 内过滤 b64_json 字段防止日志被 base64 撑爆。"""
        if not isinstance(result, dict):
            return {}
        body = {k: v for k, v in result.items() if k != "data"}
        body["data"] = [
            {k: v for k, v in d.items() if k != "b64_json"}
            for d in (result.get("data") or []) if isinstance(d, dict)
        ]
        body["data_count"] = len(body["data"])
        return body

    # ==================== Gemini 图片模型（京东网关直连） ====================

    @staticmethod
    def _is_gemini_image_model(model_name: str) -> bool:
        """判断是否为 Gemini 图片模型（兼容 provider/ 前缀）"""
        actual = model_name.split("/", 1)[-1].lower()
        return actual in _GEMINI_IMAGE_MODELS

    @staticmethod
    def _gemini_resolve_size(actual_name: str, size_wxh: str) -> tuple[str, str]:
        """根据模型名和期望 WxH 解析出 (aspect_ratio, image_size)。

        flash 模型：aspectRatio 按 W:H 比例从 10 种里选最接近，imageSize 恒 "1K"。
        3-pro 模型：aspectRatio 同 flash；imageSize 按长边归类（<=1100→1K、<=2300→2K、否则 4K）。
        """
        try:
            w_str, h_str = size_wxh.lower().split("x")
            w, h = int(w_str), int(h_str)
        except Exception:
            logger.warning(f"[Gemini] size 解析失败回退 1024x1024: size_wxh={size_wxh}")
            w, h = 1024, 1024

        # 选最接近的 aspectRatio：比例主导（0.85），log 面积兜底（0.15）避免方向错选
        target_ratio = w / h if h else 1.0
        target_log_area = math.log(max(w * h, 1))
        best_ratio, best_score = "1:1", float("inf")
        for ratio, (w0, h0) in _GEMINI_ASPECT_RATIOS.items():
            score = abs(target_ratio - w0 / h0) * 0.85 + abs(target_log_area - math.log(w0 * h0)) * 0.15
            if score < best_score:
                best_ratio, best_score = ratio, score

        # imageSize
        if actual_name.lower() == "gemini-3-pro-image-preview":
            long_edge = max(w, h)
            image_size = "1K" if long_edge < 1500 else ("2K" if long_edge < 3000 else "4K")
        else:
            image_size = "1K"

        return best_ratio, image_size

    @staticmethod
    def _build_jd_gemini_payload(
        prompt: str,
        image_urls: Optional[list[str]],
        aspect_ratio: str,
        image_size: str,
    ) -> dict:
        """构造 Gemini 文生图 / 图生图请求体。

        image_urls 为空 → 文生图；非空 → 在 text part 后追加 fileData。
        """
        parts: list[dict] = [{"text": prompt}]
        if image_urls:
            for url in image_urls:
                ext = url.split("?")[0].rsplit(".", 1)[-1].lower() if "." in url else ""
                mime = _URL_EXT_TO_MIME.get(ext, "image/jpeg")
                parts.append({"fileData": {"mimeType": mime, "fileUri": url}})

        return {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {
                "responseModalities": ["TEXT", "IMAGE"],
                "imageConfig": {"aspectRatio": aspect_ratio, "imageSize": image_size},
            },
        }

    @staticmethod
    def _call_jd_gemini_image_sync(
        payload: dict, api_key: str, api_base: str, timeout: int,
    ) -> dict:
        """同步调用 Gemini 图片 API。api_base 为 DB 配置的完整 URL，直接使用不拼接。"""
        action = "图生图" if any("fileData" in p for p in payload["contents"][0]["parts"]) else "文生图"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        logger.info(f"[同步{action}] request={payload} api_base={api_base}")
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(api_base, headers=headers, json=payload)
            # logger.debug(f"[同步{action}] resp={resp.text}")
            if resp.status_code != 200:
                raise RuntimeError(
                    f"Gemini {action}调用失败 HTTP {resp.status_code}: {resp.text}"
                )
            return resp.json()

    @staticmethod
    async def _acall_jd_gemini_image(
        payload: dict, api_key: str, api_base: str, timeout: int,
    ) -> dict:
        """异步调用 Gemini 图片 API。api_base 为 DB 配置的完整 URL，直接使用不拼接。"""
        action = "图生图" if any("fileData" in p for p in payload["contents"][0]["parts"]) else "文生图"
        headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "Authorization": f"Bearer {api_key}",
        }
        logger.info(f"[异步{action}] request={payload}")
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(api_base, headers=headers, json=payload)
            # logger.debug(f"[异步{action}] resp={resp.text}")
            if resp.status_code != 200:
                raise RuntimeError(
                    f"Gemini {action}调用失败 HTTP {resp.status_code}: {resp.text}"
                )
            return resp.json()

    @staticmethod
    def _normalize_gemini_response(raw: dict, actual_name: str) -> dict:
        """Gemini 原生响应 → litellm ImageResponse.model_dump() 兼容 dict。

        顶层同时挂 litellm 标准字段（id/data/usage）和 Gemini 原生字段
        （candidates/usageMetadata/modelVersion/responseId），
        让 _build_image_response_body 把除 data[].b64_json 之外的所有字段写入日志表。
        """
        # 提取 inlineData（图片）
        candidates = raw.get("candidates") or []
        parts = (candidates[0].get("content", {}) or {}).get("parts", []) if candidates else []
        data = [
            {"b64_json": p["inlineData"]["data"], "content_type": p["inlineData"]["mimeType"]}
            for p in parts if isinstance(p, dict) and p.get("inlineData")
        ]
        if not data:
            logger.warning(f"[Gemini] 响应无 inlineData，finishReason={candidates[0].get('finishReason') if candidates else None}")

        usage_raw = raw.get("usageMetadata") or {}

        def _sum_modality(details_list, modality: str) -> int:
            if not isinstance(details_list, list):
                return 0
            return sum(
                d.get("tokenCount", 0) for d in details_list
                if isinstance(d, dict) and d.get("modality") == modality
            )

        prompt_details = usage_raw.get("promptTokensDetails")
        candidates_details = usage_raw.get("candidatesTokensDetails")
        prompt_tokens = usage_raw.get("promptTokenCount", 0)
        completion_tokens = usage_raw.get("candidatesTokenCount", 0)

        return {
            # litellm 标准字段
            "id": raw.get("responseId") or "",
            "model": actual_name,
            "created": int(time.time()),
            "data": data,
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": usage_raw.get("totalTokenCount", prompt_tokens + completion_tokens),
                "input_tokens_details": {
                    "text_tokens": _sum_modality(prompt_details, "TEXT"),
                    "image_tokens": _sum_modality(prompt_details, "IMAGE"),
                },
                "output_tokens_details": {
                    "text_tokens": _sum_modality(candidates_details, "TEXT"),
                    "image_tokens": _sum_modality(candidates_details, "IMAGE"),
                },
            },
            # Gemini 原生字段透传（_build_image_response_body 会原样写入日志表）
            "candidates": raw.get("candidates"),
            "usageMetadata": raw.get("usageMetadata"),
            "modelVersion": raw.get("modelVersion"),
            "responseId": raw.get("responseId"),
        }

    def edit_image(
        self,
        model_key: str,
        prompt: str,
        image_urls: list[str],
        size: str = "2048x2048",
        n: int = 1,
        timeout: int = 300,
        project_id: Optional[str] = None,
        task_id: Optional[str] = None,
        model_name_override: Optional[str] = None,
    ) -> dict:
        """图生图"""
        request_id = str(uuid.uuid4())
        m = self._resolve_model(model_key, model_name_override=model_name_override)

        logger.debug(f"[图生图] edit_image 开始: request_id={request_id} model_key={model_key} model_name={m.model_name} db={'有' if self.db else 'None'}")

        # gpt-image-2 走专用 HTTP 端点；同步抓取每张输入图尺寸写入 input_media
        is_gpt_image_2 = self._is_gpt_image_2_model(m.model_name)
        is_gemini_image = self._is_gemini_image_model(m.model_name)
        if is_gpt_image_2:
            from app.utils.media_info_utils import get_image_info_from_url
            input_media = [get_image_info_from_url(url) for url in image_urls]
        else:
            input_media = [{"type": "image", "url": url} for url in image_urls]

        log_record = {
            "id": str(uuid.uuid4()),
            "user_id": getattr(self.config, "user_id", "system"),
            "project_id": project_id,
            "task_id": task_id,
            "request_id": request_id,
            "model_provider": m.provider_code,
            "model_name": m.model_name,
            "endpoint": m.api_base or f"litellm:///{m.provider_code}",
            "api_key_masked": self._mask_api_key(m.api_key or ""),
            "media_type": "image_image",
            "input_media": input_media,
            "request_body": {
                "prompt_preview": prompt[:2000],
                "reference_images": len(image_urls),
                "size": size,
                "n": n,
            },
        }

        billing_user_id = self._get_billing_user_id()
        estimated_point = Decimal("0")

        logger.debug(f"[图生图] billing_user_id={billing_user_id}")

        if billing_user_id:
            try:
                # gpt-image-2 按token计费，需根据prompt预估；其它图片模型按张数计费
                if self._is_token_billing_image_model(m.model_name):
                    estimated_point = self._estimate_points(m.model_name, prompt=prompt)
                else:
                    estimated_point = self._estimate_points(m.model_name, n=n, is_character=False, size=size, input_n=len(image_urls))
                logger.debug(f"[图生图] estimated_point={estimated_point}")
                self._pre_deduct(billing_user_id, estimated_point, source_id=request_id)
            except Exception as e:
                logger.warning(f"[图生图] 积分预扣失败: {e}")
                call_time = datetime.now()
                log_record.update({
                    "call_time": call_time.isoformat(),
                    "latency_ms": 0,
                    "error_message": str(e),
                    "point": 0,
                })
                model_call_log_writer.write(log_record)
                raise

        call_time = datetime.now()
        start = time.monotonic()
        try:
            if is_gpt_image_2:
                result = self._call_jd_gpt_image_2_edit_sync(
                    prompt=prompt,
                    image_urls=image_urls,
                    size=size,
                    n=n,
                    api_key=m.api_key,
                    api_base=m.api_base,
                    timeout=timeout,
                )
            elif is_gemini_image:
                actual = m.model_name.split("/", 1)[-1]
                aspect_ratio, image_size = self._gemini_resolve_size(actual, size)
                payload = self._build_jd_gemini_payload(
                    prompt=prompt,
                    image_urls=image_urls,
                    aspect_ratio=aspect_ratio,
                    image_size=image_size,
                )
                raw = self._call_jd_gemini_image_sync(
                    payload=payload,
                    api_key=m.api_key,
                    api_base=m.api_base,
                    timeout=timeout,
                )
                result = self._normalize_gemini_response(raw, actual)
            else:
                response = litellm.image_generation(
                    model=m.model_name,
                    prompt=prompt,
                    size=size,
                    n=n,
                    image=image_urls,
                    timeout=timeout,
                    api_key=m.api_key,
                    api_base=m.api_base,
                    custom_llm_provider=m.custom_llm_provider,
                )
                result = response.model_dump()
            # logger.info(f"[同步图生图] result={self._build_image_response_body(result)}")
            latency_ms = int((time.monotonic() - start) * 1000)

            # 提取输出图片元信息
            from app.utils.media_info_utils import parse_image_gen_output
            output_media = parse_image_gen_output(result.get("data") or [], size)

            # 提取 usage（gpt-image-2 走 result["usage_metadata"]，litellm 走 result["usage"]）
            input_tokens, output_tokens, total_tokens, usage_dict = self._extract_image_usage(result)

            logger.info(f"[同步图生图] usage_dict={usage_dict}")
            logger.debug(f"[同步图生图] input_tokens={input_tokens}, output_tokens={output_tokens}, total_tokens={total_tokens}")

            # 从usage_dict中提取计算积分所需字段
            input_text_tokens = usage_dict.get("input_tokens_details").get("text_tokens")
            input_image_tokens = usage_dict.get("input_tokens_details").get("image_tokens")

            # gpt-image-2 按实际token结算（多退少补）；其它图片模型预扣即最终
            actual_point = estimated_point
            if self._is_token_billing_image_model(m.model_name) and billing_user_id:
                if is_gpt_image_2:
                    actual_point = self._calculate_actual_points_for_image2(m.model_name, input_text_tokens, input_image_tokens, output_tokens)
                elif is_gemini_image:
                    actual_point = self._calculate_actual_points_for_banana(m.model_name, output_tokens)
                else:
                    logger.warning(f"[图生图] 模型判断错误，没有计算实际积分消耗。")

                try:
                    self._settle(billing_user_id, estimated_point, actual_point, source_id=request_id)
                except Exception as settle_err:
                    logger.warning(f"[图生图] 积分结算失败 error={settle_err} user_id={billing_user_id}")

            log_record.update({
                "call_time": call_time.isoformat(),
                "provider_request_id": self._extract_image_request_id(result),
                "response_status": 200,
                "response_body": self._build_image_response_body(result),
                "latency_ms": latency_ms,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
                "usage_details": usage_dict,
                "output_media": output_media,
                "point": float(actual_point),
                "_skip_auto_billing": True,
            })
            logger.debug(f"[图生图] 写入 model_call_log: request_id={request_id} point={actual_point} estimated={estimated_point}")
            model_call_log_writer.write(log_record)
            return result
        except Exception as e:
            if billing_user_id and estimated_point > 0:
                try:
                    self._refund(billing_user_id, estimated_point, source_id=request_id)
                except Exception as refund_err:
                    logger.warning(f"退还预扣积分失败 error={refund_err} user_id={billing_user_id}")

            latency_ms = int((time.monotonic() - start) * 1000)
            log_record.update({
                "call_time": call_time.isoformat(),
                "latency_ms": latency_ms,
                "error_message": str(e),
            })
            model_call_log_writer.write(log_record)
            raise

    def vision(
        self,
        model_key: str,
        prompt: str,
        image_urls: list[str],
        temperature: float = 0.3,
        max_tokens: int = 4096,
        timeout: int = 180,
        project_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> ModelResult:
        """图文理解（vision）"""
        request_id = str(uuid.uuid4())
        logger.debug(f"[vision] 开始: request_id={request_id} model_key={model_key} db={'有' if self.db else 'None'}")
        content: list[dict] = [{"type": "text", "text": prompt}]
        for url in image_urls:
            content.append({"type": "image_url", "image_url": {"url": url}})

        m = self._resolve_model(model_key)

        # 记录输入图片信息
        from app.utils.media_info_utils import parse_vision_input
        input_media = parse_vision_input(image_urls)

        log_record = {
            "id": str(uuid.uuid4()),
            "user_id": getattr(self.config, "user_id", "system"),
            "project_id": project_id,
            "task_id": task_id,
            "request_id": request_id,
            "model_provider": m.provider_code,
            "model_name": m.model_name,
            "endpoint": m.api_base or f"litellm:///{m.provider_code}",
            "api_key_masked": self._mask_api_key(m.api_key or ""),
            "media_type": "image_text",
            "input_media": input_media,
            "request_body": {
                "prompt_preview": prompt[:2000],
                "image_count": len(image_urls),
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
        }

        billing_user_id = self._get_billing_user_id()
        estimated_point = Decimal("0")

        logger.debug(f"[vision] billing_user_id={billing_user_id}")

        if billing_user_id:
            try:
                estimated_point = self._estimate_points(m.model_name, prompt=prompt, max_tokens=max_tokens)
                logger.debug(f"[vision] estimated_point={estimated_point}")
                self._pre_deduct(billing_user_id, estimated_point, source_id=request_id)
            except Exception as e:
                logger.warning(f"[vision] 积分预扣失败: {e}")
                call_time = datetime.now()
                log_record.update({
                    "call_time": call_time.isoformat(),
                    "latency_ms": 0,
                    "error_message": str(e),
                    "point": 0,
                })
                model_call_log_writer.write(log_record)
                raise

        call_time = datetime.now()
        start = time.monotonic()
        try:
            response = litellm.completion(
                model=m.model_name,
                messages=[{"role": "user", "content": content}],
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
                api_key=m.api_key,
                api_base=m.api_base,
                custom_llm_provider=m.custom_llm_provider,
                max_retries=0,
            )

            content_text = response.choices[0].message.content
            usage = response.usage
            latency_ms = int((time.monotonic() - start) * 1000)

            input_tokens = usage.prompt_tokens if usage else 0
            output_tokens = usage.completion_tokens if usage else 0

            actual_point = estimated_point
            if billing_user_id and usage and (input_tokens or output_tokens):
                actual_point = self._calculate_actual_points(m.model_name, input_tokens, output_tokens)
                self._settle(billing_user_id, estimated_point, actual_point, source_id=request_id)

            log_record.update({
                "call_time": call_time.isoformat(),
                "provider_request_id": getattr(response, "id", None),
                "response_status": 200,
                "response_body": {"result_preview": content_text[:2000], "result_full": content_text},
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": usage.total_tokens if usage else 0,
                "latency_ms": latency_ms,
                "point": float(actual_point),
                "_skip_auto_billing": True,
            })
            logger.debug(f"[vision] 写入 model_call_log: request_id={request_id} point={actual_point}")
            model_call_log_writer.write(log_record)

            return ModelResult(
                content=content_text,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=usage.total_tokens if usage else 0,
            )
        except Exception as e:
            if billing_user_id and estimated_point > 0:
                try:
                    self._refund(billing_user_id, estimated_point, source_id=request_id)
                except Exception as refund_err:
                    logger.warning(f"退还预扣积分失败 error={refund_err} user_id={billing_user_id}")

            latency_ms = int((time.monotonic() - start) * 1000)
            log_record.update({
                "call_time": call_time.isoformat(),
                "latency_ms": latency_ms,
                "error_message": str(e),
            })
            model_call_log_writer.write(log_record)
            raise

    # ==================== 异步方法 ====================

    async def acall(
        self,
        model_key: str,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 8192,
        timeout: int = 180,
        project_id: Optional[str] = None,
        task_id: Optional[str] = None,
        media_type_override: Optional[str] = None,
        input_media_override: Optional[list] = None,
    ) -> ModelResult:
        """异步文生文调用"""
        request_id = str(uuid.uuid4())
        m = self._resolve_model(model_key)

        api_base = m.api_base or ""

        log_record = {
            "id": str(uuid.uuid4()),
            "user_id": getattr(self.config, "user_id", "system"),
            "project_id": project_id,
            "task_id": task_id,
            "request_id": request_id,
            "model_provider": m.provider_code,
            "model_name": m.model_name,
            "endpoint": api_base or f"litellm:///{m.provider_code}",
            "api_key_masked": self._mask_api_key(m.api_key or ""),
            "media_type": media_type_override or "text_text",
            "request_body": {
                "messages_count": len(messages),
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
        }
        if input_media_override:
            log_record["input_media"] = input_media_override

        billing_user_id = self._get_billing_user_id()
        estimated_point = Decimal("0")

        if billing_user_id:
            try:
                estimated_point = self._estimate_points(
                    m.model_name, messages=messages, max_tokens=max_tokens,
                )
                self._pre_deduct(billing_user_id, estimated_point, source_id=request_id)
            except Exception as e:
                call_time = datetime.now()
                log_record.update({
                    "call_time": call_time.isoformat(),
                    "latency_ms": 0,
                    "error_message": str(e),
                    "point": 0,
                })
                model_call_log_writer.write(log_record)
                raise

        call_time = datetime.now()
        start = time.monotonic()
        try:
            response = await litellm.acompletion(
                model=m.model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
                api_key=m.api_key,
                api_base=m.api_base,
                custom_llm_provider=m.custom_llm_provider,
            )

            content = response.choices[0].message.content
            usage = response.usage
            latency_ms = int((time.monotonic() - start) * 1000)

            input_tokens = usage.prompt_tokens if usage else 0
            output_tokens = usage.completion_tokens if usage else 0
            total_tokens = usage.total_tokens if usage else 0

            actual_point = estimated_point
            if billing_user_id and usage and (input_tokens or output_tokens):
                actual_point = self._calculate_actual_points(m.model_name, input_tokens, output_tokens)
                self._settle(billing_user_id, estimated_point, actual_point, source_id=request_id)

            log_record.update({
                "call_time": call_time.isoformat(),
                "provider_request_id": getattr(response, "id", None),
                "response_status": 200,
                "response_body": {"result_preview": content[:2000], "result_full": content},
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
                "latency_ms": latency_ms,
                "point": float(actual_point),
                "_skip_auto_billing": True,
            })
            model_call_log_writer.write(log_record)

            return ModelResult(
                content=content,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
            )
        except Exception as e:
            if billing_user_id and estimated_point > 0:
                try:
                    self._refund(billing_user_id, estimated_point, source_id=request_id)
                except Exception as refund_err:
                    logger.warning(f"退还预扣积分失败 error={refund_err} user_id={billing_user_id}")

            latency_ms = int((time.monotonic() - start) * 1000)
            log_record.update({
                "call_time": call_time.isoformat(),
                "latency_ms": latency_ms,
                "error_message": str(e),
            })
            model_call_log_writer.write(log_record)
            raise self._to_llm_error(e) from e

    async def avision(
        self,
        model_key: str,
        text_prompt: str,
        image_urls: list[str],
        temperature: float = 0.3,
        max_tokens: int = 4096,
        timeout: int = 180,
        project_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> ModelResult:
        """异步视觉理解调用"""
        content: list[dict] = [{"type": "text", "text": text_prompt}]
        for url in image_urls:
            content.append({"type": "image_url", "image_url": {"url": url}})

        messages = [{"role": "user", "content": content}]
        return await self.acall(
            model_key, messages,
            temperature=temperature, max_tokens=max_tokens, timeout=timeout,
            project_id=project_id, task_id=task_id,
            media_type_override="image_text",
            input_media_override=[{"type": "image", "url": url} for url in image_urls],
        )

    async def aimage_gen(
        self,
        model_key: str,
        prompt: str,
        size: str = "2400x1600",
        n: int = 1,
        timeout: int = 300,
        project_id: Optional[str] = None,
        task_id: Optional[str] = None,
        is_character: bool = False,
    ) -> dict:
        """异步文生图调用，返回 litellm 原始响应 dict"""
        request_id = str(uuid.uuid4())
        m = self._resolve_model(model_key)
        logger.debug(f"[aimage_gen] 开始: request_id={request_id} model_key={model_key} model_name={m.model_name} is_character={is_character} n={n} db={'有' if self.db else 'None'}")

        api_base = m.api_base or ""
        is_gpt_image_2 = self._is_gpt_image_2_model(m.model_name)
        is_gemini_image = self._is_gemini_image_model(m.model_name)

        log_record = {
            "id": str(uuid.uuid4()),
            "user_id": getattr(self.config, "user_id", "system"),
            "project_id": project_id,
            "task_id": task_id,
            "request_id": request_id,
            "model_provider": m.provider_code,
            "model_name": m.model_name,
            "endpoint": api_base or f"litellm:///{m.provider_code}",
            "api_key_masked": self._mask_api_key(m.api_key or ""),
            "media_type": "text_image",
            "request_body": {
                "prompt_preview": prompt[:2000],
                "size": size,
                "n": n,
                "is_character": is_character,
            },
        }

        billing_user_id = self._get_billing_user_id()
        estimated_point = Decimal("0")

        if billing_user_id:
            try:
                # gpt-image-2 按token计费，需根据prompt预估；其它图片模型按张数计费
                if self._is_token_billing_image_model(m.model_name):
                    estimated_point = self._estimate_points(m.model_name, prompt=prompt)
                else:
                    estimated_point = self._estimate_points(m.model_name, n=n, is_character=is_character, size=size)

                self._pre_deduct(billing_user_id, estimated_point, source_id=request_id)
            except Exception as e:
                call_time = datetime.now()
                log_record.update({
                    "call_time": call_time.isoformat(),
                    "latency_ms": 0,
                    "error_message": str(e),
                    "point": 0,
                })
                model_call_log_writer.write(log_record)
                raise

        call_time = datetime.now()
        start = time.monotonic()
        try:
            if is_gpt_image_2:
                result = await self._acall_jd_gpt_image_2_gen(
                    prompt=prompt,
                    size=size,
                    n=n,
                    api_key=m.api_key,
                    api_base=m.api_base,
                    timeout=timeout,
                )
            elif is_gemini_image:
                actual = m.model_name.split("/", 1)[-1]
                aspect_ratio, image_size = self._gemini_resolve_size(actual, size)
                payload = self._build_jd_gemini_payload(
                    prompt=prompt,
                    image_urls=None,
                    aspect_ratio=aspect_ratio,
                    image_size=image_size,
                )
                raw = await self._acall_jd_gemini_image(
                    payload=payload,
                    api_key=m.api_key,
                    api_base=m.api_base,
                    timeout=timeout,
                )
                result = self._normalize_gemini_response(raw, actual)
            else:
                response = await litellm.aimage_generation(
                    model=m.model_name,
                    prompt=prompt,
                    size=size,
                    n=n,
                    timeout=timeout,
                    api_key=m.api_key,
                    api_base=m.api_base,
                    custom_llm_provider=m.custom_llm_provider,
                )
                result = response.model_dump()

            # logger.info(f"[异步文生图] result={self._build_image_response_body(result)}")
            latency_ms = int((time.monotonic() - start) * 1000)

            # 提取输出图片元信息
            from app.utils.media_info_utils import parse_image_gen_output
            output_media = parse_image_gen_output(result.get("data") or [], size)

            # 提取 usage（gpt-image-2 走 result["usage_metadata"]，litellm 走 result["usage"]）
            input_tokens, output_tokens, total_tokens, usage_dict = self._extract_image_usage(result)
            logger.info(f"[异步文生图] usage_dict={usage_dict}")
            logger.debug(f"[异步文生图] input_tokens={input_tokens}, output_tokens={output_tokens}, total_tokens={total_tokens}")

            # 从usage_dict中提取计算积分所需字段
            input_text_tokens = usage_dict.get("input_tokens_details").get("text_tokens")
            input_image_tokens = usage_dict.get("input_tokens_details").get("image_tokens")

            # gpt-image-2 按实际token结算（多退少补）；其它图片模型预扣即最终
            actual_point = estimated_point
            if self._is_token_billing_image_model(m.model_name) and billing_user_id:
                if is_gpt_image_2:
                    actual_point = self._calculate_actual_points_for_image2(m.model_name, input_text_tokens, input_image_tokens, output_tokens)
                elif is_gemini_image:
                    actual_point = self._calculate_actual_points_for_banana(m.model_name, output_tokens)
                else:
                    logger.warning(f"[异步文生图] 模型判断错误，没有计算实际积分消耗。")

                try:
                    self._settle(billing_user_id, estimated_point, actual_point, source_id=request_id)
                except Exception as settle_err:
                    logger.warning(f"[异步文生图] 积分结算失败 error={settle_err} user_id={billing_user_id}")

            log_record.update({
                "call_time": call_time.isoformat(),
                "provider_request_id": self._extract_image_request_id(result),
                "response_status": 200,
                "response_body": self._build_image_response_body(result),
                "latency_ms": latency_ms,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
                "usage_details": usage_dict,
                "output_media": output_media,
                "point": float(actual_point),
                "_skip_auto_billing": True,
            })
            model_call_log_writer.write(log_record)

            return result
        except Exception as e:
            if billing_user_id and estimated_point > 0:
                try:
                    self._refund(billing_user_id, estimated_point, source_id=request_id)
                except Exception as refund_err:
                    logger.warning(f"退还预扣积分失败 error={refund_err} user_id={billing_user_id}")

            latency_ms = int((time.monotonic() - start) * 1000)
            log_record.update({
                "call_time": call_time.isoformat(),
                "latency_ms": latency_ms,
                "error_message": str(e),
            })
            model_call_log_writer.write(log_record)
            raise self._to_llm_error(e) from e

    async def aimage_edit(
        self,
        model_key: str,
        prompt: str,
        image_urls: list[str],
        size: str = "2400x1600",
        n: int = 1,
        timeout: int = 300,
        project_id: Optional[str] = None,
        task_id: Optional[str] = None,
        is_character: bool = False,
    ) -> dict:
        """异步图生图调用，返回 litellm 原始响应 dict"""
        request_id = str(uuid.uuid4())
        m = self._resolve_model(model_key)

        api_base = m.api_base or ""

        # gpt-image-2 走专用 HTTP 端点；并发抓取每张输入图尺寸写入 input_media
        is_gpt_image_2 = self._is_gpt_image_2_model(m.model_name)
        is_gemini_image = self._is_gemini_image_model(m.model_name)
        if is_gpt_image_2:
            from app.utils.media_info_utils import get_image_info_from_url
            input_media = await asyncio.gather(
                *[asyncio.to_thread(get_image_info_from_url, url) for url in image_urls]
            )
        else:
            input_media = [{"type": "image", "url": url} for url in image_urls]

        log_record = {
            "id": str(uuid.uuid4()),
            "user_id": getattr(self.config, "user_id", "system"),
            "project_id": project_id,
            "task_id": task_id,
            "request_id": request_id,
            "model_provider": m.provider_code,
            "model_name": m.model_name,
            "endpoint": api_base or f"litellm:///{m.provider_code}",
            "api_key_masked": self._mask_api_key(m.api_key or ""),
            "media_type": "image_image",
            "input_media": input_media,
            "request_body": {
                "prompt_preview": prompt[:2000],
                "reference_images": len(image_urls),
                "size": size,
                "n": n,
                "is_character": is_character,
            },
        }

        billing_user_id = self._get_billing_user_id()
        estimated_point = Decimal("0")

        if billing_user_id:
            try:
                # gpt-image-2 按token计费，需根据prompt预估；其它图片模型按张数计费
                if self._is_token_billing_image_model(m.model_name):
                    estimated_point = self._estimate_points(m.model_name, prompt=prompt, image_info_list=input_media)
                else:
                    estimated_point = self._estimate_points(m.model_name, n=n, is_character=is_character, size=size, input_n=len(image_urls))
                self._pre_deduct(billing_user_id, estimated_point, source_id=request_id)
            except Exception as e:
                call_time = datetime.now()
                log_record.update({
                    "call_time": call_time.isoformat(),
                    "latency_ms": 0,
                    "error_message": str(e),
                    "point": 0,
                })
                model_call_log_writer.write(log_record)
                raise

        call_time = datetime.now()
        start = time.monotonic()
        try:
            if is_gpt_image_2:
                result = await self._acall_jd_gpt_image_2_edit(
                    prompt=prompt,
                    image_urls=image_urls,
                    size=size,
                    n=n,
                    api_key=m.api_key,
                    api_base=m.api_base,
                    timeout=timeout,
                )
            elif is_gemini_image:
                actual = m.model_name.split("/", 1)[-1]
                aspect_ratio, image_size = self._gemini_resolve_size(actual, size)
                payload = self._build_jd_gemini_payload(
                    prompt=prompt,
                    image_urls=image_urls,
                    aspect_ratio=aspect_ratio,
                    image_size=image_size,
                )
                raw = await self._acall_jd_gemini_image(
                    payload=payload,
                    api_key=m.api_key,
                    api_base=m.api_base,
                    timeout=timeout,
                )
                result = self._normalize_gemini_response(raw, actual)
            else:
                response = await litellm.aimage_generation(
                    model=m.model_name,
                    prompt=prompt,
                    image=image_urls,
                    size=size,
                    n=n,
                    timeout=timeout,
                    api_key=m.api_key,
                    api_base=m.api_base,
                    custom_llm_provider=m.custom_llm_provider,
                )
                result = response.model_dump()

            # logger.info(f"[异步图生图] result={self._build_image_response_body(result)}")
            latency_ms = int((time.monotonic() - start) * 1000)

            # 提取输出图片元信息
            from app.utils.media_info_utils import parse_image_gen_output
            output_media = parse_image_gen_output(result.get("data") or [], size)

            # 提取 usage（gpt-image-2 走 result["usage_metadata"]，litellm 走 result["usage"]）
            input_tokens, output_tokens, total_tokens, usage_dict = self._extract_image_usage(result)

            logger.info(f"[异步图生图] usage_dict={usage_dict}")
            logger.debug(f"[异步图生图] input_tokens={input_tokens}, output_tokens={output_tokens}, total_tokens={total_tokens}")

            # 从usage_dict中提取计算积分所需字段
            input_text_tokens = usage_dict.get("input_tokens_details").get("text_tokens")
            input_image_tokens = usage_dict.get("input_tokens_details").get("image_tokens")

            # gpt-image-2 按实际token结算（多退少补）；其它图片模型预扣即最终
            actual_point = estimated_point
            if self._is_token_billing_image_model(m.model_name) and billing_user_id:
                if is_gpt_image_2:
                    actual_point = self._calculate_actual_points_for_image2(m.model_name, input_text_tokens, input_image_tokens, output_tokens)
                elif is_gemini_image:
                    actual_point = self._calculate_actual_points_for_banana(m.model_name, output_tokens)
                else:
                    logger.warning(f"[异步图生图] 模型判断错误，没有计算实际积分消耗。")

                try:
                    self._settle(billing_user_id, estimated_point, actual_point, source_id=request_id)
                except Exception as settle_err:
                    logger.warning(f"[异步图生图] 积分结算失败 error={settle_err} user_id={billing_user_id}")

            log_record.update({
                "call_time": call_time.isoformat(),
                "provider_request_id": self._extract_image_request_id(result),
                "response_status": 200,
                "response_body": self._build_image_response_body(result),
                "latency_ms": latency_ms,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
                "usage_details": usage_dict,
                "output_media": output_media,
                "point": float(actual_point),
                "_skip_auto_billing": True,
            })
            model_call_log_writer.write(log_record)

            return result
        except Exception as e:
            if billing_user_id and estimated_point > 0:
                try:
                    self._refund(billing_user_id, estimated_point, source_id=request_id)
                except Exception as refund_err:
                    logger.warning(f"退还预扣积分失败 error={refund_err} user_id={billing_user_id}")

            latency_ms = int((time.monotonic() - start) * 1000)
            log_record.update({
                "call_time": call_time.isoformat(),
                "latency_ms": latency_ms,
                "error_message": str(e),
            })
            model_call_log_writer.write(log_record)
            raise self._to_llm_error(e) from e

    # ==================== 音色设计 ====================

    async def avoice_design(
        self,
        model_key: str,
        voice_prompt: str,
        preview_text: str,
        preferred_name: str,
        language: str = "zh",
        sample_rate: int = 24000,
        timeout: int = 180,
        project_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> dict:
        """
        异步音色设计调用

        根据配置的 audio_model 路由到对应 provider:
        - volcengine: 火山引擎音色设计 API
        - dashscope: 阿里百炼声音定制 API

        Returns:
            dict: {speaker_id, audio_base64, sample_rate, audio_format}
        """
        from app.services.voice_design import (
            VoiceDesignError,
            call_dashscope_voice_design,
            call_volcengine_voice_design,
            generate_speaker_id,
        )

        request_id = str(uuid.uuid4())
        m = self._resolve_model(model_key)

        api_key = m.api_key or ""
        api_base = m.api_base or ""

        log_record = {
            "id": str(uuid.uuid4()),
            "user_id": getattr(self.config, "user_id", "system"),
            "project_id": project_id,
            "task_id": task_id,
            "request_id": request_id,
            "model_provider": m.provider_code,
            "model_name": m.model_name,
            "endpoint": api_base or f"voice_design:///{m.provider_code}",
            "api_key_masked": self._mask_api_key(api_key),
            "request_body": {
                "voice_prompt_preview": voice_prompt[:200],
                "preview_text_preview": preview_text[:100],
                "preferred_name": preferred_name,
                "language": language,
                "sample_rate": sample_rate,
            },
        }

        print(f"[音色设计] model_key={model_key} model_name={m.model_name} provider={m.provider_code}")
        print(f"[音色设计] voice_prompt={voice_prompt}")

        billing_user_id = self._get_billing_user_id()
        estimated_point = Decimal("0")

        if billing_user_id:
            try:
                estimated_point = self._estimate_points(m.model_name)
                self._pre_deduct(billing_user_id, estimated_point, source_id=request_id)
            except Exception as e:
                call_time = datetime.now()
                log_record.update({
                    "call_time": call_time.isoformat(),
                    "latency_ms": 0,
                    "error_message": str(e),
                    "point": 0,
                })
                model_call_log_writer.write(log_record)
                raise

        call_time = datetime.now()
        start = time.monotonic()
        try:
            speaker_id = preferred_name

            if m.provider_code == "volcengine":
                if not api_key:
                    api_key = getattr(self.config, "ark_api_key", None)
                result = await call_volcengine_voice_design(
                    api_key=api_key,
                    voice_prompt=voice_prompt,
                    preview_text=preview_text,
                    speaker_id=speaker_id,
                    language=language,
                    sample_rate=sample_rate,
                    timeout=timeout,
                )
            elif m.provider_code == "dashscope":
                if not api_key:
                    api_key = getattr(self.config, "qwen_api_key", None)
                result = await call_dashscope_voice_design(
                    api_key=api_key,
                    voice_prompt=voice_prompt,
                    preview_text=preview_text,
                    preferred_name=speaker_id,
                    language=language,
                    sample_rate=sample_rate,
                    timeout=timeout,
                )
            else:
                raise VoiceDesignError(
                    f"音色设计不支持 provider: {m.provider_code}，仅支持 volcengine/dashscope"
                )

            latency_ms = int((time.monotonic() - start) * 1000)

            print(f"[音色设计] 成功: speaker_id={result.speaker_id} audio_size={len(result.audio_base64)} latency={latency_ms}ms")

            log_record.update({
                "call_time": call_time.isoformat(),
                "response_status": 200,
                "latency_ms": latency_ms,
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "point": float(estimated_point),
                "_skip_auto_billing": True,
            })
            model_call_log_writer.write(log_record)

            return {
                "speaker_id": result.speaker_id,
                "audio_base64": result.audio_base64,
                "sample_rate": result.sample_rate,
                "audio_format": result.audio_format,
            }
        except Exception as e:
            if billing_user_id and estimated_point > 0:
                try:
                    self._refund(billing_user_id, estimated_point, source_id=request_id)
                except Exception as refund_err:
                    logger.warning(f"退还预扣积分失败 error={refund_err} user_id={billing_user_id}")

            latency_ms = int((time.monotonic() - start) * 1000)
            log_record.update({
                "call_time": call_time.isoformat(),
                "latency_ms": latency_ms,
                "error_message": str(e),
            })
            model_call_log_writer.write(log_record)
            raise self._to_llm_error(e) from e

    @staticmethod
    def _to_llm_error(exc: Exception) -> Exception:
        """将原始异常转换为 LLMError 体系"""
        from app.services.llm import (
            InsufficientBalanceError,
            LLMConfigError,
            LLMError,
            LLMRateLimitError,
            LLMServiceError,
        )

        if isinstance(exc, LLMError):
            return exc

        msg = str(exc).lower()
        if "api key" in msg or "unauthorized" in msg or "未配置" in msg:
            return LLMConfigError(str(exc))
        if "rate" in msg or "429" in msg or "too many" in msg:
            return LLMRateLimitError(str(exc))
        if "timeout" in msg or "503" in msg or "502" in msg:
            return LLMServiceError(str(exc))
        return LLMServiceError(str(exc))
