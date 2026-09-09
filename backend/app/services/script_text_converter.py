"""
脚本双向转换服务

实现 v2 脚本 JSON ↔ 可编辑纯文本 的双向转换
"""
import re
import unicodedata
from typing import Optional

from loguru import logger


def _normalize_code_point(unit: str) -> str:
    """单码位规范化：NFKC + 全角 ASCII/空格折叠"""
    u = unicodedata.normalize('NFKC', unit)
    result = []
    for ch in u:
        code = ord(ch)
        if code == 0x3000:  # 全角空格
            result.append(' ')
        elif 0xFF01 <= code <= 0xFF5E:  # 全角 ASCII
            result.append(chr(code - 0xFEE0))
        else:
            result.append(ch)
    return ''.join(result)


def _normalize_needle(needle: str) -> str:
    """规范化搜索词"""
    result = []
    i = 0
    while i < len(needle):
        cp = ord(needle[i])
        if cp >= 0x10000:  # surrogate pair
            unit = needle[i:i+2]
            i += 2
        else:
            unit = needle[i]
            i += 1
        result.append(_normalize_code_point(unit))
    return ''.join(result)


def _find_asset_name_in_text(haystack: str, name: str) -> bool:
    """在文本中查找资产名称

    两级匹配：
    1. 字面量匹配（原始名称）
    2. Unicode 规范化匹配（NFKC + 全角/半角折叠）
    """
    if not name:
        return False

    # 第一级：字面量匹配
    if name in haystack:
        return True
    trimmed = name.strip()
    if trimmed != name and trimmed in haystack:
        return True

    # 短名称（trim 后长度 < 2）仅做字面量匹配，避免误匹配
    if len(trimmed) < 2:
        return False

    # 第二级：规范化匹配
    norm_needle = _normalize_needle(trimmed)
    if not norm_needle:
        return False

    # 构建规范化后的 haystack
    norm_hay = _normalize_haystack(haystack)
    return norm_needle in norm_hay


def _normalize_haystack(haystack: str) -> str:
    """规范化 haystack（简化版只返回规范化文本）"""
    result = []
    i = 0
    while i < len(haystack):
        cp = ord(haystack[i])
        if cp >= 0x10000:
            unit = haystack[i:i+2]
            i += 2
        else:
            unit = haystack[i]
            i += 1
        result.append(_normalize_code_point(unit))
    return ''.join(result)


class ScriptTextConverter:
    """脚本 JSON ↔ 纯文本 双向转换器"""

    def script_to_plain_text(self, script: dict, asset_map: dict = None) -> str:
        """将 v2 脚本 JSON 转换为可编辑的纯文本格式

        Args:
            script: 脚本 JSON
            asset_map: {assetId: {name, kind}} 资产映射
        """
        segments = script.get("segments", [])
        if not segments:
            return ""

        parts: list[str] = []

        for seg in segments:
            seg_idx = seg.get("segmentIndex", len(parts) + 1)
            # parts.append(f"=== 片段 {seg_idx} ===")

            style = seg.get("styleAndKeywords", "") or script.get("styleAndKeywords", "")
            if style:
                parts.append(f"画面风格和类型: {style}")

            intent = seg.get("segmentIntent", "")
            if intent:
                intent = self._replace_asset_names_with_chips(intent, asset_map)
                parts.append(intent)

            scene = seg.get("sceneSummary", "")
            if scene:
                parts.append("场景:")
                parts.append(scene)

            transition = seg.get("shotTransition", "")
            if transition:
                parts.append("分镜过渡:")
                parts.append(transition)

            cumulative = 0.0
            for shot in seg.get("shots", []):
                shot_idx = shot.get("index", 1)
                sec = max(0.5, min(15, float(shot.get("durationHintSec", 3))))
                start = cumulative
                end = cumulative + sec
                body = self._build_shot_body(shot, asset_map)
                parts.append(f"镜头 {shot_idx}（{start:.0f} 至 {end:.0f} 秒）：{body}")
                cumulative = end

        return "\n".join(parts)

    def _replace_asset_names_with_chips(self, text: str, asset_map: dict) -> str:
        """将文本中的资产名称替换为 [[name|TYPE|id]] 标记，便于编辑器渲染 chip"""
        if not text or not asset_map:
            return text or ""

        kind_to_tag = {"character": "ROLE", "scene": "LOC", "prop": "PROP"}
        items = []
        for asset_id, info in asset_map.items():
            if not isinstance(info, dict):
                continue
            name = info.get("name", "")
            if not name:
                continue
            type_tag = kind_to_tag.get(info.get("kind", ""), "ROLE")
            items.append((name, asset_id, type_tag))

        # 按名称长度降序，避免短名部分匹配
        items.sort(key=lambda x: len(x[0]), reverse=True)

        s = text
        for name, asset_id, type_tag in items:
            tag = f"[[{name}|{type_tag}|{asset_id}]]"
            parts = re.split(r'(\[\[[^\]]+\]\])', s)
            for i, part in enumerate(parts):
                if not part.startswith('[['):
                    parts[i] = part.replace(name, tag)
            s = ''.join(parts)

        return s

    def _build_shot_body(self, shot: dict, asset_map: dict = None) -> str:
        """构建单镜头正文，所有资产名称在文本中内联替换为 [[name|TYPE|id]]"""
        s = ""

        time_of_day = shot.get("timeOfDay", "")
        if time_of_day:
            s += f"时间：{time_of_day}，"

        scene_id = shot.get("sceneAssetId", "")
        if scene_id:
            name = self._asset_name(asset_map, scene_id, "scene")
            s += f"场景图片：[[{name}|LOC|{scene_id}]]，"

        camera = shot.get("camera", "")
        framing = ""
        if camera:
            m = re.match(r'^([^，。、]+)', camera)
            if m:
                framing = m.group(1).strip()

        if framing:
            s += f"【{framing}】"

        action = (shot.get("action", "") or "").strip()
        if action:
            s += f"{action}"

        dialogue = shot.get("dialogue", "")
        if dialogue:
            s += f"说：{dialogue}"

        sound = shot.get("soundEffect", "")
        if sound:
            s += f"；音效：{sound}"

        voice_desc = (shot.get("voice", {}) or {}).get("description", "")
        if voice_desc:
            s += f"音色：{voice_desc}"

        # 内联替换：将文本中出现的所有资产名称替换为 [[name|TYPE|id]]
        # 收集所有需要替换的资产（角色 + 场景 + 道具）
        all_items = []  # [(name, assetId, type_tag)]

        for cid in shot.get("characterAssetIds", []):
            name = self._asset_name(asset_map, cid, "character")
            if name:
                all_items.append((name, cid, "ROLE"))

        if scene_id:
            name = self._asset_name(asset_map, scene_id, "scene")
            if name:
                all_items.append((name, scene_id, "LOC"))

        for pid in shot.get("propAssetIds", []):
            name = self._asset_name(asset_map, pid, "prop")
            if name:
                all_items.append((name, pid, "PROP"))

        # 按名称长度降序，避免短名部分匹配
        all_items.sort(key=lambda x: len(x[0]), reverse=True)

        for name, asset_id, type_tag in all_items:
            tag = f"[[{name}|{type_tag}|{asset_id}]]"
            parts = re.split(r'(\[\[[^\]]+\]\])', s)
            for i, part in enumerate(parts):
                if not part.startswith('[['):
                    parts[i] = part.replace(name, tag)
            s = ''.join(parts)

        return s

    @staticmethod
    def _asset_name(asset_map: dict, asset_id: str, default_kind: str) -> str:
        if asset_map and asset_id in asset_map:
            info = asset_map[asset_id]
            return info.get("name", asset_id[:8])
        return asset_id[:8]

    def plain_text_to_script(self, text: str) -> Optional[dict]:
        """将纯文本解析回 v2 脚本 JSON"""
        if not text or not text.strip():
            return None

        script = {
            "schemaVersion": 2,
            "styleAndKeywords": "",
            "sceneSummary": "",
            "segments": [],
        }

        current_segment = None
        current_field = None

        for line in text.split("\n"):
            line = line.rstrip()

            if re.match(r'^===\s*片段\s+\d+\s*===$', line.strip()):
                if current_segment is not None:
                    script["segments"].append(current_segment)
                match = re.search(r"片段\s+(\d+)", line)
                seg_idx = int(match.group(1)) if match else len(script["segments"]) + 1
                current_segment = {
                    "segmentIndex": seg_idx,
                    "segmentIntent": "",
                    "sceneSummary": "",
                    "shotTransition": "",
                    "shots": [],
                }
                current_field = None
                continue

            # 新格式：无 === 分隔符时，自动创建 segment
            if current_segment is None:
                is_seg_start = (
                    re.match(r'^画面风格和类型:\s*', line) or
                    re.match(r'^场景:\s*', line) or
                    re.match(r'^分镜过渡:\s*', line) or
                    re.match(r'^分镜\d+\s*@', line) or
                    re.match(r'^镜头\s*\d+\s*[:（]', line)
                )
                if is_seg_start:
                    current_segment = {
                        "segmentIndex": len(script["segments"]) + 1,
                        "segmentIntent": "",
                        "sceneSummary": "",
                        "shotTransition": "",
                        "shots": [],
                    }
                    current_field = None

            # 新格式：无 === 分隔符时，检测片段边界
            # 边界判定：当前片段已经走过「场景→分镜过渡」一个完整循环，或已有 shots
            # 此时又遇到「画面风格和类型:」或「场景:」开头的片段级字段，视为新片段
            seg_passed_full_cycle = (
                current_segment
                and current_segment.get("sceneSummary")
                and ("shotTransition" in current_segment or current_segment.get("shots"))
            )
            if current_segment and (
                current_segment.get("shots") or seg_passed_full_cycle
            ):
                is_boundary = (
                    re.match(r'^画面风格和类型:\s*', line) or
                    re.match(r'^场景:\s*$', line)
                )
                if is_boundary:
                    script["segments"].append(current_segment)
                    current_segment = {
                        "segmentIndex": len(script["segments"]) + 1,
                        "segmentIntent": "",
                        "sceneSummary": "",
                        "shotTransition": "",
                        "shots": [],
                    }
                    current_field = None

            if current_segment is not None:
                style_match = re.match(r'^画面风格和类型:\s*(.*)', line)
                if style_match:
                    val = style_match.group(1).strip()
                    if val:
                        current_segment["styleAndKeywords"] = val
                        if not script["styleAndKeywords"]:
                            script["styleAndKeywords"] = val
                    current_field = None
                    continue

                scene_inline = re.match(r'^场景:\s*(.+)$', line)
                if re.match(r'^场景:\s*$', line):
                    current_field = "scene"
                    continue
                elif scene_inline:
                    current_segment["sceneSummary"] = scene_inline.group(1).strip()
                    current_field = None
                    continue

                trans_inline = re.match(r'^分镜过渡:\s*(.+)$', line)
                if re.match(r'^分镜过渡:\s*$', line):
                    current_field = "transition"
                    continue
                elif trans_inline:
                    current_segment["shotTransition"] = trans_inline.group(1).strip()
                    current_field = None
                    continue

                # 新格式：镜头 N（start 至 end 秒）：body
                shot_match = re.match(r'^镜头\s*(\d+)\s*（\s*([\d.]+)\s*至\s*([\d.]+)\s*秒\s*）\s*：\s*(.*)$', line)
                if shot_match:
                    duration = float(shot_match.group(3)) - float(shot_match.group(2))
                    shot = self._parse_shot_body(
                        int(shot_match.group(1)),
                        duration,
                        shot_match.group(4).strip(),
                    )
                    if shot:
                        current_segment["shots"].append(shot)
                    current_field = None
                    continue

                # 旧格式：分镜N @ Ns:body（向后兼容）
                shot_match = re.match(r'^分镜(\d+)\s*@\s*([\d.]+)s\s*:\s*([\s\S]*)$', line)
                if shot_match:
                    shot = self._parse_shot_body(
                        int(shot_match.group(1)),
                        float(shot_match.group(2)),
                        shot_match.group(3).strip(),
                    )
                    if shot:
                        current_segment["shots"].append(shot)
                    current_field = None
                    continue

                if current_field == "scene":
                    if line:
                        current_segment["sceneSummary"] = (current_segment["sceneSummary"] + "\n" + line).strip()
                    continue
                elif current_field == "transition":
                    if line:
                        current_segment["shotTransition"] = (current_segment["shotTransition"] + "\n" + line).strip()
                    continue

                if line and not current_segment["shots"]:
                    cleaned_line = re.sub(
                        r'\[\[([^\]|]+)\|(?:ROLE|LOC|SCENE|PROP)\|[^\]]+\]\]',
                        r'\1', line
                    )
                    if current_segment["segmentIntent"]:
                        current_segment["segmentIntent"] += "\n" + cleaned_line
                    else:
                        current_segment["segmentIntent"] = cleaned_line
            else:
                style_match = re.match(r'^画面风格和类型:\s*(.*)', line)
                if style_match:
                    val = style_match.group(1).strip()
                    if val:
                        script["styleAndKeywords"] = val

            current_field = None

        if current_segment is not None:
            script["segments"].append(current_segment)

        if not script["segments"]:
            return None

        if not script["sceneSummary"] and script["segments"]:
            script["sceneSummary"] = script["segments"][0].get("sceneSummary", "")

        return script

    def _parse_shot_body(self, index: int, duration: float, tail: str) -> Optional[dict]:
        """解析镜头正文"""
        if not tail:
            return {"index": index, "durationHintSec": duration, "camera": ""}

        u = tail.strip()
        shot = {"index": index, "durationHintSec": duration}

        time_match = re.match(r'^时间：([^，\n]+)，', u)
        if time_match:
            shot["timeOfDay"] = time_match.group(1).strip()
            u = re.sub(r'^时间：[^，\n]+，\s*', '', u)

        scene_match = re.match(r'^场景图片：\[\[([^\]|]*)\|LOC\|([^\]]+)\]\]，?', u)
        if scene_match:
            shot["sceneAssetId"] = scene_match.group(2).strip()
            u = re.sub(r'^场景图片：\[\[[^\]|]*\|LOC\|[^\]]+\]\]，?\s*', '', u)

        # 处理【景别】前缀 → 还原为 镜头：景别。
        bracket_match = re.match(r'^【([^】]+)】\s*', u)
        if bracket_match:
            framing = bracket_match.group(1).strip()
            u = f"镜头：{framing}。" + u[bracket_match.end():]

        sound_match = re.search(r'；音效：([^；\n]+)', u)
        sound = None
        if sound_match:
            sound = sound_match.group(1).strip()
            u = u.replace(sound_match.group(0), '', 1)

        say_match = re.search(r'说：「([^」]*)」', u)  # 旧格式兼容
        if not say_match:
            say_match = re.search(r'说：(.+?)(?=；音效：|音色：|$)', u)  # 新格式
        dialogue = None
        mid = u
        rest = ""
        if say_match:
            dialogue = say_match.group(1).strip()
            mid = u[:say_match.start()]
            rest = u[say_match.end():]
        else:
            voice_match = re.search(r'音色：([\s\S]+)$', u)
            if voice_match:
                mid = u[:voice_match.start()]
                rest = voice_match.group(0)

        voice = None
        action_from_voice = None
        vm = re.match(r'^音色：([\s\S]+)$', rest.strip()) if rest else None
        if vm:
            full = vm.group(1).strip()
            dot_pos = full.find('。')
            if dot_pos > 0:
                voice = {"description": full[:dot_pos].strip()}
                action_from_voice = full[dot_pos + 1:].strip()
            else:
                voice = {"description": full}
        if voice:
            shot["voice"] = voice

        role_ids = []
        prop_ids = []
        role_pattern = re.compile(r'\[\[([^\]|]*)\|ROLE\|([^\]]+)\]\]')
        loc_pattern = re.compile(r'\[\[([^\]|]*)\|LOC\|([^\]]+)\]\]')
        prop_pattern = re.compile(r'\[\[([^\]|]*)\|PROP\|([^\]]+)\]\]')
        all_asset_pattern = re.compile(r'\[\[([^\]|]*)\|(?:ROLE|LOC|PROP)\|[^\]]+\]\]')

        # 从 mid（镜头+动作）中提取角色 ID
        role_matches = list(role_pattern.finditer(mid))
        role_ids = [m.group(2).strip() for m in role_matches]
        mid_clean = all_asset_pattern.sub('', mid)

        # 从 dialogue 中提取资产 ID 并剥离标签
        if dialogue:
            dialogue_roles = role_pattern.findall(dialogue)
            role_ids.extend(r[1].strip() for r in dialogue_roles)
            dialogue = all_asset_pattern.sub(r'\1', dialogue)

        # 从 soundEffect 中提取资产 ID 并剥离标签
        if sound:
            sound_roles = role_pattern.findall(sound)
            role_ids.extend(r[1].strip() for r in sound_roles)
            sound = all_asset_pattern.sub(r'\1', sound)

        cam_action = re.match(r'^镜头：([\s\S]*?)(?:动作：|。)([\s\S]*)$', mid_clean)
        camera = ""
        action = None
        if cam_action:
            camera = cam_action.group(1).strip()
            action = cam_action.group(2).strip()
        else:
            cam_only = re.match(r'^镜头：([\s\S]*)$', mid_clean)
            camera = cam_only.group(1).strip() if cam_only else mid_clean.strip()

        if not action and not voice and action_from_voice is None:
            action_rest = re.match(r'^(?:。)?([\s\S]+)$', rest.strip()) if rest else None
            if action_rest:
                action = action_rest.group(1).strip()

        if action_from_voice:
            action = action_from_voice

        shot["camera"] = camera or ""
        # 从 action 中提取资产 ID 并剥离标签
        if action:
            action_roles = role_pattern.findall(action)
            role_ids.extend(r[1].strip() for r in action_roles)
            action_props = prop_pattern.findall(action)
            prop_ids.extend(r[1].strip() for r in action_props)
            action = all_asset_pattern.sub(r'\1', action)
        if role_ids:
            shot["characterAssetIds"] = list(dict.fromkeys(role_ids))
        if prop_ids:
            shot["propAssetIds"] = list(dict.fromkeys(prop_ids))
        if dialogue:
            shot["dialogue"] = dialogue
        if sound:
            shot["soundEffect"] = sound
        if action:
            shot["action"] = action

        return shot

    def update_script_segment(self, script: dict, segment_index: int, plain_text: str) -> dict:
        """更新脚本中指定 segment 的内容"""
        parsed = self.plain_text_to_script(plain_text)
        if not parsed or not parsed.get("segments"):
            return script

        new_seg = parsed["segments"][0]
        for i, seg in enumerate(script.get("segments", [])):
            if seg.get("segmentIndex") == segment_index:
                script["segments"][i] = new_seg
                new_seg["segmentIndex"] = segment_index
                break

        return script

    def enrich_cross_segment_consistency(
        self, script: dict, asset_descriptors: list[dict]
    ) -> dict:
        """跨 segment 资产引用一致性检查

        三类资产独立处理：
        - character → characterAssetIds (列表，可多个)
        - scene → sceneAssetId (单个)
        - prop → propAssetIds (列表，可多个)
        """
        # 按类型分类建立映射（name + aliases 全部参与匹配）
        char_map: dict[str, str] = {}    # name/alias → assetId
        scene_map: dict[str, str] = {}    # name/alias → assetId
        prop_map: dict[str, str] = {}     # name/alias → assetId

        for desc in asset_descriptors:
            name = desc.get("name", "")
            asset_id = desc.get("assetId", "")
            kind = desc.get("kind", "")
            if not name or not asset_id:
                continue
            target = {"character": char_map, "scene": scene_map, "prop": prop_map}.get(kind)
            if target is None:
                continue
            target[name] = asset_id
            for alias in desc.get("aliases", []):
                if alias and alias not in target:
                    target[alias] = asset_id

        if not char_map and not scene_map and not prop_map:
            return script

        # 按名称长度降序排列（防止短名贪婪匹配）
        sorted_char_items = sorted(char_map.items(), key=lambda x: len(x[0]), reverse=True)
        sorted_scene_items = sorted(scene_map.items(), key=lambda x: len(x[0]), reverse=True)
        sorted_prop_items = sorted(prop_map.items(), key=lambda x: len(x[0]), reverse=True)

        # 第一轮: 各 segment 独立推断
        for seg in script.get("segments", []):
            self._enrich_segment_shots(seg, sorted_char_items, sorted_scene_items, sorted_prop_items)

        # 第二轮: 收集已知引用，建立跨 segment 角色映射（只用主名称，不用 alias）
        char_name_map = {}
        for desc in asset_descriptors:
            if desc.get("kind") == "character" and desc.get("name") and desc.get("assetId"):
                char_name_map[desc["assetId"]] = desc["name"]

        role_asset_by_name: dict[str, str] = {}
        for seg in script.get("segments", []):
            for shot in seg.get("shots", []):
                for cid in shot.get("characterAssetIds", []):
                    cid = cid.strip()
                    if cid and cid in char_name_map:
                        name = char_name_map[cid]
                        if name not in role_asset_by_name:
                            role_asset_by_name[name] = cid

        # 同时将 alias 也加入传播列表
        for desc in asset_descriptors:
            if desc.get("kind") == "character" and desc.get("assetId"):
                asset_id = desc["assetId"]
                if desc.get("name") and desc["name"] not in role_asset_by_name:
                    role_asset_by_name[desc["name"]] = asset_id
                for alias in desc.get("aliases", []):
                    if alias and alias not in role_asset_by_name:
                        role_asset_by_name[alias] = asset_id

        # 第三轮: 跨 segment 角色一致性传播（仅用 shot 级别文本）
        sorted_role_items = sorted(role_asset_by_name.items(), key=lambda x: len(x[0]), reverse=True)

        for seg in script.get("segments", []):
            for shot in seg.get("shots", []):
                text_fields = [
                    shot.get("camera", ""),
                    shot.get("dialogue", ""),
                    shot.get("action", ""),
                ]
                if shot.get("voice"):
                    text_fields.append(shot["voice"].get("description", ""))
                blob = "\n".join(filter(None, text_fields))

                existing_ids = set(shot.get("characterAssetIds", []))

                for name, volc_id in sorted_role_items:
                    if volc_id not in existing_ids and _find_asset_name_in_text(blob, name):
                        shot.setdefault("characterAssetIds", []).append(volc_id)
                        existing_ids.add(volc_id)

        # 第四轮: 文本→结构化字段交叉验证
        self._cross_validate_text_vs_ids(script, sorted_char_items)

        return script

    def _enrich_segment_shots(self, seg: dict, sorted_char_items: list,
                               sorted_scene_items: list, sorted_prop_items: list):
        """单个 segment 的资产推断

        Args:
            sorted_char_items: [(name, assetId)] 角色，按名称长度降序
            sorted_scene_items: [(name, assetId)] 场景，按名称长度降序
            sorted_prop_items: [(name, assetId)] 道具，按名称长度降序
        """
        seg_level_text = "\n".join(filter(None, [
            seg.get("segmentIntent", ""),
            seg.get("sceneSummary", ""),
        ]))

        for shot in seg.get("shots", []):
            text_fields = [
                shot.get("timeOfDay", ""),
                shot.get("camera", ""),
                shot.get("dialogue", ""),
                shot.get("action", ""),
            ]
            if shot.get("voice"):
                text_fields.append(shot["voice"].get("description", ""))
            blob = "\n".join(filter(None, text_fields))

            # 角色推断
            existing_ids = set(shot.get("characterAssetIds", []))
            for name, asset_id in sorted_char_items:
                if asset_id not in existing_ids and _find_asset_name_in_text(blob, name):
                    shot.setdefault("characterAssetIds", []).append(asset_id)
                    existing_ids.add(asset_id)

            # 场景推断：先 shot 级别，再 segment 级别
            if not shot.get("sceneAssetId"):
                for name, asset_id in sorted_scene_items:
                    if _find_asset_name_in_text(blob, name):
                        shot["sceneAssetId"] = asset_id
                        break
                if not shot.get("sceneAssetId"):
                    for name, asset_id in sorted_scene_items:
                        if _find_asset_name_in_text(seg_level_text, name):
                            shot["sceneAssetId"] = asset_id
                            break

            # 道具推断
            existing_prop_ids = set(shot.get("propAssetIds", []))
            for name, asset_id in sorted_prop_items:
                if asset_id not in existing_prop_ids and _find_asset_name_in_text(blob, name):
                    shot.setdefault("propAssetIds", []).append(asset_id)
                    existing_prop_ids.add(asset_id)

    def _cross_validate_text_vs_ids(self, script: dict, sorted_char_items: list):
        """文本→结构化字段交叉验证"""
        for seg in script.get("segments", []):
            for shot in seg.get("shots", []):
                text_fields = [
                    shot.get("camera", ""),
                    shot.get("dialogue", ""),
                    shot.get("action", ""),
                ]
                blob = "\n".join(filter(None, text_fields))

                existing_ids = set(shot.get("characterAssetIds", []))
                for name, asset_id in sorted_char_items:
                    if asset_id not in existing_ids and _find_asset_name_in_text(blob, name):
                        shot.setdefault("characterAssetIds", []).append(asset_id)
                        existing_ids.add(asset_id)

    def segment_to_plain_text(self, script: dict, segment_index: int) -> str:
        """提取脚本中单个 segment 的纯文本"""
        for seg in script.get("segments", []):
            if seg.get("segmentIndex") == segment_index:
                single = {
                    "schemaVersion": 2,
                    "styleAndKeywords": script.get("styleAndKeywords", ""),
                    "sceneSummary": script.get("sceneSummary", ""),
                    "segments": [seg],
                }
                return self.script_to_plain_text(single)
        return ""


script_text_converter = ScriptTextConverter()
