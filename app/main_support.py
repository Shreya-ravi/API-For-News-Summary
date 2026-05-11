from fastapi import Request
from sqlalchemy.orm import Session

from app.models import Article
from app.repositories.article_repository import ArticleRepository
from app.schemas import ArticleDetailResponse, HistoryItemResponse
from utils import generate_short_code


def create_unique_code(db: Session):
    repository = ArticleRepository(db)
    while True:
        code = generate_short_code()
        if not repository.get_by_short_code(code):
            return code


def build_short_url(request: Request, article: Article):
    return request.url_for('redirect_short_url', code=article.short_code)


def serialize_article(request: Request, article: Article) -> ArticleDetailResponse:
    return ArticleDetailResponse(
        original_url=article.original_url or '',
        title=article.title or '',
        image=article.image or '',
        article_text=article.article_text or '',
        summary_english=article.english_summary or '',
        summary_original=article.original_summary or '',
        slug=article.slug or '',
        keywords=article.keywords or '',
        short_url=build_short_url(request, article),
        short_code=article.short_code or '',
    )


def serialize_history_item(request: Request, article: Article) -> HistoryItemResponse:
    return HistoryItemResponse(
        title=article.title or '',
        slug=article.slug or '',
        short_code=article.short_code or '',
        short_url=build_short_url(request, article),
        summary_english=article.english_summary or '',
    )
