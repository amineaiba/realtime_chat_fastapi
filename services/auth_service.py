import logging
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from db_models.user import User
from db_models.token import RefreshToken
from db_models.profile import Profile
from schemas.user import UserCreate
from core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from core.redis_manager import blocklist_token
from core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class AuthService:

    @staticmethod
    def register_user(db: Session, user_data: UserCreate) -> User:
        user_exists = (
            db.query(User)
            .filter(
                (User.email == user_data.email) | (User.username == user_data.username)
            )
            .first()
        )

        if user_exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email or username already registered",
            )

        hashed_psw = hash_password(user_data.password)

        new_user = User(
            username=user_data.username,
            email=user_data.email,
            hashed_password=hashed_psw,
        )

        try:
            db.add(new_user)
            db.commit()
            db.refresh(new_user)

            # Create empty profile automatically
            new_profile = Profile(user_id=new_user.id)
            db.add(new_profile)
            db.commit()
            return new_user
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Registration failed",
            )

    @staticmethod
    def authenticate_user(db: Session, email: str, password: str) -> dict:
        user = db.query(User).filter(User.email == email).first()

        if (
            not user
            or not user.is_active
            or not verify_password(password, user.hashed_password)
        ):
            logger.warning("Failed login attempt for email=%s", email)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        logger.info("User %s logged in", user.id)

        refresh_token = create_refresh_token(data={"sub": str(user.id)})

        expires_at = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )

        db_token = RefreshToken(
            token=refresh_token, expires_at=expires_at, user_id=user.id
        )

        try:
            db.add(db_token)
            db.commit()
            db.refresh(db_token)
        except Exception:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Login failed"
            )

        # Create access token with binding to refresh token
        # (the biding (because for the logout we dont need to logout the user from all sessions (just the current one)))
        access_token = create_access_token(
            data={
                "sub": str(user.id),
                "rt_id": str(db_token.id),
            }
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }

    @staticmethod
    #! add handling for db exceptions
    def refresh_tokens(db: Session, refresh_token: str) -> dict:
        # Decode and validate refresh token
        payload = decode_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=" Invalid or expired refresh token ",
            )

        user_id = payload.get("sub")

        # Find stored refresh token
        stored_token = (
            db.query(RefreshToken).filter(RefreshToken.token == refresh_token).first()
        )

        if not stored_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token not found or revoked",
            )

        # Check if token is expired
        if stored_token.expires_at < datetime.now(timezone.utc):
            try:
                db.delete(stored_token)
                db.commit()
            except Exception:
                db.rollback()
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token expired you must login again",
            )

        # Token Rotation: Issue new refresh token, delete old one
        new_refresh_token = create_refresh_token(data={"sub": user_id})
        expires_at = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )

        # Delete old refresh token (single-use)
        db.delete(stored_token)

        # Create new refresh token in database
        new_db_token = RefreshToken(
            token=new_refresh_token, expires_at=expires_at, user_id=user_id
        )
        try:
            db.add(new_db_token)
            db.commit()
            db.refresh(new_db_token)
        except Exception:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="error while creating new refresh token",
            )

        # Create new access token linked to new refresh token
        new_access_token = create_access_token(
            data={"sub": user_id, "rt_id": str(new_db_token.id)}
        )

        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,  # Return NEW refresh token
            "token_type": "bearer",
        }

    @staticmethod
    async def logout_user(db: Session, access_token: str) -> None:
        # Decode access token to get refresh token ID
        payload = decode_token(access_token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token"
            )

        refresh_token_id = payload.get("rt_id")

        # Find and Delete that SPECIFIC Session
        if refresh_token_id:
            stored_token = (
                db.query(RefreshToken).filter(RefreshToken.id == refresh_token_id)
            ).first()

            if stored_token:
                db.delete(stored_token)
                db.commit()
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token format"
            )

        # Blocklist the access token itself so it can't be reused before it expires
        jti = payload.get("jti")
        exp = payload.get("exp")
        if jti and exp:
            ttl_seconds = exp - int(datetime.now(timezone.utc).timestamp())
            await blocklist_token(jti, ttl_seconds)

    @staticmethod
    def change_user_password(
        db: Session, user: User, old_password: str, new_password: str
    ) -> dict:
        # Verify old password
        if not verify_password(old_password, user.hashed_password):
            raise HTTPException(status_code=400, detail="Incorrect password")

        # Update password
        user.hashed_password = hash_password(new_password)
        db.commit()

        # Logout all devices by deleting all refresh tokens
        # check if this step is neccessary
        db.query(RefreshToken).filter(RefreshToken.user_id == user.id).delete()
        db.commit()

        return {"message": "Password updated"}
