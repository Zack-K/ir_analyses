import pandas as pd
import pytest
from utils import api
from unittest.mock import patch

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


def test_company_mapping_raise_key_error_on_invalid_config(sample_source_df):
    """
    _company_mapping関数の異常系テスト: 設定ファイルが不正なケース。

    `utils.api.config` グローバル変数を `unittest.mock.patch.dict` を用いて
    一時的に書き換え、`["xbrl_mapping"]["company"]` セクションが存在しない
    状況をシミュレートする。

    この状況で `_company_mapping` 関数を呼び出した際に、
    正しく `KeyError` が送出されることを検証する。
    """
    with patch.dict(api.config, {'xbrl_mapping':{}}):
        with pytest.raises(KeyError):
            api._company_mapping(sample_source_df)


def test_company_mapping_success(sample_source_df, monkeypatch):
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

    # 2. テスト用の設定を読み込み、グローバル変数をパッチする
    test_config = api.load_config("config/config.toml")
    monkeypatch.setattr(api, 'config', test_config)

    # 3. 実際にテスト対象の関数を呼び出す
    result_dict = api._company_mapping(sample_source_df)

    # 4. 結果が期待通りか検証する
    assert result_dict == expected_dict

# --- financial_report_mappingのテスト ---

@pytest.fixture(scope="module")
def financial_report_source_df() -> pd.DataFrame:
    """
    テスト用のDataFrameを準備するフィクスチャ。
    documents/test.csvを読み込み、標準化処理を適用する。
    """
    csv_path = "documents/test.csv"
    # BOM付きUTF-8ファイルに対応するため 'utf-8-sig' を使用
    raw_df = pd.read_csv(csv_path, encoding="utf-8-sig")
    processed_df = api.standardize_raw_data(raw_df)
    return processed_df


def test_financial_report_mapping_success(financial_report_source_df, monkeypatch):
    """
    _financial_report_mapping関数の正常系テスト。
    正しくDataFrameを報告書情報の辞書に変換できるか検証する。
    """
    # 1. テスト用の設定を読み込み、グローバル変数をパッチする
    test_config = api.load_config("config/config.toml")
    monkeypatch.setattr(api, 'config', test_config)

    # 2. 期待される結果を定義
    expected_dict = {
        'document_type': '四半期報告書',
        'fiscal_year_and_quarter': '第121期 第３四半期(自  2023年10月１日  至  2023年12月31日)',
        'fiscal_year_end': '2023/12/31',
        'filing_date': '2024/2/9',
        'company_id': 99,
        'fiscal_year': '2023',
        'quarter_type': 'Q3'
    }

    # 3. 実際にテスト対象の関数を呼び出す
    result_dict = api._financial_report_mapping(financial_report_source_df, 99)

    # 4. 結果が期待通りか検証する
    assert result_dict == expected_dict


def test_financial_report_mapping_missing_config_section(financial_report_source_df, monkeypatch):
    """
    設定ファイルに financial_report セクションが存在しない場合にKeyErrorを送出するかテスト
    """
    with patch.dict(api.config, {"xbrl_mapping": {}}, clear=True):
        with pytest.raises(KeyError):
            api._financial_report_mapping(financial_report_source_df, 99)


def test_financial_report_mapping_missing_fiscal_year_key(financial_report_source_df, monkeypatch):
    """
    financial_reportセクションに必須キー(fiscal_year_and_quarter)が存在しない場合にValueErrorを送出するかテスト
    """
    config_data = api.load_config("config/config.toml")
    # 必須キーを意図的に削除
    del config_data["xbrl_mapping"]["financial_report"]["fiscal_year_and_quarter"]
    monkeypatch.setattr(api, 'config', config_data)

    with pytest.raises(ValueError, match="fiscal_year_and_quarterの値が無効です: 'None"):
        api._financial_report_mapping(financial_report_source_df, 99)

@pytest.mark.parametrize("invalid_value", [None, ""])
def test_financial_report_mapping_invalid_fiscal_year_value(financial_report_source_df, monkeypatch, invalid_value):
    """
    DataFrame内のfiscal_year_and_quarterの値が不正(None, 空文字)な場合にValueErrorを送出するかテスト
    """
    test_config = api.load_config("config/config.toml")
    monkeypatch.setattr(api, 'config', test_config)

    df = financial_report_source_df.copy()
    element_id = test_config["xbrl_mapping"]["financial_report"]["fiscal_year_and_quarter"]
    # 不正な値で上書き
    df.loc[df['element_id'] == element_id, 'value_text'] = invalid_value
    df.loc[df['element_id'] == element_id, 'is_numeric'] = False
    df.loc[df['element_id'] == element_id, 'value'] = None

    with pytest.raises(ValueError, match=f"fiscal_year_and_quarterの値が無効です: '{invalid_value}'"):
        api._financial_report_mapping(df, 99)


def test_financial_report_mapping_unparsable_string(financial_report_source_df,
                                                    monkeypatch):
    """
    fiscal_year_and_quarterの値がパース不可能な文字列の場合にValueErrorを送出するかテスト
    """
    test_config = api.load_config("config/config.toml")
    monkeypatch.setattr(api, 'config', test_config)

    df = financial_report_source_df.copy()
    element_id = test_config["xbrl_mapping"]["financial_report"][
        "fiscal_year_and_quarter"]
    unparsable_string = "これはパース不可能な文字列です"
    df.loc[df['element_id'] == element_id, 'value_text'] = unparsable_string

    with pytest.raises(ValueError,
                       match=f"会計年度の抽出に失敗しました: '{unparsable_string}'"):
        api._financial_report_mapping(df, 99)
