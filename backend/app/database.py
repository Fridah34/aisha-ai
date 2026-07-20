from pathlib import Path
from urllib.parse import urlparse, urlunparse
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
import os


env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


DATABASE_URL = os.getenv("DATABASE_URL")


def create_database_if_not_exists():
    """Local-dev convenience only — creates the target database if it's
    missing, so a fresh clone doesn't need a manual `createdb` first.

    Skipped entirely for hosted providers (Neon, and similar) where the
    database is already provisioned and the connecting role typically
    can't run CREATE DATABASE anyway. Detected via hostname rather than
    a hardcoded 'neon.tech' check alone, so any managed host is covered.
    """
    parsed = urlparse(DATABASE_URL)

    # Hosted/managed Postgres — database already exists, nothing to do.
    if parsed.hostname and (
        "neon.tech" in parsed.hostname
        or "supabase" in parsed.hostname
        or "railway" in parsed.hostname
    ):
        print(f"[DB] Hosted database detected ({parsed.hostname}) — skipping auto-create.")
        return

    db_name = parsed.path.lstrip("/")  # correctly ignores ?query=params
    default_parsed = parsed._replace(path="/postgres")
    default_url = urlunparse(default_parsed)

    default_engine = create_engine(default_url, isolation_level="AUTOCOMMIT")

    with default_engine.connect() as conn:
        result = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :db_name"),
            {"db_name": db_name}
        )
        exists = result.fetchone()

        if not exists:
            conn.execute(text(f'CREATE DATABASE "{db_name}"'))
            print(f"Database '{db_name}' created successfully")
        else:
            print(f"Database '{db_name}' already exists")

    default_engine.dispose()


create_database_if_not_exists()

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        
        