from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def create_database_if_not_exists():
    default_url = DATABASE_URL.rsplit("/", 1)[0] + "/postgres"
    db_name = DATABASE_URL.rsplit("/", 1)[1]

    default_engine = create_engine(
        default_url,
        isolation_level="AUTOCOMMIT"
    )

    with default_engine.connect() as conn:
        result = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :db_name"),
            {"db_name": db_name}
        )
        exists = result.fetchone()

        if not exists:
            conn.execute(text(f"CREATE DATABASE {db_name}"))
            print(f"Database '{db_name}' created successfully")
        else:
            print(f"Database '{db_name}' already exists")

    default_engine.dispose()

#Run the check every time the app starts
create_database_if_not_exists()

# Now create the real engine pointing to aisha_db
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
    

