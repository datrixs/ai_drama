"""
项目资产图片生成 Celery 任务
"""
import os
import traceback
from datetime import datetime, timedelta, timezone

from app.core.celery import celery
from app.core.logging import logger, LOG_DIR
from app.core.model_provider import ModelCaller
from app.core.ws import ws_manager
from app.crud.project_asset_crud import project_asset_crud
from app.db.session import SessionLocal
from app.models.project_asset import ProjectCharacter, ProjectLocation, ProjectProp
from app.models.project import Project
from app.utils.tencent_cos_utils import cos_client
from app.prompts.character_description_update import build_prompt as build_char_desc_prompt
from app.prompts.constants import (
    add_character_prompt_suffix,
    add_location_prompt_suffix,
    add_prop_prompt_suffix,
    get_art_style_prompt,
)
from app.prompts.location_description_update import build_prompt as build_loc_desc_prompt
from app.prompts.prop_modify import build_prompt as build_prop_desc_prompt
from app.services.image_processor import download_and_store_image
from app.tasks.helpers import await_sync


ASSET_MODEL_MAP = {
    "character": ProjectCharacter,
    "location": ProjectLocation,
    "prop": ProjectProp,
}

MODIFY_PROMPT_MAP = {
    "character": "请根据以下指令修改图片，保持人物核心特征一致：\n{}",
    "location": "请根据以下指令修改场景图片，保持整体风格一致：\n{}",
    "prop": "请根据以下指令修改道具图片，保持道具主体、结构和关键材质一致：\n{}",
}


def _save_to_local(project_id: str, image_url: str, asset_type: str, asset_id: str):
    """临时：从原始 URL 或 base64 下载图片，保存原格式到项目日志 assets 目录"""
    try:
        from app.services.image_processor import looks_like_base64, decode_base64_image

        assets_dir = os.path.join(LOG_DIR, "projects", project_id, "assets")
        os.makedirs(assets_dir, exist_ok=True)

        if looks_like_base64(image_url):
            raw, ext = decode_base64_image(image_url)
        else:
            import httpx
            resp = httpx.get(image_url, timeout=120)
            resp.raise_for_status()
            raw = resp.content
            content_type = resp.headers.get("content-type", "")
            ext_map = {"image/png": "png", "image/webp": "webp", "image/gif": "gif"}
            ext = ext_map.get(content_type.split(";")[0], "jpg")

        ts = datetime.now().strftime("%H%M%S")
        filename = f"{asset_type}_{asset_id[:8]}_{ts}.{ext}"
        filepath = os.path.join(assets_dir, filename)
        with open(filepath, "wb") as f:
            f.write(raw)
        logger.info(f"图片已备份到本地: {filepath}")
    except Exception as e:
        logger.warning(f"图片本地备份失败: {e}")


def _get_asset(db, asset_type, asset_id):
    model_class = ASSET_MODEL_MAP.get(asset_type)
    if not model_class:
        return None
    return db.query(model_class).filter(
        model_class.id == asset_id,
        model_class.is_deleted == False,
    ).first()


def _build_image_prompt(asset, art_style: str) -> str:
    style_desc = get_art_style_prompt(art_style) if art_style else ""

    if isinstance(asset, ProjectCharacter):
        desc = asset.description or f"角色 {asset.name}"
        desc += f", {asset.image_prompt if asset.image_prompt else ""}"
        prompt = add_character_prompt_suffix(desc)
    elif isinstance(asset, ProjectLocation):
        desc = asset.description or asset.summary or f"场景 {asset.name}"
        desc += f", {asset.image_prompt if asset.image_prompt else ""}"
        prompt = add_location_prompt_suffix(desc)
    else:
        desc = asset.description or f"道具 {asset.name}"
        desc += f", {asset.image_prompt if asset.image_prompt else ""}"
        prompt = add_prop_prompt_suffix(desc)

    if style_desc:
        prompt = f"{style_desc}{prompt}"

    system_prefix = f"{asset.image_model_system_prompt}\n" if asset.image_model_system_prompt else ""
    return f"{system_prefix}{prompt}"


def _get_asset_size(asset_type: str) -> str:
    return "2400x1600" if asset_type in ("character", "prop") else "2048x2048"


def _get_image_url(result: dict) -> str | None:
    data = result.get("data", [])
    if data and len(data) > 0:
        return data[0].get("url") or data[0].get("b64_json")
    return None


def _build_image_context(asset_type: str, has_ref: bool) -> str:
    if not has_ref:
        return ""
    contexts = {
        "character": "【参考图片】\n请仔细分析参考图片中的服装款式、颜色、材质、配饰等关键视觉特征，并将这些特征融入更新后的描述中。",
        "prop": "【参考图片】\n请仔细分析参考图片中的材质、轮廓、比例、装饰细节、配色与表面处理，并将这些特征融入更新后的描述中。",
        "location": "【参考图片】\n请仔细分析参考图片中的建筑风格、装饰元素、光线氛围、色调等关键视觉特征，并将这些特征融入更新后的描述中。",
    }
    return contexts.get(asset_type, "")


def _sync_description_after_modify(caller, db, asset, asset_type, modify_prompt, extra_image_urls, project_id):
    """AI 改图后同步更新资产描述"""
    try:
        original_desc = asset.description
        if not modify_prompt or not original_desc:
            return

        has_ref = bool(extra_image_urls)
        image_context = _build_image_context(asset_type, has_ref)

        if asset_type == "character":
            sync_prompt = build_char_desc_prompt(
                original_description=original_desc,
                modify_instruction=modify_prompt,
                image_context=image_context,
            )
        elif asset_type == "location":
            sync_prompt = build_loc_desc_prompt(
                location_name=asset.name,
                original_description=original_desc,
                modify_instruction=modify_prompt,
                image_context=image_context,
            )
        else:
            sync_prompt = build_prop_desc_prompt(
                prop_name=asset.name,
                original_description=original_desc,
                modify_instruction=modify_prompt,
                image_context=image_context,
            )

        if has_ref:
            result = caller.vision("analysis_model", sync_prompt, extra_image_urls, project_id=project_id)
        else:
            result = caller.call("analysis_model", sync_prompt, project_id=project_id)

        import json_repair
        parsed = json_repair.loads(result.content)
        new_desc = parsed.get("prompt", "") if isinstance(parsed, dict) else ""
        if new_desc:
            asset.description = new_desc
            db.add(asset)
            db.commit()
            logger.info(f"描述同步完成: {asset_type}/{asset.id}")

    except Exception as e:
        logger.warning(f"描述同步失败（不影响修图结果）: {asset_type}/{asset.id}, error={e}")


@celery.task(bind=True, max_retries=1, default_retry_delay=30)
def generate_project_asset_image(
    self,
    project_id: str,
    asset_type: str,
    asset_id: str,
    model_config: dict,
    art_style: str,
):
    db = SessionLocal()
    try:
        asset = _get_asset(db, asset_type, asset_id)
        if not asset:
            logger.error(f"资产不存在: {asset_type}/{asset_id}")
            return

        project = db.query(Project).filter(Project.id == project_id).first()
        user_id = project.user_id if project else None

        project_asset_crud.update_gen_status(db, asset, "generating")
        ws_manager.publish_project_event(
            user_id, project_id, "project_asset_generation_started",
            {"asset_id": asset_id, "asset_type": asset_type},
        )

        prompt = _build_image_prompt(asset, art_style)
        size = _get_asset_size(asset_type)

        caller = ModelCaller.from_config_snapshot(model_config, db=db)
        logger.debug(f"[Celery-文生图] caller 创建完成: db={'有' if db else 'None'} model_config_keys={list(model_config.keys()) if model_config else 'None'}")
        result = caller.generate_image(
            model_key="character_model",
            asset_type=asset_type,
            prompt=prompt,
            size=size,
            n=1,
            project_id=project_id,
        )

        image_url = _get_image_url(result)
        if not image_url:
            raise ValueError("图片生成返回空结果")

        key, thumb_key = download_and_store_image(image_url, user_id, f"project-{asset_type}")
        project_asset_crud.update_image(db, asset, key, thumb_key)

        _save_to_local(project_id, image_url, asset_type, asset_id)

        ws_manager.publish_project_event(
            user_id, project_id, "project_asset_generation_completed",
            {
                "asset_id": asset_id,
                "asset_type": asset_type,
                "image_url": cos_client.key_to_url(key),
                "thumbnail_url": cos_client.key_to_url(thumb_key) if thumb_key else None,
            },
        )

        from app.utils.volc_sync import sync_asset_to_volc
        volc_id = sync_asset_to_volc(db, project_id, asset, asset_type, user_id=user_id)
        if volc_id:
            ws_manager.publish_project_event(
                user_id, project_id, "project_asset_volc_sync_completed",
                {"asset_id": asset_id, "asset_type": asset_type, "volc_private_asset_id": volc_id},
            )
        else:
            ws_manager.publish_project_event(
                user_id, project_id, "project_asset_volc_sync_failed",
                {"asset_id": asset_id, "asset_type": asset_type},
            )

        logger.info(f"资产图片生成完成: {asset_type}/{asset_id}")

    except Exception as e:
        logger.error(f"资产图片生成失败: {asset_type}/{asset_id}, error={traceback.format_exc()}")
        try:
            asset = _get_asset(db, asset_type, asset_id)
            if asset:
                project_asset_crud.update_gen_status(db, asset, "failed")
                project = db.query(Project).filter(Project.id == project_id).first()
                user_id = project.user_id if project else None
                ws_manager.publish_project_event(
                    user_id, project_id, "project_asset_generation_failed",
                    {"asset_id": asset_id, "asset_type": asset_type, "error": str(e)},
                )
        except Exception:
            pass

        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=30)

    finally:
        db.close()


@celery.task()
def batch_generate_project_assets(
    project_id: str,
    asset_ids: list[dict],
    model_config: dict,
    art_style: str,
):
    base_eta = datetime.now(timezone.utc)
    count = 0
    for i, item in enumerate(asset_ids):
        eta = base_eta + timedelta(milliseconds=500 * i)
        generate_project_asset_image.apply_async(
            args=(project_id, item["type"], item["id"], model_config, art_style),
            eta=eta,
        )
        count += 1

    # 注释原因：批量生成不应改变项目状态，与单资产生成行为保持一致，避免前端因状态变更导致页面卡死
    # db = SessionLocal()
    # try:
    #     project = db.query(Project).filter(Project.id == project_id).first()
    #     if project:
    #         project.status = "assetGenerating"
    #         db.add(project)
    #         db.commit()
    # finally:
    #     db.close()

    logger.info(f"批量生成提交: 项目 {project_id}, 任务数 {count}, 每 0.5s 分发一个")


@celery.task(bind=True, max_retries=1, default_retry_delay=30)
def modify_project_asset_image(
    self,
    project_id: str,
    asset_type: str,
    asset_id: str,
    modify_prompt: str,
    extra_image_urls: list[str] | None,
    model_config: dict,
    art_style: str = "realistic",
):
    db = SessionLocal()
    try:
        asset = _get_asset(db, asset_type, asset_id)
        if not asset:
            logger.error(f"资产不存在: {asset_type}/{asset_id}")
            return
        if not asset.image_url:
            raise ValueError("资产无图片，无法修图")

        project = db.query(Project).filter(Project.id == project_id).first()
        user_id = project.user_id if project else None

        project_asset_crud.update_gen_status(db, asset, "generating")
        ws_manager.publish_project_event(
            user_id, project_id, "project_asset_generation_started",
            {"asset_id": asset_id, "asset_type": asset_type},
        )

        current_url = asset.image_url
        if not current_url.startswith("http"):
            current_url = cos_client.key_to_url(current_url)

        image_urls = [current_url]
        if extra_image_urls:
            image_urls.extend(extra_image_urls)

        caller = ModelCaller.from_config_snapshot(model_config, db=db)
        logger.debug(f"[Celery-图生图] caller 创建完成: db={'有' if db else 'None'}")
        size = _get_asset_size(asset_type)

        styled_prompt = MODIFY_PROMPT_MAP.get(asset_type, "{}").format(modify_prompt)

        result = caller.edit_image(
            model_key="edit_model",
            prompt=styled_prompt,
            image_urls=image_urls,
            size=size,
            n=1,
            project_id=project_id,
        )

        new_image_url = _get_image_url(result)
        if not new_image_url:
            raise ValueError("修图返回空结果")

        key, thumb_key = download_and_store_image(new_image_url, user_id, f"project-{asset_type}-edit")
        project_asset_crud.update_image(db, asset, key, thumb_key)

        _sync_description_after_modify(caller, db, asset, asset_type, modify_prompt, extra_image_urls, project_id)

        _save_to_local(project_id, new_image_url, asset_type, asset_id)

        ws_manager.publish_project_event(
            user_id, project_id, "project_asset_image_modified",
            {
                "asset_id": asset_id,
                "asset_type": asset_type,
                "image_url": cos_client.key_to_url(key),
                "thumbnail_url": cos_client.key_to_url(thumb_key) if thumb_key else None,
            },
        )

        from app.utils.volc_sync import sync_asset_to_volc
        volc_id = sync_asset_to_volc(db, project_id, asset, asset_type, user_id=user_id)
        if volc_id:
            ws_manager.publish_project_event(
                user_id, project_id, "project_asset_volc_sync_completed",
                {"asset_id": asset_id, "asset_type": asset_type, "volc_private_asset_id": volc_id},
            )
        else:
            ws_manager.publish_project_event(
                user_id, project_id, "project_asset_volc_sync_failed",
                {"asset_id": asset_id, "asset_type": asset_type},
            )

        logger.info(f"资产图片修图完成: {asset_type}/{asset_id}")

    except Exception as e:
        logger.error(f"资产图片修图失败: {asset_type}/{asset_id}, error={e}")
        try:
            asset = _get_asset(db, asset_type, asset_id)
            if asset:
                project_asset_crud.update_gen_status(db, asset, "failed")
                project = db.query(Project).filter(Project.id == project_id).first()
                user_id = project.user_id if project else None
                ws_manager.publish_project_event(
                    user_id, project_id, "project_asset_generation_failed",
                    {"asset_id": asset_id, "asset_type": asset_type, "error": str(e)},
                )
        except Exception:
            pass

        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=30)

    finally:
        db.close()


@celery.task(bind=True, max_retries=1, default_retry_delay=30)
def reference_generate_project_character(
    self,
    project_id: str,
    asset_id: str,
    reference_image_urls: list[str],
    description: str | None,
    mode: str,
    art_style: str | None,
    model_config: dict,
):
    db = SessionLocal()
    try:
        asset = _get_asset(db, "character", asset_id)
        if not asset:
            logger.error(f"角色不存在: {asset_id}")
            return

        project = db.query(Project).filter(Project.id == project_id).first()
        user_id = project.user_id if project else None

        project_asset_crud.update_gen_status(db, asset, "generating")
        ws_manager.publish_project_event(
            user_id, project_id, "project_asset_generation_started",
            {"asset_id": asset_id, "asset_type": "character"},
        )

        caller = ModelCaller.from_config_snapshot(model_config, db=db)
        desc = description or asset.description or f"角色 {asset.name}"

        if mode == "extract":
            vision_result = caller.vision(
                model_key="analysis_model",
                prompt="请详细描述这个角色的外观特征，包括发型、脸型、五官、服装、配饰、体型等。用中文描述。",
                image_urls=reference_image_urls,
                project_id=project_id,
            )
            if vision_result.content:
                desc = vision_result.content

        style_desc = get_art_style_prompt(art_style or "realistic")
        prompt = add_character_prompt_suffix(desc)
        if style_desc:
            prompt = f"{prompt}，{style_desc}"
        system_prefix = f"{asset.image_model_system_prompt}\n" if asset.image_model_system_prompt else ""
        prompt = f"{system_prefix}{prompt}"
        size = _get_asset_size("character")

        result = caller.edit_image(
            model_key="character_model",
            prompt=prompt,
            image_urls=reference_image_urls,
            size=size,
            n=1,
            project_id=project_id,
        )

        image_url = _get_image_url(result)
        if not image_url:
            raise ValueError("参考图生图返回空结果")

        key, thumb_key = download_and_store_image(image_url, user_id, "project-character-ref")
        project_asset_crud.update_image(db, asset, key, thumb_key)

        _save_to_local(project_id, image_url, "character", asset_id)

        ws_manager.publish_project_event(
            user_id, project_id, "project_asset_image_modified",
            {
                "asset_id": asset_id,
                "asset_type": "character",
                "image_url": cos_client.key_to_url(key),
                "thumbnail_url": cos_client.key_to_url(thumb_key) if thumb_key else None,
            },
        )

        from app.utils.volc_sync import sync_asset_to_volc
        volc_id = sync_asset_to_volc(db, project_id, asset, "character", user_id=user_id)
        if volc_id:
            ws_manager.publish_project_event(
                user_id, project_id, "project_asset_volc_sync_completed",
                {"asset_id": asset_id, "asset_type": "character", "volc_private_asset_id": volc_id},
            )
        else:
            ws_manager.publish_project_event(
                user_id, project_id, "project_asset_volc_sync_failed",
                {"asset_id": asset_id, "asset_type": "character"},
            )

        logger.info(f"参考图生图完成: character/{asset_id}")

    except Exception as e:
        logger.error(f"参考图生图失败: character/{asset_id}, error={e}")
        try:
            asset = _get_asset(db, "character", asset_id)
            if asset:
                project_asset_crud.update_gen_status(db, asset, "failed")
                project = db.query(Project).filter(Project.id == project_id).first()
                user_id = project.user_id if project else None
                ws_manager.publish_project_event(
                    user_id, project_id, "project_asset_generation_failed",
                    {"asset_id": asset_id, "asset_type": "character", "error": str(e)},
                )
        except Exception:
            pass

        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=30)

    finally:
        db.close()
