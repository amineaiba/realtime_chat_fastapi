import enum
import uuid

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from core.database import Base


# ---Enums---
class RoomType(str, enum.Enum):
    DM = "dm"
    GROUP = "group"


class MessageType(str, enum.Enum):
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"


# ----the bridge between rooms and users
class RoomMember(Base):
    """
    Tracks a user's membership in a room.
    Crucial for: Unread Counts, Muting, and 'Last Read' status.
    """

    __tablename__ = "room_members"

    room_id = Column(
        UUID(as_uuid=True), ForeignKey("rooms.id", ondelete="CASCADE"), primary_key=True
    )
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )

    joined_at = Column(DateTime(timezone=True), server_default=func.now())

    #! see where is this gets updated
    last_read_at = Column(
        DateTime(timezone=True), server_default=func.now()
    )  # For calculating unread messages
    # is_admin = Column(Boolean, default=False)

    # Relationships
    room = relationship("Room", back_populates="members")
    user = relationship("User", backref="room_memberships")


class Room(Base):
    __tablename__ = "rooms"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    type = Column(Enum(RoomType), default=RoomType.DM, nullable=False)
    name = Column(String, nullable=True)
    description = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    creator_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    messages = relationship(
        "Message", back_populates="room", cascade="all,delete-orphan"
    )

    members = relationship(
        "RoomMember", back_populates="room", cascade="all, delete-orphan"
    )


class Message(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), default=uuid.uuid4, primary_key=True, index=True)

    content = Column(Text, nullable=True)
    type = Column(Enum(MessageType), default=MessageType.TEXT, nullable=False)
    attachment_url = Column(String, nullable=True)

    # Status flags
    is_read = Column(Boolean, default=False)  # Global read status
    is_edited = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)  # Soft delete

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    sender_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    room_id = Column(UUID(as_uuid=True), ForeignKey("rooms.id"), nullable=False)

    sender = relationship("User", backref="messages")
    room = relationship("Room", back_populates="messages")
