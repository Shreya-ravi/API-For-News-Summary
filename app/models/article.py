from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.session import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Article(Base):
    __tablename__ = 'articles'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    original_url = Column(String(1000), nullable=False, index=True)
    short_code = Column(String(32), unique=True, index=True, nullable=False)
    title = Column(String(500), nullable=False)
    article_text = Column(Text, nullable=False)
    image = Column(String(1000), nullable=True)
    slug = Column(String(500), nullable=False)
    keywords = Column(Text, nullable=True)
    english_summary = Column(Text, nullable=False)
    original_summary = Column(Text, nullable=False)
    source_language = Column(String(16), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    user = relationship('User', back_populates='articles')
