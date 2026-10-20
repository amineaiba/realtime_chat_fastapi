from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core.database import get_db
from db_models.user import User
from dependencies import get_current_user
from schemas.user import UserSearchOut
from services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", response_model=List[UserSearchOut])
def search_users(
    q: str = Query(..., min_length=2, max_length=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    users = UserService.search_users(db, q, current_user.id)
    return [UserSearchOut.model_validate(user) for user in users]
