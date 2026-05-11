from datetime import datetime, timedelta, timezone
import hashlib
import secrets

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return pwd_context.verify(password, hashed_password)


def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {'sub': subject, 'exp': expire}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> str:
    payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    subject = payload.get('sub')
    if not subject:
        raise JWTError('Token subject missing')
    return subject


def generate_api_key() -> tuple[str, str, str]:
    raw = secrets.token_urlsafe(32)
    prefix = raw[:8]
    key_hash = hashlib.sha256(raw.encode('utf-8')).hexdigest()
    return raw, prefix, key_hash


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode('utf-8')).hexdigest()
