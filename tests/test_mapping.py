import pandas as pd
import pytest
from utils import api

# テスト用のDataFrameを準備する
@pytest.fixture
def sample_source_df() -> pd.DataFrame:
    """Companyマッピング用のテストデータを作成するフィクスチャ"""
    data = {
        'element_id': [
            "jpdei_cor:EDINETCodeDEI",
            "jpdei_cor:SecurityCodeDEI",
            "jpcrp_cor:CompanyNameCoverPage",
            "jpdei_cor:IndustryCodeWhenConsolidatedFinancialStatementsArePreparedInAccordanceWithIndustrySpecificRegulationsDEI",
            "jppfs_cor:NetSales", # 関係のないデータ
        ],
        'value': [
            "E01234",
            "12345",
            "テスト株式会社",
            "XYZ",
            1000000,
        ],
        'is_numeric': [
            False,
            False,
            False,
            False,
            True,
        ],
        'value_text': [
            "E01234",
            "12345",
            "テスト株式会社",
            "XYZ",
            None,
        ]
    }
    df = pd.DataFrame(data)
    return df

def test_company_mapping_success(sample_source_df):
    """
    _company_mapping関数が正しくDataFrameを辞書に変換できるかをテストする
    """
    # 1. 期待される結果を定義
    expected_dict = {
        "edinet_code": "E01234",
        "security_code": "12345",
        "company_name": "テスト株式会社",
        "industry_code": "XYZ",
    }

    # 2. 実際にテスト対象の関数を呼び出す
    result_dict = api._company_mapping(sample_source_df)

    # 3. 結果が期待通りか検証する
    assert result_dict == expected_dict