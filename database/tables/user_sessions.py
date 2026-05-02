from uuid import UUID
from datetime import datetime
from litestar.plugins.sqlalchemy import UUIDAuditBase
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, String, Text, DateTime

class User(UUIDAuditBase):
    __tablename__ = "user_account"
    
    username: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    salt_uuid: Mapped[UUID] = mapped_column(nullable=False)

    sessions: Mapped[list["Session"]] = relationship(back_populates="user", cascade="all, delete-orphan")

class Session(UUIDAuditBase):
    __tablename__ = "user_session"
    
    token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("user_account.id"), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    user: Mapped["User"] = relationship(back_populates="sessions")
