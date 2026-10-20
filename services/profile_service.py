import logging

import cloudinary.uploader
from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from db_models.profile import Profile
from db_models.user import User
from schemas.profile import ProfileUpdate

logger = logging.getLogger(__name__)

MAX_AVATAR_SIZE = 5 * 1024 * 1024  # 5 MB

# Magic-byte signatures for the image formats we accept — checked against the
# actual file content, since the client-supplied content_type header can be spoofed.
IMAGE_SIGNATURES = {
    b"\xff\xd8\xff": "jpeg",
    b"\x89PNG\r\n\x1a\n": "png",
    b"GIF87a": "gif",
    b"GIF89a": "gif",
    b"RIFF": "webp",  # followed by "WEBP" at offset 8, checked separately
}


def _sniff_image_format(header: bytes) -> str | None:
    for signature, fmt in IMAGE_SIGNATURES.items():
        if header.startswith(signature):
            if fmt == "webp" and header[8:12] != b"WEBP":
                continue
            return fmt
    return None


class ProfileService:
    @staticmethod
    def get_user_profile(db: Session, user: User) -> Profile:
        profile = db.query(Profile).filter(Profile.user_id == user.id).first()

        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found "
            )

        return profile

    @staticmethod
    def update_user_profile(
        db: Session, user: User, profile_data: ProfileUpdate
    ) -> Profile:
        profile = db.query(Profile).filter(Profile.user_id == user.id).first()

        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
            )

        update_data = profile_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(profile, field, value)

        try:
            db.commit()
            db.refresh(profile)
            return profile
        except Exception:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update profile",
            )

    @staticmethod
    def upload_avatar(db: Session, user: User, file: UploadFile) -> str:
        contents = file.file.read(MAX_AVATAR_SIZE + 1)

        if len(contents) > MAX_AVATAR_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File too large, max {MAX_AVATAR_SIZE // (1024 * 1024)}MB",
            )

        if _sniff_image_format(contents[:12]) is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must be a valid JPEG, PNG, GIF, or WEBP image",
            )

        file.file.seek(0)

        profile = db.query(Profile).filter(Profile.user_id == user.id).first()

        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
            )

        try:
            result = cloudinary.uploader.upload(
                file.file,
                folder="chat_app/avatars",
                public_id=f"user_{user.id}",
                overwrite=True,
                resource_type="image",
            )
            profile.avatar_url = result.get("secure_url")
            db.commit()
            db.refresh(profile)
            return profile.avatar_url

        except Exception as e:
            db.rollback()
            logger.error("Avatar upload failed for user %s: %s", user.id, e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Avatar upload failed",
            )

    @staticmethod
    def delete_avatar(db: Session, user: User) -> None:
        profile = db.query(Profile).filter(Profile.user_id == user.id).first()

        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
            )

        if profile.avatar_url:
            try:
                cloudinary.uploader.destroy(f"chat_app/avatars/user_{user.id}")
            except Exception as e:
                logger.error(
                    "Cloudinary avatar delete failed for user %s: %s", user.id, e
                )

        profile.avatar_url = None

        try:
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error("Avatar delete failed for user %s: %s", user.id, e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Avatar delete failed",
            )
