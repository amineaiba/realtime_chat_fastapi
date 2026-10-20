from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from schemas.user import UserOut


class RoomTypeEnum(str, Enum):
    DM = "dm"
    GROUP = "group"


class MessageTypeEnum(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"


class MessageCreate(BaseModel):
    content: Optional[str] = None
    room_id: UUID
    type: MessageTypeEnum = MessageTypeEnum.TEXT
    attachemnt_url: Optional[str] = None


class MessageUpdate(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)


# todo :  hide the content if is_deleted is True in the logic or use a validator
class MessageOut(BaseModel):
    id: UUID
    content: Optional[str]
    type: MessageTypeEnum
    attachment_url: Optional[str]

    sender: UserOut
    room_id: UUID

    is_edited: bool
    is_deleted: bool
    created_at: datetime

    class Config:
        from_attributes = True


# rooms schemas
class RoomCreate(BaseModel):
    type: RoomTypeEnum = RoomTypeEnum.GROUP
    name: Optional[str] = None  # Required if group
    member_ids: List[UUID] = []


class RoomUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)


class RoomMemberOut(BaseModel):
    user: UserOut
    joined_at: datetime
    last_read_at: datetime

    class Config:
        from_attributes = True


class RoomBase(BaseModel):
    id: UUID
    type: RoomTypeEnum
    name: Optional[str]
    is_active: bool
    creator_id: Optional[UUID]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class RoomListOut(RoomBase):
    # Metadata for the list view
    unread_count: Optional[int] = 0
    last_message: Optional[MessageOut] = None
    # Lets the room list show a DM partner's name, avatar, and presence.
    members: List[RoomMemberOut] = []


class RoomDetailOut(RoomBase):
    members: List[RoomMemberOut]
