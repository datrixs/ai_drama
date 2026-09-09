"""
多模态脚本服务
- 生成多片段脚本
- 解析脚本 JSON
- 将资产引用注入脚本
- 根据脚本创建分镜片段记录
"""
import json
import re
from typing import Optional

from loguru import logger
from sqlalchemy.orm import Session

from app.core.prompts.multimodal_script import MULTIMODAL_SCRIPT_SYSTEM_PROMPT
from app.enums.user import UserRegion


def get_project_asset_map(db: Session, project_id: str) -> dict[str, str]:
    """获取项目的资产映射 {assetId: imageUrl}"""
    from app.models.project_asset import ProjectCharacter, ProjectLocation, ProjectProp

    asset_map = {}
    for char in db.query(ProjectCharacter).filter(
        ProjectCharacter.project_id == project_id,
        ProjectCharacter.is_deleted == False,
    ).all():
        if char.image_url:
            asset_map[char.id] = char.image_url

    for loc in db.query(ProjectLocation).filter(
        ProjectLocation.project_id == project_id,
        ProjectLocation.is_deleted == False,
    ).all():
        if loc.image_url:
            asset_map[loc.id] = loc.image_url

    for prop in db.query(ProjectProp).filter(
        ProjectProp.project_id == project_id,
        ProjectProp.is_deleted == False,
    ).all():
        if prop.image_url:
            asset_map[prop.id] = prop.image_url

    return asset_map


def get_volc_asset_map(db: Session, project_id: str, region: str = UserRegion.DOMESTIC) -> dict[str, str]:
    """获取项目的火山资产映射 {internalId: Asset://volcPrivateAssetId}

    优先使用火山私域 ID（Asset://格式），未同步的回退到 COS 签名 URL

    Args:
        region: DOMESTIC-使用 volc_private_asset_id；OVERSEAS-使用 byteplus_asset_id
    """
    from app.models.project_asset import ProjectCharacter, ProjectLocation, ProjectProp
    from app.utils.tencent_cos_utils import cos_client

    volc_map = {}
    asset_id_field = "byteplus_asset_id" if region == UserRegion.OVERSEAS else "volc_private_asset_id"

    def _resolve(internal_id: str, volc_id: str | None, cos_key: str | None) -> str:
        if volc_id and volc_id.strip():
            vid = volc_id.strip()
            return f"Asset://{vid}" if not vid.startswith("Asset://") else vid
        if cos_key:
            if cos_key.startswith("http://") or cos_key.startswith("https://"):
                return cos_key
            return cos_client.key_to_url(cos_key)
        return ""

    for char in db.query(ProjectCharacter).filter(
        ProjectCharacter.project_id == project_id,
        ProjectCharacter.is_deleted == False,
    ).all():
        url = _resolve(char.id, getattr(char, asset_id_field, None), char.image_url)
        if url:
            volc_map[char.id] = url

    for loc in db.query(ProjectLocation).filter(
        ProjectLocation.project_id == project_id,
        ProjectLocation.is_deleted == False,
    ).all():
        url = _resolve(loc.id, getattr(loc, asset_id_field, None), loc.image_url)
        if url:
            volc_map[loc.id] = url

    for prop in db.query(ProjectProp).filter(
        ProjectProp.project_id == project_id,
        ProjectProp.is_deleted == False,
    ).all():
        url = _resolve(prop.id, getattr(prop, asset_id_field, None), prop.image_url)
        if url:
            volc_map[prop.id] = url

    return volc_map


def _get_asset_descriptors(db: Session, project_id: str) -> list[dict]:
    """获取项目资产描述列表（用于 prompt 和一致性检查）"""
    from app.models.project_asset import ProjectCharacter, ProjectLocation, ProjectProp

    def _parse_aliases(raw) -> list[str]:
        if not raw:
            return []
        if isinstance(raw, list):
            return [a.strip() for a in raw if a and a.strip()]
        return [a.strip() for a in str(raw).replace(",", "，").replace("、", "，").split("，") if a.strip()]

    descriptors = []
    for char in db.query(ProjectCharacter).filter(
        ProjectCharacter.project_id == project_id,
        ProjectCharacter.is_deleted == False,
    ).all():
        aliases = _parse_aliases(char.aliases)
        descriptors.append({
            "assetId": char.id,
            "kind": "character",
            "name": char.name,
            "aliases": aliases,
            "description": (char.description or "")[:200],
        })

    for loc in db.query(ProjectLocation).filter(
        ProjectLocation.project_id == project_id,
        ProjectLocation.is_deleted == False,
    ).all():
        descriptors.append({
            "assetId": loc.id,
            "kind": "scene",
            "name": loc.name,
            "aliases": [],
            "description": (loc.summary or loc.description or "")[:200],
        })

    for prop in db.query(ProjectProp).filter(
        ProjectProp.project_id == project_id,
        ProjectProp.is_deleted == False,
    ).all():
        aliases = _parse_aliases(prop.aliases)
        descriptors.append({
            "assetId": prop.id,
            "kind": "prop",
            "name": prop.name,
            "aliases": aliases,
            "description": (prop.description or "")[:200],
        })

    return descriptors


def _safe_parse_json(raw_text: str) -> Optional[dict]:
    """安全解析 LLM 返回的 JSON"""
    # 去除 markdown 代码块标记
    text = raw_text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)
        text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # 尝试提取第一个 { 到最后一个 }
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass
        return None


class MultimodalScriptService:
    """多模态脚本服务"""

    def __init__(self, db: Session):
        self.db = db

    def generate_script(self, episode_id: str, project_id: str) -> dict:
        """
        调用 LLM 生成多片段脚本

        Args:
            episode_id: 剧集ID
            project_id: 项目ID

        Returns:
            解析后的脚本 dict
        """
        from app.models.project_asset import Episode
        episode = self.db.query(Episode).filter(Episode.id == episode_id).first()
        if not episode:
            raise ValueError(f"剧集不存在: {episode_id}")

        # 获取资产描述
        asset_descriptors = _get_asset_descriptors(self.db, project_id)

        # 获取模型配置
        from app.services.config_reader import ConfigReader
        from app.models.project import Project
        config_reader = ConfigReader(self.db)
        project = self.db.query(Project).filter(Project.id == project_id).first()
        resolved = config_reader.get_project_config(
            project.user_id if project else "",
            project.config if project else None,
        )

        # 构建用户消息
        episode_brief = (episode.episode_script or "").strip() or "（无正文，请根据资产生成短片脚本）"

        # 资产清单：只传名称和别名，要求 LLM 在文本中使用这些精确名称
        # ID 匹配由业务层 enrich_cross_segment_consistency 完成
        sorted_descriptors = sorted(
            [d for d in asset_descriptors if d.get("name") and d.get("assetId")],
            key=lambda d: len(d["name"]),
            reverse=True,
        )
        asset_lines = "\n".join(
            f"- 类型={d['kind']} 名称={d['name']}"
            + (f" 别名={','.join(d['aliases'])}" if d.get("aliases") else "")
            for d in sorted_descriptors
        )

        # 自动估算片段数量
        brief_len = len(episode_brief)
        estimated_total_sec = min(300, max(15, round(brief_len / 12)))
        min_segments = max(1, -(-estimated_total_sec // 15))  # ceil

        user_prompt_content = (
            f"【用户剧情/要求】\n{episode_brief}\n\n"
            f"【资产清单】\n{asset_lines or '(无资产，仅写纯文本分镜)'}\n\n"
            f"【系统自动估算（须遵守）】叙事体量约对应成片 {estimated_total_sec}s；"
            f"segments 数量至少 {min_segments}；"
            f"每个 segments[k].shots 时长之和必须≤15s。\n"
        )

        # 调用 LLM（temperature=0.3）
        from app.core.model_provider import ModelCaller
        caller = ModelCaller(resolved, db=self.db)
        result = caller.call(
            model_key="storyboard_model",
            prompt=user_prompt_content,
            system_prompt=MULTIMODAL_SCRIPT_SYSTEM_PROMPT,
            project_id=project_id,
            temperature=0.3,
            timeout=600,
        )

        raw_text = result.content
        if not raw_text:
            raise ValueError("LLM 返回为空")

        logger.info(f"脚本生成 LLM 完整返回 (input_tokens={result.input_tokens}, output_tokens={result.output_tokens}):\n{raw_text}")

        # 解析 JSON
        script = _safe_parse_json(raw_text)
        if not script:
            raise ValueError(f"无法解析 LLM 返回的 JSON: {raw_text[:500]}")

        # 验证 schema version
        if script.get("schemaVersion") != 2:
            logger.warning(f"脚本 schemaVersion 不是 2: {script.get('schemaVersion')}")

        return script

    def parse_script_json(self, raw_text: str) -> Optional[dict]:
        """解析脚本 JSON（v1/v2 兼容）"""
        script = _safe_parse_json(raw_text)
        if not script:
            return None

        # v1 格式兼容：包装成 v2
        if script.get("schemaVersion") == 1 or "segments" not in script:
            script = {
                "schemaVersion": 2,
                "styleAndKeywords": script.get("styleAndKeywords", ""),
                "sceneSummary": script.get("sceneSummary", ""),
                "segments": [
                    {
                        "segmentIndex": 1,
                        "segmentIntent": script.get("segmentIntent", ""),
                        "sceneSummary": script.get("sceneSummary", ""),
                        "shotTransition": script.get("shotTransition", ""),
                        "shots": script.get("shots", []),
                    }
                ],
            }

        return script

    def create_storyboard_from_script(self, db: Session, episode_id: str, script: dict,
                                       plain_text: str = "") -> list:
        """
        根据脚本创建分镜片段记录

        Args:
            db: 数据库会话
            episode_id: 剧集ID
            script: 脚本 dict
            plain_text: 原始纯文本（用于设置 video_prompt）

        Returns:
            创建的 Storyboard 列表
        """
        from app.models.project_asset import Storyboard
        from uuid import uuid4

        segments = script.get("segments", [])
        created = []

        # 清除该剧集已有的分镜片段（软删除，旧记录保留在数据库中）
        db.query(Storyboard).filter(
            Storyboard.episode_id == episode_id,
            Storyboard.is_deleted == False,
        ).update({"is_deleted": True})

        # 将纯文本按片段拆分，用于设置 video_prompt
        seg_texts = self._split_plain_text_by_segments(plain_text)

        for segment_data in segments:
            segment_index = segment_data.get("segmentIndex", len(created) + 1)
            shots = segment_data.get("shots", [])

            # 从纯文本中获取该片段的编辑内容作为 video_prompt
            seg_plain = seg_texts.get(segment_index, "")

            storyboard = Storyboard(
                id=str(uuid4()),
                episode_id=episode_id,
                segment_index=segment_index,
                segment_intent=segment_data.get("segmentIntent", ""),
                scene_summary=segment_data.get("sceneSummary", ""),
                shots=shots,
                style_and_keywords=script.get("styleAndKeywords", ""),
                raw_text=json.dumps(segment_data, ensure_ascii=False),
                video_prompt=seg_plain,
                status="pending",
                create_uid="system",
            )
            db.add(storyboard)
            created.append(storyboard)

        db.flush()
        logger.info(f"从脚本创建了 {len(created)} 个分镜片段: episode_id={episode_id}")
        return created

    def update_single_storyboard(
        self, db: Session, episode_id: str, segment_index: int,
        segment_plain_text: str, parsed_segment: dict, style_and_keywords: str = "",
    ) -> "Storyboard":
        """增量更新单个片段的 storyboard，已有记录则更新，不存在则创建"""
        from app.crud.storyboard_crud import storyboard_crud
        from app.models.project_asset import Storyboard
        from uuid import uuid4

        existing = storyboard_crud.get_by_segment_index(db, episode_id, segment_index)

        if existing:
            existing.segment_intent = parsed_segment.get("segmentIntent", "")
            existing.scene_summary = parsed_segment.get("sceneSummary", "")
            existing.shots = parsed_segment.get("shots", [])
            existing.style_and_keywords = style_and_keywords
            existing.raw_text = json.dumps(parsed_segment, ensure_ascii=False)
            existing.video_prompt = segment_plain_text
            db.add(existing)
            db.flush()
            logger.info(f"增量更新片段: episode_id={episode_id}, segment_index={segment_index}")
            return existing
        else:
            storyboard = Storyboard(
                id=str(uuid4()),
                episode_id=episode_id,
                segment_index=segment_index,
                segment_intent=parsed_segment.get("segmentIntent", ""),
                scene_summary=parsed_segment.get("sceneSummary", ""),
                shots=parsed_segment.get("shots", []),
                style_and_keywords=style_and_keywords,
                raw_text=json.dumps(parsed_segment, ensure_ascii=False),
                video_prompt=segment_plain_text,
                status="pending",
                create_uid="system",
            )
            db.add(storyboard)
            db.flush()
            logger.info(f"新建片段 storyboard: episode_id={episode_id}, segment_index={segment_index}")
            return storyboard

    @staticmethod
    def _split_plain_text_by_segments(plain_text: str) -> dict[int, str]:
        """将纯文本拆分为各片段文本（支持有/无 === 片段 N === 分隔符）"""
        if not plain_text or not plain_text.strip():
            return {}
        result = {}
        lines = plain_text.split("\n")

        # 1. 先尝试按旧格式 === 片段 N === 拆分（向后兼容）
        current_idx = None
        current_lines = []
        has_separator = False
        for line in lines:
            m = re.match(r"^===\s*片段\s+(\d+)\s*===$", line.strip())
            if m:
                has_separator = True
                if current_idx is not None:
                    result[current_idx] = "\n".join(current_lines)
                current_idx = int(m.group(1))
                current_lines = [line]
            elif current_idx is not None:
                current_lines.append(line)
        if has_separator:
            if current_idx is not None:
                result[current_idx] = "\n".join(current_lines)
            return result

        # 2. 无分隔符：按段落结构拆分
        # heuristic: 边界触发条件：当前片段已经走过「场景→分镜过渡」一个完整循环，或已有 shots
        # 此时又遇到「画面风格和类型:」或「场景:」开头的片段级字段，视为新片段
        seg_idx = 1
        seg_lines = []
        has_shots = False
        has_scene = False
        has_transition = False
        for line in lines:
            stripped = line.strip()
            # 边界检测（用上一轮的状态）
            passed_full_cycle = has_scene and has_transition
            if (has_shots or passed_full_cycle) and (
                re.match(r"^画面风格和类型:\s*", stripped) or
                re.match(r"^场景:\s*$", stripped)
            ):
                result[seg_idx] = "\n".join(seg_lines)
                seg_idx += 1
                seg_lines = []
                has_shots = False
                has_scene = False
                has_transition = False
            # 检测是否已进入 shots 区域
            if re.match(r"^分镜\d+\s*@", stripped) or re.match(r"^镜头\s*\d+\s*[:（]", stripped):
                has_shots = True
            # 状态更新（在边界检测之后）
            if re.match(r"^场景:\s*", stripped):
                has_scene = True
            if re.match(r"^分镜过渡:\s*", stripped):
                has_transition = True
            seg_lines.append(line)
        if seg_lines:
            result[seg_idx] = "\n".join(seg_lines)
        return result
