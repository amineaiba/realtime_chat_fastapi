from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, status
from sqlalchemy.orm import Session

from core.database import get_db
from db_models.user import User
from dependencies import get_current_user
from schemas.chat import (
    MessageOut,
    MessageUpdate,
    RoomCreate,
    RoomDetailOut,
    RoomListOut,
    RoomUpdate,
)
from services.chat_services import ChatService

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.put("/rooms/{room_id}/mark-as-read", status_code=status.HTTP_200_OK)
def mark_room_as_read(
    room_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return ChatService.mark_as_read(db, room_id, current_user.id)


@router.get("/rooms/{room_id}", response_model=RoomDetailOut)
def get_room_detail(
    room_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    room = ChatService.get_room_by_id(db, room_id, current_user.id)
    return RoomDetailOut.model_validate(room)


@router.get("/rooms", response_model=List[RoomListOut])
def get_my_rooms(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    rooms = ChatService.get_user_rooms(db, current_user.id)
    return [RoomListOut.model_validate(room) for room in rooms]


@router.post(
    "/rooms/create", response_model=RoomDetailOut, status_code=status.HTTP_200_OK
)
def create_room(
    room_data: Annotated[RoomCreate, Body()],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    room = ChatService.get_or_create_room(
        db=db,
        user_id=current_user.id,
        type=room_data.type,
        name=room_data.name,
        participant_ids=room_data.member_ids,
    )
    return RoomDetailOut.model_validate(room)


@router.patch("/rooms/{room_id}", response_model=RoomDetailOut)
def update_room(
    room_id: UUID,
    room_data: Annotated[RoomUpdate, Body],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    room = ChatService.update_room(db, room_id, current_user.id, room_data)
    return RoomDetailOut.model_validate(room)


@router.delete("/rooms/{room_id}", status_code=status.HTTP_200_OK)
def delete_room(
    room_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ChatService.delete_room(db, room_id, current_user.id)
    return {"message": "Room deleted successfully"}


@router.get("/unread-count")
def get_unread_count(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    count = ChatService.get_global_unread_count(db, current_user.id)
    return {"unread_count": count}


@router.patch("/messages/{message_id}", response_model=MessageOut)
def edit_message(
    message_id: UUID,
    message_data: Annotated[MessageUpdate, Body],
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    message = ChatService.edit_message(
        db, message_id, current_user.id, message_data.content
    )
    return MessageOut.model_validate(message)


@router.delete("/messages/{message_id}/delete", status_code=status.HTTP_204_NO_CONTENT)
def delete_message(
    message_id: UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ChatService.delete_message(db, current_user.id, message_id)
    return None


@router.post("/rooms/{room_id}/members/add")
def add_member(
    room_id: UUID,
    user_to_add_id: Annotated[UUID, Body(embed=True)],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ChatService.add_member(db, room_id, current_user.id, user_to_add_id)
    return {"message": "Member added successfully"}


@router.delete(
    "/rooms/{room_id}/members/{user_id}/delete", status_code=status.HTTP_200_OK
)
def remove_member(
    room_id: UUID,
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ChatService.remove_member(db, room_id, current_user.id, user_id)
    return {"message": "Member removed successfully"}


@router.delete("/rooms/{room_id}/leave", status_code=status.HTTP_200_OK)
def leave_room(
    room_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ChatService.leave_room(db, room_id, current_user.id)
    return {"message": "Left group successfully"}


@router.get("/rooms/{room_id}/messages", response_model=List[MessageOut])
def get_room_messages(
    room_id: UUID,
    limit: int = Query(
        default=50, ge=1, le=100, description="Number of messages to return"
    ),
    before_id: Optional[UUID] = Query(
        default=None, description="Cursor: get messages before this ID"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get message history with cursor-based pagination.
    """
    messages = ChatService.get_messages(db, room_id, current_user.id, limit, before_id)
    return [MessageOut.model_validate(msg) for msg in messages]
