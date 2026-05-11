from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.article import Article


class ArticleRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_short_code(self, code: str) -> Article | None:
        stmt = select(Article).where(Article.short_code == code)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_recent_by_url(self, url: str, ttl_seconds: int) -> Article | None:
        threshold = datetime.now(timezone.utc) - timedelta(seconds=ttl_seconds)
        stmt = (
            select(Article)
            .where(Article.original_url == url, Article.created_at >= threshold)
            .order_by(Article.created_at.desc())
        )
        return self.db.execute(stmt).scalars().first()

    def create(self, **kwargs) -> Article:
        article = Article(**kwargs)
        self.db.add(article)
        self.db.commit()
        self.db.refresh(article)
        return article

    def list_recent(self, limit: int = 10, user_id: int | None = None) -> list[Article]:
        stmt = select(Article)
        if user_id is not None:
            stmt = stmt.where(Article.user_id == user_id)
        stmt = stmt.order_by(Article.created_at.desc()).limit(limit)
        return list(self.db.execute(stmt).scalars())
