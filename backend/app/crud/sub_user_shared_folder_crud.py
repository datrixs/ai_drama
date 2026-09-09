from sqlalchemy.orm import Session

from app.models.sys_permission import SubUserSharedFolder


class SubUserSharedFolderCRUD:

    @staticmethod
    def get_shared_folder_ids(db: Session, sub_user_id: str) -> list[str]:
        rows = (
            db.query(SubUserSharedFolder.folder_id)
            .filter_by(sub_user_id=sub_user_id, is_deleted=False)
            .all()
        )
        return [r.folder_id for r in rows]

    @staticmethod
    def set_shared_folders(db: Session, sub_user_id: str, folder_ids: list[str]) -> None:
        db.query(SubUserSharedFolder).filter_by(sub_user_id=sub_user_id).delete(
            synchronize_session=False
        )
        for fid in folder_ids:
            obj = SubUserSharedFolder(
                sub_user_id=sub_user_id,
                folder_id=fid,
            )
            db.add(obj)
        db.flush()

    @staticmethod
    def get_sub_user_ids_by_folder(db: Session, folder_id: str) -> list[str]:
        rows = (
            db.query(SubUserSharedFolder.sub_user_id)
            .filter_by(folder_id=folder_id, is_deleted=False)
            .all()
        )
        return [r.sub_user_id for r in rows]


sub_user_shared_folder_crud = SubUserSharedFolderCRUD()
