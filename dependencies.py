from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from core.database import get_db
from core.redis_manager import is_token_blocklisted
from core.security import decode_token
from db_models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)], db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_token(token=token)

    if payload is None:
        raise credentials_exception

    user_id: str = payload.get("sub")
    token_type: str = payload.get("type")

    if user_id is None:
        raise credentials_exception

    if token_type != "access":
        raise credentials_exception

    jti: str = payload.get("jti")
    if await is_token_blocklisted(jti):
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise credentials_exception

    return user
