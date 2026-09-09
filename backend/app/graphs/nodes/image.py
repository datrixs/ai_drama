import json

from loguru import logger

from app.graphs.states import GenerateImageState, ModifyImageState
from app.graphs.nodes.common import report_progress
from app.core.model_provider import ModelCaller
from app.services.image_processor import download_and_store_image, ratio_to_size
from app.services.llm import extract_json, LLMError
from app.prompts.constants import (
    add_character_prompt_suffix, add_location_prompt_suffix, add_prop_prompt_suffix,
    get_art_style_prompt,
    CHARACTER_ASSET_IMAGE_RATIO, LOCATION_ASSET_IMAGE_RATIO, PROP_ASSET_IMAGE_RATIO,
)
from app.prompts.location_description_update import build_prompt as _build_location_desc_update
from app.prompts.prop_modify import build_prompt as _build_prop_desc_update
from app.prompts.character_description_update import build_prompt as _build_character_desc_update
from app.utils.tencent_cos_utils import cos_client
from app.enums import TaskStatus


def _get_caller(state: dict) -> ModelCaller:
    from app.db.session import SessionLocal

    config_snapshot = state.get("payload", {}).get("config_snapshot")
    user_id = config_snapshot.get("user_id", "N/A") if config_snapshot else "N/A"
    logger.debug(f"[Graph/_get_caller] config_snapshot={'有' if config_snapshot else 'None'} user_id={user_id}")
    if config_snapshot:
        db = SessionLocal()
        logger.debug(f"[Graph/_get_caller] db={'有' if db else 'None'} user_id_in_config={user_id}")
        caller = ModelCaller.from_config_snapshot(config_snapshot, db=db)
        logger.debug(f"[Graph/_get_caller] caller 创建完成: db={'有' if caller.db else 'None'}")
        return caller
    return ModelCaller.from_system_defaults()


def _parent_asset_deleted(db, asset_type: str, asset_id: str) -> bool:
    """父资产在生成期间是否被软删。True=已删，应放弃写库。"""
    from app.models.asset import GlobalCharacter, GlobalLocation
    model = GlobalCharacter if asset_type == "character" else GlobalLocation
    return not db.query(model).filter(
        model.id == asset_id,
        model.is_deleted == False,
    ).first()


def load_appearance_generate(state: GenerateImageState) -> dict:
    payload = state.get("payload", {})
    asset_type = payload.get("type", "character")
    asset_id = payload.get("id", payload.get("asset_id", ""))
    appearance_index = payload.get("appearance_index", 0)
    count = int(payload.get("count", 3))
    art_style = payload.get("art_style", "")

    base = {
        "asset_type": asset_type,
        "asset_id": asset_id,
        "appearance_index": appearance_index,
        "count": count,
        "art_style": art_style,
        "descriptions": [],
        "image_keys": [],
        "image_results": [],
        "progress": 15,
    }

    from app.db.session import SessionLocal

    if asset_type == "character":
        from app.models.asset import GlobalCharacter, GlobalCharacterAppearance

        with SessionLocal() as db:
            character = db.query(GlobalCharacter).filter(
                GlobalCharacter.id == asset_id, GlobalCharacter.is_deleted == False
            ).first()
            if not character:
                return {
                    "errors": state.get("errors", []) + [{
                        "node": "load_appearance_generate",
                        "message": "角色不存在",
                        "retryable": False,
                    }],
                }

            appearance = db.query(GlobalCharacterAppearance).filter(
                GlobalCharacterAppearance.character_id == asset_id,
                GlobalCharacterAppearance.appearance_index == appearance_index,
                GlobalCharacterAppearance.is_deleted == False,
            ).first()
            if not appearance:
                return {
                    "errors": state.get("errors", []) + [{
                        "node": "load_appearance_generate",
                        "message": "外观不存在",
                        "retryable": False,
                    }],
                }

            descriptions = json.loads(appearance.descriptions) if appearance.descriptions else []
            if not descriptions and appearance.description:
                descriptions = [appearance.description]

            system_prompt = appearance.image_model_system_prompt or ""
            base["descriptions"] = descriptions
            base["payload"] = {**payload, "_system_prompt": system_prompt}

            appearance.gen_status = "generating"
            db.commit()

            from app.core.ws import ws_manager
            ws_manager.publish_asset_hub_event(
                user_id=state["user_id"],
                event_type="asset_hub_generation_started",
                data={"target_type": "appearance", "target_id": appearance.id, "asset_type": "character"},
            )
            return base

    # location / prop
    from app.models.asset import GlobalLocation, GlobalLocationImage

    with SessionLocal() as db:
        location = db.query(GlobalLocation).filter(
            GlobalLocation.id == asset_id, GlobalLocation.is_deleted == False
        ).first()
        if not location:
            return {
                "errors": state.get("errors", []) + [{
                    "node": "load_appearance_generate",
                    "message": "场景/道具不存在",
                    "retryable": False,
                }],
            }

        art_style = art_style or location.art_style or ""
        images = db.query(GlobalLocationImage).filter(
            GlobalLocationImage.location_id == asset_id,
            GlobalLocationImage.is_deleted == False,
        ).order_by(GlobalLocationImage.image_index).all()

        image_index = int(payload.get("image_index", 0))

        from app.core.ws import ws_manager

        if images and images[0].image_url:
            # 重新生成：按 image_index 定位单条记录
            target_img = next((img for img in images if img.image_index == image_index), images[0])
            target_img.gen_status = "generating"
            db.commit()

            descriptions = [target_img.description] if target_img.description else [location.summary or location.name]
            system_prompts = [target_img.image_model_system_prompt or ""]

            ws_manager.publish_asset_hub_event(
                user_id=state["user_id"],
                event_type="asset_hub_generation_started",
                data={"target_type": "location_image", "target_id": target_img.id, "asset_type": asset_type},
            )
        else:
            # 首次生成：批量模式
            descriptions = []
            system_prompts = []
            for img in images:
                if img.description:
                    descriptions.append(img.description)
                    system_prompts.append(img.image_model_system_prompt or "")

            if not descriptions:
                desc = location.summary or location.name
                descriptions = [desc]

            images_to_generate = images[:count]
            for img in images_to_generate:
                img.gen_status = "generating"
            db.commit()

            for img in images_to_generate:
                ws_manager.publish_asset_hub_event(
                    user_id=state["user_id"],
                    event_type="asset_hub_generation_started",
                    data={"target_type": "location_image", "target_id": img.id, "asset_type": asset_type},
                )

        base["art_style"] = art_style
        base["descriptions"] = descriptions
        base["image_index"] = image_index
        base["payload"] = {**payload, "_system_prompts": system_prompts}
        return base


def build_image_prompt(state: GenerateImageState) -> dict:
    descriptions = state.get("descriptions", [])
    art_style = state.get("art_style", "")
    asset_type = state.get("asset_type", "character")
    locale = state.get("payload", {}).get("locale", "zh")

    suffix_fn = {
        "character": add_character_prompt_suffix,
        "location": add_location_prompt_suffix,
        "prop": add_prop_prompt_suffix,
    }.get(asset_type, add_character_prompt_suffix)

    system_prompt = state.get("payload", {}).get("_system_prompt", "")
    system_prompts = state.get("payload", {}).get("_system_prompts", [])

    prompts = []
    for i, desc in enumerate(descriptions):
        prompt = suffix_fn(desc)
        if art_style:
            prompt = f"{get_art_style_prompt(art_style, locale=locale)},{prompt}"
        sp = system_prompt or (system_prompts[i] if i < len(system_prompts) else "")
        if sp:
            prompt = f"{sp}\n{prompt}"
        prompts.append(prompt)

    if not prompts:
        return {
            "errors": state.get("errors", []) + [{
                "node": "build_image_prompt",
                "message": "无可用描述生成图片",
                "retryable": False,
            }],
        }

    return {"payload": {**state.get("payload", {}), "_prompts": prompts}, "progress": 20}


async def generate_images(state: GenerateImageState) -> dict:
    from app.services import task as task_service
    from app.enums import TaskStatus

    prompts = state.get("payload", {}).get("_prompts", [])
    asset_type = state.get("asset_type", "character")
    model_key = "character_model" if asset_type == "character" else "location_model"
    count = int(state.get("count", 1))
    caller = _get_caller(state)
    logger.debug(f"[Graph/generate_images] 开始: asset_type={asset_type} model_key={model_key} count={count} prompts={len(prompts)}")

    ratio_map = {
        "character": CHARACTER_ASSET_IMAGE_RATIO,
        "location": LOCATION_ASSET_IMAGE_RATIO,
        "prop": PROP_ASSET_IMAGE_RATIO,
    }
    ratio = ratio_map.get(asset_type, CHARACTER_ASSET_IMAGE_RATIO)
    size = ratio_to_size(ratio)

    image_keys = []
    thumb_keys = []
    for i in range(count):
        progress = 20 + int((i / max(count, 1)) * 60)
        task_service.update_task_status(state["task_id"], TaskStatus.PROCESSING, progress)
        desc_idx = i if i < len(prompts) else 0
        prompt = prompts[desc_idx] if prompts else ""

        try:
            logger.debug(f"[Graph/generate_images] 调用 aimage_gen: i={i} model_key={model_key} is_character={asset_type == 'character'}")
            response = await caller.aimage_gen(model_key, prompt, size=size, n=1, is_character=(asset_type == "character"))
            for item in response.get("data", []):
                image_ref = item.get("url") or item.get("b64_json")
                if image_ref:
                    key, thumb_key = download_and_store_image(image_ref, state["user_id"], state.get("asset_type", "character"))
                    image_keys.append(key)
                    thumb_keys.append(thumb_key)
        except Exception as e:
            logger.warning(f"[Graph:generate_images] 第{i+1}张生成失败: {e}")

    if not image_keys:
        return {
            "errors": state.get("errors", []) + [{
                "node": "generate_images",
                "message": "所有图片均生成失败",
                "retryable": True,
            }],
        }

    return {"image_keys": image_keys, "thumb_keys": thumb_keys, "progress": 85}


def update_appearance_db(state: GenerateImageState) -> dict:
    asset_id = state.get("asset_id", "")
    asset_type = state.get("asset_type", "character")
    appearance_index = state.get("appearance_index", 0)
    image_keys = state.get("image_keys", [])
    thumb_keys = state.get("thumb_keys", [])

    from app.db.session import SessionLocal

    with SessionLocal() as db:
        if _parent_asset_deleted(db, asset_type, asset_id):
            logger.info(f"资产在生成期间被删除，放弃写库: {asset_type}/{asset_id}")
            return {
                "errors": state.get("errors", []) + [{
                    "node": "update_appearance_db",
                    "message": "资产已被删除",
                    "retryable": False,
                }],
            }

    if asset_type == "character":
        from app.models.asset import GlobalCharacterAppearance

        with SessionLocal() as db:
            appearance = db.query(GlobalCharacterAppearance).filter(
                GlobalCharacterAppearance.character_id == asset_id,
                GlobalCharacterAppearance.appearance_index == appearance_index,
                GlobalCharacterAppearance.is_deleted == False,
            ).first()
            if appearance:
                appearance.image_urls = json.dumps(image_keys)
                appearance.image_url = image_keys[0] if image_keys else None
                appearance.thumbnail_urls = json.dumps(thumb_keys) if thumb_keys else None
                appearance.thumbnail_url = thumb_keys[0] if thumb_keys else None
                appearance.selected_index = None
                appearance.volc_private_asset_id = None
                appearance.gen_status = "completed"
                db.commit()

                from app.core.ws import ws_manager
                ws_manager.publish_asset_hub_event(
                    user_id=state["user_id"],
                    event_type="asset_hub_generation_completed",
                    data={
                        "target_type": "appearance",
                        "target_id": appearance.id,
                        "asset_type": "character",
                        "image_url": cos_client.key_to_url(image_keys[0]) if image_keys else "",
                        "thumbnail_url": cos_client.key_to_url(thumb_keys[0]) if thumb_keys else None,
                    },
                )
    else:
        from app.models.asset import GlobalLocationImage

        count = int(state.get("count", 1))
        image_index = int(state.get("image_index", 0))

        with SessionLocal() as db:
            images = db.query(GlobalLocationImage).filter(
                GlobalLocationImage.location_id == asset_id,
                GlobalLocationImage.is_deleted == False,
            ).order_by(GlobalLocationImage.image_index).all()

            if images and images[0].image_url:
                # 重新生成：按 image_index 定位单条记录
                target = next((img for img in images if img.image_index == image_index), None)
                if target and image_keys:
                    target.previous_image_url = target.image_url
                    target.previous_thumbnail_url = target.thumbnail_url
                    target.image_url = image_keys[0]
                    target.thumbnail_url = thumb_keys[0] if thumb_keys else None
                    target.gen_status = "completed"
                    db.commit()

                    from app.core.ws import ws_manager
                    ws_manager.publish_asset_hub_event(
                        user_id=state["user_id"],
                        event_type="asset_hub_generation_completed",
                        data={
                            "target_type": "location_image",
                            "target_id": target.id,
                            "asset_type": asset_type,
                            "image_url": cos_client.key_to_url(image_keys[0]),
                            "thumbnail_url": cos_client.key_to_url(thumb_keys[0]) if thumb_keys else None,
                        },
                    )
            else:
                # 首次生成：批量模式
                images_to_update = images[:count]
                for i, key in enumerate(image_keys):
                    thumb_k = thumb_keys[i] if i < len(thumb_keys) else None
                    if i < len(images_to_update):
                        images_to_update[i].image_url = key
                        images_to_update[i].thumbnail_url = thumb_k
                        images_to_update[i].gen_status = "completed"
                    else:
                        max_index = max((img.image_index for img in images), default=-1)
                        new_img = GlobalLocationImage(
                            location_id=asset_id,
                            image_index=max_index + 1 + (i - len(images_to_update)),
                            image_url=key,
                            thumbnail_url=thumb_k,
                            description=state.get("descriptions", [""])[0] if state.get("descriptions") else "",
                            gen_status="completed",
                        )
                        db.add(new_img)

                # Mark images that were set to "generating" but not filled as "failed"
                for i in range(len(image_keys), len(images_to_update)):
                    images_to_update[i].gen_status = "failed"
                db.commit()

                from app.core.ws import ws_manager
                asset_type = state.get("asset_type", "location")
                all_images = db.query(GlobalLocationImage).filter(
                    GlobalLocationImage.location_id == asset_id,
                    GlobalLocationImage.is_deleted == False,
                ).all()
                for img in all_images:
                    if img.image_url in image_keys:
                        ws_manager.publish_asset_hub_event(
                            user_id=state["user_id"],
                            event_type="asset_hub_generation_completed",
                            data={
                                "target_type": "location_image",
                                "target_id": img.id,
                                "asset_type": asset_type,
                                "image_url": cos_client.key_to_url(img.image_url),
                                "thumbnail_url": cos_client.key_to_url(img.thumbnail_url) if img.thumbnail_url else None,
                            },
                        )

    return {"result_data": {"image_keys": image_keys}, "progress": 95}


# ==================== 图生图节点 ====================

def load_appearance_modify(state: ModifyImageState) -> dict:
    payload = state.get("payload", {})
    asset_id = payload.get("id", payload.get("asset_id", ""))
    asset_type = payload.get("type", "character")
    appearance_index = payload.get("appearance_index", 0)
    image_index = payload.get("image_index", 0)
    modify_prompt = payload.get("modify_prompt", "")

    from app.db.session import SessionLocal

    if asset_type == "character":
        from app.models.asset import GlobalCharacter, GlobalCharacterAppearance

        with SessionLocal() as db:
            character = db.query(GlobalCharacter).filter(
                GlobalCharacter.id == asset_id, GlobalCharacter.is_deleted == False
            ).first()
            if not character:
                return {
                    "errors": state.get("errors", []) + [{
                        "node": "load_appearance_modify",
                        "message": "角色不存在",
                        "retryable": False,
                    }],
                }

            appearance = db.query(GlobalCharacterAppearance).filter(
                GlobalCharacterAppearance.character_id == asset_id,
                GlobalCharacterAppearance.appearance_index == appearance_index,
                GlobalCharacterAppearance.is_deleted == False,
            ).first()
            if not appearance:
                return {
                    "errors": state.get("errors", []) + [{
                        "node": "load_appearance_modify",
                        "message": "外观不存在",
                        "retryable": False,
                    }],
                }

            image_urls = json.loads(appearance.image_urls) if appearance.image_urls else []
            current_key = image_urls[image_index] if image_index < len(image_urls) else None

            appearance.gen_status = "generating"
            db.commit()

            from app.core.ws import ws_manager
            ws_manager.publish_asset_hub_event(
                user_id=state["user_id"],
                event_type="asset_hub_generation_started",
                data={"target_type": "appearance", "target_id": appearance.id, "asset_type": "character"},
            )

            return {
                "asset_id": asset_id,
                "asset_type": asset_type,
                "appearance_index": appearance_index,
                "image_index": image_index,
                "modify_prompt": modify_prompt,
                "current_image_key": current_key,
                "reference_images": [],
                "progress": 15,
            }

    # location / prop
    from app.models.asset import GlobalLocation, GlobalLocationImage

    with SessionLocal() as db:
        location = db.query(GlobalLocation).filter(
            GlobalLocation.id == asset_id, GlobalLocation.is_deleted == False
        ).first()
        if not location:
            return {
                "errors": state.get("errors", []) + [{
                    "node": "load_appearance_modify",
                    "message": "场景/道具不存在",
                    "retryable": False,
                }],
            }

        loc_image = db.query(GlobalLocationImage).filter(
            GlobalLocationImage.location_id == asset_id,
            GlobalLocationImage.image_index == image_index,
            GlobalLocationImage.is_deleted == False,
        ).first()
        current_key = loc_image.image_url if loc_image else None

        if loc_image:
            loc_image.gen_status = "generating"
            db.commit()

            from app.core.ws import ws_manager
            ws_manager.publish_asset_hub_event(
                user_id=state["user_id"],
                event_type="asset_hub_generation_started",
                data={"target_type": "location_image", "target_id": loc_image.id, "asset_type": asset_type},
            )

        return {
            "asset_id": asset_id,
            "asset_type": asset_type,
            "asset_name": location.name,
            "appearance_index": appearance_index,
            "image_index": image_index,
            "modify_prompt": modify_prompt,
            "current_image_key": current_key,
            "reference_images": [],
            "progress": 15,
        }


def load_reference_image(state: ModifyImageState) -> dict:
    current_key = state.get("current_image_key")
    reference_images = []
    if current_key:
        reference_images.append(cos_client.get_signed_url(current_key))

    payload = state.get("payload", {})
    extra_urls = payload.get("extra_image_urls", [])
    reference_images.extend(extra_urls)

    return {"reference_images": reference_images, "progress": 30}


async def generate_modified_image(state: ModifyImageState) -> dict:
    asset_type = state.get("asset_type", "character")
    modify_prompt = state.get("modify_prompt", "")

    prompt_map = {
        "character": f"请根据以下指令修改图片，保持人物核心特征一致：\n{modify_prompt}",
        "location": f"请根据以下指令修改场景图片，保持整体风格一致：\n{modify_prompt}",
        "prop": f"请根据以下指令修改道具图片，保持道具主体、结构和关键材质一致：\n{modify_prompt}",
    }
    prompt = prompt_map.get(asset_type, prompt_map["character"])

    reference_images = state.get("reference_images", [])
    caller = _get_caller(state)
    logger.debug(f"[Graph/generate_modified_image] 开始: asset_type={asset_type} ref_images={len(reference_images)}")

    ratio_map = {
        "character": CHARACTER_ASSET_IMAGE_RATIO,
        "location": LOCATION_ASSET_IMAGE_RATIO,
        "prop": PROP_ASSET_IMAGE_RATIO,
    }
    ratio = ratio_map.get(asset_type, CHARACTER_ASSET_IMAGE_RATIO)
    size = ratio_to_size(ratio)

    try:
        response = await caller.aimage_edit("edit_model", prompt, reference_images, size=size, n=1, is_character=(asset_type == "character"))
        data = response.get("data", [])
        image_ref = (data[0].get("url") or data[0].get("b64_json")) if data else None
        if not image_ref:
            return {
                "errors": state.get("errors", []) + [{
                    "node": "generate_modified_image",
                    "message": "图片修改失败",
                    "retryable": True,
                }],
            }

        new_key, new_thumb_key = download_and_store_image(image_ref, state["user_id"], state.get("asset_type", "character"))
        return {"new_image_key": new_key, "new_thumb_key": new_thumb_key, "progress": 70}
    except Exception as e:
        return {
            "errors": state.get("errors", []) + [{
                "node": "generate_modified_image",
                "message": str(e),
                "retryable": True,
            }],
        }


def update_modify_db(state: ModifyImageState) -> dict:
    asset_id = state.get("asset_id", "")
    asset_type = state.get("asset_type", "character")
    appearance_index = state.get("appearance_index", 0)
    image_index = state.get("image_index", 0)
    new_key = state.get("new_image_key")
    new_thumb_key = state.get("new_thumb_key")

    if not new_key:
        return {}

    from app.db.session import SessionLocal

    with SessionLocal() as db:
        if _parent_asset_deleted(db, asset_type, asset_id):
            logger.info(f"资产在生成期间被删除，跳过 modify 写库: {asset_type}/{asset_id}")
            return {}

    if asset_type == "character":
        from app.models.asset import GlobalCharacterAppearance

        with SessionLocal() as db:
            appearance = db.query(GlobalCharacterAppearance).filter(
                GlobalCharacterAppearance.character_id == asset_id,
                GlobalCharacterAppearance.appearance_index == appearance_index,
                GlobalCharacterAppearance.is_deleted == False,
            ).first()
            if appearance:
                image_urls = json.loads(appearance.image_urls) if appearance.image_urls else []
                thumb_urls = json.loads(appearance.thumbnail_urls) if appearance.thumbnail_urls else []

                appearance.previous_image_url = appearance.image_url
                appearance.previous_image_urls = appearance.image_urls
                appearance.previous_description = appearance.description
                appearance.previous_descriptions = appearance.descriptions

                if image_index < len(image_urls):
                    image_urls[image_index] = new_key
                else:
                    image_urls.append(new_key)
                appearance.image_urls = json.dumps(image_urls)

                # 同步维护 thumbnail_urls 数组（与 image_urls 一一对应）
                while len(thumb_urls) < len(image_urls) - 1:
                    thumb_urls.append(None)
                if image_index < len(thumb_urls):
                    thumb_urls[image_index] = new_thumb_key
                else:
                    thumb_urls.append(new_thumb_key)
                appearance.thumbnail_urls = json.dumps(thumb_urls)

                if appearance.selected_index is None or appearance.selected_index == image_index:
                    appearance.image_url = new_key
                    appearance.thumbnail_url = new_thumb_key

                appearance.gen_status = "completed"
                db.commit()

                from app.core.ws import ws_manager
                ws_manager.publish_asset_hub_event(
                    user_id=state["user_id"],
                    event_type="asset_hub_generation_completed",
                    data={
                        "target_type": "appearance",
                        "target_id": appearance.id,
                        "asset_type": "character",
                        "image_url": cos_client.key_to_url(new_key),
                        "thumbnail_url": cos_client.key_to_url(new_thumb_key) if new_thumb_key else None,
                    },
                )
    else:
        from app.models.asset import GlobalLocationImage

        with SessionLocal() as db:
            loc_image = db.query(GlobalLocationImage).filter(
                GlobalLocationImage.location_id == asset_id,
                GlobalLocationImage.image_index == image_index,
                GlobalLocationImage.is_deleted == False,
            ).first()
            if loc_image:
                loc_image.previous_image_url = loc_image.image_url
                loc_image.previous_description = loc_image.description
                loc_image.image_url = new_key
                loc_image.thumbnail_url = new_thumb_key

                new_desc = state.get("new_description")
                if new_desc:
                    loc_image.description = new_desc
                new_slots = state.get("new_available_slots")
                if new_slots:
                    loc_image.available_slots = new_slots

                loc_image.gen_status = "completed"
                db.commit()

                from app.core.ws import ws_manager
                ws_manager.publish_asset_hub_event(
                    user_id=state["user_id"],
                    event_type="asset_hub_generation_completed",
                    data={
                        "target_type": "location_image",
                        "target_id": loc_image.id,
                        "asset_type": asset_type,
                        "image_url": cos_client.key_to_url(new_key),
                        "thumbnail_url": cos_client.key_to_url(new_thumb_key) if new_thumb_key else None,
                    },
                )

    return {"result_data": {"image_key": new_key}, "progress": 95}


def _build_image_context(asset_type: str, has_reference_images: bool) -> str:
    if not has_reference_images:
        return ""
    if asset_type == "character":
        return "【参考图片】\n请仔细分析参考图片中的服装款式、颜色、材质、配饰等关键视觉特征，并将这些特征融入更新后的描述中。"
    if asset_type == "prop":
        return "【参考图片】\n请仔细分析参考图片中的材质、轮廓、比例、装饰细节、配色与表面处理，并将这些特征融入更新后的描述中。"
    return "【参考图片】\n请仔细分析参考图片中的建筑风格、装饰元素、光线氛围、色调等关键视觉特征，并将这些特征融入更新后的描述中。"


async def sync_description_after_modify(state: ModifyImageState) -> dict:
    asset_type = state.get("asset_type", "character")
    modify_prompt = state.get("modify_prompt", "")

    if not modify_prompt:
        return {}

    locale = state.get("payload", {}).get("locale", "zh")
    has_reference_images = bool(state.get("reference_image_urls", []))
    image_context = _build_image_context(asset_type, has_reference_images)

    from app.db.session import SessionLocal
    from app.models.asset import GlobalLocation, GlobalLocationImage

    asset_id = state.get("asset_id", "")
    image_index = state.get("image_index", 0)

    with SessionLocal() as db:
        location = db.query(GlobalLocation).filter(
            GlobalLocation.id == asset_id, GlobalLocation.is_deleted == False
        ).first()
        if not location:
            return {}

        loc_image = db.query(GlobalLocationImage).filter(
            GlobalLocationImage.location_id == asset_id,
            GlobalLocationImage.image_index == image_index,
            GlobalLocationImage.is_deleted == False,
        ).first()
        original_description = loc_image.description if loc_image else ""
        location_name = location.name

    try:
        if asset_type == "character":
            prompt = _build_character_desc_update(
                original_description, modify_prompt,
                image_context=image_context, locale=locale,
            )
        elif asset_type == "location":
            prompt = _build_location_desc_update(
                location_name, original_description, modify_prompt,
                image_context=image_context, locale=locale,
            )
        else:
            prompt = _build_prop_desc_update(
                location_name, original_description, modify_prompt,
                image_context=image_context, locale=locale,
            )

        caller = _get_caller(state)

        result = await caller.acall(
            "analysis_model",
            [{"role": "user", "content": prompt}],
        )
        raw_completion = {"choices": [{"message": {"content": result.content}}]}
        parsed = extract_json(raw_completion)
        new_description = parsed.get("prompt", "")
        update = {"new_description": new_description}
        if asset_type == "location":
            available_slots = parsed.get("available_slots", [])
            if available_slots:
                update["new_available_slots"] = json.dumps(available_slots, ensure_ascii=False)
        return update
    except Exception as e:
        logger.warning(f"[Graph:sync_description] 描述同步失败: {e}")
        return {}
