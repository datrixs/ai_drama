from loguru import logger

from app.graphs.states import (
    DesignCharacterState,
    ModifyCharacterState,
    DesignLocationState,
    ModifyLocationState,
    ModifyPropState,
)
from app.graphs.nodes.common import report_progress
from app.core.model_provider import ModelCaller
from app.services.llm import extract_json, LLMError
from app.prompts.character_create import build_prompt as _build_create_prompt
from app.prompts.character_modify import build_prompt as _build_modify_prompt
from app.prompts.character_regenerate import build_prompt as _build_character_regenerate_prompt
from app.prompts.location_create import build_prompt as _build_location_create_prompt
from app.prompts.location_modify import build_prompt as _build_location_modify_prompt
from app.prompts.location_regenerate import build_prompt as _build_location_regenerate_prompt
from app.prompts.prop_modify import build_prompt as _build_prop_modify_prompt
from app.enums import TaskStatus


def _get_caller(state: dict) -> ModelCaller:
    from app.db.session import SessionLocal

    config_snapshot = state.get("payload", {}).get("config_snapshot")
    if config_snapshot:
        db = SessionLocal()
        return ModelCaller.from_config_snapshot(config_snapshot, db=db)
    return ModelCaller.from_system_defaults()


def build_design_prompt(state: DesignCharacterState) -> dict:
    payload = state.get("payload", {})
    user_instruction = payload.get("user_instruction", "")
    locale = payload.get("locale", "zh")

    prompt = _build_create_prompt(user_instruction, locale=locale)
    return {
        "user_instruction": user_instruction,
        "prompt_text": prompt,
        "progress": 25,
    }


def build_modify_prompt(state: ModifyCharacterState) -> dict:
    payload = state.get("payload", {})
    current_description = payload.get("current_description", "")
    modify_instruction = payload.get("modify_instruction", "")
    locale = payload.get("locale", "zh")

    prompt = _build_modify_prompt(current_description, modify_instruction, locale=locale)
    return {
        "current_description": current_description,
        "modify_instruction": modify_instruction,
        "prompt_text": prompt,
        "progress": 25,
    }


async def call_llm(state: DesignCharacterState | ModifyCharacterState) -> dict:
    report_progress(state)

    prompt = state.get("prompt_text", "")
    caller = _get_caller(state)

    try:
        result = await caller.acall(
            "analysis_model",
            [{"role": "user", "content": prompt}],
        )
        raw_completion = {
            "choices": [{"message": {"content": result.content}}],
        }
        return {"raw_completion": raw_completion, "progress": 60}
    except LLMError as e:
        logger.error(f"[Graph:call_llm] 调用失败: {e}")
        return {
            "errors": state.get("errors", []) + [{
                "node": "call_llm",
                "message": str(e),
                "retryable": e.retryable,
            }],
            "progress": 0,
        }
    except Exception as e:
        logger.error(f"[Graph:call_llm] 调用失败: {e}")
        return {
            "errors": state.get("errors", []) + [{
                "node": "call_llm",
                "message": str(e),
                "retryable": True,
            }],
            "progress": 0,
        }


def parse_json_result(state: DesignCharacterState | ModifyCharacterState) -> dict:
    raw = state.get("raw_completion")
    if not raw:
        return {
            "errors": state.get("errors", []) + [{
                "node": "parse_json_result",
                "message": "LLM 返回为空",
                "retryable": True,
            }],
        }

    try:
        parsed = extract_json(raw)
        description = parsed.get("prompt", "")
        return {"parsed_result": parsed, "description": description, "progress": 80}
    except Exception as e:
        return {
            "errors": state.get("errors", []) + [{
                "node": "parse_json_result",
                "message": str(e),
                "retryable": False,
            }],
        }


def validate_description(state: DesignCharacterState | ModifyCharacterState) -> dict:
    description = state.get("description", "")
    if not description:
        return {
            "errors": state.get("errors", []) + [{
                "node": "validate_description",
                "message": "AI 返回空描述",
                "retryable": True,
            }],
        }
    return {"progress": 90, "result_data": {"prompt": description}}


# ==================== 场景设计/修改节点 ====================

def build_location_design_prompt(state: DesignLocationState) -> dict:
    payload = state.get("payload", {})
    user_instruction = payload.get("user_instruction", "")
    locale = payload.get("locale", "zh")

    prompt = _build_location_create_prompt(user_instruction, locale=locale)
    return {
        "user_instruction": user_instruction,
        "prompt_text": prompt,
        "progress": 25,
    }


def build_location_modify_prompt(state: ModifyLocationState) -> dict:
    payload = state.get("payload", {})
    location_name = payload.get("location_name", "")
    current_description = payload.get("current_description", "")
    modify_instruction = payload.get("modify_instruction", "")
    locale = payload.get("locale", "zh")

    prompt = _build_location_modify_prompt(location_name, current_description, modify_instruction, locale=locale)
    return {
        "location_name": location_name,
        "current_description": current_description,
        "modify_instruction": modify_instruction,
        "prompt_text": prompt,
        "progress": 25,
    }


def build_prop_modify_prompt(state: ModifyPropState) -> dict:
    payload = state.get("payload", {})
    prop_name = payload.get("prop_name", "")
    current_description = payload.get("current_description", "")
    modify_instruction = payload.get("modify_instruction", "")
    image_context = payload.get("image_context", "")
    locale = payload.get("locale", "zh")

    prompt = _build_prop_modify_prompt(prop_name, current_description, modify_instruction, image_context=image_context, locale=locale)
    return {
        "prop_name": prop_name,
        "current_description": current_description,
        "modify_instruction": modify_instruction,
        "prompt_text": prompt,
        "progress": 25,
    }


# ==================== 角色重新生成节点 ====================

def build_character_regenerate_prompt(state: dict) -> dict:
    payload = state.get("payload", {})
    character_name = payload.get("character_name", "")
    current_descriptions = payload.get("current_descriptions", "")
    change_reason = payload.get("change_reason", "")
    novel_text = payload.get("novel_text", "")
    locale = payload.get("locale", "zh")

    prompt = _build_character_regenerate_prompt(
        character_name, current_descriptions, change_reason, novel_text, locale=locale,
    )
    return {
        "prompt_text": prompt,
        "progress": 25,
    }


def parse_regenerate_json_result(state: dict) -> dict:
    raw = state.get("raw_completion")
    if not raw:
        return {
            "errors": state.get("errors", []) + [{
                "node": "parse_regenerate_json_result",
                "message": "LLM 返回为空",
                "retryable": True,
            }],
        }

    try:
        parsed = extract_json(raw)
        descriptions = parsed.get("descriptions", [])
        return {
            "parsed_result": parsed,
            "descriptions": descriptions,
            "progress": 80,
        }
    except Exception as e:
        return {
            "errors": state.get("errors", []) + [{
                "node": "parse_regenerate_json_result",
                "message": str(e),
                "retryable": False,
            }],
        }


def validate_regenerate_descriptions(state: dict) -> dict:
    descriptions = state.get("descriptions", [])
    if not descriptions:
        return {
            "errors": state.get("errors", []) + [{
                "node": "validate_regenerate_descriptions",
                "message": "AI 返回空描述列表",
                "retryable": True,
            }],
        }
    result_data = {"descriptions": descriptions}
    parsed = state.get("parsed_result", {})
    available_slots = parsed.get("available_slots", [])
    if available_slots:
        result_data["available_slots"] = available_slots
    return {"progress": 90, "result_data": result_data}


# ==================== 场景重新生成节点 ====================

def build_location_regenerate_prompt(state: dict) -> dict:
    payload = state.get("payload", {})
    location_name = payload.get("location_name", "")
    current_descriptions = payload.get("current_descriptions", "")
    locale = payload.get("locale", "zh")

    prompt = _build_location_regenerate_prompt(
        location_name, current_descriptions, locale=locale,
    )
    return {
        "prompt_text": prompt,
        "progress": 25,
    }


def parse_location_json_result(state: DesignLocationState | ModifyLocationState) -> dict:
    raw = state.get("raw_completion")
    if not raw:
        return {
            "errors": state.get("errors", []) + [{
                "node": "parse_json_result",
                "message": "LLM 返回为空",
                "retryable": True,
            }],
        }

    try:
        parsed = extract_json(raw)
        description = parsed.get("prompt", "")
        available_slots = parsed.get("available_slots", [])
        return {
            "parsed_result": parsed,
            "description": description,
            "available_slots": available_slots,
            "progress": 80,
        }
    except Exception as e:
        return {
            "errors": state.get("errors", []) + [{
                "node": "parse_json_result",
                "message": str(e),
                "retryable": False,
            }],
        }


def parse_prop_json_result(state: ModifyPropState) -> dict:
    raw = state.get("raw_completion")
    if not raw:
        return {
            "errors": state.get("errors", []) + [{
                "node": "parse_json_result",
                "message": "LLM 返回为空",
                "retryable": True,
            }],
        }

    try:
        parsed = extract_json(raw)
        description = parsed.get("prompt", "")
        return {"parsed_result": parsed, "description": description, "progress": 80}
    except Exception as e:
        return {
            "errors": state.get("errors", []) + [{
                "node": "parse_json_result",
                "message": str(e),
                "retryable": False,
            }],
        }


def validate_location_description(state: DesignLocationState | ModifyLocationState) -> dict:
    description = state.get("description", "")
    if not description:
        return {
            "errors": state.get("errors", []) + [{
                "node": "validate_description",
                "message": "AI 返回空描述",
                "retryable": True,
            }],
        }
    result_data = {"prompt": description}
    available_slots = state.get("available_slots", [])
    if available_slots:
        result_data["available_slots"] = available_slots
    return {"progress": 90, "result_data": result_data}


def validate_prop_description(state: ModifyPropState) -> dict:
    description = state.get("description", "")
    if not description:
        return {
            "errors": state.get("errors", []) + [{
                "node": "validate_description",
                "message": "AI 返回空描述",
                "retryable": True,
            }],
        }
    return {"progress": 90, "result_data": {"prompt": description}}
