from fastapi import Depends, HTTPException, Path
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.models.project import Project
from app.models.project_analyze import AnalysisResult
from app.models.user import User


def get_project(
    project_id: str = Path(..., description="项目ID"),
    db: Session = Depends(get_db),
) -> Project:
    """获取项目（公共依赖）"""
    project = db.get(Project, project_id)
    if not project or project.is_deleted:
        raise HTTPException(status_code=404, detail="项目不存在")
    return project


def get_analysis_result(
    project: Project = Depends(get_project),
    db: Session = Depends(get_db),
) -> AnalysisResult:
    """获取项目的分析结果"""
    from app.crud.project_analyze_crud import analysis_result as ar_crud
    result = ar_crud.get_by_project(db, project.id)
    if not result:
        raise HTTPException(status_code=404, detail="分析结果不存在")
    return result


def get_project_with_user(
    project: Project = Depends(get_project),
    current_user: User = Depends(get_current_user),
) -> Project:
    """获取当前用户的项目（校验权限）"""
    if project.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权访问该项目")
    return project
