import logging

from fastapi import APIRouter, Cookie, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_auth_service
from app.main_support import build_short_url, create_unique_code
from app.services.article_service import ArticleService
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)
router = APIRouter(tags=['Pages'])

def get_templates() -> Jinja2Templates:
    from pathlib import Path
    return Jinja2Templates(directory='Templates' if Path('Templates').exists() else 'templates')


def render_result(templates: Jinja2Templates, request: Request, article):
    return templates.TemplateResponse(
        'result.html',
        {
            'request': request,
            'title': article.title,
            'article_text': article.article_text,
            'summary_english': article.english_summary,
            'summary_original': article.original_summary,
            'image': article.image,
            'slug': article.slug,
            'keywords': article.keywords,
            'short_url': build_short_url(request, article),
        },
    )


@router.get('/', response_class=HTMLResponse)
def login_page(request: Request):
    return get_templates().TemplateResponse('index.html', {'request': request})


@router.post('/login')
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    auth_service: AuthService = Depends(get_auth_service),
):
    templates = get_templates()
    try:
        _, token = auth_service.login(username, password)
    except HTTPException:
        return templates.TemplateResponse('index.html', {'request': request, 'error': 'Invalid credentials'}, status_code=401)
    response = RedirectResponse('/dashboard', status_code=302)
    response.set_cookie(key='access_token', value=token, httponly=True, samesite='lax')
    return response


@router.get('/dashboard', response_class=HTMLResponse)
def dashboard(
    request: Request,
    access_token: str | None = Cookie(default=None),
    auth_service: AuthService = Depends(get_auth_service),
    db: Session = Depends(get_db),
):
    if not access_token:
        return RedirectResponse('/', status_code=302)
    try:
        current_user = auth_service.get_current_user_from_token(access_token)
    except HTTPException:
        return RedirectResponse('/', status_code=302)
    templates = get_templates()
    service = ArticleService(db)
    recent_articles = service.list_recent(limit=10, user_id=current_user.id)
    return templates.TemplateResponse('dashboard.html', {'request': request, 'recent_articles': recent_articles, 'current_user': current_user})


@router.get('/summarize')
def summarize_page_redirect(
    access_token: str | None = Cookie(default=None),
    auth_service: AuthService = Depends(get_auth_service),
):
    if not access_token:
        return RedirectResponse('/', status_code=302)
    try:
        auth_service.get_current_user_from_token(access_token)
    except HTTPException:
        return RedirectResponse('/', status_code=302)
    return RedirectResponse('/dashboard', status_code=302)


@router.post('/summarize')
async def summarize(
    request: Request,
    url: str = Form(...),
    access_token: str | None = Cookie(default=None),
    auth_service: AuthService = Depends(get_auth_service),
    db: Session = Depends(get_db),
):
    templates = get_templates()
    if not access_token:
        return RedirectResponse('/', status_code=302)
    try:
        current_user = auth_service.get_current_user_from_token(access_token)
    except HTTPException:
        return RedirectResponse('/', status_code=302)
    service = ArticleService(db)
    try:
        article = await service.summarize_url(url, current_user.id, create_unique_code)
        return render_result(templates, request, article)
    except Exception as exc:
        logger.exception('Summarize page failed')
        recent_articles = service.list_recent(limit=10, user_id=current_user.id)
        return templates.TemplateResponse('dashboard.html', {'request': request, 'error': str(exc), 'recent_articles': recent_articles, 'current_user': current_user}, status_code=400)


@router.get('/s/{code}', response_class=HTMLResponse, name='redirect_short_url')
def redirect_short_url(request: Request, code: str, db: Session = Depends(get_db)):
    templates = get_templates()
    service = ArticleService(db)
    article = service.get_by_short_code(code)
    if not article:
        return templates.TemplateResponse('dashboard.html', {'request': request, 'error': 'Invalid URL'}, status_code=404)
    return render_result(templates, request, article)


@router.get('/logout')
def logout():
    response = RedirectResponse(url='/', status_code=302)
    response.delete_cookie('access_token')
    return response
