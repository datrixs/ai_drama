"""对话记录 API 端点"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.crud.conversation_crud import conversation_crud
from app.models import User
from app.schemas.conversation import ConversationCreate, ConversationResponse, MessageCreate
from app.utils.response import success_response

router = APIRouter()


@router.post("/projects/{project_id}/conversations")
def create_conversation(
    project_id: str,
    body: ConversationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建对话"""
    from uuid import uuid4

    messages = []
    if body.initial_message:
        from datetime import datetime
        messages.append({
            "role": "user",
            "content": body.initial_message,
            "timestamp": datetime.utcnow().isoformat(),
        })

    data = {
        "id": str(uuid4()),
        "project_id": project_id,
        "episode_id": body.episode_id,
        "user_id": current_user.id,
        "conversation_type": body.conversation_type,
        "title": body.title,
        "messages": messages,
        "create_uid": current_user.id,
    }

    from app.models.conversation import ConversationRecord
    record = ConversationRecord(**data)
    db.add(record)
    db.commit()
    db.refresh(record)

    return success_response(data=ConversationResponse.model_validate(record))


@router.get("/projects/{project_id}/conversations")
def get_conversations(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取对话列表"""
    records = conversation_crud.get_by_project(db, project_id)
    items = [ConversationResponse.model_validate(r) for r in records]
    return success_response(data=items)


@router.post("/projects/{project_id}/conversations/{conversation_id}/messages")
def send_message(
    project_id: str,
    conversation_id: str,
    body: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """发送消息到对话"""
    record = conversation_crud.get(id=conversation_id, db=db)
    if not record or record.is_deleted:
        raise HTTPException(status_code=404, detail="对话不存在")

    conversation_crud.add_message(db, conversation_id, body.model_dump())
    db.commit()
    db.refresh(record)

    return success_response(data=ConversationResponse.model_validate(record))


@router.get("/projects/{project_id}/conversations/{conversation_id}")
def get_conversation_detail(
    project_id: str,
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取对话详情"""
    record = conversation_crud.get(id=conversation_id, db=db)
    if not record or record.is_deleted:
        raise HTTPException(status_code=404, detail="对话不存在")

    return success_response(data=ConversationResponse.model_validate(record))
