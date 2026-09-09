import uuid

from sqlalchemy.orm import Session

from app.crud.base_crud import CRUDBase
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectConfirm


class CRUDProject(CRUDBase[Project, ProjectCreate, ProjectConfirm]):
    def create(self, *, obj_in, created_by_id=None, db: Session) -> Project:
        """重写 create，支持 dict 输入"""
        if isinstance(obj_in, dict):
            db_obj = self.model(**obj_in)
        else:
            db_obj = self.model(**obj_in.model_dump(exclude_unset=True))
        db_obj.id = db_obj.id or str(uuid.uuid4())
        if created_by_id:
            db_obj.create_uid = created_by_id
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_by_user(self, db: Session, user_id: str, *, skip: int = 0, limit: int = 100) -> list[Project]:
        """获取用户的项目列表"""
        return (
            db.query(Project)
            .filter(Project.user_id == user_id, Project.is_deleted == False)
            .order_by(Project.id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def update_status(self, db: Session, project_id: str, status: str) -> Project:
        """更新项目状态"""
        project = self.get(id=project_id, db=db)
        if not project:
            raise ValueError(f"项目 {project_id} 不存在")
        project.status = status
        db.add(project)
        db.commit()
        db.refresh(project)
        return project

    def get_paginated(self, db: Session, user_id: str, page: int = 1, page_size: int = 8, search: str = "") -> tuple[list[Project], int]:
        """分页查询用户项目"""
        query = db.query(Project).filter(
            Project.user_id == user_id,
            Project.is_deleted == False,
        )
        if search:
            query = query.filter(Project.title.ilike(f"%{search}%"))
        total = query.count()
        items = query.order_by(
            Project.update_time.desc().nullslast(),
            Project.create_time.desc(),
        ).offset((page - 1) * page_size).limit(page_size).all()
        return items, total


project = CRUDProject(Project)
