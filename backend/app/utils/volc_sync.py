"""火山私域/BytePlus 同步工具"""
from app.core.logging import logger
from app.crud.user_crud import user_crud
from app.enums.user import UserRegion
from app.models.project import Project
from app.services.volc_control_plane import VolcControlPlane
from app.utils.tencent_cos_utils import cos_client


def sync_asset_to_volc(
    db,
    project_id: str,
    asset,
    asset_type: str,
    user_id: str = None,
    raise_on_error: bool = False,
) -> str | None:
    """同步资产图片到火山私域/BytePlus，返回对应的 asset_id 或 None

    根据 user_id 读取用户区域：
      - DOMESTIC：调用火山引擎，写回 asset.volc_private_asset_id，资产组写回 project.volc_private_asset_group_id
      - OVERSEAS：调用 BytePlus，写回 asset.byteplus_asset_id，资产组写回 project.byteplus_private_asset_group_id

    raise_on_error=True 时，所有失败场景（项目不存在、image_url 为空、远端调用异常）都抛异常；
    默认 False，失败仅记日志并返回 None。
    """
    try:
        region = user_crud.get_region(user_id=user_id, db=db)
        overseas = region == UserRegion.OVERSEAS

        group_field = "byteplus_private_asset_group_id" if overseas else "volc_private_asset_group_id"
        asset_id_field = "byteplus_asset_id" if overseas else "volc_private_asset_id"

        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            if raise_on_error:
                raise ValueError(f"项目不存在: {project_id}")
            return None

        group_id = getattr(project, group_field, None)
        if not group_id:
            volc = VolcControlPlane(region=region)
            group_id = volc.create_asset_group(f"project_{project_id}")
            setattr(project, group_field, group_id)
            db.commit()

        image_url = asset.image_url
        if image_url and not image_url.startswith("http"):
            image_url = cos_client.key_to_url(image_url)

        if not image_url:
            if raise_on_error:
                raise ValueError("资产 image_url 为空，无法同步")
            return None

        volc = VolcControlPlane(region=region)
        remote_id = volc.create_asset(
            group_id=group_id,
            image_url=image_url,
            display_name=asset.name,
        )
        setattr(asset, asset_id_field, remote_id)
        db.commit()
        return remote_id
    except Exception as e:
        logger.warning(f"火山/BytePlus 私域同步失败: {e}")
        if raise_on_error:
            raise
        return None
