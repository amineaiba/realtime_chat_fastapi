from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, aliased, joinedload

from db_models.chat import Message, Room, RoomMember, RoomType
from db_models.user import User


class ChatService:
    @staticmethod
    def mark_as_read(db: Session, room_id: UUID, user_id: UUID):
        room_member = (
            db.query(RoomMember)
            .filter(RoomMember.room_id == room_id, RoomMember.user_id == user_id)
            .first()
        )
        if not room_member:
            raise HTTPException(404, "user is not a member ")

        room_member.last_read_at = datetime.now()
        db.commit()
        db.refresh(room_member)

        return {
            "message": "Room marked as read",
            "room_id": str(room_id),
            "last_read_at": room_member.last_read_at,
        }

    @staticmethod
    def get_room_by_id(db: Session, room_id: UUID, user_id: UUID):
        room = (
            db.query(Room)
            .join(RoomMember, Room.id == RoomMember.room_id)
            .options(
                joinedload(Room.members)
                .joinedload(RoomMember.user)
                .joinedload(User.profile)
            )
            .filter(
                Room.id == room_id,
                RoomMember.user_id == user_id,
                Room.is_active.is_(True),
            )
            .first()
        )

        if not room:
            raise HTTPException(
                404, "Room not found or you are not a member of this room "
            )
        return room

    @staticmethod
    def get_user_rooms(db: Session, user_id: UUID):
        """
        Get all rooms for a user, sorted by most recent message activity.
        """
        # Latest message per room (Postgres DISTINCT ON), aliased so it can
        # be joined against like a normal Message entity.
        latest_message_subquery = (
            db.query(Message)
            .distinct(Message.room_id)
            .order_by(Message.room_id, Message.created_at.desc())
            .subquery()
        )
        LatestMessage = aliased(Message, latest_message_subquery)
        # loader options on a subquery-derived alias must be applied to the outer
        # query (see below), options on the inner query are discarded by .subquery()

        unread_count_subquery = (
            select(Message.room_id, func.count(Message.id).label("unread_count"))
            .join(RoomMember, Message.room_id == RoomMember.room_id)
            .where(
                and_(
                    RoomMember.user_id == user_id,
                    Message.sender_id != user_id,  # own messages are never unread
                    or_(
                        RoomMember.last_read_at.is_(None),
                        Message.created_at > RoomMember.last_read_at,
                    ),
                )
            )
            .group_by(Message.room_id)
            .subquery()  # Turn this into a subquery (a temporary table) that I can join with the main query.
        )

        # Single query: rooms + unread counts + last message preview, sorted by activity
        rooms = (
            db.query(
                Room,
                func.coalesce(unread_count_subquery.c.unread_count, 0).label(
                    "unread_count"
                ),  # if room = NULL (room  has no unread messages), convert it to 0
                LatestMessage,
            )
            .join(RoomMember, Room.id == RoomMember.room_id)
            .outerjoin(LatestMessage, Room.id == LatestMessage.room_id)
            .outerjoin(
                unread_count_subquery, Room.id == unread_count_subquery.c.room_id
            )
            .options(joinedload(LatestMessage.sender).joinedload(User.profile))
            .filter(RoomMember.user_id == user_id, Room.is_active.is_(True))
            .order_by(LatestMessage.created_at.desc().nullslast())
            .all()
        )

        result = []
        for room, unread_count, last_message in rooms:
            room.unread_count = unread_count
            room.last_message = last_message
            result.append(room)

        return result

    @staticmethod
    # if type is DM and a room already exists between the two users, returns it instead of creating a new one
    def get_or_create_room(
        db: Session,
        user_id: UUID,
        type: str = None,
        name: str = None,
        participant_ids: List[UUID] = None,
    ):
        if participant_ids is None:
            participant_ids = []

        # first check if the participants_ids are valid
        all_user_ids = {user_id}
        all_user_ids.update(participant_ids)

        existing_users = db.query(User.id).filter(User.id.in_(all_user_ids)).all()
        existing_user_ids = {u.id for u in existing_users}

        invalid_ids = all_user_ids - existing_user_ids
        if invalid_ids:
            raise HTTPException(400, f"Invalid user IDs: {invalid_ids}")

        if type == RoomType.DM:
            if len(participant_ids) != 1:
                raise HTTPException(
                    400, "DM must have exactly one participant (the other user)."
                )

            if participant_ids[0] == user_id:
                raise HTTPException(400, "You cannot create a DM with yourself.")

            existing_room = ChatService.get_existing_dm_room(
                db, user_id, participant_ids[0]
            )
            if existing_room:
                return existing_room
            name = None

        if type == RoomType.GROUP and not name:
            raise HTTPException(status_code=400, detail="Group chats must have a name")

        # Create the Room
        new_room = Room(type=type, name=name, creator_id=user_id, is_active=True)
        db.add(new_room)
        db.commit()
        db.refresh(new_room)

        #  Add Members
        db_members = [
            RoomMember(room_id=new_room.id, user_id=uid) for uid in all_user_ids
        ]

        db.add_all(db_members)
        db.commit()

        return new_room

    @staticmethod
    def update_room(db: Session, room_id: UUID, user_id: UUID, room_data):
        room = db.query(Room).filter(Room.id == room_id).first()

        if not room:
            raise HTTPException(404, "Room not found")

        if room.type != RoomType.GROUP:
            raise HTTPException(400, "Can only update group rooms")

        #  Only creator can update
        if room.creator_id != user_id:
            raise HTTPException(403, "Only the room creator can update the room")

        # Update fields
        if room_data.name is not None:
            room.name = room_data.name

        db.commit()
        db.refresh(room)

        return room

    @staticmethod
    def delete_room(db: Session, room_id: UUID, user_id: UUID):
        room = db.query(Room).filter(Room.id == room_id).first()

        if not room:
            raise HTTPException(404, "Room not found")

        if room.type != RoomType.GROUP:
            raise HTTPException(400, "Can only delete group rooms")

        #  Only creator can delete
        if room.creator_id != user_id:
            raise HTTPException(403, "Only the room creator can delete the room")

        # Soft delete
        room.is_active = False

        db.commit()

    @staticmethod
    def get_existing_dm_room(db: Session, user_id: UUID, other_user_id: UUID):
        "find a room of type dm where both users are members"

        query = (
            select(Room)
            .join(RoomMember, Room.id == RoomMember.room_id)
            .where(
                Room.type == RoomType.DM,
                RoomMember.user_id.in_([user_id, other_user_id]),
            )
            .group_by(Room.id)
            .having(func.count(RoomMember.user_id) == 2)
        )

        return db.execute(query).scalars().first()

    @staticmethod
    def get_global_unread_count(db: Session, user_id: UUID):
        count = (
            db.query(func.count(Message.id))
            .join(RoomMember, RoomMember.room_id == Message.room_id)
            .filter(
                RoomMember.user_id == user_id,
                Message.sender_id != user_id,  # own messages are never unread
                or_(
                    RoomMember.last_read_at.is_(
                        None
                    ),  # thats mean he did not open the room
                    Message.created_at > RoomMember.last_read_at,
                ),
            )
            .scalar()  # returns a single value
        )
        return count or 0

    @staticmethod
    def edit_message(db: Session, message_id: UUID, user_id: UUID, new_content: str):
        message = (
            db.query(Message)
            .options(joinedload(Message.sender).joinedload(User.profile))
            .filter(Message.id == message_id)
            .first()
        )

        if not message:
            raise HTTPException(404, "Message not found")

        # only sender can edit

        if message.sender_id != user_id:
            raise HTTPException(403, "You can only edit your own messages")

        # update content
        message.content = new_content
        message.is_edited = True
        db.commit()
        db.refresh(message)

        return message

    @staticmethod
    def delete_message(db: Session, user_id: UUID, message_id: UUID):
        message = db.query(Message).filter(Message.id == message_id).first()
        if not message:
            raise HTTPException(404, "Message not found")
        if message.sender_id != user_id:
            raise HTTPException(403, "You can only edit your own messages")

        message.content = "This message is deleted"
        message.is_deleted = True
        db.commit()
        db.refresh(message)

    @staticmethod
    def add_member(db: Session, room_id: UUID, user_id: UUID, user_to_add_id: UUID):
        room = (
            db.query(Room).filter(Room.id == room_id, Room.is_active.is_(True)).first()
        )
        if not room:
            raise HTTPException(404, "Room not found")

        if room.type != RoomType.GROUP:
            raise HTTPException(400, "You can only add members to group rooms")

        # Change this when group admin roles are added.
        if room.creator_id != user_id:
            raise HTTPException(403, "Only the room creator can add members")

        user_to_add = db.query(User).filter(User.id == user_to_add_id).first()
        if not user_to_add:
            raise HTTPException(404, "User not found")

        existing = (
            db.query(RoomMember)
            .filter(RoomMember.room_id == room_id, RoomMember.user_id == user_to_add_id)
            .first()
        )
        if existing:
            raise HTTPException(409, "User is already a member of this room")

        new_member = RoomMember(room_id=room_id, user_id=user_to_add_id)
        db.add(new_member)
        db.commit()

    @staticmethod
    def remove_member(db: Session, room_id: UUID, creator_id: UUID, user_id: UUID):
        room = db.query(Room).filter(Room.id == room_id).first()

        if not room:
            raise HTTPException(404, "Room not found")

        if room.type != RoomType.GROUP:
            raise HTTPException(400, "Can only remove members from group rooms")

        #  Only creator can remove members (change this when implementing the admins feature )
        if room.creator_id != creator_id:
            raise HTTPException(403, "Only the room creator can remove members")

        # Can't remove the creator
        if user_id == creator_id:
            raise HTTPException(400, "Cannot remove the room creator")

        # Remove member
        member = (
            db.query(RoomMember)
            .filter(RoomMember.room_id == room_id, RoomMember.user_id == user_id)
            .first()
        )

        if not member:
            raise HTTPException(404, "User is not a member of this room")

        db.delete(member)
        db.commit()

    @staticmethod
    def leave_room(db: Session, room_id: UUID, user_id: UUID):
        room = db.query(Room).filter(Room.id == room_id).first()

        if not room:
            raise HTTPException(404, "Room not found")

        if room.type != RoomType.GROUP:
            raise HTTPException(400, "Can only leave group rooms")

        if user_id == room.creator_id:
            raise HTTPException(
                400, "Room creator cannot leave; delete the room instead"
            )

        member = (
            db.query(RoomMember)
            .filter(RoomMember.room_id == room_id, RoomMember.user_id == user_id)
            .first()
        )

        if not member:
            raise HTTPException(404, "You are not a member of this room")

        db.delete(member)
        db.commit()

    @staticmethod
    def get_messages(
        db: Session,
        room_id: UUID,
        user_id: UUID,
        limit: int = 50,
        before_id: Optional[UUID] = None,
    ):
        """
        Get messages from a room with cursor-based pagination.

        Args:
            room_id: The room to fetch messages from
            user_id: The requesting user (for membership validation)
            limit: Number of messages to return (default 50, max 100)
            before_id: Cursor - get messages before this message ID (for loading older messages)

        Returns:
            List of messages ordered by newest first
        """
        # Validate user is member of room
        member = (
            db.query(RoomMember)
            .filter(RoomMember.room_id == room_id, RoomMember.user_id == user_id)
            .first()
        )
        if not member:
            raise HTTPException(404, "You are not a member of this room")

        room = (
            db.query(Room).filter(Room.id == room_id, Room.is_active.is_(True)).first()
        )
        if not room:
            raise HTTPException(404, "Room not found")

        # Limit max page size
        if limit > 100:
            limit = 100

        # Base query: get messages from room, ordered newest first
        query = (
            db.query(Message)
            .options(joinedload(Message.sender).joinedload(User.profile))
            .filter(Message.room_id == room_id)
            .order_by(Message.created_at.desc(), Message.id.desc())
        )

        # Apply cursor if provided (get messages before this ID)
        if before_id:
            cursor_message = db.query(Message).filter(Message.id == before_id).first()
            if not cursor_message:
                raise HTTPException(404, "Cursor message not found")

            # Get messages created before the cursor message
            query = query.filter(
                or_(
                    Message.created_at < cursor_message.created_at,
                    and_(
                        Message.created_at == cursor_message.created_at,
                        Message.id < cursor_message.id,
                    ),
                )
            )

        messages = query.limit(limit).all()
        return messages
