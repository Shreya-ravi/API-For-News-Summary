import logging

from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.repositories.article_repository import ArticleRepository
from app.services.cache_service import CacheService
from app.services.text_service import build_slug, extract_keywords
from utils import extract_article, summarize_text

logger = logging.getLogger(__name__)


class ArticleService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = ArticleRepository(db)
        self.cache = CacheService(self.repository)

    async def summarize_url(self, url: str, user_id: int | None, short_code_factory) -> object:
        cached = self.cache.get_cached_article(url)
        if cached:
            logger.info('Cache hit for url=%s', url)
            return cached

        data = await run_in_threadpool(extract_article, url)
        if not data['text']:
            raise ValueError('Could not extract full article content from this URL.')

        summaries = await run_in_threadpool(summarize_text, data['text'])
        title = data['title']
        article_text = data['text']
        image = data['image']
        slug = build_slug(url, title)
        keywords = extract_keywords(f'{title} {article_text}')
        short_code = short_code_factory(self.db)

        logger.info('Creating summarized article for url=%s', url)
        return self.repository.create(
            user_id=user_id,
            original_url=url,
            short_code=short_code,
            title=title,
            article_text=article_text,
            image=image,
            slug=slug,
            keywords=keywords,
            english_summary=summaries['english'],
            original_summary=summaries['original'],
            source_language=summaries.get('language'),
        )

    def get_by_short_code(self, code: str):
        return self.repository.get_by_short_code(code)

    def list_recent(self, limit: int = 10, user_id: int | None = None):
        return self.repository.list_recent(limit=limit, user_id=user_id)
