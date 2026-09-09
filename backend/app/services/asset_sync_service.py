"""资产批量同步 service（公用）

为资产中心的"批量同步"功能提供：
- 查询当前用户未同步资产（按 region 判断 volc_private_asset_id / byteplus_asset_id 字段）
- 批量执行同步，逐条回调进度

设计原则：查询和执行分离，执行层 run_batch_sync 不绑定作用域，
未来项目资产库的批量同步只需新增 collect_project_unsynced_assets 即可复用执行层。
"""
from dataclasses import dataclass, field
from typing import Callable

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.core.logging import logger
from app.enums.user import UserRegion
from app.models import GlobalCharacter, GlobalCharacterAppearance, GlobalLocation, GlobalLocationImage, GlobalVoice, User
from app.utils.user_volc_sync import sync_user_asset_to_volc


# 同步状态回调签名：(status, item, remote_id, error) -> None
#   status: "success" | "failed"
ProgressCallback = Callable[[str, "AssetItem", str | None, str | None], None]


@dataclass
class AssetItem:
    """待同步资产条目"""
    kind: str           # "character_appearance" | "location_image" | "voice"
    asset_id: str
    model: object       # ORM 实例
    display_name: str
    asset_subtype: str = ""  # location_image 时区分 "scene" / "prop"，用于前端分类计数


@dataclass
class BatchSyncResult:
    """批量同步结果"""
    total: int = 0
    success_count: int = 0
    failed_count: int = 0
    failed_items: list[dict] = field(default_factory=list)


def _resolve_owner_user_id(db: Session, user_id: str) -> str:
    """解析用户的 owner_user_id（主账号id）。

    - 主账号（parent_user_id 为空）：owner = 自己
    - 子账号：owner = parent_user_id
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return user_id
    return user.parent_user_id if user.parent_user_id else str(user.id)


def _user_filter(model_cls, user_id: str, owner_user_id: str):
    """统一的用户数据隔离过滤条件：owner_user_id 命中，或 owner_user_id 为空且 user_id 命中"""
    return or_(
        model_cls.owner_user_id == owner_user_id,
        and_(model_cls.owner_user_id.is_(None), model_cls.user_id == user_id),
    )


def _apply_folder_filter(query, model_cls, folder_id: str | None):
    """把前端的三态 folder_id 映射到 ORM 过滤条件。

    - None：不加过滤（全部资产组）
    - 'null' 字符串哨兵：folder_id IS NULL（未分组）
    - 其他字符串：folder_id == folder_id
    """
    if folder_id is None:
        return query
    if folder_id == "null":
        return query.filter(model_cls.folder_id.is_(None))
    return query.filter(model_cls.folder_id == folder_id)


def collect_user_unsynced_assets(
    db: Session,
    user_id: str,
    region: str,
    folder_id: str | None = None,
) -> list[AssetItem]:
    """收集用户所有未同步资产。

    按 region 选判断字段：
      - DOMESTIC：volc_private_asset_id 为空
      - OVERSEAS：byteplus_asset_id 为空

    folder_id 三态语义见 _apply_folder_filter。
    """
    owner_user_id = _resolve_owner_user_id(db, user_id)
    overseas = region == UserRegion.OVERSEAS
    sync_field = "byteplus_asset_id" if overseas else "volc_private_asset_id"

    items: list[AssetItem] = []

    # 1. 角色形象：join GlobalCharacter 做用户隔离
    char_q = db.query(GlobalCharacterAppearance).join(
        GlobalCharacter,
        GlobalCharacter.id == GlobalCharacterAppearance.character_id,
    ).filter(
        GlobalCharacterAppearance.is_deleted == False,
        GlobalCharacter.is_deleted == False,
        GlobalCharacterAppearance.image_url != None,
        GlobalCharacterAppearance.image_url != "",
        getattr(GlobalCharacterAppearance, sync_field).is_(None),
        _user_filter(GlobalCharacter, user_id, owner_user_id),
    )
    char_q = _apply_folder_filter(char_q, GlobalCharacter, folder_id)
    for app in char_q.all():
        items.append(AssetItem(
            kind="character_appearance",
            asset_id=str(app.id),
            model=app,
            display_name="",
        ))

    # 2. 场景/道具图片：join GlobalLocation 做用户隔离 + asset_kind 区分
    loc_q = db.query(GlobalLocationImage, GlobalLocation.asset_kind).join(
        GlobalLocation,
        GlobalLocation.id == GlobalLocationImage.location_id,
    ).filter(
        GlobalLocationImage.is_deleted == False,
        GlobalLocation.is_deleted == False,
        GlobalLocationImage.image_url != None,
        GlobalLocationImage.image_url != "",
        getattr(GlobalLocationImage, sync_field).is_(None),
        _user_filter(GlobalLocation, user_id, owner_user_id),
    )
    loc_q = _apply_folder_filter(loc_q, GlobalLocation, folder_id)
    for img, asset_kind in loc_q.all():
        items.append(AssetItem(
            kind="location_image",
            asset_id=str(img.id),
            model=img,
            display_name="",
            asset_subtype="prop" if asset_kind == "prop" else "scene",
        ))

    # 3. 音色：直接查 GlobalVoice
    voice_q = db.query(GlobalVoice).filter(
        GlobalVoice.is_deleted == False,
        GlobalVoice.custom_voice_url != None,
        GlobalVoice.custom_voice_url != "",
        getattr(GlobalVoice, sync_field).is_(None),
        _user_filter(GlobalVoice, user_id, owner_user_id),
    )
    voice_q = _apply_folder_filter(voice_q, GlobalVoice, folder_id)
    for v in voice_q.all():
        items.append(AssetItem(
            kind="voice",
            asset_id=str(v.id),
            model=v,
            display_name=v.name or "",
        ))

    return items


def get_user_unsynced_summary(
    db: Session,
    user_id: str,
    region: str,
    folder_id: str | None = None,
) -> dict:
    """返回按类别分组的未同步资产计数，用于弹窗展示。

    返回：{character, scene, prop, voice, total}
    """
    items = collect_user_unsynced_assets(db, user_id, region, folder_id=folder_id)
    character = sum(1 for i in items if i.kind == "character_appearance")
    scene = sum(1 for i in items if i.kind == "location_image" and i.asset_subtype != "prop")
    prop = sum(1 for i in items if i.kind == "location_image" and i.asset_subtype == "prop")
    voice = sum(1 for i in items if i.kind == "voice")
    return {
        "character": character,
        "scene": scene,
        "prop": prop,
        "voice": voice,
        "total": len(items),
    }


def run_batch_sync(
    db: Session,
    user_id: str,
    items: list[AssetItem],
    region: str,
    on_progress: ProgressCallback | None = None,
) -> BatchSyncResult:
    """批量同步资产，逐条调用底层同步工具，单条失败不中断。

    底层 sync_user_asset_to_volc 已实现：
      - region 自动切换字段（volc_private_asset_id / byteplus_asset_id）
      - 幂等检查（已同步直接返回 existing_id）
      - URL 签名转换、asset_type 推断
      - 异常被 catch 后返回 None（除非 raise_on_error=True）
    """
    result = BatchSyncResult(total=len(items))

    for idx, item in enumerate(items, 1):
        try:
            remote_id = sync_user_asset_to_volc(
                db, user_id, item.model,
                display_name=item.display_name,
                raise_on_error=False,
            )
            if remote_id:
                result.success_count += 1
                if on_progress:
                    on_progress("success", item, remote_id, None)
            else:
                result.failed_count += 1
                err = "同步失败：未获取到远程资产ID"
                result.failed_items.append({
                    "asset_id": item.asset_id, "kind": item.kind, "error": err,
                })
                if on_progress:
                    on_progress("failed", item, None, err)
        except Exception as e:
            logger.warning(f"批量同步单条异常: asset_id={item.asset_id}, kind={item.kind}, error={e}")
            result.failed_count += 1
            err = str(e) or "同步异常"
            result.failed_items.append({
                "asset_id": item.asset_id, "kind": item.kind, "error": err,
            })
            if on_progress:
                on_progress("failed", item, None, err)

    return result


# ==================== 项目资产库（ProjectAsset）批量同步 ====================

def collect_project_unsynced_assets(
    db: Session,
    project_id: str,
    region: str,
) -> list[AssetItem]:
    """收集项目下所有有图但未同步的资产。

    按 region 选判断字段：DOMESTIC→volc_private_asset_id，OVERSEAS→byteplus_asset_id。
    返回 AssetItem 列表（kind 为 'character' / 'location' / 'prop'，与项目资产类型一致）。
    """
    from app.models.project_asset import ProjectCharacter, ProjectLocation, ProjectProp

    overseas = region == UserRegion.OVERSEAS
    sync_field = "byteplus_asset_id" if overseas else "volc_private_asset_id"
    items: list[AssetItem] = []

    base_filters = [
        ProjectCharacter.project_id == project_id,
        ProjectCharacter.is_deleted == False,
        ProjectCharacter.image_url != None,
        ProjectCharacter.image_url != "",
    ]
    for asset in db.query(ProjectCharacter).filter(*base_filters, getattr(ProjectCharacter, sync_field).is_(None)).all():
        items.append(AssetItem(kind="character", asset_id=str(asset.id), model=asset, display_name=asset.name or ""))

    for model_cls, kind in [(ProjectLocation, "location"), (ProjectProp, "prop")]:
        q = db.query(model_cls).filter(
            model_cls.project_id == project_id,
            model_cls.is_deleted == False,
            model_cls.image_url != None,
            model_cls.image_url != "",
            getattr(model_cls, sync_field).is_(None),
        )
        for asset in q.all():
            items.append(AssetItem(kind=kind, asset_id=str(asset.id), model=asset, display_name=asset.name or ""))

    return items


def get_project_unsynced_summary(
    db: Session,
    project_id: str,
    region: str,
) -> dict:
    """返回按类别分组的项目未同步资产计数与完整 asset_id 列表。

    返回：{character, scene, prop, total, asset_ids}
    asset_ids 用于前端在用户确认同步时立即把对应卡片标记为"同步中"，
    不必等待后端 WS started 事件到达。
    注：项目资产里 location 即"场景"。
    """
    items = collect_project_unsynced_assets(db, project_id, region)
    character = sum(1 for i in items if i.kind == "character")
    scene = sum(1 for i in items if i.kind == "location")
    prop = sum(1 for i in items if i.kind == "prop")
    return {
        "character": character,
        "scene": scene,
        "prop": prop,
        "total": len(items),
        "asset_ids": [i.asset_id for i in items],
    }
