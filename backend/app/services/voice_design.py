"""
音色设计 HTTP 客户端

支持两种 provider：
- volcengine: 火山引擎豆包语音音色设计 API
- dashscope: 阿里百炼 DashScope 声音定制 API
"""
import base64
import uuid
from dataclasses import dataclass

import httpx

from app.core.logging import logger


@dataclass
class VoiceDesignResult:
    """音色设计结果"""
    speaker_id: str
    audio_base64: str
    sample_rate: int
    audio_format: str


async def call_volcengine_voice_design(
    api_key: str,
    voice_prompt: str,
    preview_text: str,
    speaker_id: str,
    language: str = "zh",
    audio_format: str = "wav",
    sample_rate: int = 24000,
    timeout: int = 180,
) -> VoiceDesignResult:
    """
    调用火山引擎音色设计 API

    端点: https://openspeech.bytedance.com/api/v3/tts/voice_design
    文档: https://www.volcengine.com/docs/6561/2277844
    """
    url = "https://openspeech.bytedance.com/api/v3/tts/voice_design"

    request_body = {
        "speaker_id": speaker_id,
        "text": preview_text[:300],
        "prompt": {
            "text_prompt": voice_prompt,
        },
        # "audio_config": {
        #     "encoding": audio_format,
        #     "sample_rate": sample_rate,
        # },
    }

    headers = {
        "Content-Type": "application/json",
        "X-Api-Key": f"{api_key}",
        "X-Api-Request-Id": str(uuid.uuid4())
    }

    logger.debug(
        f"[Volcengine VoiceDesign] 请求: speaker_id={speaker_id} "
        f"voice_prompt={voice_prompt[:50]}... preview_text={preview_text[:30]}..."
    )

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(url, json=request_body, headers=headers)

        if response.status_code != 200:
            error_text = response.text[:500]
            logger.error(
                f"[Volcengine VoiceDesign] 失败: status={response.status_code} "
                f"body={error_text}"
            )
            raise VoiceDesignError(
                f"火山引擎音色设计 API 调用失败 (HTTP {response.status_code}): {error_text}"
            )

        # 火山引擎返回二进制音频数据
        audio_bytes = response.content
        if not audio_bytes:
            raise VoiceDesignError("火山引擎音色设计 API 返回空音频数据")

        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

        logger.info(
            f"[Volcengine VoiceDesign] 成功: speaker_id={speaker_id} "
            f"audio_size={len(audio_bytes)} bytes"
        )

        return VoiceDesignResult(
            speaker_id=speaker_id,
            audio_base64=audio_b64,
            sample_rate=sample_rate,
            audio_format=audio_format,
        )


async def call_dashscope_voice_design(
    api_key: str,
    voice_prompt: str,
    preview_text: str,
    preferred_name: str,
    language: str = "zh",
    sample_rate: int = 24000,
    timeout: int = 180,
) -> VoiceDesignResult:
    """
    调用阿里百炼 DashScope 声音定制 API

    端点: https://dashscope.aliyuncs.com/api/v1/services/audio/tts/customization
    """
    url = "https://dashscope.aliyuncs.com/api/v1/services/audio/tts/customization"

    request_body = {
        "model": "qwen-voice-design",
        "input": {
            "action": "create",
            "target_model": "qwen3-tts-vd-2026-01-26",
            "voice_prompt": voice_prompt,
            "preview_text": preview_text[:200],
            "preferred_name": preferred_name,
            "language": language,
        },
        "parameters": {
            "sample_rate": sample_rate,
            "response_format": "wav",
        },
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    logger.debug(
        f"[DashScope VoiceDesign] 请求: preferred_name={preferred_name} "
        f"voice_prompt={voice_prompt[:50]}... preview_text={preview_text[:30]}..."
    )

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(url, json=request_body, headers=headers)
        data = response.json()

        if response.status_code != 200 or not data.get("output"):
            error_msg = data.get("message", "未知错误")
            error_code = data.get("code", "UNKNOWN")
            logger.error(
                f"[DashScope VoiceDesign] 失败: code={error_code} message={error_msg}"
            )
            raise VoiceDesignError(f"百炼音色设计 API 调用失败 ({error_code}): {error_msg}")

        output = data["output"]
        voice_id = output.get("voice", "")
        preview_audio = output.get("preview_audio", {})
        audio_b64 = preview_audio.get("data", "")

        if not voice_id or not audio_b64:
            raise VoiceDesignError("百炼音色设计 API 返回数据不完整")

        logger.info(
            f"[DashScope VoiceDesign] 成功: voice_id={voice_id} "
            f"request_id={data.get('request_id')}"
        )

        return VoiceDesignResult(
            speaker_id=voice_id,
            audio_base64=audio_b64,
            sample_rate=preview_audio.get("sample_rate", sample_rate),
            audio_format=preview_audio.get("response_format", "wav"),
        )


def generate_speaker_id(index: int) -> str:
    """生成音色 ID: voice_{uuid_short}_{index}"""
    short_id = uuid.uuid4().hex[:8]
    return f"voice_{short_id}_{index}"


class VoiceDesignError(Exception):
    """音色设计异常"""
