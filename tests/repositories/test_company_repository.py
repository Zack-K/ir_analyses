"""
BaseRepositoryの基本機能と、CompanyRepository固有の機能の両方をテストします。


"""

import os
from dotenv import load_dotenv
import pytest
from sqlalchemy.engine import create_engine
from sqlalchemy.orm import sessionmaker, Session

from utils.db_models import Company
from utils.repositories.company_repository import CompanyRepository 


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
    db.query(Company).delete() 
    db.commit()
    try:
        yield db
    finally:
        db.rollback()
        db.close()


@pytest.fixture(scope="function")
def company_data():
    company = Company(
        edinet_code="E12345",
        security_code="S1234",
        industry_code="TEST",
        company_name="Test Company",
    )
    return company


def test_add_and_get_company(db_session, company_data):
    """AAA(Arrange, Act, Assert)パターンに従い、Companyの追加と取得をテストします。"""
    # Arrenge:準備
    repo = CompanyRepository(db_session)
    repo.add(company_data)
    # Act:実行
    db_session.commit()  # トランザクションをコミットしてDBに反映
    retrieved_company = repo.get(company_data.company_id)
    # Assert:検証
    assert retrieved_company is not None
    assert retrieved_company.edinet_code == company_data.edinet_code
    assert retrieved_company.security_code == company_data.security_code
    assert retrieved_company.industry_code == company_data.industry_code
    assert retrieved_company.company_name == company_data.company_name

