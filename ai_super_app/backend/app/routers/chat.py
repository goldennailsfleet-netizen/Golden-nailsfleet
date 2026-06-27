"""
Chat Router - AI Chat Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from app.models.ai_router import router as ai_router
from app.database.models import get_db, Chat, Message
from app.auth import get_current_user
from app.database.models import User
from sqlalchemy.orm import Session
from datetime import datetime

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    chat_id: Optional[int] = None
    context: Optional[str] = None
    prefer_offline: bool = False
    model: Optional[str] = "auto"


class ChatResponse(BaseModel):
    success: bool
    response: str
    model_used: str
    latency_ms: float
    chat_id: int


@router.post("/send", response_model=ChatResponse)
async def send_message(request: ChatRequest, background_tasks: BackgroundTasks,
                      current_user: User = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    if request.chat_id:
        chat = db.query(Chat).filter(Chat.id == request.chat_id, Chat.user_id == current_user.id).first()
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")
    else:
        chat = Chat(title=request.message[:50] + "...", user_id=current_user.id)
        db.add(chat)
        db.commit()
        db.refresh(chat)

    user_message = Message(chat_id=chat.id, role="user", content=request.message)
    db.add(user_message)
    db.commit()

    result = await ai_router.route_query(
        query=request.message, context=request.context,
        prefer_offline=request.prefer_offline
    )

    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error", "AI request failed"))

    ai_message = Message(
        chat_id=chat.id, role="assistant", content=result["response"],
        model_used=result["model_used"], latency_ms=result["latency_ms"]
    )
    db.add(ai_message)
    db.commit()

    chat.updated_at = datetime.utcnow()
    db.commit()

    return ChatResponse(
        success=True, response=result["response"],
        model_used=result["model_used"], latency_ms=result["latency_ms"],
        chat_id=chat.id
    )


@router.get("/history/{chat_id}")
async def get_chat_history(chat_id: int,
                          current_user: User = Depends(get_current_user),
                          db: Session = Depends(get_db)):
    chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == current_user.id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    messages = db.query(Message).filter(Message.chat_id == chat_id).order_by(Message.created_at).all()
    return {
        "chat_id": chat_id,
        "messages": [
            {"role": msg.role, "content": msg.content,
             "model_used": msg.model_used, "created_at": str(msg.created_at)}
            for msg in messages
        ]
    }


@router.get("/chats")
async def get_user_chats(current_user: User = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    chats = db.query(Chat).filter(Chat.user_id == current_user.id).order_by(Chat.updated_at.desc()).all()
    return {
        "chats": [
            {"id": chat.id, "title": chat.title,
             "created_at": str(chat.created_at), "updated_at": str(chat.updated_at)}
            for chat in chats
        ]
    }


@router.delete("/{chat_id}")
async def delete_chat(chat_id: int,
                     current_user: User = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == current_user.id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    db.query(Message).filter(Message.chat_id == chat_id).delete()
    db.delete(chat)
    db.commit()
    return {"success": True, "message": "Chat deleted"}
