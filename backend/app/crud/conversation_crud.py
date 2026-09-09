"""对话记录 CRUD"""
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.crud.base_crud import CRUDBase
from app.models.conversation import ConversationRecord


class CRUDConversationRecord(CRUDBase[ConversationRecord, dict, dict]):
    """对话记录 CRUD 操作"""

    def get_by_project(
        self, db: Session, project_id: str, limit: int = 50
    ) -> list[ConversationRecord]:
        """获取项目下所有对话"""
        return (
            db.query(self.model)
            .filter(self.model.project_id == project_id, self.model.is_deleted == False)
            .order_by(self.model.create_time.desc())
            .limit(limit)
            .all()
        )

    def get_by_episode(
        self, db: Session, episode_id: str
    ) -> list[ConversationRecord]:
        """获取剧集下所有对话"""
        return (
            db.query(self.model)
            .filter(self.model.episode_id == episode_id, self.model.is_deleted == False)
            .order_by(self.model.create_time)
            .all()
        )

    def add_message(
        self, db: Session, conversation_id: str, message: dict
    ) -> None:
        """追加消息到对话记录"""
        record = db.get(self.model, conversation_id)
        if record:
            messages = record.messages or []
            message["timestamp"] = datetime.utcnow().isoformat()
            messages.append(message)
            record.messages = messages
            db.flush()


conversation_crud = CRUDConversationRecord(ConversationRecord)
