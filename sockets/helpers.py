from core.database import SessionLocal
from db_models.chat import Room, RoomMember


async def get_user_rooms(user_id: str, db=None):
    """Get all room IDs where user is a member"""
    if db is None:
        db = SessionLocal()
        close_db = True
    else:
        close_db = False

    try:
        members = db.query(RoomMember).filter(RoomMember.user_id == user_id).all()
        room_ids = [str(member.room_id) for member in members]

        return room_ids

    finally:
        if close_db:
            db.close()


async def get_online_users_in_room(room_id: str, db=None):
    """Get list of online user IDs in a specific room"""
    if db is None:
        db = SessionLocal()
        close_db = True
    else:
        close_db = False

    try:
        from core.redis_manager import is_user_online
        from db_models.chat import RoomMember

        members = db.query(RoomMember).filter(RoomMember.room_id == room_id).all()

        online_users = []
        for member in members:
            if await is_user_online(member.user_id):
                online_users.append(str(member.user_id))

        return online_users

    finally:
        if close_db:
            db.close()


def get_active_membership(db, room_id: str, user_id: str) -> RoomMember | None:
    """The user's membership in a room, or None if not a member or the room is deleted."""
    return (
        db.query(RoomMember)
        .join(Room, Room.id == RoomMember.room_id)
        .filter(
            RoomMember.room_id == room_id,
            RoomMember.user_id == user_id,
            Room.is_active.is_(True),
        )
        .first()
    )
