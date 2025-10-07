"""
FinancialReportRepository固有の機能の両方をテストします。

```Docker内部でのテスト実行コマンド
$ docker compose exec streamlit_app pytest ./tests/repositories/test_financial_report_repository.py
```
"""

import os
from dotenv import load_dotenv
import pytest
from sqlalchemy.engine import create_engine
from sqlalchemy.orm import sessionmaker, Session

from utils.db_models  import Financial_report, Company
from utils.repositories.financial_report_repository import FinancialReportRepository

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
def company_data():
    company = Company(
        edinet_code="E12345",
        security_code="S1234",
        industry_code="TEST",
        company_name="Test Company",
    )
    return company

@pytest.fixture(scope="function")
def latest_report_data(company_data):
    financial_report = Financial_report(
        company = company_data,
        document_type = "四半期報告書",
        fiscal_year = 2024,
        quarter_type = "Q1",
        fiscal_year_end = "2024/3/30",
        filing_date = "2024/1/10",
    )
    return financial_report


@pytest.fixture(scope="function")
def old_report_data(company_data):
    financial_report = Financial_report(
        company = company_data,
        document_type = "四半期報告書",
        fiscal_year = 2023,
        quarter_type = "Q4",
        fiscal_year_end = "2023/3/30",
        filing_date = "2022/12/10",
    )
    return financial_report

def test_find_latest_by_company_id(db_session, company_data, latest_report_data, old_report_data):
    """find_latest_by_company_idメソッドの正常系テスト"""
    # Arrenge
    repo = FinancialReportRepository(db_session)
    repo.add(company_data)
    repo.add(latest_report_data)
    repo.add(old_report_data)
    db_session.commit()
    # Act
    company_id = latest_report_data.company.company_id
    result = repo.find_latest_by_company_id(company_id)
    expected_result = latest_report_data
    # Assert
    assert result is not None
    assert expected_result.fiscal_year == result.fiscal_year 
    assert expected_result.report_id == result.report_id

#TODO 異常系のテストを数種類