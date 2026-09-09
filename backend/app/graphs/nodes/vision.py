from loguru import logger

from app.graphs.states import ReferenceToCharacterState
from app.graphs.nodes.common import report_progress
from app.core.model_provider import ModelCaller
from app.services.image_processor import download_and_store_image
from app.services.llm import extract_content, LLMError
from app.prompts.character_image_to_description import build_prompt as _build_image_to_desc_prompt
from app.prompts.character_reference_to_sheet import build_prompt as _build_ref_to_sheet_prompt
from app.prompts.constants import (
    add_character_prompt_suffix, get_art_style_prompt,
)
from app.enums import TaskStatus
from app.utils.tencent_cos_utils import cos_client


def _get_caller(state: dict) -> ModelCaller:
    from app.db.session import SessionLocal

    config_snapshot = state.get("payload", {}).get("config_snapshot")
    if config_snapshot:
        db = SessionLocal()
        return ModelCaller.from_config_snapshot(config_snapshot, db=db)
    return ModelCaller.from_system_defaults()


def load_reference_config(state: ReferenceToCharacterState) -> dict:
    payload = state.get("payload", {})
    appearance_id = payload.get("appearance_id")
    is_background_job = payload.get("is_background_job", False)

    if is_background_job and appearance_id:
        from app.db.session import SessionLocal
        from app.models.asset import GlobalCharacterAppearance
        try:
            with SessionLocal() as db:
                appearance = db.query(GlobalCharacterAppearance).filter(
                    GlobalCharacterAppearance.id == appearance_id,
                ).first()
                if appearance:
                    appearance.gen_status = "generating"
                    db.commit()
                    from app.core.ws import ws_manager
                    ws_manager.publish_asset_hub_event(
                        user_id=state.get("user_id", ""),
                        event_type="asset_hub_generation_started",
                        data={"target_type": "appearance", "target_id": appearance.id, "asset_type": "character"},
                    )
        except Exception:
            pass

    return {
        "reference_image_urls": payload.get("reference_image_urls", []),
        "extract_only": payload.get("extract_only", False),
        "art_style": payload.get("art_style", ""),
        "custom_description": payload.get("custom_description", ""),
        "count": int(payload.get("count", 3)),
        "appearance_id": appearance_id,
        "is_background_job": is_background_job,
        "progress": 15,
    }


def route_by_extract_only(state: ReferenceToCharacterState) -> str:
    return "call_vision" if state.get("extract_only") else "build_image_prompt"


async def call_vision(state: ReferenceToCharacterState) -> dict:
    report_progress({**state, "progress": 45})

    image_urls = state.get("reference_image_urls", [])
    locale = state.get("payload", {}).get("locale", "zh")
    prompt = _build_image_to_desc_prompt(locale=locale)
    caller = _get_caller(state)

    try:
        result = await caller.avision("analysis_model", prompt, image_urls, temperature=0.3)
        description = result.content
        if not description:
            return {
                "errors": state.get("errors", []) + [{
                    "node": "call_vision",
                    "message": "视觉模型返回空描述",
                    "retryable": True,
                }],
            }
        raw_completion = {"choices": [{"message": {"content": description}}]}
        return {"raw_completion": raw_completion, "description": description, "progress": 80}
    except LLMError as e:
        logger.error(f"[Graph:call_vision] 调用失败: {e}")
        return {
            "errors": state.get("errors", []) + [{
                "node": "call_vision",
                "message": str(e),
                "retryable": e.retryable,
            }],
        }
    except Exception as e:
        logger.error(f"[Graph:call_vision] 调用失败: {e}")
        return {
            "errors": state.get("errors", []) + [{
                "node": "call_vision",
                "message": str(e),
                "retryable": True,
            }],
        }


def extract_description(state: ReferenceToCharacterState) -> dict:
    description = state.get("description", "")
    if not description:
        raw = state.get("raw_completion")
        if raw:
            try:
                description = extract_content(raw)
            except Exception:
                description = ""
    return {"description": description or "", "progress": 90, "result_data": {"description": description or ""}}


def build_image_prompt(state: ReferenceToCharacterState) -> dict:
    custom_desc = state.get("custom_description", "")
    locale = state.get("payload", {}).get("locale", "zh")
    if custom_desc:
        prompt = add_character_prompt_suffix(custom_desc)
    else:
        base_prompt = _build_ref_to_sheet_prompt(locale=locale)
        prompt = add_character_prompt_suffix(base_prompt)

    art_style = state.get("art_style", "")
    if art_style:
        prompt = f"{prompt}，{get_art_style_prompt(art_style, locale=locale)}"

    return {"prompt_text": prompt, "progress": 35}


async def generate_ref_images(state: ReferenceToCharacterState) -> dict:
    prompt = state.get("prompt_text", "")
    reference_urls = state.get("reference_image_urls", [])
    count = int(state.get("count", 1))
    caller = _get_caller(state)

    image_keys = []
    thumb_keys = []
    for i in range(count):
        report_progress({**state, "progress": 35 + int((i / count) * 40)})
        try:
            response = await caller.aimage_edit("character_model", prompt, reference_urls, n=1, is_character=True)
            for item in response.get("data", []):
                url = item.get("url")
                if url:
                    key, thumb_key = download_and_store_image(url, state["user_id"])
                    image_keys.append(key)
                    thumb_keys.append(thumb_key)
        except Exception as e:
            logger.warning(f"[Graph:generate_ref_images] 第{i+1}张生成失败: {e}")

    if not image_keys:
        return {
            "errors": state.get("errors", []) + [{
                "node": "generate_ref_images",
                "message": "所有图片均生成失败",
                "retryable": True,
            }],
        }

    return {"image_results": [{"image_key": k, "thumb_key": t} for k, t in zip(image_keys, thumb_keys)], "progress": 80}


async def optional_extract_description(state: ReferenceToCharacterState) -> dict:
    caller = _get_caller(state)
    image_urls = state.get("reference_image_urls", [])
    locale = state.get("payload", {}).get("locale", "zh")
    try:
        prompt = _build_image_to_desc_prompt(locale=locale)
        result = await caller.avision("analysis_model", prompt, image_urls, temperature=0.3)
        return {"description": result.content or ""}
    except LLMError as e:
        logger.warning(f"[Graph:optional_extract_description] 描述提取失败（非致命）: {e}")
        return {"description": ""}


def update_appearance_db(state: ReferenceToCharacterState) -> dict:
    image_results = state.get("image_results", [])
    image_keys = [r["image_key"] for r in image_results if "image_key" in r]
    thumb_keys = [r.get("thumb_key") for r in image_results if "image_key" in r]
    description = state.get("description", "")

    if not image_keys:
        return {}

    if state.get("is_background_job") and state.get("appearance_id"):
        import json
        from app.db.session import SessionLocal
        from app.models.asset import GlobalCharacterAppearance

        with SessionLocal() as db:
            appearance = db.query(GlobalCharacterAppearance).filter(
                GlobalCharacterAppearance.id == state["appearance_id"]
            ).first()
            if appearance:
                appearance.image_urls = json.dumps(image_keys)
                appearance.image_url = image_keys[0]
                appearance.thumbnail_urls = json.dumps(thumb_keys) if thumb_keys else None
                appearance.thumbnail_url = thumb_keys[0] if thumb_keys else None
                if description:
                    appearance.description = description
                    appearance.descriptions = json.dumps([description])
                appearance.selected_index = None
                appearance.gen_status = "completed"
                db.commit()

                from app.core.ws import ws_manager
                ws_manager.publish_asset_hub_event(
                    user_id=state.get("user_id", ""),
                    event_type="asset_hub_generation_completed",
                    data={
                        "target_type": "appearance",
                        "target_id": appearance.id,
                        "asset_type": "character",
                        "image_url": cos_client.key_to_url(image_keys[0]),
                        "thumbnail_url": cos_client.key_to_url(thumb_keys[0]) if thumb_keys else None,
                    },
                )

    return {"result_data": {"image_keys": image_keys, "description": description}, "progress": 95}
