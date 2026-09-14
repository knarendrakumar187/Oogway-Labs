import logging
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker
from backend.app.config import settings

logger = logging.getLogger(__name__)

Base = declarative_base()

def get_engine():
    db_url = settings.DATABASE_URL
    if db_url.startswith("postgresql"):
        try:
            logger.info("Attempting connection to PostgreSQL: %s", db_url.split("@")[-1])
            engine = create_engine(db_url, pool_pre_ping=True, connect_args={"connect_timeout": 3})
            # Test connection
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Successfully connected to PostgreSQL.")
            return engine
        except Exception as e:
            logger.warning(
                "Could not connect to PostgreSQL (%s). Falling back to local SQLite database (%s) for zero-downtime execution.",
                e,
                settings.SQLITE_FALLBACK_URL
            )
    
    # SQLite fallback
    os.makedirs(settings.DATA_DIR, exist_ok=True)
    sqlite_engine = create_engine(
        settings.SQLITE_FALLBACK_URL,
        connect_args={"check_same_thread": False}
    )
    return sqlite_engine

engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    from backend.app.models import SessionModel, MessageModel, SourceCitedModel
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized successfully.")
