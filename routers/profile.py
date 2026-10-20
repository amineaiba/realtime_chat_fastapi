from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.orm import Session

from core.database import get_db
from db_models.user import User
from dependencies import get_current_user
from schemas.profile import ProfileResponse, ProfileUpdate
from services.profile_service import ProfileService

router = APIRouter(prefix="/profile", tags=["Profile"])


@router.get("/me", response_model=ProfileResponse)
def get_my_profile(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    return ProfileService.get_user_profile(db=db, user=current_user)


@router.patch("/me/", response_model=ProfileResponse)
def update_my_profile(
    profile_data: ProfileUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    return ProfileService.update_user_profile(
        db=db, user=current_user, profile_data=profile_data
    )


@router.post("/me/avatar")
def upload_avatar(
    file: Annotated[UploadFile, File()],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    """Upload profile avatar to Cloudinary"""
    avatar_url = ProfileService.upload_avatar(db=db, user=current_user, file=file)
    return {"avatar_url": avatar_url}


@router.delete("/me/avatar", status_code=status.HTTP_204_NO_CONTENT)
def delete_avatar(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    ProfileService.delete_avatar(db=db, user=current_user)
