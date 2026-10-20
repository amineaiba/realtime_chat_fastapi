from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ProfileUpdate(BaseModel):
    bio: Optional[str] = Field(None, max_length=500)
    status: Optional[str] = Field(None, max_length=40)
    phone_number: Optional[str] = Field(None, max_length=20)
    date_of_birth: Optional[datetime] = None
    location: Optional[str] = Field(None, max_length=100)


class ProfileResponse(BaseModel):
    id: UUID
    user_id: UUID
    bio: Optional[str]
    avatar_url: Optional[str]
    status: Optional[str]
    phone_number: Optional[str]
    date_of_birth: Optional[datetime]
    location: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True  # Enables reading from profile.id, profile.bio
