import re
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    # "..." means Required!
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)

    @field_validator(
        "username"
    )  # the field_validator make sure the func is executed before acepting the username
    # cls is the class itself (UserCreate)
    # v is the value being validated
    def username_alphanumeric(cls, v):
        if not re.match(r"^[a-zA-Z0-9_]+$", v):
            raise ValueError(
                "username must be alphanumeric (letter, numbers, underscore)"
            )
        return v

    @field_validator("password")
    def password_strength(cls, v):
        if not re.search(r"[A-Z]", v):
            raise ValueError("Must contain uppercase letter")
        if not re.search(r"[0-9]", v):
            raise ValueError("Must contain number")
        return v


class UserOut(BaseModel):
    id: UUID
    username: str
    email: EmailStr
    avatar_url: Optional[str] = None
    created_at: datetime
    is_active: bool

    class Config:
        # from_attributs = True means that we are allowing pydantic to convert orm models (db obj) to pydantic model
        from_attributes = True


class UserSearchOut(BaseModel):
    id: UUID
    username: str
    avatar_url: Optional[str] = None

    class Config:
        from_attributes = True


class PasswordChange(BaseModel):
    old_password: str = Field(..., min_length=8)
    new_password: str = Field(..., min_length=8)

    @field_validator("new_password")
    def password_strength(cls, v):
        if not re.search(r"[A-Z]", v):
            raise ValueError("Must contain uppercase letter")
        if not re.search(r"[0-9]", v):
            raise ValueError("Must contain number")
        return v
