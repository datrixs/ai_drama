"""资产同步到火山私域/BytePlus Celery 任务"""
from app.core.celery import celery
from app.core.ws import ws_manager
from app.crud.user_crud import user_crud
from app.enums.user import UserRegion
from loguru import logger
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.project_asset import ProjectCharacter, ProjectLocation, ProjectProp
from app.models.project import Project
from app.services.asset_sync_service import (
    collect_user_unsynced_assets,
    collect_project_unsynced_assets,
    run_batch_sync,
)
from app.utils.volc_sync import sync_asset_to_volc


@celery.task(bind=True, max_retries=2, default_retry_delay=60, time_limit=600)
def sync_single_asset_to_volc(self, project_id: str, asset_id: str, asset_kind: str):
    """同步单个资产到火山私域/BytePlus"""
    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise ValueError("项目不存在")

        region = user_crud.get_region(user_id=project.user_id, db=db)
        overseas = region == UserRegion.OVERSEAS
        group_field = "byteplus_private_asset_group_id" if overseas else "volc_private_asset_group_id"
        asset_id_field = "byteplus_asset_id" if overseas else "volc_private_asset_id"

        group_id = getattr(project, group_field, None)
        if not group_id:
            raise ValueError("项目未创建资产组")

        # 根据类型获取资产
        if asset_kind == "character":
            asset = db.query(ProjectCharacter).filter(ProjectCharacter.id == asset_id).first()
        elif asset_kind == "scene":
            asset = db.query(ProjectLocation).filter(ProjectLocation.id == asset_id).first()
        elif asset_kind == "prop":
            asset = db.query(ProjectProp).filter(ProjectProp.id == asset_id).first()
        else:
            raise ValueError(f"未知资产类型: {asset_kind}")

        if not asset or not asset.image_url:
            raise ValueError("资产不存在或无图片URL")

        # 同步到火山/BytePlus
        from app.services.volc_control_plane import VolcControlPlane
        volc = VolcControlPlane(region=region)
        remote_id = volc.create_asset(
            group_id=group_id,
            image_url=asset.image_url,
            display_name=asset.name if hasattr(asset, "name") else "",
        )

        setattr(asset, asset_id_field, remote_id)
        db.commit()

        logger.info(f"资产同步成功: asset_id={asset_id}, region={region}, remote_id={remote_id}")

    except Exception as e:
        logger.error(f"资产同步失败: asset_id={asset_id}, error={e}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)

    finally:
        db.close()


@celery.task(bind=True, max_retries=1, default_retry_delay=120, time_limit=1800)
def sync_project_all_assets(self, project_id: str):
    """批量同步项目所有未同步资产到火山私域/BytePlus。

    流程对齐资产中心 sync_user_all_assets：
      1. 收集项目所有未同步资产（character/location/prop，按 region 选字段）
      2. 推送 project_batch_sync_started（带总数 + asset_ids）
      3. 逐条同步，每条完成推送 project_batch_sync_progress（含成功/失败 + 错误原因）
      4. 完成：project_batch_sync_completed（带成功/失败计数）
      5. 异常：project_batch_sync_failed
    """
    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise ValueError("项目不存在")

        user_id = str(project.user_id)
        region = user_crud.get_region(user_id=user_id, db=db)
        items = collect_project_unsynced_assets(db, project_id, region)
        total = len(items)

        # 起始事件：完整 asset_ids 用于逐条标记"同步中"角标
        ws_manager.publish_project_event(user_id, project_id, "project_batch_sync_started", {
            "total": total,
            "region": region,
            "asset_ids": [i.asset_id for i in items],
        })

        if total == 0:
            ws_manager.publish_project_event(user_id, project_id, "project_batch_sync_completed", {
                "total": 0, "success_count": 0, "failed_count": 0,
            })
            return

        overseas = region == UserRegion.OVERSEAS
        asset_id_field = "byteplus_asset_id" if overseas else "volc_private_asset_id"

        logger.info(f"开始批量同步项目资产: project_id={project_id}, region={region}, total={total}")

        success_count = 0
        failed_count = 0

        for item in items:
            try:
                remote_id = sync_asset_to_volc(
                    db, project_id, item.model, item.kind,
                    user_id=user_id, raise_on_error=True,
                )
                if remote_id:
                    success_count += 1
                    ws_manager.publish_project_event(user_id, project_id, "project_batch_sync_progress", {
                        "asset_id": item.asset_id,
                        "asset_name": item.display_name,
                        "kind": item.kind,
                        "status": "success",
                        "volc_id": remote_id,
                    })
                else:
                    failed_count += 1
                    err = "未获取到远程资产ID"
                    ws_manager.publish_project_event(user_id, project_id, "project_batch_sync_progress", {
                        "asset_id": item.asset_id,
                        "asset_name": item.display_name,
                        "kind": item.kind,
                        "status": "failed",
                        "error": err,
                    })
            except Exception as e:
                failed_count += 1
                logger.warning(f"项目资产同步失败: project_id={project_id}, asset_id={item.asset_id}, error={e}")
                ws_manager.publish_project_event(user_id, project_id, "project_batch_sync_progress", {
                    "asset_id": item.asset_id,
                    "asset_name": item.display_name,
                    "kind": item.kind,
                    "status": "failed",
                    "error": str(e),
                })

        ws_manager.publish_project_event(user_id, project_id, "project_batch_sync_completed", {
            "total": total,
            "success_count": success_count,
            "failed_count": failed_count,
        })
        logger.info(f"项目批量同步完成: project_id={project_id}, success={success_count}, failed={failed_count}")

    except Exception as e:
        logger.error(f"项目批量同步任务失败: project_id={project_id}, error={e}")
        # 失败时需要拿 project.user_id 才能推 WS；若连 project 都没有，直接跳过 WS
        try:
            project = db.query(Project).filter(Project.id == project_id).first()
            if project:
                ws_manager.publish_project_event(str(project.user_id), project_id, "project_batch_sync_failed", {
                    "error": str(e),
                })
        except Exception:
            pass
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)

    finally:
        db.close()


@celery.task(bind=True, max_retries=1, default_retry_delay=120, time_limit=1800)
def sync_user_all_assets(self, user_id: str, folder_id: str | None = None):
    """批量同步用户资产中心所有未同步资产到火山私域/BytePlus。

    流程：
      1. 查询当前用户所有未同步资产（按 region 选字段，按 folder_id 过滤）
      2. 推送 asset_hub_batch_sync_started 事件（带总数和完整 asset_ids）
      3. 逐条同步，每条完成推送 asset_hub_batch_sync_progress
      4. 全部完成推送 asset_hub_batch_sync_completed（带成功/失败计数）
      5. 异常时推送 asset_hub_batch_sync_failed

    folder_id 三态：None=全部，'null'=未分组，其他字符串=指定资产组
    """
    db = SessionLocal()
    try:
        region = user_crud.get_region(user_id=user_id, db=db)
        items = collect_user_unsynced_assets(db, user_id, region, folder_id=folder_id)
        total = len(items)

        # 起始事件：完整 asset_ids，前端用于逐条标记"同步中"角标
        ws_manager.publish_asset_hub_event(user_id, "asset_hub_batch_sync_started", {
            "total": total,
            "region": region,
            "folder_id": folder_id,
            "asset_ids": [i.asset_id for i in items],
        })

        if total == 0:
            ws_manager.publish_asset_hub_event(user_id, "asset_hub_batch_sync_completed", {
                "total": 0,
                "success_count": 0,
                "failed_count": 0,
            })
            return

        def on_progress(status, item, remote_id, error):
            ws_manager.publish_asset_hub_event(user_id, "asset_hub_batch_sync_progress", {
                "asset_id": item.asset_id,
                "kind": item.kind,
                "status": status,
                "volc_id": remote_id,
                "error": error,
            })

        logger.info(f"开始批量同步用户资产: user_id={user_id}, region={region}, total={total}")

        result = run_batch_sync(db, user_id, items, region, on_progress=on_progress)

        ws_manager.publish_asset_hub_event(user_id, "asset_hub_batch_sync_completed", {
            "total": result.total,
            "success_count": result.success_count,
            "failed_count": result.failed_count,
        })
        logger.info(
            f"批量同步完成: user_id={user_id}, success={result.success_count}, failed={result.failed_count}"
        )

    except Exception as e:
        logger.error(f"批量同步任务失败: user_id={user_id}, error={e}")
        ws_manager.publish_asset_hub_event(user_id, "asset_hub_batch_sync_failed", {
            "error": str(e),
        })
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)

    finally:
        db.close()
