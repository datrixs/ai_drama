"""画布 prompt token 解析与上游节点引用聚合

将前端发来的 prompt_tokens（文本片段 + mention 引用）解析为：
- 给 LLM 的纯文本 prompt（IMAGE mention 跳过、TEXT mention 内联展开 + sanitize）
- 给视频生成的 image 引用（按 mention.role 分流到 first_frame / last_frame / reference）

参考 AICON `services/canvas.py` 的 `_build_prompt_text` / `_collect_reference_image_urls` /
`_sanitize_reference_text` / `_collect_reference_image_object_keys`，对齐 pipixia-drama 的
ORM（CanvasItem）和 Seedance 字段（first_frame_url/last_frame_url/reference_image_urls）。
"""
from __future__ import annotations

import re
from typing import Any, Iterable

from sqlalchemy.orm import Session

from app.crud.user_crud import user_crud
from app.enums.canvas import CanvasItemType
from app.enums.user import UserRegion
from app.models.canvas import CanvasItem
from app.utils.tencent_cos_utils import cos_client


# ── 常量 ────────────────────────────────────────────────

REFERENCE_TEXT_LIMIT = 1500
VALID_IMAGE_ROLES = {"first_frame", "last_frame", "reference"}

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_PLACEHOLDER_RE = re.compile(r"^\s*(<br\s*/?>|</?p>|\s)+\s*$", re.IGNORECASE)


# ── 工具函数 ────────────────────────────────────────────

def sanitize_reference_text(text: str | None, limit: int = REFERENCE_TEXT_LIMIT) -> str:
    """把 HTML/富文本正文转纯文本，压缩空白，超长截断"""
    if not text:
        return ""
    # 去 HTML 标签
    plain = _TAG_RE.sub("", text)
    # html unescape 不做（pipixia 正文存的就是用户输入 HTML，不预期 entity）
    # 压缩连续空白
    plain = _WS_RE.sub(" ", plain).strip()
    if len(plain) > limit:
        plain = plain[:limit].rstrip() + "..."
    return plain


def _node_body_text(item: CanvasItem) -> str:
    """从 canvas_item.content_json 取节点的"正文"纯文本

    文本节点：取 content_json.body（富文本 HTML）→ sanitize
    图片/视频节点：取 content_json.prompt 或 last_output_json 的描述（如有），否则空
    """
    if not item or not item.content_json:
        return ""
    cj = item.content_json
    body = cj.get("body")
    if body:
        return sanitize_reference_text(body)
    prompt = cj.get("prompt")
    if prompt:
        return sanitize_reference_text(prompt)
    return ""


def _node_media_url(
    db: Session,
    item: CanvasItem,
    user_id: str | None,
    prefer_asset_protocol: bool = True,
) -> str:
    """从 canvas_item 取媒体 URL（图片/视频/音频节点通用）

    优先按用户区域返回私域资产引用 `Asset://{volc_asset_id|byteplus_asset_id}`，
    便于火山引擎/BytePlus 内部走资产通道（无需对外签名、不受 COS TTL 限制）；
    若对应字段为空（资产库同步失败或本就未同步），回退到存储的永久 URL。

    prefer_asset_protocol=False 时跳过 Asset:// 分支，直接返回存储的 HTTP(S) URL，
    用于图片生成模型（gpt-image-2 / Gemini / litellm）等只接受公开 HTTP URL 的场景。
    """
    if not item:
        return ""

    if prefer_asset_protocol:
        region = user_crud.get_region(user_id=user_id, db=db) if user_id else UserRegion.DOMESTIC
        asset_id = None
        if region == UserRegion.OVERSEAS:
            asset_id = item.byteplus_asset_id
        else:
            asset_id = item.volc_asset_id
        if asset_id:
            return f"Asset://{asset_id}"

    out = item.last_output_json or {}
    url = out.get("url") or out.get("image_url") or out.get("video_url") or out.get("audio_url")
    if url:
        return str(url)
    cj = item.content_json or {}
    return str(
        cj.get("url")
        or cj.get("image_url")
        or cj.get("video_url")
        or cj.get("audio_url")
        or ""
    )


# 旧名保留为 alias，避免破坏现有调用
_node_image_url = _node_media_url


def _resolve_upstream_item(db: Session, node_id: str, current_item_id: str | None) -> CanvasItem | None:
    """根据 mention.node_id 查 canvas_item，校验同画布且不是自己"""
    if not node_id:
        return None
    item = db.get(CanvasItem, node_id)
    if not item or item.is_deleted:
        return None
    if current_item_id and item.id == current_item_id:
        return None
    return item


def _expand_group_to_effective_tokens(
    db: Session,
    group_item: CanvasItem,
    role: str | None,
) -> list[dict[str, Any]]:
    """把 group mention 展开为子节点的伪 mention token 列表（image/video/audio）

    - 仅取 image / video / audio 子节点（其他类型跳过）
    - 按 create_time 升序保持稳定顺序
    - role 仅对 image 子节点有效（group→video 默认 role=reference）
    """
    children = (
        db.query(CanvasItem)
        .filter(
            CanvasItem.parent_id == group_item.id,
            CanvasItem.is_deleted == False,
            CanvasItem.item_type.in_([
                CanvasItemType.IMAGE.value,
                CanvasItemType.VIDEO.value,
                CanvasItemType.AUDIO.value,
            ]),
        )
        .order_by(CanvasItem.create_time.asc())
        .all()
    )
    out: list[dict[str, Any]] = []
    for c in children:
        out.append({
            "type": "mention",
            "node_id": str(c.id),
            "node_type": (c.item_type or "").lower(),
            "role": role if (c.item_type or "").lower() == "image" else None,
            "node_title": c.title or "",
            "_from_group": str(group_item.id),
        })
    return out


# ── 核心解析 ────────────────────────────────────────────

def build_prompt_for_llm(
    db: Session,
    prompt_tokens: Iterable[dict[str, Any]] | None,
    current_item_id: str | None = None,
) -> str:
    """把 prompt_tokens 拼成发给 LLM 的纯文本

    - text token：直接拼接 value
    - mention token：
        - node_type=text：取上游节点正文，前置"参考："前缀，内联展开
        - node_type=image：跳过（图片不进 LLM prompt，靠 collect_media_refs_by_role 走 image 通道）
        - node_type=video/audio：内联一行轻量语义提示「参考视频/参考音频：{节点标题}」，
          真实字节走 collect_media_refs_by_role 的 video/audio 通道

    若 prompt_tokens 为空或全空，返回空字符串（调用方负责兜底）。
    """
    if not prompt_tokens:
        return ""

    parts: list[str] = []
    inline_refs: list[str] = []

    for tok in prompt_tokens:
        if not isinstance(tok, dict):
            continue
        ttype = str(tok.get("type") or "").strip()
        if ttype == "text":
            value = tok.get("value")
            if value:
                parts.append(str(value))
        elif ttype == "mention":
            node_id = tok.get("node_id") or tok.get("nodeId")
            node_type = str(tok.get("node_type") or tok.get("nodeType") or "").strip()
            upstream = _resolve_upstream_item(db, str(node_id) if node_id else "", current_item_id)
            if not upstream:
                continue
            if node_type == "text":
                ref = _node_body_text(upstream)
                if ref:
                    inline_refs.append(ref)
            elif node_type == "video":
                title = (upstream.title or "参考视频").strip() or "参考视频"
                inline_refs.append(f"参考视频：{title}")
            elif node_type == "audio":
                title = (upstream.title or "参考音频").strip() or "参考音频"
                inline_refs.append(f"参考音频：{title}")
            # image 类型：跳过，留给 collect_media_refs_by_role 处理

    out = ""
    if parts:
        out = "".join(parts).strip()
    if inline_refs:
        ref_block = "\n\n".join(f"参考：\n{r}" for r in inline_refs)
        out = (out + "\n\n" + ref_block).strip() if out else ref_block
    return out


def collect_media_refs_by_role(
    db: Session,
    prompt_tokens: Iterable[dict[str, Any]] | None,
    current_item_id: str | None = None,
    user_id: str | None = None,
    prefer_asset_protocol: bool = True,
) -> dict[str, Any]:
    """从 prompt_tokens 收集 图片/视频/音频 mention，按 node_type + role 分流

    返回：
        {
          "first_frame_url": str | None,       # 第一个 role=first_frame 的图
          "last_frame_url": str | None,        # 第一个 role=last_frame 的图
          "reference_image_urls": list[str],   # 所有 role=reference + 无 role 的图（按出现顺序去重）
          "reference_video_urls": list[str],   # 所有 video mention（按出现顺序去重）
          "reference_audio_urls": list[str],   # 所有 audio mention（按出现顺序去重）
        }

    user_id 用于按区域解析私域资产 ID（国内 volc_asset_id / 国际 byteplus_asset_id），
    解析失败或未同步时回退到存储的永久 URL。

    视频/音频 mention 不消费 role 字段（Seedance 仅支持 reference 角色）。

    prefer_asset_protocol=False 时返回 HTTP(S) URL（用于只接受公开 URL 的图片生成模型），
    详见 _node_media_url。
    """
    result: dict[str, Any] = {
        "first_frame_url": None,
        "last_frame_url": None,
        "reference_image_urls": [],
        "reference_video_urls": [],
        "reference_audio_urls": [],
    }
    if not prompt_tokens:
        return result

    # 各通道独立去重（同一 url 在不同通道里允许出现，但同通道内去重）
    seen_image: set[str] = set()
    seen_video: set[str] = set()
    seen_audio: set[str] = set()

    # 预处理：把 group mention 展开为子节点的 effective mention，再合并到迭代流
    effective_tokens: list[dict[str, Any]] = []
    for tok in prompt_tokens:
        if not isinstance(tok, dict):
            continue
        if str(tok.get("type") or "").strip() != "mention":
            continue
        node_type = str(tok.get("node_type") or tok.get("nodeType") or "").strip()
        if node_type == "group":
            node_id = tok.get("node_id") or tok.get("nodeId")
            group_item = _resolve_upstream_item(db, str(node_id) if node_id else "", current_item_id)
            if not group_item:
                continue
            role = str(tok.get("role") or "").strip()
            effective_tokens.extend(_expand_group_to_effective_tokens(db, group_item, role))
        else:
            effective_tokens.append(tok)

    for tok in effective_tokens:
        node_type = str(tok.get("node_type") or tok.get("nodeType") or "").strip()
        if node_type not in ("image", "video", "audio"):
            continue
        node_id = tok.get("node_id") or tok.get("nodeId")
        upstream = _resolve_upstream_item(db, str(node_id) if node_id else "", current_item_id)
        if not upstream:
            continue
        url = _node_media_url(db, upstream, user_id, prefer_asset_protocol=prefer_asset_protocol)
        if not url:
            continue

        if node_type == "image":
            if url in seen_image:
                continue
            seen_image.add(url)
            role = str(tok.get("role") or "").strip()
            if role not in VALID_IMAGE_ROLES:
                role = "reference"
            if role == "first_frame" and not result["first_frame_url"]:
                result["first_frame_url"] = url
            elif role == "last_frame" and not result["last_frame_url"]:
                result["last_frame_url"] = url
            else:
                result["reference_image_urls"].append(url)
        elif node_type == "video":
            if url in seen_video:
                continue
            seen_video.add(url)
            result["reference_video_urls"].append(url)
        elif node_type == "audio":
            if url in seen_audio:
                continue
            seen_audio.add(url)
            result["reference_audio_urls"].append(url)

    return result


def collect_image_refs_by_role(
    db: Session,
    prompt_tokens: Iterable[dict[str, Any]] | None,
    current_item_id: str | None = None,
    user_id: str | None = None,
) -> dict[str, Any]:
    """[已弃用，保留兼容] 仅返回图片三通道，等价于 collect_media_refs_by_role 的 image 子集"""
    full = collect_media_refs_by_role(db, prompt_tokens, current_item_id, user_id)
    return {
        "first_frame_url": full["first_frame_url"],
        "last_frame_url": full["last_frame_url"],
        "reference_image_urls": full["reference_image_urls"],
    }


def build_video_prompt_with_labels(
    db: Session,
    prompt_tokens: Iterable[dict[str, Any]] | None,
    current_item_id: str | None = None,
) -> str:
    """构建视频生成的 text prompt：把 mention 替换为 @图片N / @视频N / @音频N 占位符

    与成品页（短视频）规则对齐：第 1 张图 → 「@图片1」，第 1 段视频 → 「@视频1」，
    第 1 段音频 → 「@音频1」。编号按 mention 在 tokens 中的出现顺序独立累计，
    与 collect_media_refs_by_role 的 url 收集顺序一致，便于 Seedance 对齐参考素材。

    与 build_prompt_for_llm 的区别：
    - 图片/视频/音频 mention：替换为占位符（不内联"参考视频：xxx"），由 Seedance 配合
      reference_image_urls / reference_video_urls / reference_audio_urls 数组解析
    - 文本 mention：仍内联展开上游 body（保持 LLM 拿到完整文本语义）

    若 prompt_tokens 为空或全空，返回空字符串（调用方负责兜底）。
    """
    if not prompt_tokens:
        return ""

    parts: list[str] = []
    inline_refs: list[str] = []
    img_idx = vid_idx = aud_idx = 0

    for tok in prompt_tokens:
        if not isinstance(tok, dict):
            continue
        ttype = str(tok.get("type") or "").strip()
        if ttype == "text":
            value = tok.get("value")
            if value:
                parts.append(str(value))
        elif ttype == "mention":
            node_id = tok.get("node_id") or tok.get("nodeId")
            node_type = str(tok.get("node_type") or tok.get("nodeType") or "").strip()
            # group mention：展开为子节点占位符（图片/视频/音频）
            if node_type == "group":
                group_item = _resolve_upstream_item(db, str(node_id) if node_id else "", current_item_id)
                if not group_item:
                    continue
                role = str(tok.get("role") or "").strip()
                for sub in _expand_group_to_effective_tokens(db, group_item, role):
                    sub_type = (sub.get("node_type") or "").strip()
                    if sub_type == "image":
                        img_idx += 1
                        parts.append(f"@图片{img_idx}")
                    elif sub_type == "video":
                        vid_idx += 1
                        parts.append(f"@视频{vid_idx}")
                    elif sub_type == "audio":
                        aud_idx += 1
                        parts.append(f"@音频{aud_idx}")
                continue
            if node_type == "image":
                img_idx += 1
                parts.append(f"@图片{img_idx}")
            elif node_type == "video":
                vid_idx += 1
                parts.append(f"@视频{vid_idx}")
            elif node_type == "audio":
                aud_idx += 1
                parts.append(f"@音频{aud_idx}")
            elif node_type == "text":
                upstream = _resolve_upstream_item(db, str(node_id) if node_id else "", current_item_id)
                if upstream:
                    ref = _node_body_text(upstream)
                    if ref:
                        inline_refs.append(ref)

    out = ""
    if parts:
        out = "".join(parts).strip()
    if inline_refs:
        ref_block = "\n\n".join(f"参考：\n{r}" for r in inline_refs)
        out = (out + "\n\n" + ref_block).strip() if out else ref_block
    return out


def plain_text_from_tokens(
    prompt_tokens: Iterable[dict[str, Any]] | None,
    label_for_mention: callable | None = None,
) -> str:
    """把 tokens 拼成纯文本展示用（每个 mention 用 label_for_mention(token) 替换，默认 [节点名]）

    主要用于前端展示和落库存档（content_json.prompt_plain_text），不发给 LLM。
    """
    if not prompt_tokens:
        return ""

    def _default_label(tok: dict[str, Any]) -> str:
        title = tok.get("node_title") or tok.get("nodeTitle") or tok.get("node_type") or "节点"
        role = str(tok.get("role") or "").strip()
        suffix = f"#{role}" if role and role in VALID_IMAGE_ROLES else ""
        return f"[{title}{suffix}]"

    label_fn = label_for_mention or _default_label
    parts: list[str] = []
    for tok in prompt_tokens:
        if not isinstance(tok, dict):
            continue
        ttype = str(tok.get("type") or "").strip()
        if ttype == "text":
            value = tok.get("value")
            if value:
                parts.append(str(value))
        elif ttype == "mention":
            parts.append(label_fn(tok))
    return "".join(parts).strip()
