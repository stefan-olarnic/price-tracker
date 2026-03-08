import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase


class Base(DeclarativeBase):
    pass


def get_engine():
    database_url = os.getenv("DATABASE_URL")
    secret = os.getenv("SECRET_KEY")

    print(f"DATABASE_URL found: {database_url is not None}")
    print(f"SECRET_KEY found: {secret is not None}")
    print(f"All env var names: {[k for k in os.environ.keys()]}")

    if not database_url:
        raise ValueError("DATABASE_URL environment variable is not set")

    # Fix pentru unele platforme care folosesc postgres://
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    return create_engine(database_url)


engine = get_engine()
SessionLocal = sessionmaker(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
