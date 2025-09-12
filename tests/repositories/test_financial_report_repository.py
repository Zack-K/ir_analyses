import os
from dotenv import load_dotenv
import pytest
from sqlalchemy.engine import create_engine
from sqlalchemy.orm import sessionmaker, Session

from utils.repositories.financial_report_repository import Financial_report

@pytest.fixture(scope="session")
def engine():
    load_dotenv()
    db_user = os.environ.get("DB_USER")
    db_password = os.environ.get("DB_PASSWORD")
    db_host = os.environ.get("DB_HOST", "localhost")
    db_port = os.environ.get("DB_PORT", "5432")
    db_name = os.environ.get("DB_NAME", "ir_analyses_db")

    db_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    db_engine = create_engine(db_url)
    return db_engine


@pytest.fixture(scope="function")
def db_session(engine):
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db: Session = SessionLocal()
    db.query(Financial_report).delete()
    db.commit()
    try:
        yield db
    finally:
        db.rollback()
        db.close()

@pytest.fixture(scope="function")
def report_data()
    financial_report = Financial_report(

    )