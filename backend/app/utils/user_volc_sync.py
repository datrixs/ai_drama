"""用户级火山私域/BytePlus 同步工具

GroupID 来源按资产类型分流：
  - 客户端资产（is_management_asset=False）：从 user_api_config 读取
  - 平台资产（is_management_asset=True）：从 admin.admin_users 表读取
"""
from sqlalchemy import text

from app.core.logging import logger
from app.crud.user_api_config_crud import user_api_config_crud
from app.crud.user_crud import user_crud
from app.enums.user import UserRegion
from app.services.volc_control_plane import VolcControlPlane
from app.utils.tencent_cos_utils import cos_client


def _get_admin_asset_group_id(db, admin_user_id: str, group_field: str) -> str | None:
    """从 admin.admin_users 表读取火山资产组 ID"""
    result = db.execute(
        text(f"SELECT {group_field} FROM admin.admin_users WHERE id = :uid AND is_deleted = false"),
        {"uid": admin_user_id},
    ).fetchone()
    if result and result[0]:
        return result[0]
    return None


def ensure_user_volc_asset_group(
    db, user_id: str, region: str = None, is_management_asset: bool = False
) -> str:
    """确保在指定区域有资产组 ID，返回 group_id。

    - 客户端资产（is_management_asset=False）：从 user_api_config 读取，没有则创建。
      region 默认按用户当前 region 读取。DOMESTIC 写回 volc_private_asset_group_id，
      OVERSEAS 写回 byteplus_private_asset_group_id。
    - 平台资产（is_management_asset=True）：从 admin.admin_users 表读取（不自动创建）。
      region 默认 DOMESTIC。
    """
    if is_management_asset:
        overseas = region == UserRegion.OVERSEAS
        group_field = "byteplus_private_asset_group_id" if overseas else "volc_private_asset_group_id"
        group_id = _get_admin_asset_group_id(db, user_id, group_field)
        if not group_id:
            raise ValueError(f"平台资产所属账号 {user_id} 未配置 {group_field}，请先在管理后台配置资产组")
        return group_id

    # 客户端资产：保持原逻辑
    if region is None:
        region = user_crud.get_region(user_id=user_id, db=db)
    overseas = region == UserRegion.OVERSEAS
    group_field = "byteplus_private_asset_group_id" if overseas else "volc_private_asset_group_id"

    config = user_api_config_crud.get_by_user_id(user_id=user_id, db=db)
    if config and getattr(config, group_field, None):
        return getattr(config, group_field)

    volc = VolcControlPlane(region=region)
    group_id = volc.create_asset_group(f"user_{user_id}")

    if config:
        setattr(config, group_field, group_id)
    else:
        config = user_api_config_crud.get_default_api_config(user_id)
        setattr(config, group_field, group_id)
        db.add(config)
    db.commit()

    return group_id


def _resolve_management_flag(db, asset, fallback_user_id: str):
    """解析资产是否为平台资产。

    返回 (is_management_asset, asset_user_id)：
      - 顶层资产（character/location/voice）：直接取 is_management_asset 和 user_id
      - 子资产（appearance/location_image）：通过父资产判断
      - 其他资产（如 ShortVideoAsset）：默认客户端
    """
    is_mgmt = getattr(asset, "is_management_asset", None)
    if is_mgmt is not None:
        return bool(is_mgmt), getattr(asset, "user_id", fallback_user_id)

    # 子资产：通过父资产判断
    parent_character_id = getattr(asset, "character_id", None)
    if parent_character_id:
        from app.models.asset import GlobalCharacter
        parent = db.query(GlobalCharacter).filter(
            GlobalCharacter.id == parent_character_id,
            GlobalCharacter.is_deleted == False,
        ).first()
        if parent:
            return bool(parent.is_management_asset), parent.user_id
        return False, fallback_user_id

    parent_location_id = getattr(asset, "location_id", None)
    if parent_location_id:
        from app.models.asset import GlobalLocation
        parent = db.query(GlobalLocation).filter(
            GlobalLocation.id == parent_location_id,
            GlobalLocation.is_deleted == False,
        ).first()
        if parent:
            return bool(parent.is_management_asset), parent.user_id
        return False, fallback_user_id

    return False, fallback_user_id


def sync_user_asset_to_volc(
    db, user_id: str, asset, display_name: str = "", raise_on_error: bool = False
) -> str | None:
    """同步资产到火山私域/BytePlus 资产组。返回对应 region 的 asset_id 或 None。幂等。

    根据资产类型自动选择 GroupID 来源：
      - 客户端资产：从 user_api_config 读取，按 user.region 选择区域
      - 平台资产：从 admin.admin_users 表读取，默认国内区域
    """
    try:
        is_mgmt, asset_user_id = _resolve_management_flag(db, asset, user_id)

        if is_mgmt:
            # 平台资产：默认国内 region
            region = UserRegion.DOMESTIC
        else:
            region = user_crud.get_region(user_id=user_id, db=db)

        overseas = region == UserRegion.OVERSEAS

        # ShortVideoAsset 用 volc_asset_id，其他资产表用 volc_private_asset_id
        if overseas:
            local_field = "byteplus_asset_id"
        else:
            local_field = "volc_asset_id" if hasattr(asset, "volc_asset_id") else "volc_private_asset_id"

        existing_id = getattr(asset, local_field, None)
        if existing_id:
            return existing_id

        image_url = getattr(asset, "image_url", None) or getattr(asset, "asset_url", None) or getattr(asset, "custom_voice_url", None)
        if image_url:
            if image_url.startswith("http"):
                key = cos_client.url_to_key(image_url)
                if key and key != image_url:
                    image_url = cos_client.get_signed_url(key)
            else:
                image_url = cos_client.get_signed_url(image_url)
        if not image_url:
            if raise_on_error:
                raise ValueError("资产 URL 为空，无法同步")
            return None

        # 推断火山 AssetType
        asset_type = "Image"
        if hasattr(asset, "asset_type") and getattr(asset, "asset_type", None):
            type_map = {"image": "Image", "video": "Video", "audio": "Audio"}
            asset_type = type_map.get(getattr(asset, "asset_type", "").lower(), "Image")
        elif hasattr(asset, "custom_voice_url") and getattr(asset, "custom_voice_url", None):
            asset_type = "Audio"

        group_id = ensure_user_volc_asset_group(
            db, asset_user_id, region=region, is_management_asset=is_mgmt
        )

        volc = VolcControlPlane(region=region)
        remote_id = volc.create_asset(
            group_id=group_id,
            image_url=image_url,
            display_name=display_name or "",
            asset_type=asset_type,
        )

        setattr(asset, local_field, remote_id)
        db.commit()
        return remote_id
    except Exception as e:
        logger.warning(f"用户级火山/BytePlus 同步失败: user_id={user_id}, error={e}")
        if raise_on_error:
            raise
        return None
