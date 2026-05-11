from pathlib import Path
import os
from dataclasses import dataclass


BASE_DIR = Path(__file__).resolve().parents[2]


@dataclass
class Settings:
    app_name: str = os.getenv('APP_NAME', 'News Summarizer API')
    secret_key: str = os.getenv('SECRET_KEY', 'change-me-in-production')
    algorithm: str = os.getenv('JWT_ALGORITHM', 'HS256')
    access_token_expire_minutes: int = int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES', '60'))
    database_url: str = os.getenv('DATABASE_URL', 'sqlite:///./news.db')
    cache_ttl_seconds: int = int(os.getenv('CACHE_TTL_SECONDS', '21600'))
    rate_limit_per_minute: int = int(os.getenv('RATE_LIMIT_PER_MINUTE', '20'))
    demo_admin_username: str = os.getenv('DEMO_ADMIN_USERNAME', 'admin')
    demo_admin_password: str = os.getenv('DEMO_ADMIN_PASSWORD', 'admin123')
    log_level: str = os.getenv('LOG_LEVEL', 'INFO')


settings = Settings()
