"""
Seedance 2.0 视频任务构建器

负责将多模态脚本数据转换为 Seedance 2.0 API 请求体
支持全能参考图（最多9张）和首尾帧
"""
import re
from typing import Optional

from loguru import logger

from app.core.prompts.seedance_video import (
    SECTION_STYLE,
    SECTION_SCENE_SUMMARY,
    SECTION_TRANSITION,
    SECTION_REFERENCE_NOTE,
    SECTION_SHOT_DETAILS,
    SECTION_QUALITY,
    SECTION_CONSTRAINTS,
    REFERENCE_NOTE_TEMPLATE,
    QUALITY_PARAMS_DEFAULT,
    CONSTRAINTS_DEFAULT,
    SHOT_LABEL_INDEX,
    SHOT_LABEL_TIME,
    SHOT_LABEL_CAMERA,
    SHOT_LABEL_ACTION,
    SHOT_LABEL_DIALOGUE,
    SHOT_LABEL_SOUND,
    SHOT_LABEL_DURATION,
)

MAX_REFERENCE_IMAGES = 9
SEEDANCE_DURATION_CATALOG = [4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]


def sanitize_narrative_fields(data: dict) -> dict:
    """清理落库 JSON 中混入的 <role>/<location> 标签，还原为裸 assetId"""
    tag_pattern = re.compile(r"<(?:role|location|prop)>([^<]+)</(?:role|location|prop)>")

    for field in ("segment_intent", "scene_summary", "shot_transition"):
        val = data.get(field, "")
        if isinstance(val, str) and tag_pattern.search(val):
            data[field] = tag_pattern.sub(r"\1", val)

    shots = data.get("shots", [])
    for shot in shots:
        for key in ("action", "dialogue"):
            val = shot.get(key, "")
            if isinstance(val, str) and tag_pattern.search(val):
                shot[key] = tag_pattern.sub(r"\1", val)
    return data


def collect_ordered_reference_asset_ids(
    script_data: dict,
    all_assets: dict[str, str],
) -> list[str]:
    """
    收集有序的参考图 assetId（最多9张）

    综合正文标签出现顺序 + JSON结构化数据收集

    Args:
        script_data: 片段脚本数据
        all_assets: {assetId: imageUrl} 所有可用资产

    Returns:
        有序的 assetId 列表
    """
    ordered_ids: list[str] = []
    seen: set[str] = set()

    # 1. 从正文中提取 assetId
    text_fields = []
    for field in ("segment_intent", "scene_summary", "shot_transition", "style_and_keywords"):
        val = script_data.get(field, "")
        if isinstance(val, str):
            text_fields.append(val)
    for shot in script_data.get("shots", []):
        for key in ("action", "dialogue"):
            val = shot.get(key, "")
            if isinstance(val, str):
                text_fields.append(val)

    full_text = "\n".join(text_fields)
    for asset_id in all_assets:
        if asset_id in full_text and asset_id not in seen:
            ordered_ids.append(asset_id)
            seen.add(asset_id)

    # 2. 从 shots 的结构化字段补充
    for shot in script_data.get("shots", []):
        scene_id = shot.get("sceneAssetId", "")
        if scene_id and scene_id not in seen and scene_id in all_assets:
            ordered_ids.append(scene_id)
            seen.add(scene_id)

        for char_id in shot.get("characterAssetIds", []):
            if char_id and char_id not in seen and char_id in all_assets:
                ordered_ids.append(char_id)
                seen.add(char_id)

        for prop_id in shot.get("propAssetIds", []):
            if prop_id and prop_id not in seen and prop_id in all_assets:
                ordered_ids.append(prop_id)
                seen.add(prop_id)

    # 3. 截断到最多9张
    return ordered_ids[:MAX_REFERENCE_IMAGES]


def apply_reference_picture_labels(text: str, ordered_asset_ids: list[str]) -> str:
    """
    将正文中的 assetId 替换为「@图片1」「@图片2」... 编号
    Seedance 2.0 要求用「@图片k」指称参考图
    """
    result = text
    for i, asset_id in enumerate(ordered_asset_ids, start=1):
        result = result.replace(asset_id, f"@图片{i}")
    return result


def compile_seedance_text_prompt(
    script_data: dict,
    ordered_asset_ids: list[str],
) -> str:
    """
    编译最终发送给模型的文本 prompt

    格式模板来自 core/prompts/seedance_video.py，包含:
    风格关键词 + 场景总述 + 分镜过渡 + 参考图使用说明 + 分镜明细
    """
    parts: list[str] = []

    # 风格关键词
    style = script_data.get("style_and_keywords", "")
    if style:
        parts.append(f"{SECTION_STYLE}{style}")

    # 场景总述
    scene_summary = script_data.get("scene_summary", "")
    if scene_summary:
        labeled = apply_reference_picture_labels(scene_summary, ordered_asset_ids)
        parts.append(f"{SECTION_SCENE_SUMMARY}{labeled}")

    # 分镜过渡
    transition = script_data.get("shot_transition", "")
    if transition:
        labeled = apply_reference_picture_labels(transition, ordered_asset_ids)
        parts.append(f"{SECTION_TRANSITION}{labeled}")

    # 参考图使用说明
    if ordered_asset_ids:
        ref_note = "、".join([f"@图片{i}" for i in range(1, len(ordered_asset_ids) + 1)])
        parts.append(f"{SECTION_REFERENCE_NOTE}{REFERENCE_NOTE_TEMPLATE.format(ref_labels=ref_note)}")

    # 分镜明细
    shots = script_data.get("shots", [])
    if shots:
        parts.append(SECTION_SHOT_DETAILS)
        for shot in shots:
            shot_parts = []
            index = shot.get("index", 0)
            shot_parts.append(SHOT_LABEL_INDEX.format(index=index))

            if shot.get("timeOfDay"):
                shot_parts.append(SHOT_LABEL_TIME.format(value=shot["timeOfDay"]))

            camera = shot.get("camera", "")
            if camera:
                labeled = apply_reference_picture_labels(camera, ordered_asset_ids)
                shot_parts.append(SHOT_LABEL_CAMERA.format(value=labeled))

            action = shot.get("action", "")
            if action:
                labeled = apply_reference_picture_labels(action, ordered_asset_ids)
                shot_parts.append(SHOT_LABEL_ACTION.format(value=labeled))

            dialogue = shot.get("dialogue", "")
            if dialogue:
                labeled = apply_reference_picture_labels(dialogue, ordered_asset_ids)
                # 编译层保障花括号包裹（符合 PE 指南台词规范）
                if not (labeled.startswith("{") and labeled.endswith("}")):
                    labeled = f"{{{labeled}}}"
                shot_parts.append(SHOT_LABEL_DIALOGUE.format(value=labeled))

            sound = shot.get("soundEffect", "")
            if sound:
                shot_parts.append(SHOT_LABEL_SOUND.format(value=sound))

            duration_hint = shot.get("durationHintSec")
            if duration_hint:
                shot_parts.append(SHOT_LABEL_DURATION.format(value=duration_hint))

            parts.append(" ".join(shot_parts))

    # 画质参数（U 型注意力尾部，增强模型对画质的关注度）
    parts.append(f"{SECTION_QUALITY}{QUALITY_PARAMS_DEFAULT}")

    # 约束条件（U 型注意力最尾部，约束最终输出质量）
    parts.append(f"{SECTION_CONSTRAINTS}{CONSTRAINTS_DEFAULT}")

    return "\n".join(parts)


def sum_shot_duration_hints(shots: list[dict]) -> float:
    """汇总各分镜时长（每镜夹在 0.5-3s，缺省 3s）"""
    total = 0.0
    for shot in shots:
        hint = shot.get("durationHintSec")
        if hint and isinstance(hint, (int, float)):
            clamped = max(0.5, min(3.0, float(hint)))
            total += clamped
        else:
            total += 3.0
    return total


def snap_to_duration_catalog(total_seconds: float) -> int:
    """将总秒数映射到离散 duration 档位"""
    rounded = round(total_seconds)
    for d in SEEDANCE_DURATION_CATALOG:
        if rounded <= d:
            return d
    return SEEDANCE_DURATION_CATALOG[-1]


def build_seedance_task_from_script(
    script_data: dict,
    all_assets: dict[str, str],
    model: str = "doubao-seedance-2-0-260128",
    resolution: str = "720p",
    ratio: str = "16:9",
    duration: Optional[int] = None,
    generate_audio: bool = True,
    first_frame_url: Optional[str] = None,
    last_frame_url: Optional[str] = None,
) -> dict:
    """
    核心构建函数：将片段脚本数据构建为 Seedance 2.0 API 请求体

    Args:
        script_data: 片段脚本数据（含 shots、scene_summary 等）
        all_assets: {assetId: imageUrl} 所有可用资产映射
        model: 模型名称
        resolution: 分辨率
        ratio: 画面比例
        duration: 指定时长（None 则自动计算）
        generate_audio: 是否生成音频
        first_frame_url: 首帧图片URL
        last_frame_url: 尾帧图片URL

    Returns:
        SeedanceVideoTaskBody 请求体 dict
    """
    # 1. 清理叙事字段
    script_data = sanitize_narrative_fields(dict(script_data))

    # 2. 收集有序参考图
    ordered_asset_ids = collect_ordered_reference_asset_ids(script_data, all_assets)
    logger.info(f"收集到 {len(ordered_asset_ids)} 张参考图: {ordered_asset_ids}")

    # 3. 编译文本 prompt
    text_prompt = compile_seedance_text_prompt(script_data, ordered_asset_ids)

    # 4. 构建 content 数组
    content: list[dict] = []

    # 文本
    content.append({"type": "text", "text": text_prompt})

    # 参考图
    for asset_id in ordered_asset_ids:
        image_url = all_assets.get(asset_id, "")
        if image_url:
            # 使用 Asset:// URI 格式（火山私域）或直接URL
            if not image_url.startswith("http"):
                image_url = f"Asset://{asset_id}"
            content.append({
                "type": "image_url",
                "image_url": {"url": image_url},
                "role": "reference_image",
            })

    # 首帧
    if first_frame_url:
        content.append({
            "type": "image_url",
            "image_url": {"url": first_frame_url},
            "role": "first_frame",
        })

    # 尾帧
    if last_frame_url:
        content.append({
            "type": "image_url",
            "image_url": {"url": last_frame_url},
            "role": "last_frame",
        })

    # 5. 计算时长
    if duration is None:
        total_seconds = sum_shot_duration_hints(script_data.get("shots", []))
        duration = snap_to_duration_catalog(total_seconds)

    # 6. 组装请求体
    body = {
        "model": model,
        "content": content,
        "resolution": resolution,
        "ratio": ratio,
        "duration": duration,
        "generate_audio": generate_audio,
    }

    logger.info(f"构建Seedance请求体: model={model}, resolution={resolution}, ratio={ratio}, duration={duration}s, "
                f"参考图={len(ordered_asset_ids)}张, 首帧={'有' if first_frame_url else '无'}, 尾帧={'有' if last_frame_url else '无'}")

    return body


def build_single_shot_task(
    text_prompt: str,
    reference_image_urls: Optional[list[str]] = None,
    model: str = "doubao-seedance-2-0-260128",
    resolution: str = "720p",
    ratio: str = "16:9",
    duration: int = 5,
    first_frame_url: Optional[str] = None,
    last_frame_url: Optional[str] = None,
    generate_audio: bool = True,
    reference_video_urls: Optional[list[str]] = None,
    reference_audio_urls: Optional[list[str]] = None,
) -> dict:
    """
    构建单镜头视频生成请求体（不依赖多模态脚本）

    Args:
        text_prompt: 文本提示词
        reference_image_urls: 参考图URL列表
        model: 模型名称
        resolution: 分辨率
        ratio: 画面比例
        duration: 时长
        first_frame_url: 首帧图片URL
        last_frame_url: 尾帧图片URL
        generate_audio: 是否生成音频
        reference_video_urls: 参考视频URL列表（来自视频节点 mention，url 已含 Asset:// 前缀或永久 URL）
        reference_audio_urls: 参考音频URL列表（来自音频节点 mention）

    Returns:
        SeedanceVideoTaskBody 请求体 dict

    Notes:
        Seedance content 数组格式（与 video_generation_service.build_short_video_body 对齐）:
        - 参考图: {"type": "image_url", "role": "reference_image", "image_url": {"url": ...}}
        - 参考视频: {"type": "video_url", "role": "reference_video", "video_url": {"url": ...}}
        - 参考音频: {"type": "audio_url", "role": "reference_audio", "audio_url": {"url": ...}}
        url 是否带 Asset:// 前缀由调用方决定（已同步火山时使用 Asset://{volc_id}）。
    """
    content: list[dict] = [{"type": "text", "text": text_prompt}]

    if reference_image_urls:
        for url in reference_image_urls[:MAX_REFERENCE_IMAGES]:
            content.append({
                "type": "image_url",
                "image_url": {"url": url},
                "role": "reference_image",
            })

    if reference_video_urls:
        for url in reference_video_urls:
            content.append({
                "type": "video_url",
                "video_url": {"url": url},
                "role": "reference_video",
            })

    if reference_audio_urls:
        for url in reference_audio_urls:
            content.append({
                "type": "audio_url",
                "audio_url": {"url": url},
                "role": "reference_audio",
            })

    if first_frame_url:
        content.append({
            "type": "image_url",
            "image_url": {"url": first_frame_url},
            "role": "first_frame",
        })

    if last_frame_url:
        content.append({
            "type": "image_url",
            "image_url": {"url": last_frame_url},
            "role": "last_frame",
        })

    return {
        "model": model,
        "content": content,
        "resolution": resolution,
        "ratio": ratio,
        "duration": duration,
        "generate_audio": generate_audio,
    }


# ============================================================================
# Episode 级别构建函数
# ============================================================================


def resolve_script_for_video_task(
    episode_script_json: dict,
    segment_index: int,
    plain_text: str = None,
) -> dict:
    """从 Episode 完整脚本中提取指定 segment 的脚本数据

    - 处理 v1/v2 格式
    - 如果有 plain_text，尝试合并到脚本数据中

    Args:
        episode_script_json: Episode 的完整脚本 JSON
        segment_index: 目标 segment 索引
        plain_text: 可选的纯文本（用于覆盖/合并）

    Returns:
        单个 segment 的脚本数据 dict（可直接传给 build_seedance_task_from_script）
    """
    schema_version = episode_script_json.get("schemaVersion", 2)

    if schema_version == 1 or "segments" not in episode_script_json:
        # v1 格式：整个脚本就是一个 segment
        script_data = _v1_to_segment_data(episode_script_json)
    else:
        # v2 格式：从 segments 中提取
        segments = episode_script_json.get("segments", [])
        target_seg = None
        for seg in segments:
            if seg.get("segmentIndex") == segment_index:
                target_seg = seg
                break

        if not target_seg:
            if segments:
                target_seg = segments[min(segment_index, len(segments) - 1)]
            else:
                raise ValueError(f"脚本中没有 segment: index={segment_index}")

        script_data = _segment_to_script_data(target_seg, episode_script_json)

    # 如果有 plain_text，合并覆盖
    if plain_text:
        from app.services.script_text_converter import script_text_converter
        parsed = script_text_converter.plain_text_to_script(plain_text)
        if parsed and parsed.get("segments"):
            override_seg = parsed["segments"][0]
            script_data = _merge_segment_data(script_data, override_seg)

    return script_data


def resolve_asset_url(asset_id: str, asset_map: dict, use_volc_asset: bool = False) -> str:
    """将 assetId 解析为 Seedance 可用的 URL

    - use_volc_asset=True → "Asset://{assetId}"（火山私域格式）
    - use_volc_asset=False → asset_map[asset_id]（实际 COS URL）

    Args:
        asset_id: 资产 ID
        asset_map: {assetId: imageUrl} 映射
        use_volc_asset: 是否使用火山私域 Asset:// URI

    Returns:
        可用于 Seedance API 的 URL 字符串
    """
    if use_volc_asset:
        return f"Asset://{asset_id}"

    url = asset_map.get(asset_id, "")
    if url:
        return url

    return f"Asset://{asset_id}"


def build_episode_segment_task(
    episode_script_json: dict,
    segment_index: int,
    asset_map: dict,
    plain_text: str = None,
    model: str = "doubao-seedance-2-0-260128",
    resolution: str = "720p",
    ratio: str = "16:9",
    duration: Optional[int] = None,
    generate_audio: bool = True,
    first_frame_url: Optional[str] = None,
    last_frame_url: Optional[str] = None,
    use_volc_asset: bool = False,
) -> dict:
    """Episode 级别的视频任务构建入口

    - resolve_script_for_video_task() 提取 segment 数据
    - 调用 build_seedance_task_from_script() 构建请求

    Args:
        episode_script_json: Episode 的完整脚本 JSON
        segment_index: 目标 segment 索引
        asset_map: {assetId: imageUrl} 资产映射
        plain_text: 可选的纯文本覆盖
        model: 模型名称
        resolution: 分辨率
        ratio: 画面比例
        duration: 指定时长
        generate_audio: 是否生成音频
        first_frame_url: 首帧图片URL
        last_frame_url: 尾帧图片URL
        use_volc_asset: 是否使用 Asset:// URI 格式

    Returns:
        SeedanceVideoTaskBody 请求体 dict
    """
    script_data = resolve_script_for_video_task(
        episode_script_json, segment_index, plain_text
    )

    resolved_asset_map = asset_map
    if use_volc_asset:
        resolved_asset_map = {
            aid: resolve_asset_url(aid, asset_map, use_volc_asset=True)
            for aid in asset_map
        }

    return build_seedance_task_from_script(
        script_data=script_data,
        all_assets=resolved_asset_map,
        model=model,
        resolution=resolution,
        ratio=ratio,
        duration=duration,
        generate_audio=generate_audio,
        first_frame_url=first_frame_url,
        last_frame_url=last_frame_url,
    )


def _v1_to_segment_data(script: dict) -> dict:
    """将 v1 格式脚本转换为 segment 脚本数据"""
    return {
        "segment_intent": script.get("segmentIntent", ""),
        "scene_summary": script.get("sceneSummary", ""),
        "shot_transition": script.get("shotTransition", ""),
        "shots": script.get("shots", []),
        "style_and_keywords": script.get("styleAndKeywords", ""),
    }


def _segment_to_script_data(segment: dict, full_script: dict) -> dict:
    """将 v2 segment 转换为脚本数据（继承全局 styleAndKeywords）"""
    return {
        "segment_intent": segment.get("segmentIntent", ""),
        "scene_summary": segment.get("sceneSummary", ""),
        "shot_transition": segment.get("shotTransition", ""),
        "shots": segment.get("shots", []),
        "style_and_keywords": full_script.get("styleAndKeywords", ""),
    }


def _merge_segment_data(base: dict, override: dict) -> dict:
    """合并两个 segment 数据（override 覆盖 base 中非空字段）"""
    merged = dict(base)
    for key in ("segment_intent", "scene_summary", "shot_transition", "style_and_keywords"):
        val = override.get(key)
        if val:
            merged[key] = val
    shots = override.get("shots")
    if shots:
        merged["shots"] = shots
    return merged
