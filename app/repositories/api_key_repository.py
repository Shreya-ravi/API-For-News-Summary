from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.api_key import ApiKey


class ApiKeyRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, user_id: int, name: str, prefix: str, key_hash: str) -> ApiKey:
        api_key = ApiKey(user_id=user_id, name=name, prefix=prefix, key_hash=key_hash)
        self.db.add(api_key)
        self.db.commit()
        self.db.refresh(api_key)
        return api_key

    def get_by_hash(self, key_hash: str) -> ApiKey | None:
        stmt = select(ApiKey).where(ApiKey.key_hash == key_hash, ApiKey.is_active.is_(True))
        return self.db.execute(stmt).scalar_one_or_none()

    def list_for_user(self, user_id: int) -> list[ApiKey]:
        stmt = select(ApiKey).where(ApiKey.user_id == user_id).order_by(ApiKey.created_at.desc())
        return list(self.db.execute(stmt).scalars())

    def touch(self, api_key: ApiKey) -> None:
        api_key.last_used_at = datetime.now(timezone.utc)
        self.db.add(api_key)
        self.db.commit()
