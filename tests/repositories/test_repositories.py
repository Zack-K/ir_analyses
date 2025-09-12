"""
BaseRepositoryの基本機能と、CompanyRepository固有の機能の両方をテストします。

```Docker内部でのテスト実行コマンド
$ docker compose exec streamlit_app pytest tests/repositories/test_repositories.py
```
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


@pytest.fixture(scope="function")
def company_data2():
    company = Company(
        edinet_code="E67890",
        security_code="S5678",
        industry_code="TEST2",
        company_name="Another Test Company",
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


def test_get_all_company_names_and_edinet_code(db_session, company_data, company_data2):
    """全てのCompany名を取得するテストを行います。"""
    repo = CompanyRepository(db_session)
    repo.add(company_data)
    repo.add(company_data2)
    db_session.commit()  # トランザクションをコミットしてDBに反映
    company_names = repo.get_all_company_names_and_edinet_code()
    expected_result = {
        (company_data.company_name, company_data.edinet_code),
        (company_data2.company_name, company_data2.edinet_code)
    }  # setにして順不同を考慮
    assert set(company_names) == expected_result

def test_find_by_edinet_code(db_session, company_data):
    repo = CompanyRepository(db_session)
    repo.add(company_data)
    db_session.commit()
    find_result_company = repo.find_by_edinet_code(company_data.edinet_code)
    expected_result = company_data
    assert expected_result == find_result_company

def test_delete_company(db_session, company_data):
    """Companyの削除をテストします。"""
    repo = CompanyRepository(db_session)
    repo.add(company_data)
    db_session.commit()
    repo.delete(company_data)
    db_session.commit()
    assert repo.get(company_data.company_id) is None


def test_upsert_inserts_new_record(db_session, company_data):
    """upsertメソッドで新規レコードが挿入され、updateされることを確認します。"""
    repo = CompanyRepository(db_session)
    persisted_company = repo.upsert(company_data)
    db_session.commit()
    retrieved_company = repo.get(persisted_company.company_id)
    assert retrieved_company is not None
    assert retrieved_company.edinet_code == company_data.edinet_code


def test_upsert_updates_existing_record(db_session, company_data):
    """upsertメソッドで既存レコードが更新されることを確認します。"""
    repo = CompanyRepository(db_session)
    repo.add(company_data)
    db_session.commit()
    updated_name = "Updated Company Name"
    company_data.company_name = updated_name
    updated_instance = repo.upsert(company_data)
    db_session.commit()
    retrieved_company = repo.get(updated_instance.company_id)
    assert retrieved_company is not None
    assert retrieved_company.company_name == updated_name


def test_get_not_found_company(db_session):
    """存在しないCompanyを取得しようとした場合、Noneが返ることを確認します。"""
    repo = CompanyRepository(db_session)
    retrieved_company = repo.get(9999)  # 存在しないIDを指定
    assert retrieved_company is None


def test_get_all_empty(db_session):
    """Companyが一件も登録されていない場合、空リストが返ることを確認します。"""
    repo = CompanyRepository(db_session)
    company_names = repo.get_all_company_names_and_edinet_code()
    assert company_names == []
