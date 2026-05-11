from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

DATABASE_URL = settings.database_url
connect_args = {'check_same_thread': False} if DATABASE_URL.startswith('sqlite') else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
