from typing import List
from uuid import UUID

from sqlalchemy.orm import Session, joinedload

from db_models.user import User


class UserService:
    @staticmethod
    def search_users(
        db: Session, query: str, current_user_id: UUID, limit: int = 25
    ) -> List[User]:
        return (
            db.query(User)
            .options(joinedload(User.profile))
            .filter(
                User.username.ilike(f"%{query}%"),
                User.id != current_user_id,
                User.is_active.is_(True),
            )
            .limit(limit)
            .all()
        )
