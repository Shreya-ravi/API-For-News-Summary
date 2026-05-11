import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.logging import setup_logging
from app.db.base import Base
from app.db.session import engine, SessionLocal
from app.routers import articles, auth, pages
from app.services.auth_service import AuthService

setup_logging()
logger = logging.getLogger(__name__)


def create_application() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        description='API for extracting news articles, generating multilingual summaries, and resolving short URLs.',
        version='2.0.0',
    )
    app.mount('/static', StaticFiles(directory='static'), name='static')
    Base.metadata.create_all(bind=engine)

    @app.on_event('startup')
    def startup() -> None:
        db = SessionLocal()
        try:
            AuthService(db).bootstrap_demo_admin()
        finally:
            db.close()

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception('Unhandled error at %s', request.url.path)
        if request.url.path.startswith('/api/'):
            return JSONResponse(status_code=500, content={'detail': 'Internal server error'})
        return JSONResponse(status_code=500, content={'detail': 'Internal server error'})

    app.include_router(auth.router)
    app.include_router(articles.router)
    app.include_router(pages.router)
    return app


app = create_application()
