from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from config.config import DATABASE_URL


engine = create_engine(DATABASE_URL)
Base = declarative_base()

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def get_db():
    try:
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()
    except Exception as e:
        from config.config import logger
        logger.error(f"Error in get_db: {e}")
        raise e