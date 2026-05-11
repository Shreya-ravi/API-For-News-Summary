from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import api_rate_limit, get_current_user_api
from app.schemas import ArticleDetailResponse, HealthResponse, HistoryItemResponse, SummarizeRequest, SummarizeResponse
from app.services.article_service import ArticleService
from app.services.auth_service import AuthService
from app.main_support import build_short_url, create_unique_code, serialize_article, serialize_history_item

router = APIRouter(prefix='/api', tags=['Articles'])


@router.get('/health', response_model=HealthResponse)
def health_check():
    return HealthResponse(status='ok', service='news-summarizer')


@router.post('/summarize', response_model=SummarizeResponse, dependencies=[Depends(api_rate_limit)])
async def summarize_api(
    payload: SummarizeRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_api),
):
    service = ArticleService(db)
    try:
        article = await service.summarize_url(str(payload.url), current_user.id, create_unique_code)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail='Unexpected summarization error.') from exc
    return SummarizeResponse(**serialize_article(request, article).model_dump(exclude={'original_url'}))


@router.get('/article/{code}', response_model=ArticleDetailResponse, dependencies=[Depends(api_rate_limit)])
def get_article(code: str, request: Request, db: Session = Depends(get_db), current_user=Depends(get_current_user_api)):
    service = ArticleService(db)
    article = service.get_by_short_code(code)
    if not article:
        raise HTTPException(status_code=404, detail='Article not found.')
    return serialize_article(request, article)


@router.get('/history', response_model=list[HistoryItemResponse], dependencies=[Depends(api_rate_limit)])
def get_history(request: Request, limit: int = 10, db: Session = Depends(get_db), current_user=Depends(get_current_user_api)):
    service = ArticleService(db)
    articles = service.list_recent(limit=limit, user_id=current_user.id)
    return [serialize_history_item(request, article) for article in articles]
