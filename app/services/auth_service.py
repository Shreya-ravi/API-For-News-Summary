import logging

from fastapi import HTTPException
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, decode_access_token, generate_api_key, hash_api_key, hash_password, verify_password
from app.repositories.api_key_repository import ApiKeyRepository
from app.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.api_keys = ApiKeyRepository(db)

    def bootstrap_demo_admin(self) -> None:
        if self.users.has_users():
            return
        logger.info('Bootstrapping demo admin user')
        self.users.create(settings.demo_admin_username, hash_password(settings.demo_admin_password))

    def register_user(self, username: str, password: str):
        if self.users.get_by_username(username):
            raise HTTPException(status_code=400, detail='Username already exists.')
        return self.users.create(username=username, password_hash=hash_password(password))

    def authenticate_user(self, username: str, password: str):
        user = self.users.get_by_username(username)
        if not user or not verify_password(password, user.password_hash):
            raise HTTPException(status_code=401, detail='Invalid credentials.')
        if not user.is_active:
            raise HTTPException(status_code=403, detail='User account is inactive.')
        return user

    def login(self, username: str, password: str) -> tuple[object, str]:
        user = self.authenticate_user(username, password)
        token = create_access_token(str(user.id))
        return user, token

    def get_current_user_from_token(self, token: str):
        try:
            subject = decode_access_token(token)
        except JWTError as exc:
            raise HTTPException(status_code=401, detail='Invalid or expired token.') from exc
        user = self.users.get_by_id(int(subject))
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail='User not found or inactive.')
        return user

    def create_api_key(self, user_id: int, name: str) -> tuple[object, str]:
        raw_key, prefix, key_hash = generate_api_key()
        api_key = self.api_keys.create(user_id=user_id, name=name, prefix=prefix, key_hash=key_hash)
        return api_key, raw_key

    def get_user_by_api_key(self, raw_key: str):
        key_hash = hash_api_key(raw_key)
        api_key = self.api_keys.get_by_hash(key_hash)
        if not api_key:
            raise HTTPException(status_code=401, detail='Invalid API key.')
        self.api_keys.touch(api_key)
        user = self.users.get_by_id(api_key.user_id)
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail='API key owner is invalid.')
        return user
