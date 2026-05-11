from app.core.config import settings
from app.repositories.article_repository import ArticleRepository


class CacheService:
    def __init__(self, repository: ArticleRepository) -> None:
        self.repository = repository

    def get_cached_article(self, url: str):
        return self.repository.get_recent_by_url(url, settings.cache_ttl_seconds)
