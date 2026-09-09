"""
项目管理 API 端点
"""
import io
import math
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.core.logging import logger
from app.deps.permission_deps import require_permission
from app.core.project_logger import get_project_logger
from app.crud.project_crud import project as project_crud
from app.crud.project_analyze_crud import analysis_result as ar_crud
from app.crud.task_crud import operation_record as op_crud
from app.crud.episode_crud import episode_crud
from app.models.project import Project
from app.models.project_asset import Episode, Storyboard, ProjectCharacter, ProjectLocation, ProjectProp
from app.models.user import User
from app.models.user_api_config import UserApiConfig
from app.schemas.project import (
    ProjectCreate, ProjectCreateResponse,
    ProjectConfirm, ProjectConfirmResponse, ProjectConfigResponse,
    ProjectConfigUpdateRequest, ProjectConfigGetResponse,
    ProjectDetailResponse, NovelMetaResponse,
    UploadNovelResponse,
    ProjectStatsResponse, ProjectListItemResponse,
    ProjectListResponse, PaginationResponse,
    ProjectUpdateRequest,
)
from app.utils.response import success_response

router = APIRouter()

ALLOWED_EXTENSIONS = {".txt", ".docx"}

# 可继承配置的键，与 UserApiConfig 列名一致
_CONFIGURABLE_KEYS = [
    "video_ratio", "art_style",
    "analysis_model", "character_model", "location_model",
    "storyboard_model", "edit_model", "video_model", "audio_model",
]

VIDEO_RESOLUTION_MAP = {
    "21:9": "2560x1080",
    "16:9": "1920x1080",
    "4:3": "1440x1080",
    "1:1": "1080x1080",
    "3:4": "1080x1440",
    "9:16": "1080x1920",
}


def _resolve_video_resolution(ratio: str) -> str:
    """根据画面比例计算视频分辨率"""
    return VIDEO_RESOLUTION_MAP.get(ratio, "1080x1920")


def _resolve_image_resolution() -> str:
    """图片分辨率固定值"""
    return "2K"


def _build_resolved_config(
    project_config: dict,
    user_config: UserApiConfig | None,
) -> ProjectConfigResponse:
    """合并 project.config > UserApiConfig > 系统默认值"""
    resolved = {}
    for key in _CONFIGURABLE_KEYS:
        # 兼容旧 key
        config_key = key
        if key == "video_ratio" and key not in project_config and "ratio" in project_config:
            config_key = "ratio"
        elif key == "art_style" and key not in project_config and "style" in project_config:
            config_key = "style"

        if config_key in project_config and project_config[config_key] is not None:
            resolved[key] = project_config[config_key]
        elif user_config:
            val = getattr(user_config, key, None)
            if val is not None:
                resolved[key] = val

    ratio = resolved.get("video_ratio", "9:16")
    resolved["video_resolution"] = _resolve_video_resolution(ratio)
    resolved["image_resolution"] = _resolve_image_resolution()

    return ProjectConfigResponse(**resolved)


def _build_default_config(user_config: UserApiConfig | None) -> ProjectConfigResponse:
    """构建全局默认配置"""
    defaults = {}
    for key in _CONFIGURABLE_KEYS:
        if user_config:
            val = getattr(user_config, key, None)
            if val is not None:
                defaults[key] = val

    ratio = defaults.get("video_ratio", "9:16")
    defaults["video_resolution"] = _resolve_video_resolution(ratio)
    defaults["image_resolution"] = _resolve_image_resolution()

    return ProjectConfigResponse(**defaults)


def _get_project_and_check(
    project_id: str,
    db: Session,
    current_user: User,
    require_created: bool = True,
) -> Project:
    """获取项目并校验权限"""
    proj = project_crud.get(id=project_id, db=db)
    if not proj or proj.is_deleted:
        raise HTTPException(status_code=404, detail="项目不存在")
    if proj.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权访问该项目")
    if require_created and proj.status not in ("projectCreated", "assetsReady", "producing", "completed"):
        raise HTTPException(status_code=400, detail="项目尚未创建，无法读取配置")
    return proj


def _extract_text_from_txt(content: bytes) -> str:
    """从 TXT 文件提取文本"""
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return content.decode("gbk")


def _extract_text_from_docx(content: bytes) -> str:
    """从 DOCX 文件提取文本"""
    try:
        from docx import Document
    except ImportError:
        raise HTTPException(status_code=500, detail="服务器未安装 python-docx，无法解析 DOCX 文件")

    doc = Document(io.BytesIO(content))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)


# ============ 上传小说文件 ============

@router.post("/upload/novel")
def upload_novel(
    file: UploadFile = File(..., description="小说文件（.txt 或 .docx）"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("project:create")),
):
    """上传小说文件，提取纯文本"""
    filename = file.filename or ""
    ext = ""
    if "." in filename:
        ext = "." + filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的文件格式，仅支持 {', '.join(ALLOWED_EXTENSIONS)}",
        )

    content = file.file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="文件内容为空")

    try:
        if ext == ".txt":
            extracted_text = _extract_text_from_txt(content)
            file_format = "txt"
        elif ext == ".docx":
            extracted_text = _extract_text_from_docx(content)
            file_format = "docx"
        else:
            raise HTTPException(status_code=400, detail="不支持的文件格式")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件解析失败: {e}")
        raise HTTPException(status_code=400, detail=f"文件解析失败: {str(e)}")

    char_count = len(extracted_text)

    data = UploadNovelResponse(
        file_url="",
        extracted_text=extracted_text,
        char_count=char_count,
        format=file_format,
    )
    return success_response(data=data)


# ============ 创建项目 ============

def _create_director_project(db: Session, current_user: User, body: ProjectCreate):
    """导演模式：跳过剧情分析，直接建项目 + N 集空剧集"""
    if not body.title or not body.title.strip():
        raise HTTPException(status_code=400, detail="导演模式下项目名称必填")
    if body.expected_episodes is None:
        raise HTTPException(status_code=400, detail="导演模式下预计集数必填")

    config = {
        "mode": "director",
        "video_ratio": body.video_ratio or "9:16",
        "art_style": body.art_style or "realistic",
    }

    proj = project_crud.create(obj_in={
        "user_id": current_user.id,
        "title": body.title.strip(),
        "novel_text": "",
        "file_url": "",
        "status": "projectCreated",
        "config": config,
    }, created_by_id=current_user.id, db=db)

    # 批量建 N 集空剧集，与项目同事务
    if body.expected_episodes > 0:
        episode_crud.bulk_create_empty(
            db, project_id=proj.id, count=body.expected_episodes, user_id=current_user.id,
        )

    op_crud.log_operation(
        db, project_id=proj.id, user_id=current_user.id,
        action="create_project", target_type="project", target_id=proj.id,
    )

    plog = get_project_logger(proj.id)
    plog.info(f"用户 {current_user.id} 创建导演模式项目，预生成 {body.expected_episodes} 集")

    return proj


@router.post("", status_code=status.HTTP_201_CREATED)
def create_project(
    body: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("project:create")),
):
    """创建项目

    - mode=novel（默认）：走剧情分析流程
    - mode=director：跳过剧情分析，直接预生成 N 集空剧集
    """
    if body.mode == "director":
        proj = _create_director_project(db, current_user, body)
        data = ProjectCreateResponse(id=proj.id, status=proj.status, create_time=proj.create_time)
        return success_response(data=data)

    # ===== novel 模式（原逻辑） =====
    novel_text = body.novel_text
    if not novel_text or len(novel_text) < 20:
        raise HTTPException(status_code=400, detail="novel_text 至少 20 个字符")
    file_name = body.file_name
    is_long_text = len(novel_text) > 5000

    store_text = novel_text[:200] if is_long_text else novel_text

    proj = project_crud.create(obj_in={
        "user_id": current_user.id,
        "title": "待确认项目",
        "novel_text": store_text,
        "file_url": "",
        "status": "draft",
    }, created_by_id=current_user.id, db=db)

    # 长文本：上传COS，key = novel/{project_id}/{timestamp}_{原始文件名}
    if is_long_text:
        try:
            import time as _time
            from app.utils.tencent_cos_utils import cos_client
            ts = int(_time.time() * 1000)
            name = file_name or "story.txt"
            # 上传的是提取后的纯文本，key 统一使用 .txt 后缀，避免后续按后缀解析 docx 时出错
            if "." in name:
                name = name.rsplit(".", 1)[0] + ".txt"
            else:
                name = name + ".txt"
            date_path = datetime.now().strftime("%Y%m%d")
            file_key = f"novel/{date_path}/{proj.id}/{ts}_{name}"
            text_bytes = novel_text.encode("utf-8")
            ok = cos_client.upload_object(
                file_data=text_bytes, file_key=file_key,
                content_type="text/plain; charset=utf-8",
            )
            if not ok:
                raise HTTPException(status_code=500, detail="文本上传云存储失败，请稍后重试")
            proj.file_url = cos_client.get_permanent_url(file_key)
            db.commit()
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"长文本上传COS失败: {e}")
            raise HTTPException(status_code=500, detail="文本上传云存储失败，请稍后重试")

    ar_crud.create(obj_in={
        "project_id": proj.id,
        "status": "pending",
    }, created_by_id=current_user.id, db=db)

    op_crud.log_operation(
        db, project_id=proj.id, user_id=current_user.id,
        action="create_project", target_type="project", target_id=proj.id,
    )

    plog = get_project_logger(proj.id)
    plog.info(f"用户 {current_user.id} 创建项目")

    data = ProjectCreateResponse(id=proj.id, status=proj.status, create_time=proj.create_time)
    return success_response(data=data)


# ============ 确认项目设置 ============

@router.put("/{project_id}/confirm")
def confirm_project(
    project_id: str,
    body: ProjectConfirm,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("project:update")),
):
    """确认项目设置"""
    proj = project_crud.get(id=project_id, db=db)
    if not proj or proj.is_deleted:
        raise HTTPException(status_code=404, detail="项目不存在")
    if proj.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权访问该项目")
    if proj.status != "storyReady":
        raise HTTPException(status_code=400, detail="当前状态不允许确认项目设置")

    proj.title = body.title
    proj.config = {
        **(proj.config or {}),
        "video_ratio": body.ratio,
        "art_style": body.style,
    }
    proj.status = "projectCreated"
    proj.update_uid = current_user.id
    db.add(proj)

    result = ar_crud.get_by_project(db, proj.id)
    if result:
        result.status = "completed"
        db.add(result)

    db.commit()
    db.refresh(proj)

    op_crud.log_operation(
        db, project_id=proj.id, user_id=current_user.id,
        action="confirm_project", target_type="project", target_id=proj.id,
        detail={"title": body.title, "ratio": body.ratio, "style": body.style},
    )

    plog = get_project_logger(proj.id)
    plog.info(f"用户 {current_user.id} 确认项目设置 title={body.title} ratio={body.ratio} style={body.style}")

    user_config = db.query(UserApiConfig).filter_by(user_id=current_user.id).first()
    resolved_config = _build_resolved_config(proj.config, user_config)

    data = ProjectConfirmResponse(
        id=proj.id,
        status=proj.status,
        title=proj.title,
        config=resolved_config,
    )
    return success_response(data=data)


# ============ 获取全部项目列表（主账号+子账号） ============

@router.get("/all", summary="获取全部项目列表（主账号专用）")
def get_all_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.parent_user_id is not None:
        raise HTTPException(status_code=403, detail="仅主账号可调用此接口")
    user_ids = [current_user.id]
    sub_users = db.query(User).filter(
        User.parent_user_id == current_user.id,
        User.is_deleted == False,
    ).all()
    user_ids.extend([u.id for u in sub_users])
    items = (
        db.query(Project)
        .filter(Project.user_id.in_(user_ids), Project.is_deleted == False)
        .order_by(Project.update_time.desc().nullslast(), Project.create_time.desc())
        .all()
    )
    projects = [
        {"id": p.id, "title": p.title}
        for p in items
    ]
    return success_response(data=projects)


# ============ 获取项目详情 ============

@router.get("/{project_id}")
def get_project_detail(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("project:read")),
):
    """获取项目详情"""
    proj = project_crud.get(id=project_id, db=db)
    if not proj or proj.is_deleted:
        raise HTTPException(status_code=404, detail="项目不存在")
    if proj.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权访问该项目")

    # 更新最近访问时间（直接 update，避免触发 update_time 的 onupdate）
    db.query(Project).filter(Project.id == proj.id).update(
        {Project.last_access_time: datetime.now()},
        synchronize_session=False,
    )
    db.commit()

    result = ar_crud.get_by_project(db, proj.id)
    analysis_status = result.status if result else None
    current_version_number = None
    if result:
        from app.crud.project_analyze_crud import analysis_version as av_crud
        current_ver = av_crud.get_current_version(db, result.id)
        if current_ver:
            current_version_number = current_ver.version_number

    data = ProjectDetailResponse(
        id=proj.id,
        user_id=proj.user_id,
        title=proj.title,
        status=proj.status,
        phase=proj.phase,
        config=proj.config,
        novel_meta=NovelMetaResponse(**(proj.novel_meta or {})),
        analysis_status=analysis_status,
        current_version_number=current_version_number,
        create_time=proj.create_time,
        update_time=proj.update_time,
    )
    return success_response(data=data)


# ============ 获取小说原文 ============

@router.get("/{project_id}/novel-text")
def get_project_novel_text(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("project:read")),
):
    """获取项目小说原文：短文本直接返回，长文本从 COS 下载"""
    proj = project_crud.get(id=project_id, db=db)
    if not proj or proj.is_deleted:
        raise HTTPException(status_code=404, detail="项目不存在")
    if proj.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权访问该项目")

    novel_text = proj.novel_text or ""

    # 长文本：novel_text 被截断为预览，需从 COS 下载完整内容
    if proj.file_url and len(novel_text) <= 5000:
        try:
            from app.utils.tencent_cos_utils import cos_client
            file_key = cos_client.url_to_key(proj.file_url)
            if file_key:
                raw_bytes = cos_client.download_object_as_bytes(file_key)
                if raw_bytes:
                    ext = file_key.rsplit(".", 1)[-1].lower() if "." in file_key else "txt"
                    if ext == "docx":
                        from docx import Document
                        try:
                            doc = Document(io.BytesIO(raw_bytes))
                            novel_text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
                        except Exception:
                            # 后缀与实际内容不符时按文本兜底解码
                            try:
                                novel_text = raw_bytes.decode("utf-8")
                            except UnicodeDecodeError:
                                novel_text = raw_bytes.decode("gbk")
                    else:
                        try:
                            novel_text = raw_bytes.decode("utf-8")
                        except UnicodeDecodeError:
                            novel_text = raw_bytes.decode("gbk")
        except Exception as e:
            logger.error(f"从COS下载小说原文失败: {e}")

    return success_response(data={"novel_text": novel_text})


# ============ 项目配置读写 ============

@router.get("/{project_id}/config")
def get_project_config(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("project:read")),
):
    """获取项目配置（含全局配置参考）"""
    proj = _get_project_and_check(project_id, db, current_user)
    user_config = db.query(UserApiConfig).filter_by(user_id=current_user.id).first()
    project_config = proj.config or {}

    data = ProjectConfigGetResponse(
        title=proj.title,
        resolved=_build_resolved_config(project_config, user_config),
        defaults=_build_default_config(user_config),
        overrides={k: v for k, v in project_config.items() if k in _CONFIGURABLE_KEYS},
    )
    return success_response(data=data)


@router.put("/{project_id}/config")
def update_project_config(
    project_id: str,
    body: ProjectConfigUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("project:update")),
):
    """更新项目配置（传 null 清除覆盖，回退到全局配置）"""
    proj = _get_project_and_check(project_id, db, current_user)
    config = {**(proj.config or {})}

    if body.title is not None and "title" in body.model_fields_set:
        proj.title = body.title

    for key in _CONFIGURABLE_KEYS:
        if key not in body.model_fields_set:
            continue
        val = getattr(body, key)
        if val is None:
            config.pop(key, None)
        else:
            config[key] = val

    proj.config = config
    proj.update_uid = current_user.id
    db.add(proj)
    db.commit()
    db.refresh(proj)

    user_config = db.query(UserApiConfig).filter_by(user_id=current_user.id).first()

    data = ProjectConfigGetResponse(
        title=proj.title,
        resolved=_build_resolved_config(proj.config, user_config),
        defaults=_build_default_config(user_config),
        overrides={k: v for k, v in proj.config.items() if k in _CONFIGURABLE_KEYS},
    )
    return success_response(data=data)


# ============ 资产统计 ============

def _build_stats_map(db: Session, project_ids: list[str]) -> dict[str, dict]:
    """批量查询多个项目的资产统计。

    口径按项目模式分流：
    - episodes / videos：两种模式一致（剧集数 / 有 video_url 的分镜数）
    - images：novel 模式 = 分镜总数；director 模式 = 项目资产库已生成 image_url 的资产数
      （导演模式项目初始只有空剧集，没有分镜；用户感知的"图片"主要是资产库里的角色/场景/道具图）
    """
    if not project_ids:
        return {}
    stats_map = {pid: {"episodes": 0, "images": 0, "videos": 0} for pid in project_ids}

    # 剧集
    rows = db.query(Episode.project_id, func.count()).filter(
        Episode.project_id.in_(project_ids), Episode.is_deleted == False
    ).group_by(Episode.project_id).all()
    for pid, cnt in rows:
        stats_map[pid]["episodes"] = cnt

    # 通过 episode 关联查询分镜（用于 novel 模式 images 和两种模式 videos）
    episode_rows = db.query(Episode.project_id, Episode.id).filter(
        Episode.project_id.in_(project_ids), Episode.is_deleted == False
    ).all()
    episode_ids = [eid for _, eid in episode_rows]
    episode_project_map = {eid: pid for pid, eid in episode_rows}

    # 区分项目模式
    project_rows = db.query(Project.id, Project.config).filter(Project.id.in_(project_ids)).all()
    director_pids = set()
    novel_pids = set()
    for pid, cfg in project_rows:
        mode = (cfg or {}).get("mode") if isinstance(cfg, dict) else None
        (director_pids if mode == "director" else novel_pids).add(pid)

    # videos：两种模式口径一致 —— 有 video_url 的分镜数
    if episode_ids:
        vid_rows = db.query(Storyboard.episode_id, func.count()).filter(
            Storyboard.episode_id.in_(episode_ids),
            Storyboard.is_deleted == False,
            Storyboard.video_url != None,
            Storyboard.video_url != "",
        ).group_by(Storyboard.episode_id).all()
        for eid, cnt in vid_rows:
            pid = episode_project_map.get(eid)
            if pid:
                stats_map[pid]["videos"] += cnt

    # images：novel = 分镜数；director = 资产库已生成 image_url 的资产数
    if novel_pids and episode_ids:
        novel_eids = [eid for pid, eid in episode_rows if pid in novel_pids]
        if novel_eids:
            sb_rows = db.query(Storyboard.episode_id, func.count()).filter(
                Storyboard.episode_id.in_(novel_eids), Storyboard.is_deleted == False
            ).group_by(Storyboard.episode_id).all()
            for eid, cnt in sb_rows:
                pid = episode_project_map.get(eid)
                if pid:
                    stats_map[pid]["images"] += cnt

    if director_pids:
        pid_list = list(director_pids)
        for model in (ProjectCharacter, ProjectLocation, ProjectProp):
            asset_rows = db.query(model.project_id, func.count()).filter(
                model.project_id.in_(pid_list),
                model.is_deleted == False,
                model.image_url != None,
                model.image_url != "",
            ).group_by(model.project_id).all()
            for pid, cnt in asset_rows:
                stats_map[pid]["images"] += cnt

    return stats_map


# ============ 项目列表 ============

@router.get("")
def list_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(8, ge=1, le=50),
    search: str = Query(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("project:read")),
):
    """获取当前用户的项目列表"""
    items, total = project_crud.get_paginated(db, str(current_user.id), page, page_size, search)
    project_ids = [p.id for p in items]
    stats_map = _build_stats_map(db, project_ids)

    projects = []
    for p in items:
        s = stats_map.get(p.id, {})
        # 截取小说内容预览（最多80个字符）
        novel_preview = None
        if p.novel_text:
            text = p.novel_text.strip()[:80]
            novel_preview = text + "..." if len(p.novel_text.strip()) > 80 else text
        projects.append(ProjectListItemResponse(
            id=p.id,
            title=p.title,
            description=p.description,
            status=p.status,
            mode=(p.config or {}).get("mode", "novel"),
            novel_preview=novel_preview,
            stats=ProjectStatsResponse(**s),
            create_time=p.create_time,
            update_time=p.update_time,
        ))

    total_pages = math.ceil(total / page_size) if total > 0 else 0
    data = ProjectListResponse(
        projects=projects,
        pagination=PaginationResponse(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
        ),
    )
    return success_response(data=data)


# ============ 编辑项目 ============

@router.patch("/{project_id}")
def update_project(
    project_id: str,
    body: ProjectUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("project:update")),
):
    """编辑项目名称和描述"""
    proj = project_crud.get(id=project_id, db=db)
    if not proj or proj.is_deleted:
        raise HTTPException(status_code=404, detail="项目不存在")
    if proj.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权访问该项目")

    proj.title = body.title
    proj.description = body.description
    proj.update_uid = current_user.id
    db.add(proj)
    db.commit()
    db.refresh(proj)

    stats = _build_stats_map(db, [proj.id]).get(proj.id, {})
    novel_preview = None
    if proj.novel_text:
        text = proj.novel_text.strip()[:80]
        novel_preview = text + "..." if len(proj.novel_text.strip()) > 80 else text
    data = ProjectListItemResponse(
        id=proj.id,
        title=proj.title,
        description=proj.description,
        status=proj.status,
        mode=(proj.config or {}).get("mode", "novel"),
        novel_preview=novel_preview,
        stats=ProjectStatsResponse(**stats),
        create_time=proj.create_time,
        update_time=proj.update_time,
    )
    return success_response(data=data)


# ============ 删除项目 ============

@router.delete("/{project_id}")
def delete_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("project:delete")),
):
    """软删除项目"""
    proj = project_crud.get(id=project_id, db=db)
    if not proj or proj.is_deleted:
        raise HTTPException(status_code=404, detail="项目不存在")
    if proj.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权访问该项目")

    from datetime import datetime
    proj.is_deleted = True
    proj.delete_time = datetime.now()
    proj.update_uid = current_user.id
    db.add(proj)
    db.commit()

    plog = get_project_logger(project_id)
    plog.info(f"用户 {current_user.id} 删除项目")

    return success_response(data={"id": project_id})
