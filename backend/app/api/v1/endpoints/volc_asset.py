"""火山引擎资产同步 API 端点"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.crud.user_crud import user_crud
from app.models import User
from app.models.project import Project
from app.services.asset_sync_service import (
    get_user_unsynced_summary,
    get_project_unsynced_summary,
)
from app.utils.response import success_response


class SyncAssetRequest(BaseModel):
    asset_id: str = Field(description="资产ID")
    asset_kind: str = Field(description="资产类型: character/scene/prop")


class SyncUserAssetRequest(BaseModel):
    asset_id: str = Field(description="资产ID")
    asset_kind: str = Field(description="资产类型: character_appearance/location_image/voice")


class SyncUserAllAssetsRequest(BaseModel):
    # folder_id 三态：None=全部，'null'=未分组（folder_id IS NULL），其他字符串=指定资产组
    folder_id: str | None = Field(default=None, description="资产组过滤")


router = APIRouter()


@router.post("/projects/{project_id}/sync-asset-group")
def sync_volc_asset_group(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建火山资产组并同步项目资产"""
    from app.services.volc_control_plane import VolcControlPlane
    from app.models.project import Project

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    volc = VolcControlPlane()
    group_id = volc.create_asset_group(f"project_{project_id}")
    project.volc_private_asset_group_id = group_id
    db.commit()

    # 异步批量同步
    from app.celery_tasks.asset_sync import sync_project_all_assets
    sync_project_all_assets.delay(project_id)

    return success_response(data={"volc_private_asset_group_id": group_id})


@router.post("/projects/{project_id}/sync-asset")
def sync_volc_asset(
    project_id: str,
    body: SyncAssetRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """同步单个资产到火山私域"""
    from app.models.project_asset import ProjectCharacter, ProjectLocation, ProjectProp
    from app.utils.volc_sync import sync_asset_to_volc

    if body.asset_kind == "character":
        asset = db.query(ProjectCharacter).filter(ProjectCharacter.id == body.asset_id).first()
    elif body.asset_kind == "scene":
        asset = db.query(ProjectLocation).filter(ProjectLocation.id == body.asset_id).first()
    elif body.asset_kind == "prop":
        asset = db.query(ProjectProp).filter(ProjectProp.id == body.asset_id).first()
    else:
        raise HTTPException(status_code=400, detail=f"未知资产类型: {body.asset_kind}")

    if not asset:
        raise HTTPException(status_code=404, detail="资产不存在")

    asset_name = asset.name or ""
    try:
        volc_id = sync_asset_to_volc(
            db, project_id, asset, body.asset_kind,
            user_id=str(current_user.id), raise_on_error=True,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"「{asset_name}」同步火山失败：{e}")
    if not volc_id:
        raise HTTPException(status_code=500, detail=f"「{asset_name}」同步火山失败：未知原因")

    return success_response(data={
        "volc_private_asset_id": volc_id,
        "asset_id": body.asset_id,
    })


@router.post("/projects/{project_id}/sync-all-assets")
def sync_all_volc_assets(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """批量同步项目资产到火山私域"""
    from app.celery_tasks.asset_sync import sync_project_all_assets
    sync_project_all_assets.delay(project_id)

    return success_response(msg="批量同步任务已提交")


@router.get("/projects/{project_id}/unsynced-summary")
def get_project_unsynced_summary_api(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """查询项目下未同步资产分类计数（用于批量同步弹窗展示）。

    按 project.user_id 解析 region：DOMESTIC→volc_private_asset_id，OVERSEAS→byteplus_asset_id。
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    if str(project.user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="无权访问该项目")

    region = user_crud.get_region(user_id=str(project.user_id), db=db)
    summary = get_project_unsynced_summary(db, project_id, region)
    return success_response(data={"region": region, **summary})


@router.post("/user/sync-asset")
def sync_user_volc_asset(
    body: SyncUserAssetRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """同步用户资产中心资产到火山私域"""
    from app.utils.user_volc_sync import sync_user_asset_to_volc

    if body.asset_kind == "character_appearance":
        from app.models.asset import GlobalCharacterAppearance
        asset = db.query(GlobalCharacterAppearance).filter(GlobalCharacterAppearance.id == body.asset_id).first()
    elif body.asset_kind == "location_image":
        from app.models.asset import GlobalLocationImage
        asset = db.query(GlobalLocationImage).filter(GlobalLocationImage.id == body.asset_id).first()
    elif body.asset_kind == "voice":
        from app.models.asset import GlobalVoice
        asset = db.query(GlobalVoice).filter(GlobalVoice.id == body.asset_id).first()
    else:
        raise HTTPException(status_code=400, detail=f"未知资产类型: {body.asset_kind}")

    if not asset:
        raise HTTPException(status_code=404, detail="资产不存在")

    try:
        volc_id = sync_user_asset_to_volc(
            db, str(current_user.id), asset, raise_on_error=True,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"同步火山失败：{e}")
    if not volc_id:
        raise HTTPException(status_code=500, detail="同步火山失败：未知原因")

    return success_response(data={
        "volc_id": volc_id,
        "asset_id": body.asset_id,
    })


@router.get("/user/unsynced-summary")
def get_user_unsynced_summary_api(
    folder_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """查询当前用户未同步资产分类计数（用于批量同步弹窗展示）。

    按 user.region 选判断字段：DOMESTIC→volc_private_asset_id，OVERSEAS→byteplus_asset_id。
    folder_id 三态：不传=全部，'null'=未分组，其他字符串=指定资产组。
    """
    region = user_crud.get_region(user_id=str(current_user.id), db=db)
    summary = get_user_unsynced_summary(db, str(current_user.id), region, folder_id=folder_id)
    return success_response(data={"region": region, **summary})


@router.post("/user/sync-all-assets")
def sync_user_all_assets_api(
    body: SyncUserAllAssetsRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """触发用户资产批量同步任务（异步）。"""
    from app.celery_tasks.asset_sync import sync_user_all_assets
    folder_id = body.folder_id if body else None
    sync_user_all_assets.delay(str(current_user.id), folder_id=folder_id)
    return success_response(msg="批量同步任务已提交")
