import json
import re
from decimal import Decimal

import json_repair
from loguru import logger

from app.core.config import settings


# ==================== 异常定义 ====================

class LLMError(Exception):
    def __init__(self, message: str, retryable: bool = False, provider: str = ""):
        super().__init__(message)
        self.retryable = retryable
        self.provider = provider


class LLMConfigError(LLMError):
    def __init__(self, message: str, provider: str = ""):
        super().__init__(message, retryable=False, provider=provider)


class LLMContentFilterError(LLMError):
    def __init__(self, message: str = "内容被安全过滤，请修改输入", provider: str = ""):
        super().__init__(message, retryable=False, provider=provider)


class LLMResponseError(LLMError):
    def __init__(self, message: str, provider: str = ""):
        super().__init__(message, retryable=True, provider=provider)


class LLMRateLimitError(LLMError):
    def __init__(self, message: str = "请求过于频繁，请稍后重试", provider: str = ""):
        super().__init__(message, retryable=True, provider=provider)


class LLMServiceError(LLMError):
    def __init__(self, message: str, provider: str = ""):
        super().__init__(message, retryable=True, provider=provider)


from app.services.point import InsufficientBalanceError


# ==================== Provider 配置 ====================

CONTENT_FILTER_KEYWORDS: dict[str, list[str]] = {
    "openai": ["content_policy", "safety", "content_filter"],
    "dashscope": ["DataInspectionFailed", "content_filter"],
    "siliconflow": ["content_policy", "safety"],
    "deepseek": ["content_policy"],
    "openrouter": ["content_policy", "safety"],
    "ark": ["content_filter", "safety", "policy"],
}


def _is_content_filter_error(error_str: str, provider: str) -> bool:
    lowered = error_str.lower()
    keywords = CONTENT_FILTER_KEYWORDS.get(provider, [])
    for kw in keywords:
        if kw.lower() in lowered:
            return True
    return False


# ==================== 响应提取 ====================

def _safe_extract_content(completion: dict) -> str | None:
    try:
        choices = completion.get("choices", [])
        if not choices:
            return None
        message = choices[0].get("message", {})
        content = message.get("content")
        if content is None:
            return None
        if isinstance(content, str):
            return content.strip() or None
        if isinstance(content, list):
            texts = []
            for part in content:
                if isinstance(part, dict):
                    text = part.get("text", "")
                    part_type = part.get("type", "text")
                    if text and part_type != "reasoning":
                        texts.append(text)
            return " ".join(texts).strip() or None
        return None
    except (KeyError, IndexError, TypeError) as e:
        logger.debug(f"[LLM] 内容提取异常: {e}")
        return None


def extract_content(completion: dict) -> str:
    content = _safe_extract_content(completion)
    if content is None:
        raise LLMResponseError("LLM 返回内容为空或格式异常")
    return content


def extract_json(completion: dict) -> dict:
    content = extract_content(completion)
    cleaned = _strip_markdown_fence(content)
    extracted = _extract_json_substring(cleaned)

    try:
        result = json_repair.loads(extracted)
        if isinstance(result, dict):
            return result
        if isinstance(result, list) and len(result) > 0:
            return result[0] if isinstance(result[0], dict) else {"items": result}
        return {"raw": result}
    except Exception as e:
        logger.warning(f"[LLM] JSON 解析失败: {e}, 原始内容: {content[:200]}")
        raise LLMResponseError(f"LLM 返回的 JSON 无法解析: {e}") from e


def _strip_markdown_fence(text: str) -> str:
    pattern = r"```(?:json)?\s*\n?(.*?)\n?\s*```"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()


def _extract_json_substring(text: str) -> str:
    text = text.strip()
    for open_char, close_char in [("{", "}"), ("[", "]")]:
        start = text.find(open_char)
        if start == -1:
            continue
        depth = 0
        for i in range(start, len(text)):
            if text[i] == open_char:
                depth += 1
            elif text[i] == close_char:
                depth -= 1
            if depth == 0:
                return text[start:i+1]
    return text
