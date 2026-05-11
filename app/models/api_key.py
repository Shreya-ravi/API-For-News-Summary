from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db.session import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ApiKey(Base):
    __tablename__ = 'api_keys'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    prefix = Column(String(16), nullable=False, index=True)
    key_hash = Column(String(255), nullable=False, unique=True)
    is_active = Column(Boolean, default=True, nullable=False)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    user = relationship('User', back_populates='api_keys')
