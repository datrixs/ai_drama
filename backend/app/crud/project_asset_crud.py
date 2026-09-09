"""
项目资产 CRUD 操作
"""
import io
import json
import re
import zipfile
from datetime import datetime
from uuid import uuid4

import httpx
from fastapi import HTTPException
from sqlalchemy import or_, and_
from sqlalchemy.orm import Session

from app import crud
from app.core.logging import logger
from app.models.project_asset import ProjectCharacter, ProjectLocation, ProjectProp, Episode, Storyboard
from app.utils.tencent_cos_utils import cos_client


class CRUDProjectAsset:
    """项目资产 CRUD（角色/场景/道具通用）"""

    # 区域字段：图片被替换/撤销时必须同时清空两个区域的同步 ID，
    # 否则旧 ID 会残留导致页面误显示"已同步"，且新图同步失败时无法回退为"未同步"。
    _REGION_ASSET_ID_FIELDS = ("volc_private_asset_id", "byteplus_asset_id")

    def _clear_volc_ids(self, asset) -> None:
        """清空资产的两个区域同步 ID（不 commit，由调用方负责）"""
        for field in self._REGION_ASSET_ID_FIELDS:
            if hasattr(asset, field):
                setattr(asset, field, None)

    # ============ 查询 ============

    def get_by_project(self, db: Session, project_id: str, model_class):
        """获取项目的某类资产"""
        return db.query(model_class).filter(
            model_class.project_id == project_id,
            model_class.is_deleted == False,
        ).order_by(model_class.create_time).all()

    def count_by_project(self, db: Session, project_id: str, model_class) -> int:
        """计数"""
        return db.query(model_class).filter(
            model_class.project_id == project_id,
            model_class.is_deleted == False,
        ).count()

    def count_by_status(self, db: Session, project_id: str, model_class, status: str) -> int:
        """按状态计数"""
        return db.query(model_class).filter(
            model_class.project_id == project_id,
            model_class.is_deleted == False,
            model_class.gen_status == status,
        ).count()

    def get_asset(self, db: Session, asset_type: str, asset_id: str):
        """根据类型和 ID 获取资产"""
        model_map = {
            "character": ProjectCharacter,
            "location": ProjectLocation,
            "prop": ProjectProp,
        }
        model_class = model_map.get(asset_type)
        if not model_class:
            return None
        return db.query(model_class).filter(
            model_class.id == asset_id,
            model_class.is_deleted == False,
        ).first()

    def get_all_pending(self, db: Session, project_id: str) -> list[dict]:
        """获取所有未完成（非 completed）的资产，返回 [{type, id}]"""
        result = []
        for asset_type, model_class in [
            ("character", ProjectCharacter),
            ("location", ProjectLocation),
            ("prop", ProjectProp),
        ]:
            rows = db.query(model_class).filter(
                model_class.project_id == project_id,
                model_class.is_deleted == False,
                model_class.gen_status != "completed",
            ).all()
            for row in rows:
                result.append({"type": asset_type, "id": row.id})
        return result

    # ============ 状态更新 ============

    def update_gen_status(self, db: Session, asset, status: str):
        """更新生成状态"""
        asset.gen_status = status
        db.add(asset)
        db.commit()

    def update_image(self, db: Session, asset, image_url: str, thumbnail_url: str | None = None):
        """更新图片 URL 和状态（保存当前图片/缩略图到 previous_*）"""
        if asset.image_url:
            asset.previous_image_url = asset.image_url
        asset.image_url = image_url
        # 同步保存旧缩略图（用于撤销时恢复）
        if hasattr(asset, "previous_thumbnail_url"):
            if asset.thumbnail_url:
                asset.previous_thumbnail_url = asset.thumbnail_url
            if thumbnail_url is not None:
                asset.thumbnail_url = thumbnail_url
        elif thumbnail_url is not None:
            asset.thumbnail_url = thumbnail_url
        asset.gen_status = "completed"
        # 图片变了，原同步 ID 失效；清空两个区域字段，由调用方按需重新同步
        self._clear_volc_ids(asset)
        db.add(asset)
        db.commit()

    def undo_image(self, db: Session, asset) -> str | None:
        """撤销图片：将 previous_image_url / previous_thumbnail_url 交换回当前"""
        if not asset.previous_image_url:
            return None
        current = asset.image_url
        asset.image_url = asset.previous_image_url
        asset.previous_image_url = current
        # 同步交换缩略图
        if hasattr(asset, "previous_thumbnail_url"):
            current_thumb = asset.thumbnail_url
            asset.thumbnail_url = asset.previous_thumbnail_url
            asset.previous_thumbnail_url = current_thumb
        asset.gen_status = "completed"
        # 图片被还原，原同步 ID 对应的是另一张图，必须清空
        self._clear_volc_ids(asset)
        db.add(asset)
        db.commit()
        return asset.image_url

    def soft_delete(self, db: Session, asset):
        """软删除"""
        asset.is_deleted = True
        asset.delete_time = datetime.now()
        db.add(asset)
        db.commit()

    def create_asset(self, db: Session, project_id: str, asset_type: str, data: dict, user_id: str):
        """手动创建单个资产"""
        model_map = {
            "character": ProjectCharacter,
            "location": ProjectLocation,
            "prop": ProjectProp,
        }
        model_class = model_map.get(asset_type)
        if not model_class:
            return None
        asset = model_class(
            id=str(uuid4()),
            project_id=project_id,
            gen_status="pending",
            create_uid=user_id,
            update_uid=user_id,
            **data,
        )
        db.add(asset)
        db.commit()
        db.refresh(asset)
        return asset

    # ============ 统计 ============

    def compute_stats(self, db: Session, project_id: str) -> dict:
        """计算资产统计"""
        stats = {"total": 0, "pending": 0, "generating": 0, "completed": 0, "failed": 0}
        for model_class in [ProjectCharacter, ProjectLocation, ProjectProp]:
            stats["pending"] += self.count_by_status(db, project_id, model_class, "pending")
            stats["generating"] += self.count_by_status(db, project_id, model_class, "generating")
            stats["completed"] += self.count_by_status(db, project_id, model_class, "completed")
            stats["failed"] += self.count_by_status(db, project_id, model_class, "failed")
        stats["total"] = stats["pending"] + stats["generating"] + stats["completed"] + stats["failed"]
        return stats

    def check_all_ready(self, db: Session, project_id: str) -> bool:
        """检查是否所有资产都已有图片且不在生成中"""
        for model_class in [ProjectCharacter, ProjectLocation, ProjectProp]:
            count = self.count_by_project(db, project_id, model_class)
            if count == 0:
                return False
            # 有图片的数量
            with_image = db.query(model_class).filter(
                model_class.project_id == project_id,
                model_class.is_deleted == False,
                model_class.image_url != None,
                model_class.image_url != "",
            ).count()
            if with_image != count:
                return False
            # 没有正在生成的
            generating = self.count_by_status(db, project_id, model_class, "generating")
            if generating > 0:
                return False
        return True

    # ============ 解析（从分析结果创建资产） ============

    def parse_from_analysis(self, db: Session, project_id: str, version, user_id: str) -> dict:
        """
        从 AnalysisVersion 解析创建资产/剧集/分镜记录。
        幂等：已有资产记录时跳过。
        """
        # 幂等检查
        existing = self.count_by_project(db, project_id, ProjectCharacter)
        if existing > 0:
            logger.info(f"项目 {project_id} 已有 {existing} 个角色，跳过解析")
            return self._count_all(db, project_id)

        # 诊断日志
        cp_type = type(version.character_profiles).__name__
        cp_preview = str(version.character_profiles)[:200] if version.character_profiles else "None"
        sd_type = type(version.scene_descriptions).__name__
        sd_preview = str(version.scene_descriptions)[:200] if version.scene_descriptions else "None"
        pd_type = type(version.prop_descriptions).__name__
        pd_preview = str(version.prop_descriptions)[:200] if version.prop_descriptions else "None"
        logger.info(
            f"资产解析诊断 project={project_id} version={version.id} | "
            f"character_profiles({cp_type}): {cp_preview} | "
            f"scene_descriptions({sd_type}): {sd_preview} | "
            f"prop_descriptions({pd_type}): {pd_preview}"
        )

        counts = {"characters": 0, "locations": 0, "props": 0, "episodes": 0, "storyboards": 0}

        # 解析角色
        profiles = self._parse_json_field(version.character_profiles)
        if isinstance(profiles, list):
            for p in profiles:
                if not isinstance(p, dict) or not p.get("name"):
                    continue
                char = ProjectCharacter(
                    id=str(uuid4()),
                    project_id=project_id,
                    name=p["name"],
                    aliases=p.get("aliases"),
                    description=p.get("description"),
                    profile_data=p.get("profile_data"),
                    image_prompt=p.get("image_prompt"),
                    gen_status="pending",
                    create_uid=user_id,
                    update_uid=user_id,
                )
                db.add(char)
                counts["characters"] += 1

        # 解析场景
        scenes = self._parse_json_field(version.scene_descriptions)
        if isinstance(scenes, list):
            for s in scenes:
                if not isinstance(s, dict) or not s.get("name"):
                    continue
                loc = ProjectLocation(
                    id=str(uuid4()),
                    project_id=project_id,
                    name=s["name"],
                    place=s.get("place"),
                    time=s.get("time"),
                    summary=s.get("summary"),
                    description=s.get("description"),
                    image_prompt=s.get("image_prompt"),
                    gen_status="pending",
                    create_uid=user_id,
                    update_uid=user_id,
                )
                db.add(loc)
                counts["locations"] += 1

        # 解析道具：Layer 2 提供 name/description/image_prompt
        props = self._parse_json_field(version.prop_descriptions)
        if isinstance(props, list):
            for p in props:
                if not isinstance(p, dict) or not p.get("name"):
                    continue
                prop = ProjectProp(
                    id=str(uuid4()),
                    project_id=project_id,
                    name=p["name"],
                    aliases=p.get("aliases"),
                    description=p.get("description"),
                    image_prompt=p.get("image_prompt"),
                    gen_status="pending",
                    create_uid=user_id,
                    update_uid=user_id,
                )
                db.add(prop)
                counts["props"] += 1

        # 解析剧集（幂等：已存在则复用）
        outlines = self._parse_json_field(version.episode_outlines)
        if isinstance(outlines, list):
            for ep in outlines:
                if not isinstance(ep, dict):
                    continue
                ep_num = ep.get("episode_number", ep.get("episode"))
                if ep_num is None:
                    continue
                try:
                    ep_num = int(ep_num)
                except (ValueError, TypeError):
                    continue
                existing = db.query(Episode).filter(
                    Episode.project_id == project_id,
                    Episode.episode_number == ep_num,
                    Episode.is_deleted == False,
                ).first()
                if existing:
                    continue
                episode = Episode(
                    id=str(uuid4()),
                    project_id=project_id,
                    episode_number=ep_num,
                    title=ep.get("title", ""),
                    outline=ep.get("summary", ep.get("outline", "")),
                    status="pending",
                    create_uid=user_id,
                    update_uid=user_id,
                )
                db.add(episode)
                counts["episodes"] += 1

        db.flush()

        # # 解析第一集分镜
        # storyboard_data = self._parse_json_field(version.first_ep_storyboard)
        # scenes_list = []
        # if isinstance(storyboard_data, dict):
        #     scenes_list = storyboard_data.get("scenes", [])
        # elif isinstance(storyboard_data, list):
        #     scenes_list = storyboard_data
        #
        # first_episode_id = episodes_map.get(1)
        # if first_episode_id and isinstance(scenes_list, list):
        #     for idx, scene in enumerate(scenes_list):
        #         if not isinstance(scene, dict):
        #             continue
        #         sb = Storyboard(
        #             id=str(uuid4()),
        #             episode_id=first_episode_id,
        #             shot_number=scene.get("scene_number", scene.get("shot_number", idx + 1)),
        #             description=scene.get("action", scene.get("description", "")),
        #             reference_image=scene.get("reference_image"),
        #             duration=scene.get("duration"),
        #             status="pending",
        #             create_uid=user_id,
        #             update_uid=user_id,
        #         )
        #         db.add(sb)
        #         counts["storyboards"] += 1

        db.commit()
        logger.info(f"项目 {project_id} 解析完成: {counts}")
        return counts

    def _count_all(self, db: Session, project_id: str) -> dict:
        """统计已有记录数"""
        return {
            "characters": self.count_by_project(db, project_id, ProjectCharacter),
            "locations": self.count_by_project(db, project_id, ProjectLocation),
            "props": self.count_by_project(db, project_id, ProjectProp),
            "episodes": db.query(Episode).filter(
                Episode.project_id == project_id, Episode.is_deleted == False,
            ).count(),
            "storyboards": 0,
        }

    @staticmethod
    def _parse_json_field(value):
        """兼容 JSON 字符串和已解析对象"""
        if value is None:
            return None
        if isinstance(value, (list, dict)):
            return value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return None
        return None

    # ============ 从资产中心导入 ============

    def copy_character_from_global(self, db: Session, project_character_id: str, global_character_id: str, user_id: str, owner_user_id: str) -> ProjectCharacter:
        """从全局角色导入图片和音色到项目角色"""
        # 1. 查找全局角色
        global_char = crud.global_character_crud.get_by_owner(db, user_id, owner_user_id).filter(
            crud.global_character_crud.model.id == global_character_id,
        ).first()
        if not global_char:
            raise HTTPException(status_code=400, detail="全局角色不存在或无权访问")

        # 2. 获取全局角色形象，提取主形象图片 COS key 和缩略图 key
        appearances = crud.global_character_appearance_crud.get_by_character(db, global_character_id).all()
        image_key = self._resolve_character_image_key(appearances)
        thumb_key = self._resolve_character_thumbnail_key(appearances)

        # 3. 加载目标项目角色
        project_char = db.query(ProjectCharacter).filter(
            ProjectCharacter.id == project_character_id,
            ProjectCharacter.is_deleted == False,
        ).first()
        if not project_char:
            raise HTTPException(status_code=400, detail="项目角色不存在")

        # 4. 更新项目角色
        # 若新图与当前图不同，原同步 ID 失效，必须清空（与新图重新同步由调用方负责）
        image_changed = image_key and image_key != project_char.image_url
        project_char.image_url = image_key
        project_char.thumbnail_url = thumb_key
        project_char.source_global_id = global_character_id
        project_char.profile_confirmed = True
        project_char.voice_id = global_char.voice_id
        project_char.voice_type = global_char.voice_type
        project_char.custom_voice_url = global_char.custom_voice_url
        if image_key:
            project_char.gen_status = "completed"
        if image_changed:
            self._clear_volc_ids(project_char)

        db.add(project_char)
        db.commit()
        db.refresh(project_char)
        return project_char

    def copy_location_from_global(self, db: Session, project_asset_id: str, global_location_id: str, owner_user_id: str, model_class) -> object:
        """从全局场景/道具导入图片到项目场景/道具（通用）"""
        # 1. 查找全局场景
        global_loc = crud.global_location_crud.get_by_owner(db, owner_user_id).filter(
            crud.global_location_crud.model.id == global_location_id,
        ).first()
        if not global_loc:
            raise HTTPException(status_code=400, detail="全局场景/道具不存在或无权访问")

        # 2. 获取全局场景图片，提取选中图片 COS key 和缩略图 key
        images = crud.global_location_image_crud.get_by_location(db, global_location_id).all()
        image_key = self._resolve_location_image_key(images)
        thumb_key = self._resolve_location_thumbnail_key(images)

        # 3. 加载目标项目资产
        project_asset = db.query(model_class).filter(
            model_class.id == project_asset_id,
            model_class.is_deleted == False,
        ).first()
        if not project_asset:
            raise HTTPException(status_code=400, detail="项目资产不存在")

        # 4. 更新项目资产
        # 若新图与当前图不同，原同步 ID 失效，必须清空
        image_changed = image_key and image_key != project_asset.image_url
        project_asset.image_url = image_key
        project_asset.thumbnail_url = thumb_key
        project_asset.source_global_id = global_location_id
        if image_key:
            project_asset.gen_status = "completed"
        if image_changed:
            self._clear_volc_ids(project_asset)
        # 场景类型额外复制 summary
        if hasattr(project_asset, 'summary') and hasattr(global_loc, 'summary'):
            project_asset.summary = global_loc.summary

        db.add(project_asset)
        db.commit()
        db.refresh(project_asset)
        return project_asset

    @staticmethod
    def _resolve_character_image_key(appearances: list) -> str | None:
        """从角色形象列表提取主形象图片的 COS key（不转换为 URL）"""
        if not appearances:
            return None
        primary = next((a for a in appearances if a.appearance_index == 0), appearances[0])
        image_urls = json.loads(primary.image_urls) if primary.image_urls else []
        if image_urls:
            idx = primary.selected_index if primary.selected_index is not None else 0
            key = image_urls[idx] if idx < len(image_urls) else image_urls[0]
            if key:
                return key
        return primary.image_url

    @staticmethod
    def _resolve_character_thumbnail_key(appearances: list) -> str | None:
        """从角色形象列表提取主形象缩略图的 COS key（优先从 thumbnail_urls 数组按 selected_index 选取）"""
        if not appearances:
            return None
        primary = next((a for a in appearances if a.appearance_index == 0), appearances[0])
        thumb_urls = json.loads(primary.thumbnail_urls) if primary.thumbnail_urls else []
        if thumb_urls:
            idx = primary.selected_index if primary.selected_index is not None else 0
            key = thumb_urls[idx] if idx < len(thumb_urls) else thumb_urls[0]
            if key:
                return key
        return primary.thumbnail_url

    @staticmethod
    def _resolve_location_image_key(images: list) -> str | None:
        """从场景图片列表提取选中图片的 COS key（不转换为 URL）"""
        if not images:
            return None
        selected = next((i for i in images if i.is_selected), images[0])
        return selected.image_url if selected else None

    @staticmethod
    def _resolve_location_thumbnail_key(images: list) -> str | None:
        """从场景图片列表提取选中图片缩略图的 COS key"""
        if not images:
            return None
        selected = next((i for i in images if i.is_selected), images[0])
        return selected.thumbnail_url if selected else None

    # ============ 打包下载 ============

    def get_assets_with_images(self, db: Session, project_id: str) -> dict:
        """获取项目下所有有图片的资产"""
        characters = db.query(ProjectCharacter).filter(
            ProjectCharacter.project_id == project_id,
            ProjectCharacter.is_deleted == False,
            ProjectCharacter.image_url != None,
            ProjectCharacter.image_url != "",
        ).order_by(ProjectCharacter.create_time).all()

        locations = db.query(ProjectLocation).filter(
            ProjectLocation.project_id == project_id,
            ProjectLocation.is_deleted == False,
            ProjectLocation.image_url != None,
            ProjectLocation.image_url != "",
        ).order_by(ProjectLocation.create_time).all()

        props = db.query(ProjectProp).filter(
            ProjectProp.project_id == project_id,
            ProjectProp.is_deleted == False,
            ProjectProp.image_url != None,
            ProjectProp.image_url != "",
        ).order_by(ProjectProp.create_time).all()

        return {"characters": characters, "locations": locations, "props": props}

    def build_download_zip(self, assets_dict: dict) -> io.BytesIO | None:
        """将资产图片打包为 ZIP，无文件时返回 None"""
        _FILENAME_RE = re.compile(r'[/\\:*?"<>|]')

        def _sanitize(name: str) -> str:
            return _FILENAME_RE.sub('_', name).strip() or 'unnamed'

        def _fetch_image_bytes(url_or_key: str) -> bytes | None:
            if not url_or_key:
                return None
            try:
                url = cos_client.key_to_url(url_or_key) if not url_or_key.startswith('http') else url_or_key
                resp = httpx.get(url, timeout=30)
                return resp.content if resp.status_code == 200 else None
            except Exception:
                return None

        def _add_to_zip(zf: zipfile.ZipFile, category: str, assets: list) -> bool:
            name_count: dict[str, int] = {}
            has_file = False
            for asset in assets:
                data = _fetch_image_bytes(asset.image_url)
                if not data:
                    continue
                name = _sanitize(asset.name)
                if name in name_count:
                    name_count[name] += 1
                    fname = f"{category}/{name}_{name_count[name]}.jpg"
                else:
                    name_count[name] = 0
                    fname = f"{category}/{name}.jpg"
                zf.writestr(fname, data)
                has_file = True
            return has_file

        buffer = io.BytesIO()
        has_file = False

        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            has_file |= _add_to_zip(zf, "characters", assets_dict["characters"])
            has_file |= _add_to_zip(zf, "locations", assets_dict["locations"])
            has_file |= _add_to_zip(zf, "props", assets_dict["props"])

        if not has_file:
            return None

        buffer.seek(0)
        return buffer


project_asset_crud = CRUDProjectAsset()
