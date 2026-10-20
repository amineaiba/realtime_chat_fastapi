import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError

from core.database import SessionLocal
from core.redis_manager import is_token_blocklisted, set_user_offline, set_user_online
from core.security import decode_token
from core.socket_manager import sio
from db_models.chat import Message, RoomMember
from db_models.user import User
from sockets.helpers import (
    get_active_membership,
    get_online_users_in_room,
    get_user_rooms,
)

logger = logging.getLogger(__name__)


async def handle_connect(sid, environ, auth):
    # Extract Token — only from the auth payload, never the query string
    # (query params leak into server/proxy access logs and browser history)
    token = auth.get("token") if auth else None

    if not token:
        return False

    # Validate Token
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        return False

    # Same rule as REST: a logged-out access token can't open a socket.
    if await is_token_blocklisted(payload.get("jti")):
        return False

    user_id = payload.get("sub")
    if not user_id:
        return False

    with SessionLocal() as db:
        user = db.get(User, UUID(user_id))
        if user is None or not user.is_active:
            return False

    #  Save Session
    await sio.save_session(sid, {"user_id": user_id})
    logger.info("User %s connected", user_id)

    await set_user_online(user_id)

    # Tell every room the user belongs to that they came online
    db = SessionLocal()
    try:
        rooms = await get_user_rooms(user_id, db)

        # Broadcast user_online to all their rooms
        for room_id in rooms:
            await sio.emit(
                "user_online",
                {"user_id": str(user_id), "message": "User came online"},
                to=room_id,
            )
    finally:
        db.close()
    return True


async def handle_disconnect(sid):
    """Handle user disconnecting"""
    db = None
    try:
        session = await sio.get_session(sid)
        user_id = session.get("user_id")

        if not user_id:
            return

        # Mark user offline in Redis
        await set_user_offline(user_id)

        #  Get all rooms user was member of

        db = SessionLocal()
        try:
            rooms = await get_user_rooms(user_id, db)

            # Broadcast user_offline to all their rooms
            for room_id in rooms:
                await sio.emit(
                    "user_offline",
                    {"user_id": str(user_id), "message": "User went offline"},
                    to=room_id,
                )
        finally:
            db.close()

        logger.info("User %s disconnected", user_id)

    except Exception:
        logger.exception("Error in disconnect")


async def handle_join_room(sid, data):
    """Handle user joining a room"""

    db = None
    try:
        session = await sio.get_session(sid)
        user_id = session.get("user_id")

        if not user_id:
            await sio.emit("error", {"message": "unauthorized"}, to=sid)
            return

        room_id = data.get("room_id")
        if not room_id:
            await sio.emit("error", {"message": "room_id is required"}, to=sid)
            return

        try:
            UUID(room_id)  # Will throw if invalid UUID
        except ValueError:
            await sio.emit("error", {"message": "Invalid room_id format"}, to=sid)
            return

        # Validate membership

        db = SessionLocal()
        try:
            member = get_active_membership(db, room_id, user_id)

            if not member:
                await sio.emit(
                    "error", {"message": "You are not a member of this room"}, to=sid
                )
                return

            # Update last_read_at (mark as read)

            member.last_read_at = datetime.now(timezone.utc)
            db.commit()

            # Join the SocketIO room
            await sio.enter_room(sid, str(room_id))

            #  Get online users
            online_users = await get_online_users_in_room(room_id, db)

            # Send confirmation
            await sio.emit(
                "room_joined",
                {
                    "room_id": str(room_id),
                    "message": "Successfully joined room",
                    "online_users": online_users,
                },
                to=sid,
            )

            logger.debug("User %s joined room %s", user_id, room_id)

        except SQLAlchemyError:
            logger.exception("Database error in join_room")
            await sio.emit("error", {"message": "Database error occurred"}, to=sid)

        finally:
            if db:
                db.close()

    except Exception:
        logger.exception("Error in join_room")
        await sio.emit("error", {"message": "Failed to join room"}, to=sid)


async def handle_leave_room(sid, data):
    """Handle user leaving a room"""
    db = None
    try:
        session = await sio.get_session(sid)
        user_id = session.get("user_id")

        if not user_id:
            await sio.emit("error", {"message": "unauthorized"}, to=sid)
            return

        room_id = data.get("room_id")
        if not room_id:
            await sio.emit("error", {"message": "room_id is required"}, to=sid)
            return

        # Validate membership before leaving

        db = SessionLocal()
        try:
            member = (
                db.query(RoomMember)
                .filter(RoomMember.room_id == room_id, RoomMember.user_id == user_id)
                .first()
            )

            if not member:
                await sio.emit(
                    "error", {"message": "You are not a member of this room"}, to=sid
                )
                return

            # Leave the SocketIO room
            await sio.leave_room(sid, str(room_id))

            # Send confirmation
            await sio.emit(
                "room_left",
                {"room_id": str(room_id), "message": "Successfully left room"},
                to=sid,
            )

            logger.debug("User %s left room %s", user_id, room_id)
        except SQLAlchemyError:
            logger.exception("Database error in leave_room")
            await sio.emit("error", {"message": "Database error occurred"}, to=sid)

        finally:
            if db:
                db.close()

    except Exception:
        logger.exception("Error in leave_room")
        await sio.emit("error", {"message": "Failed to leave room"}, to=sid)


async def handle_send_message(sid, data):
    db = None

    try:
        session = await sio.get_session(sid)
        user_id = session.get("user_id")

        if not user_id:
            await sio.emit("error", {"message": "unauthorized"}, to=sid)
            return

        room_id = data.get("room_id")
        content = data.get("content")

        if not room_id:
            await sio.emit("error", {"message": "room_id is required"}, to=sid)
            return

        if not content:
            await sio.emit("error", {"message": "content is required"}, to=sid)
            return

        if len(content.strip()) == 0:
            await sio.emit(
                "error", {"message": "message content cannot be empty"}, to=sid
            )
            return

        # Validate UUID format
        try:
            UUID(room_id)
        except ValueError:
            await sio.emit("error", {"message": "Invalid room_id format"}, to=sid)
            return

        # Database operations

        db = SessionLocal()
        try:
            # Check if user is member of room
            member = get_active_membership(db, room_id, user_id)

            if not member:
                await sio.emit(
                    "error", {"message": "You are not a member of this room"}, to=sid
                )
                return

            # Create message
            message = Message(
                room_id=room_id,
                sender_id=user_id,
                content=content.strip(),
                created_at=datetime.now(timezone.utc),
            )

            db.add(message)
            db.commit()
            db.refresh(message)

            # Broadcast to room
            await sio.emit(
                "new_message",
                {
                    "id": str(message.id),
                    "room_id": str(message.room_id),
                    "user_id": str(message.sender_id),
                    "content": message.content,
                    "created_at": message.created_at.isoformat(),
                },
                to=str(room_id),  # Send to all in room
            )

            logger.debug("User %s sent message to room %s", user_id, room_id)

        except SQLAlchemyError:
            logger.exception("Database error in send_message")
            db.rollback()
            await sio.emit("error", {"message": "Failed to send message"}, to=sid)

        finally:
            if db:
                db.close()

    except Exception:
        logger.exception("Error in send_message")
        await sio.emit("error", {"message": "Failed to send message"}, to=sid)


async def handle_get_online_users(sid, data):
    """Handle request to get online users in a room"""
    db = None
    try:
        session = await sio.get_session(sid)
        user_id = session.get("user_id")

        if not user_id:
            await sio.emit("error", {"message": "unauthorized"}, to=sid)
            return

        room_id = data.get("room_id")
        if not room_id:
            await sio.emit("error", {"message": "room_id is required"}, to=sid)
            return

        # Validate UUID format
        try:
            UUID(room_id)
        except ValueError:
            await sio.emit("error", {"message": "Invalid room_id format"}, to=sid)
            return

        db = SessionLocal()

        online_users = await get_online_users_in_room(room_id, db)

        await sio.emit(
            "online_users", {"room_id": str(room_id), "users": online_users}, to=sid
        )

        logger.debug("User %s requested online users for room %s", user_id, room_id)

    except Exception:
        logger.exception("Error in get_online_users")
        await sio.emit("error", {"message": "Failed to get online users"}, to=sid)

    finally:
        if db:
            db.close()


async def handle_typing_start(sid, data):
    """
    Handle user starting to type.
    Broadcasts typing indicator to other users in the room.
    """
    db = None
    try:
        session = await sio.get_session(sid)
        user_id = session.get("user_id")

        if not user_id:
            await sio.emit("error", {"message": "Unauthorized"}, to=sid)
            return

        room_id = data.get("room_id")
        if not room_id:
            await sio.emit("error", {"message": "room_id is required"}, to=sid)
            return

        # Validate UUID format
        try:
            room_id = UUID(room_id)
        except ValueError:
            await sio.emit("error", {"message": "Invalid room_id format"}, to=sid)
            return

        db = SessionLocal()

        # Validate user is member of room
        member = get_active_membership(db, room_id, user_id)

        if not member:
            await sio.emit("error", {"message": "Not a member of this room"}, to=sid)
            return

        # Get user info for display
        user = db.query(User).filter(User.id == user_id).first()

        # Broadcast to room (excluding sender)
        await sio.emit(
            "user_typing",
            {
                "room_id": str(room_id),
                "user_id": str(user_id),
                "username": user.username if user else "Unknown",
                "is_typing": True,
            },
            room=str(room_id),
            skip_sid=sid,  # Don't send back to sender
        )

        logger.debug("User %s started typing in room %s", user_id, room_id)

    except Exception:
        logger.exception("Error in typing_start")
        await sio.emit(
            "error", {"message": "Failed to broadcast typing status"}, to=sid
        )

    finally:
        if db:
            db.close()


async def handle_typing_stop(sid, data):
    """
    Handle user stopping typing.
    Broadcasts typing stop indicator to other users in the room.
    """
    db = None
    try:
        session = await sio.get_session(sid)
        user_id = session.get("user_id")

        if not user_id:
            await sio.emit("error", {"message": "Unauthorized"}, to=sid)
            return

        room_id = data.get("room_id")
        if not room_id:
            await sio.emit("error", {"message": "room_id is required"}, to=sid)
            return

        # Validate UUID format
        try:
            room_id = UUID(room_id)
        except ValueError:
            await sio.emit("error", {"message": "Invalid room_id format"}, to=sid)
            return

        db = SessionLocal()

        # Validate user is member of room
        member = get_active_membership(db, room_id, user_id)

        if not member:
            await sio.emit("error", {"message": "Not a member of this room"}, to=sid)
            return

        # Get user info for display
        user = db.query(User).filter(User.id == user_id).first()

        # Broadcast to room (excluding sender)
        await sio.emit(
            "user_typing",
            {
                "room_id": str(room_id),
                "user_id": str(user_id),
                "username": user.username if user else "Unknown",
                "is_typing": False,
            },
            room=str(room_id),
            skip_sid=sid,  # Don't send back to sender
        )

        logger.debug("User %s stopped typing in room %s", user_id, room_id)

    except Exception:
        logger.exception("Error in typing_stop")
        await sio.emit(
            "error", {"message": "Failed to broadcast typing status"}, to=sid
        )

    finally:
        if db:
            db.close()
