"""
项目日志 API 端点
"""
import io
import os
import zipfile

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.core.logging import LOG_DIR
from app.crud.project_crud import project as project_crud
from app.models.user import User

router = APIRouter()


@router.get("/{project_id}/logs")
def download_project_logs(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """下载项目全部日志（ZIP）"""
    proj = project_crud.get(id=project_id, db=db)
    if not proj or proj.is_deleted:
        raise HTTPException(status_code=404, detail="项目不存在")
    if proj.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权访问该项目")

    project_log_dir = os.path.join(LOG_DIR, "projects", project_id)
    if not os.path.isdir(project_log_dir):
        raise HTTPException(status_code=404, detail="项目日志不存在")

    log_files = ["project.log", "task.log", "model_call.log"]
    existing_files = [f for f in log_files if os.path.isfile(os.path.join(project_log_dir, f))]
    if not existing_files:
        raise HTTPException(status_code=404, detail="项目日志文件不存在")

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for filename in existing_files:
            filepath = os.path.join(project_log_dir, filename)
            zf.write(filepath, filename)
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=project_{project_id}_logs.zip"},
    )
