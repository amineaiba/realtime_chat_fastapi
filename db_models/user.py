import uuid

from sqlalchemy import Boolean, Column, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    profile = relationship(
        "Profile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    tokens = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )

    @property
    def avatar_url(self) -> str | None:
        return self.profile.avatar_url if self.profile else None
