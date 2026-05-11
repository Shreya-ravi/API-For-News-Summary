from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_auth_service, get_current_user_api
from app.schemas import ApiKeyCreateRequest, ApiKeyResponse, LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix='/api/auth', tags=['Auth'])


@router.post('/register', response_model=UserResponse)
def register(payload: RegisterRequest, auth_service: AuthService = Depends(get_auth_service)):
    user = auth_service.register_user(payload.username, payload.password)
    return UserResponse(id=user.id, username=user.username)


@router.post('/login', response_model=TokenResponse)
def login(payload: LoginRequest, auth_service: AuthService = Depends(get_auth_service)):
    _, token = auth_service.login(payload.username, payload.password)
    return TokenResponse(access_token=token)


@router.post('/api-keys', response_model=ApiKeyResponse)
def create_api_key(
    payload: ApiKeyCreateRequest,
    current_user=Depends(get_current_user_api),
    auth_service: AuthService = Depends(get_auth_service),
):
    api_key, raw_key = auth_service.create_api_key(current_user.id, payload.name)
    return ApiKeyResponse(name=api_key.name, prefix=api_key.prefix, api_key=raw_key)
