import logging

from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from model_service.config import DATABASE_URL

logger = logging.getLogger(__name__)

if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL is not set. Please check your .env file."
    )

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


def init_db():
    Base.metadata.create_all(bind=engine)
    # Safely migrate new columns if running against an existing postgres container
    migrations = [
        "ALTER TABLE predictions ADD COLUMN IF NOT EXISTS features JSON;",
        "ALTER TABLE ingestion_stats ADD COLUMN IF NOT EXISTS records_failed INTEGER DEFAULT 0;",
        "ALTER TABLE ingestion_stats ADD COLUMN IF NOT EXISTS criticality VARCHAR DEFAULT 'NONE';",
        "ALTER TABLE ingestion_stats ADD COLUMN IF NOT EXISTS error_summary JSON;",
    ]
    with engine.connect() as conn:
        for stmt in migrations:
            try:
                conn.execute(text(stmt))
                conn.commit()
            except Exception as e:
                logger.debug(f"Migration note: {e}")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
