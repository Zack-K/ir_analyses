import pandas as pd
import pytest
from utils import api
from unittest.mock import patch
import numpy as np

# テスト用のDataFrameを準備する
@pytest.fixture
def sample_source_df() -> pd.DataFrame:
    """
    _company_mapping関数用の最小限のテストデータを作成するフィクスチャ。
    """
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
    異常系: _company_mapping - 設定ファイルが不正な場合にKeyErrorを送出する。

    `utils.api.config`から`["xbrl_mapping"]["company"]`セクションが存在しない
    状況をシミュレートし、関数が正しく`KeyError`を送出することを検証する。
    """
    with patch.dict(api.config, {'xbrl_mapping':{}}):
        with pytest.raises(KeyError):
            api._company_mapping(sample_source_df)


def test_company_mapping_success(sample_source_df, monkeypatch):
    """
    正常系: _company_mapping - DataFrameを正しく辞書に変換できる。
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
    以降のテストで使用する、実データに基づいた標準化済みDataFrameを作成するフィクスチャ。

    `documents/test.csv`を読み込み、`standardize_raw_data`を適用する。
    モジュールスコープで実行され、テストセッション中に一度だけ生成される。
    """
    csv_path = "documents/test.csv"
    # BOM付きUTF-8ファイルに対応するため 'utf-8-sig' を使用
    raw_df = pd.read_csv(csv_path, encoding="utf-8-sig")
    processed_df = api.standardize_raw_data(raw_df)
    return processed_df


def test_financial_report_mapping_success(financial_report_source_df, monkeypatch):
    """
    正常系: _financial_report_mapping - DataFrameを正しく報告書辞書に変換できる。
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
    異常系: _financial_report_mapping - 設定に`financial_report`セクションがない場合にKeyError。
    """
    with patch.dict(api.config, {"xbrl_mapping": {}}, clear=True):
        with pytest.raises(KeyError):
            api._financial_report_mapping(financial_report_source_df, 99)


def test_financial_report_mapping_missing_fiscal_year_key(financial_report_source_df, monkeypatch):
    """
    異常系: _financial_report_mapping - `fiscal_year_and_quarter`キーがない場合にValueError。
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
    異常系: _financial_report_mapping - パース対象の値がNoneまたは空文字列の場合にValueError。
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
    異常系: _financial_report_mapping - パース対象が不正な形式の文字列の場合にValueError。
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

# --- financial_item_mappingのテスト ---

def test_financial_item_mapping_success(financial_report_source_df):
    """
    正常系: _financial_item_mapping - 実データからユニークな財務項目が正しく抽出される。

    - `jppfs_cor:`で始まる項目のみが対象となること。
    - `element_id`で重複が排除されること。
    - 各項目が正しいキー(`element_id`, `item_name`, `unit_type`, `category`)を持つこと。
    - 特定の項目(`Assets`)の値が期待通りであること。
    """
    result_list = api._financial_item_mapping(financial_report_source_df)
    
    # 期待されるキーがすべて存在するか
    expected_keys = {'element_id', 'item_name', 'unit_type', 'category'}
    assert all(expected_keys.issubset(item.keys()) for item in result_list)

    # jppfs_cor: で始まるユニークなIDの数を取得
    expected_count = financial_report_source_df[financial_report_source_df['element_id'].str.startswith('jppfs_cor:')]['element_id'].nunique()
    assert len(result_list) == expected_count

    # 特定の項目の値が正しいか (資産項目を代表としてチェック)
    assets_item = next((item for item in result_list if item["element_id"] == "jppfs_cor:Assets"), None)
    assert assets_item is not None
    assert assets_item['item_name'] == '資産'
    assert assets_item['unit_type'] == 'JPY'
    assert assets_item['category'] == 'Consolidated'


def test_financial_item_mapping_empty_df():
    """
    境界値: _financial_item_mapping - 空のDataFrameから空のリストが返される。
    """
    empty_df = pd.DataFrame(columns=['element_id', 'item_name_jp', 'consolidated_type', 'unit_id'])
    result = api._financial_item_mapping(empty_df)
    assert result == []

@pytest.mark.parametrize(
    "consolidated_type, expected_category",
    [("連結", "Consolidated"), ("個別", "Non-consolidated"), ("その他", "Non-consolidated"), (np.nan, "Non-consolidated")]
)
def test_financial_item_mapping_category_logic(consolidated_type, expected_category):
    """
    正常系: _financial_item_mapping - 様々な`consolidated_type`から`category`が正しく判定される。
    """
    test_data = {
        'element_id': ["jppfs_cor:Assets"],
        'item_name_jp': ["資産"],
        'consolidated_type': [consolidated_type],
        'unit_id': ["JPY"]
    }
    df = pd.DataFrame(test_data)
    result = api._financial_item_mapping(df)
    assert len(result) == 1
    assert result[0]['category'] == expected_category

def test_financial_item_mapping_missing_column(financial_report_source_df):
    """
    異常系: _financial_item_mapping - 必須カラム(`item_name_jp`)欠損時にKeyErrorが発生する。
    """
    df_missing_column = financial_report_source_df.drop(columns=['item_name_jp'])
    with pytest.raises(KeyError):
        api._financial_item_mapping(df_missing_column)
