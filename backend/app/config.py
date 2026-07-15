from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

# Define the project root directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Load variables from the .env file
load_dotenv(BASE_DIR / ".env")


class Settings:
    # 1. Normalize environment string to lowercase for safe matching
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()

    # 2. Guard the database fallback behavior
    _db_url = os.getenv("DATABASE_URL")
    
    if not _db_url:
        if ENVIRONMENT == "development":
            # Safe local fallback restricted strictly to development environments
            RAW_DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/aisha_db"
        else:
            # Prevent silent failures in staging/production
            raise ValueError(
                "CRITICAL SETUP ERROR: DATABASE_URL is not set in the environment. "
                "The application cannot start in production without a valid database connection string."
            )
    else:
        RAW_DATABASE_URL = _db_url

    # 3. DB connection pooling options (tunable via environment variables)
    DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "20"))
    DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "10"))
    DB_POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "1800"))


# Instantiate the settings instance to be imported elsewhere
settings = Settings()
