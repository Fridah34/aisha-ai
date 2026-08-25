# Enable modern string-based type hinting to prevent version evaluation crashes
from __future__ import annotations

import logging
import re
from collections.abc import AsyncGenerator, Generator
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

# Import database core engines and session managers
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# Import centralized application settings
from app.config import settings

# ==============================================================================
# LOGGING SETUP
# ==============================================================================
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO if settings.ENVIRONMENT == "production" else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
# Silence noisy third-party libraries at DEBUG. Left at root DEBUG in dev,
# these dump full HTTP request/response bodies (Groq + Twilio API payloads,
# connection-pool internals) on every call, burying the app's own
# [Webhook]/[Twilio]/[Redis] prints that actually matter for debugging.
for noisy_logger in (
    "httpx",
    "httpcore",
    "urllib3",
    "twilio.http_client",
    "groq",
    "hpack",
    "redis",
):
    logging.getLogger(noisy_logger).setLevel(logging.WARNING)

# ==============================================================================
# CONNECTION PATH CONFIGURATION
# ==============================================================================
raw_url = settings.RAW_DATABASE_URL

# 1. Standardize protocol for asyncpg
if raw_url.startswith("postgres://"):
    raw_url = raw_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif raw_url.startswith("postgresql://") and not raw_url.startswith(
    "postgresql+asyncpg://"
):
    raw_url = raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)

# 2. Strip libpq-specific query parameters that cause asyncpg TypeErrors
parsed = urlparse(raw_url)
query_params = parse_qs(parsed.query)

# Remove all libpq parameters asyncpg doesn't support
FORBIDDEN_PARAMS = [
    "sslmode",
    "ssl",
    "channel_binding",
    "gssencmode",
    "target_session_attrs",
]
for param in FORBIDDEN_PARAMS:
    query_params.pop(param, None)

cleaned_query = urlencode(query_params, doseq=True)
ASYNC_DATABASE_URL = urlunparse(
    (
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        cleaned_query,
        parsed.fragment,
    )
)

# Clean URL for synchronous SQLAlchemy engine
SYNC_DATABASE_URL = ASYNC_DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

# ==============================================================================
# SMART SSL DETECTION (Neon DB vs Local/CI Postgres)
# ==============================================================================
parsed_db = urlparse(SYNC_DATABASE_URL)

# Detect if running in local development, CI runner, or docker network vs production Neon DB
is_local_db = parsed_db.hostname in {"localhost", "127.0.0.1", "postgres", "db", None}

sync_connect_args = {}
async_connect_args = {"prepared_statement_cache_size": 0}

if not is_local_db:
    # Enforce strict SSL in remote production environments (e.g. Neon DB, AWS RDS)
    sync_connect_args["sslmode"] = "require"
    async_connect_args["ssl"] = "require"
else:
    # Allow non-SSL / fallback for local dev & GitHub Actions CI runners
    sync_connect_args["sslmode"] = "disable"


# ==============================================================================
# SELF-HEALING DATABASE INITIALIZATION (DEVELOPMENT ONLY)
# ==============================================================================
def create_database_if_not_exists() -> None:
    """Verifies target db existence and boots a fresh instance if missing in DEV only."""
    if settings.ENVIRONMENT != "development":
        logger.debug(
            "Skipping automatic database creation (not in development environment)."
        )
        return

    try:
        default_url, db_name = SYNC_DATABASE_URL.rsplit("/", 1)
        if "?" in db_name:
            db_name = db_name.split("?")[0]

        # Security check: Validate the database name to prevent interpolation injection
        if not re.match(r"^[a-zA-Z0-9_]+$", db_name):
            raise ValueError(f"Invalid database name format detected: {db_name}")

        default_system_url = f"{default_url}/postgres"
        default_engine = create_engine(
            default_system_url,
            connect_args=sync_connect_args,  # Added for Neon DB SSL requirement
            isolation_level="AUTOCOMMIT",
        )

        with default_engine.connect() as conn:
            result = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :db_name"),
                {"db_name": db_name},
            )

            if not result.fetchone():
                # Safe to interpolate now since db_name passed regex validation
                conn.execute(text(f"CREATE DATABASE {db_name}"))
                logger.info(f"Database '{db_name}' created successfully.")
            else:
                logger.info(f"Database '{db_name}' verified and ready.")

        default_engine.dispose()

    except Exception as e:
        logger.error(f"Failed to verify or create database during startup: {e}")
        # Fail fast instead of swallowing the exception
        raise


# Trigger initialization (safely gated by environment checks)
create_database_if_not_exists()

# ==============================================================================
# HIGH-PERFORMANCE ASYNCHRONOUS ENGINE TRACKS (AISHA AI CORE)
# ==============================================================================
async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    connect_args=async_connect_args,
    pool_pre_ping=True,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_recycle=settings.DB_POOL_RECYCLE,
)

async_session_factory = async_sessionmaker(
    bind=async_engine, class_=AsyncSession, expire_on_commit=False
)

# ==============================================================================
# CORE RELATIONAL SYNCHRONOUS ENGINE TRACKS (BACKWARD COMPATIBILITY)
# ==============================================================================
sync_engine = create_engine(
    SYNC_DATABASE_URL,
    connect_args=sync_connect_args,  # <--- Enforces SSL for sync connections
    pool_pre_ping=True,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_recycle=settings.DB_POOL_RECYCLE,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)

# Backward-compatible alias: startup code (e.g. main.py's Base.metadata.create_all(bind=engine))
# expects a plain synchronous `engine` name.
engine = sync_engine


class Base(DeclarativeBase):
    """Modern DeclarativeBase subclass mapping python models to database tables cleanly."""


# ==============================================================================
# DEPENDENCY INJECTION GENERATORS
# ==============================================================================
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        try:
            db.close()
        except Exception:
            logger.warning(
                "Ignoring error while closing DB session (connection likely "
                "already dropped by the server)",
                exc_info=True,
            )
