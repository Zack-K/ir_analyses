"""
pytestによるCompanyモデルのCRUD自動テスト

特徴:
- pytestのfixtureを用いてテストデータの準備・クリーンアップを自動化
- insert, read, update, deleteの各操作を個別のテスト関数で検証
- print文は使用せず、assertで期待値と実際の値を厳密に比較
- テストは冪等性があり、何度でも安全に実行可能
- pytestコマンドで自動的に全テストが実行される

【実行手順】
1. DockerでDBを起動
   $ docker compose up -d

2. （必要に応じて）アプリケーション用コンテナに入る
   $ docker compose exec streamlit_app /bin/bash

3. pytestでテストを実行
   $ pytest tests/test_db_controller.py

※DBが起動していない場合、テストは失敗します。
"""

import sys
import os
# utilsをimportするための設定
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


import pytest
import sqlalchemy
from utils.db_controller import insert, read, update, delete, create_session
from utils.db_models import Company


@pytest.fixture
def company_data():
    return {
        "edinet_code": "E00001",
        "company_name": "pytest株式会社",
        "security_code": "1234",
        "industry_code": "5678"
    }

@pytest.fixture(autouse=True)
def clean_up(company_data):
    # テスト前後でデータをクリーンアップ
    yield
    session = create_session()
    company = session.query(Company).filter_by(edinet_code=company_data["edinet_code"]).first()
    if company:
        session.delete(company)
        session.commit()
    session.close()

def test_insert(company_data):
    """
    Companyモデルに新規データを挿入できること、
    および同じデータの重複挿入が失敗することを検証する。
    """
    assert insert(Company, company_data) is True
    assert insert(Company, company_data) is False

def test_read(company_data):
    """
    Companyモデルに挿入したデータが正しく取得できること、
    存在しないデータの検索時は空のDataFrameが返ることを検証する。
    """
    insert(Company, company_data)
    df = read(Company, {"edinet_code": company_data["edinet_code"]})
    assert not df.empty
    assert len(df) == 1
    row = df.iloc[0]
    for key, value in company_data.items():
        assert row[key] == value
    df = read(Company, {"edinet_code": "NOEXIST"})
    assert df.empty

def test_update(company_data):
    """
    Companyモデルの既存データを更新できること、
    更新後に新しい値が正しく反映されていることを検証する。
    """
    insert(Company, company_data)
    update_data = {"company_name": "更新株式会社"}
    assert update(Company, {"edinet_code": company_data["edinet_code"]}, update_data) is True
    df = read(Company, {"edinet_code": company_data["edinet_code"]})
    assert not df.empty
    assert df.iloc[0]["company_name"] == "更新株式会社"

def test_delete(company_data):
    """
    Companyモデルの既存データを削除できること、
    削除済みデータを再度削除しようとした場合は失敗することを検証する。
    """
    insert(Company, company_data)
    assert delete(Company, {"edinet_code": company_data["edinet_code"]}) is True
    assert delete(Company, {"edinet_code": company_data["edinet_code"]}) is False