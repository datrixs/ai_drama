"""
音色设计 LangGraph 节点

节点:
- validate_voice_input: 校验音色设计参数
- generate_voice_scheme: 生成单个音色方案并上传 COS
- should_continue_generating: 条件边，控制循环
"""
import base64

from loguru import logger

from app.graphs.states import VoiceDesignState
from app.services.voice_design import generate_speaker_id


def validate_voice_input(state: VoiceDesignState) -> dict:
    """校验音色设计输入参数"""
    payload = state.get("payload", {})
    errors = state.get("errors", [])

    voice_prompt = payload.get("voice_prompt", "").strip()
    preview_text = payload.get("preview_text", "").strip()
    scheme_count = payload.get("count", 3)
    language = payload.get("language", "zh").strip()

    if not voice_prompt:
        errors.append({"message": "音色描述不能为空", "node": "validate_voice_input"})
        return {"errors": errors}

    if len(voice_prompt) > 500:
        errors.append({"message": "音色描述不能超过500字", "node": "validate_voice_input"})
        return {"errors": errors}

    if not preview_text:
        errors.append({"message": "试听文本不能为空", "node": "validate_voice_input"})
        return {"errors": errors}

    if len(preview_text) < 5:
        errors.append({"message": "试听文本至少需要5个字符", "node": "validate_voice_input"})
        return {"errors": errors}

    if len(preview_text) > 300:
        preview_text = preview_text[:300]

    scheme_count = max(1, min(5, int(scheme_count)))

    logger.debug(
        f"[VoiceDesign/validate] voice_prompt={voice_prompt[:30]}... "
        f"preview_text={preview_text[:20]}... scheme_count={scheme_count}"
    )

    return {
        "voice_prompt": voice_prompt,
        "preview_text": preview_text,
        "scheme_count": scheme_count,
        "language": language,
        "voice_schemes": [],
        "generated_count": 0,
        "progress": 20,
    }


async def generate_voice_scheme(state: VoiceDesignState) -> dict:
    """生成单个音色方案，上传音频到 COS"""
    from app.core.model_provider import ModelCaller
    from app.services import task as task_service
    from app.services.voice_design import VoiceDesignError
    from app.utils.tencent_cos_utils import cos_client

    payload = state.get("payload", {})
    config_snapshot = payload.get("config_snapshot", {})
    voice_prompt = state["voice_prompt"]
    preview_text = state["preview_text"]
    language = state.get("language", "zh")
    generated_count = state.get("generated_count", 0)
    voice_schemes = list(state.get("voice_schemes", []))
    user_id = state.get("user_id", "")
    errors = list(state.get("errors", []))

    scheme_count = state["scheme_count"]
    speaker_id = generate_speaker_id(generated_count)

    logger.info(
        f"[VoiceDesign/generate] 生成方案 {generated_count + 1}/{scheme_count} "
        f"speaker_id={speaker_id}"
    )

    caller = ModelCaller.from_config_snapshot(config_snapshot)

    try:
        result = await caller.avoice_design(
            model_key="audio_model",
            voice_prompt=voice_prompt,
            preview_text=preview_text,
            preferred_name=speaker_id,
            language=language,
            task_id=state.get("task_id"),
        )

        audio_b64 = result["audio_base64"]
        audio_bytes = base64.b64decode(audio_b64)
        audio_format = result.get("audio_format", "wav")
        sample_rate = result.get("sample_rate", 24000)

        # 上传到 COS
        key = cos_client.generate_unique_key("voice", "design", user_id, audio_format)
        content_type = "audio/wav" if audio_format == "wav" else "audio/mpeg"
        cos_client.upload_object(audio_bytes, key, content_type=content_type)
        audio_url = cos_client.key_to_url(key)

        voice_schemes.append({
            "voice_id": result["speaker_id"],
            "audio_url": audio_url,
            "audio_base64": audio_b64,
            "sample_rate": sample_rate,
            "audio_format": audio_format,
        })

        new_count = generated_count + 1
        progress = 20 + int((new_count / scheme_count) * 70)

        task_service.update_task_status(
            state["task_id"],
            "processing",
            progress,
        )

        logger.info(
            f"[VoiceDesign/generate] 方案 {new_count}/{scheme_count} 完成 "
            f"speaker_id={result['speaker_id']} cos_key={key}"
        )

        update = {
            "voice_schemes": voice_schemes,
            "generated_count": new_count,
            "progress": progress,
        }

        # 最后一个方案完成后，设置 result_data 供 finalize_result 使用
        if new_count >= scheme_count:
            update["result_data"] = {
                "voices": [
                    {
                        "voice_id": s["voice_id"],
                        "audio_url": s["audio_url"],
                        "sample_rate": s["sample_rate"],
                        "audio_format": s["audio_format"],
                    }
                    for s in voice_schemes
                ],
            }

        return update
    except VoiceDesignError as e:
        logger.error(f"[VoiceDesign/generate] 方案生成失败: {e}")
        errors.append({
            "message": f"音色方案 {generated_count + 1} 生成失败: {e}",
            "node": "generate_voice_scheme",
            "retryable": True,
        })
        return {
            "voice_schemes": voice_schemes,
            "generated_count": generated_count + 1,
            "errors": errors,
        }
    except Exception as e:
        logger.error(f"[VoiceDesign/generate] 未知错误: {e}")
        errors.append({
            "message": f"音色方案 {generated_count + 1} 生成失败: {e}",
            "node": "generate_voice_scheme",
            "retryable": False,
        })
        return {
            "voice_schemes": voice_schemes,
            "generated_count": generated_count + 1,
            "errors": errors,
        }


def should_continue_generating(state: VoiceDesignState) -> str:
    """条件边：判断是否继续生成下一个方案"""
    generated_count = state.get("generated_count", 0)
    scheme_count = state.get("scheme_count", 3)
    errors = state.get("errors", [])

    # 有不可重试的错误，直接终止
    if errors:
        non_retryable = [e for e in errors if not e.get("retryable", False)]
        if non_retryable:
            return "handle_error"

    if generated_count < scheme_count:
        return "generate_voice_scheme"

    # 全部完成，检查是否有方案
    voice_schemes = state.get("voice_schemes", [])
    if not voice_schemes:
        return "handle_error"

    return "finalize_result"
