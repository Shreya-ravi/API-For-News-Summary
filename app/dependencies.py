from typing import Optional

from fastapi import Cookie, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.rate_limiter import rate_limiter
from app.db.session import get_db
from app.services.auth_service import AuthService


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(db)


def extract_bearer_token(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(' ')
    if scheme.lower() != 'bearer' or not token:
        return None
    return token


def get_current_user_api(
    authorization: Optional[str] = Header(default=None),
    x_api_key: Optional[str] = Header(default=None),
    auth_service: AuthService = Depends(get_auth_service),
):
    token = extract_bearer_token(authorization)
    if token:
        return auth_service.get_current_user_from_token(token)
    if x_api_key:
        return auth_service.get_user_by_api_key(x_api_key)
    raise HTTPException(status_code=401, detail='Authentication required.')


def get_current_user_web(
    access_token: Optional[str] = Cookie(default=None),
    auth_service: AuthService = Depends(get_auth_service),
):
    if not access_token:
        raise HTTPException(status_code=401, detail='Authentication required.')
    return auth_service.get_current_user_from_token(access_token)


def api_rate_limit(request: Request) -> None:
    client = request.client.host if request.client else 'unknown'
    rate_limiter.check(f'api:{client}:{request.url.path}', settings.rate_limit_per_minute)
