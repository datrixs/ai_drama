"""
剧情分析和 AI 扩写 API 端点
"""


from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.core.model_provider import ModelCaller
from app.core.project_logger import get_project_logger
from app.services.config_reader import ConfigReader
from app.crud.project_crud import project as project_crud
from app.crud.project_analyze_crud import analysis_result as ar_crud, analysis_version as av_crud
from app.crud.task_crud import operation_record as op_crud
from app.models.user import User
from app.schemas.project_analyze import (
    AnalysisRequest, AnalysisTriggerResponse,
    AnalysisResponse,
    AiStoryExpandRequest, AiStoryExpandResponse,
)
from app.utils.response import success_response

router = APIRouter()


# ============ JSON 数组 → 展示文本格式化 ============

def _format_list_to_text(data, item_formatter: callable) -> str:
    """通用：将 JSON 数组或字符串格式化为展示文本"""
    if data is None:
        return ""
    if isinstance(data, str):
        return data
    if isinstance(data, list):
        return "\n\n".join(item_formatter(item) for item in data)
    return ""


def _format_character_profiles(data) -> str:
    def fmt(c):
        if not isinstance(c, dict):
            return str(c)
        parts = []
        if c.get("name"):
            parts.append(f"【{c['name']}】" + (f"（{c['role']}）" if c.get("role") else ""))
        if c.get("aliases"):
            parts.append(f"别名：{c['aliases']}")
        if c.get("description"):
            parts.append(c["description"])
        if c.get("image_prompt"):
            parts.append(f"视觉关键词：{c['image_prompt']}")
        return "\n".join(parts)
    return _format_list_to_text(data, fmt)


def _format_scene_descriptions(data) -> str:
    def fmt(s):
        if not isinstance(s, dict):
            return str(s)
        parts = []
        if s.get("name"):
            parts.append(f"【{s['name']}】" + (f"（{s['type']}）" if s.get("type") else ""))
        if s.get("place"):
            parts.append(f"地点：{s['place']}")
        if s.get("time"):
            parts.append(f"时间：{s['time']}")
        if s.get("summary"):
            parts.append(f"氛围：{s['summary']}")
        if s.get("description"):
            parts.append(s["description"])
        if s.get("image_prompt"):
            parts.append(f"视觉关键词：{s['image_prompt']}")
        return "\n".join(parts)
    return _format_list_to_text(data, fmt)


def _format_prop_descriptions(data) -> str:
    def fmt(p):
        if not isinstance(p, dict):
            return str(p)
        parts = []
        if p.get("name"):
            parts.append(f"【{p['name']}】" + (f"（{p['importance']}）" if p.get("importance") else ""))
        if p.get("aliases"):
            parts.append(f"别名：{p['aliases']}")
        if p.get("description"):
            parts.append(p["description"])
        if p.get("image_prompt"):
            parts.append(f"视觉关键词：{p['image_prompt']}")
        return "\n".join(parts)
    return _format_list_to_text(data, fmt)


def _format_episode_outlines(data) -> str:
    def fmt(ep):
        if not isinstance(ep, dict):
            return str(ep)
        num = ep.get("episode_number", "?")
        title = ep.get("title", "")
        summary = ep.get("summary", "")
        parts = [f"第{num}集：{title}", summary]
        hook = ep.get("hook") or ep.get("cliffhanger")
        if hook:
            parts.append(f"钩子：{hook}")
        return "\n".join(parts)
    return _format_list_to_text(data, fmt)

AI_STORY_EXPAND_SYSTEM = (
    "你是一位专业的短剧编剧助手。用户会给出故事创意、关键词或简短大纲，"
    "请根据输入扩展生成一个完整的短剧故事文本。要求：\n"
    "1. 保持用户创意的核心冲突和人物设定\n"
    "2. 扩展成有起承转合的完整故事\n"
    "3. 包含主要人物、场景、对白和情节发展\n"
    "4. 输出纯中文文本，500-2000字为宜"
)


# ============ 校验模型配置 ============

@router.get("/check_analysis_model_config")
def check_model_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """校验用户是否已配置必要模型"""
    config_reader = ConfigReader(db)
    resolved = config_reader.get_config(str(current_user.id))
    missing = []
    if not resolved.analysis_model:
        missing.append("分析模型")
    if missing:
        raise HTTPException(
            status_code=400,
            detail="请先在设置中心配置默认模型",
        )
    return success_response(data={"ok": True})


# ============ 触发/调整分析 ============

@router.put("/{project_id}/analyze")
def trigger_analysis(
    project_id: str,
    body: AnalysisRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """触发故事分析或增量调整"""
    proj = project_crud.get(id=project_id, db=db)
    if not proj or proj.is_deleted:
        raise HTTPException(status_code=404, detail="项目不存在")
    if proj.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权访问该项目")

    result = ar_crud.get_by_project(db, proj.id)
    if not result:
        raise HTTPException(status_code=404, detail="分析结果不存在")

    if body.adjustment is None:
        # 首次分析
        if proj.status != "draft":
            raise HTTPException(status_code=400, detail="当前状态不允许首次分析")

        config_reader = ConfigReader(db)
        resolved = config_reader.get_project_config(str(current_user.id), proj.config)

        proj.status = "analyzingStory"
        result.status = "generating"
        db.commit()

        version = av_crud.create(obj_in={
            "analysis_result_id": result.id,
            "version_number": 1,
            "is_confirmed": False,
        }, created_by_id=current_user.id, db=db)

        model_config = resolved.to_dict()

        from app.celery_tasks.story_analysis import story_analysis_workflow
        task = story_analysis_workflow.delay(proj.id, version.id, model_config)

        op_crud.log_operation(
            db, project_id=proj.id, user_id=current_user.id,
            action="start_analysis", target_type="analysis_version", target_id=version.id,
        )

        plog = get_project_logger(proj.id)
        plog.info(f"用户 {current_user.id} 触发首次分析 version={version.version_number}")

        data = AnalysisTriggerResponse(task_id=task.id, project_status="analyzingStory")
        return success_response(data=data)
    else:
        # 增量调整
        if proj.status != "projectCreated":
            raise HTTPException(status_code=400, detail="当前状态不允许调整")

        config_reader = ConfigReader(db)
        resolved = config_reader.get_project_config(str(current_user.id), proj.config)

        proj.status = "analyzingStory"
        result.status = "generating"
        db.commit()

        current_version = av_crud.get_current_version(db, result.id)
        if not current_version:
            raise HTTPException(status_code=400, detail="没有可调整的版本")

        new_version = av_crud.create(obj_in={
            "analysis_result_id": result.id,
            "parent_version_id": current_version.id,
            "version_number": current_version.version_number + 1,
            "is_confirmed": False,
        }, created_by_id=current_user.id, db=db)

        model_config = resolved.to_dict()

        from app.celery_tasks.story_analysis import story_analysis_adjust
        task = story_analysis_adjust.delay(proj.id, new_version.id, body.adjustment, model_config)

        op_crud.log_operation(
            db, project_id=proj.id, user_id=current_user.id,
            action="adjust_analysis", target_type="analysis_version", target_id=new_version.id,
            detail={"adjustment": body.adjustment},
        )

        plog = get_project_logger(proj.id)
        plog.info(f"用户 {current_user.id} 触发增量调整 version={new_version.version_number}")

        data = AnalysisTriggerResponse(task_id=task.id, project_status="analyzingStory")
        return success_response(data=data)


# ============ 获取分析结果 ============

@router.get("/{project_id}/analysis")
def get_analysis(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取最新分析结果"""
    proj = project_crud.get(id=project_id, db=db)
    if not proj or proj.is_deleted:
        raise HTTPException(status_code=404, detail="项目不存在")
    if proj.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权访问该项目")

    result = ar_crud.get_by_project(db, proj.id)
    if not result:
        raise HTTPException(status_code=404, detail="分析结果不存在")

    version = av_crud.get_current_version(db, result.id)
    if not version:
        raise HTTPException(status_code=404, detail="分析版本不存在")

    data = AnalysisResponse(
        version_id=version.id,
        version_number=version.version_number,
        is_confirmed=version.is_confirmed,
        global_setting=version.global_setting,
        episode_outlines=_format_episode_outlines(version.episode_outlines),
        character_profiles=_format_character_profiles(version.character_profiles),
        scene_descriptions=_format_scene_descriptions(version.scene_descriptions),
        prop_descriptions=_format_prop_descriptions(version.prop_descriptions),
    )
    return success_response(data=data)


# # ============ 保存手动编辑的分镜（暂未开放） ============
#
# @router.put("/{project_id}/analysis/storyboard")
# def save_storyboard(
#     project_id: str,
#     body: StoryboardSaveRequest,
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user),
# ):
#     """保存手动编辑的第一集分镜"""
#     proj = project_crud.get(id=project_id, db=db)
#     if not proj or proj.is_deleted:
#         raise HTTPException(status_code=404, detail="项目不存在")
#     if proj.user_id != current_user.id:
#         raise HTTPException(status_code=403, detail="无权访问该项目")
#     if proj.status != "projectCreated":
#         raise HTTPException(status_code=400, detail="当前状态不允许编辑分镜")
#
#     result = ar_crud.get_by_project(db, proj.id)
#     if not result:
#         raise HTTPException(status_code=404, detail="分析结果不存在")
#
#     version = av_crud.get_current_version(db, result.id)
#     if not version:
#         raise HTTPException(status_code=404, detail="分析版本不存在")
#
#     version.first_ep_storyboard = body.storyboard.model_dump()
#     version.update_uid = current_user.id
#     db.add(version)
#     db.commit()
#     db.refresh(version)
#
#     plog = get_project_logger(project_id)
#     plog.info(f"用户 {current_user.id} 保存分镜编辑")
#
#     data = StoryboardSaveResponse(version_id=version.id, updated=True)
#     return success_response(data=data)


# ============ AI 故事扩写 ============

@router.post("/ai_story_expand")
def ai_story_expand(
    req: AiStoryExpandRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """AI 故事扩写，接收短创意，输出完整短剧故事"""
    config_reader = ConfigReader(db)
    resolved = config_reader.get_config(str(user.id))
    caller = ModelCaller(resolved, db=db)
    result = caller.call(
        model_key="analysis_model",
        prompt=req.prompt,
        system_prompt=AI_STORY_EXPAND_SYSTEM,
        temperature=0.7,
        max_tokens=4096,
        user_id=str(user.id),
    )
    data = AiStoryExpandResponse(expanded_text=result.content.strip())
    return success_response(data=data)
