"""Fill an empty database with demo users, rooms, and messages.

Run it inside the backend container:
    docker compose exec backend python -m scripts.seed_demo

Every demo account uses the password "Password1".
Running it twice does nothing: it stops if the demo users already exist.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from core.database import SessionLocal
from db_models.chat import Message, MessageType, RoomMember, RoomType
from db_models.user import User
from schemas.user import UserCreate
from services.auth_service import AuthService
from services.chat_services import ChatService

PASSWORD = "Password1"

USERS = {
    "sara": {
        "status": "Shipping the chat API",
        "bio": "Backend developer. Python, FastAPI, PostgreSQL.",
        "location": "Algiers",
    },
    "yacine": {
        "status": "In a meeting",
        "bio": "Frontend and design.",
        "location": "Oran",
    },
    "lina": {
        "status": "Writing tests",
        "bio": "QA and automation.",
        "location": "Constantine",
    },
}

# (sender, message, minutes ago)
GROUP_MESSAGES = [
    ("yacine", "Morning! Is the new room list ready?", 95),
    ("sara", "Almost. It sorts by the latest message now.", 92),
    ("sara", "Unread counts come from one query, no N+1.", 91),
    ("lina", "Nice. I'll add tests for the unread count.", 80),
    ("yacine", "Can we show who is online in the header?", 45),
    ("sara", "Yes, presence is in Redis, so it works across workers.", 43),
    ("lina", "Refresh token rotation passed all my checks", 12),
    ("yacine", "Great work, let's ship it today", 3),
]

DM_MESSAGES = [
    ("yacine", "Do you have a minute to review my PR?", 30),
    ("sara", "Sure, send me the link", 28),
    ("yacine", "Thanks! It's the profile page one.", 27),
]


def create_users(db: Session) -> dict[str, User]:
    users = {}
    for username, profile_data in USERS.items():
        user = AuthService.register_user(
            db,
            UserCreate(
                username=username, email=f"{username}@example.com", password=PASSWORD
            ),
        )
        for field, value in profile_data.items():
            setattr(user.profile, field, value)
        users[username] = user
    db.commit()
    return users


def add_messages(db: Session, room_id, users: dict[str, User], messages: list) -> None:
    now = datetime.now(timezone.utc)
    for sender, content, minutes_ago in messages:
        db.add(
            Message(
                room_id=room_id,
                sender_id=users[sender].id,
                content=content,
                type=MessageType.TEXT,
                created_at=now - timedelta(minutes=minutes_ago),
            )
        )
    db.commit()


def mark_read(db: Session, room_id, user: User, minutes_ago: int) -> None:
    member = db.query(RoomMember).filter_by(room_id=room_id, user_id=user.id).one()
    member.last_read_at = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
    db.commit()


def main() -> None:
    db = SessionLocal()
    try:
        if db.query(User).filter(User.username.in_(USERS)).first():
            print("Demo users already exist, nothing to do.")
            return

        users = create_users(db)
        sara, yacine, lina = users["sara"], users["yacine"], users["lina"]

        group = ChatService.get_or_create_room(
            db, sara.id, RoomType.GROUP, "Backend team", [yacine.id, lina.id]
        )
        add_messages(db, group.id, users, GROUP_MESSAGES)

        dm = ChatService.get_or_create_room(db, yacine.id, RoomType.DM, None, [sara.id])
        add_messages(db, dm.id, users, DM_MESSAGES)

        # Leave a few unread messages so the badges show up.
        mark_read(db, group.id, sara, 40)
        mark_read(db, dm.id, sara, 29)

        print("Seeded: sara, yacine, lina (password: Password1)")
    finally:
        db.close()


if __name__ == "__main__":
    main()
