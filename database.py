import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase


class Base(DeclarativeBase):
    pass


def get_engine():
    database_url = os.getenv("POSTGRES_URL")
    secret = os.getenv("SECRET_KEY")
    print(f"POSTGRES_URL found: {database_url is not None}")
    print(f"SECRET_KEY found: {secret is not None}")
    print(f"All env var names: {[k for k in os.environ.keys()]}")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is not set")
    return create_engine(database_url)


engine = get_engine()
SessionLocal = sessionmaker(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
