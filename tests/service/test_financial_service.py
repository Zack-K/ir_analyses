"""
FinancialServiceの各メソッドの機能をテストします。
"""

import pytest
import pandas as pd

from utils.service.financial_service import FinancialService


@pytest.fixture(scope="function")
def company_name_and_edinet_code_list():
    company_name_and_edinet_code_list = [
        ("TST_株式会社", "ABCED1"),
        ("TST_株式会社_2", "ABCED2"),
        ("TST_株式会社_3", "ABCED3"),
    ]
    return company_name_and_edinet_code_list


@pytest.fixture(scope="function")
def empty_list():
    empty_list = []
    return empty_list


def test_get_company_selection_list(mocker, company_name_and_edinet_code_list):
    # Given：前提条件
    # unit of workクラスをモック化、返却する値を設定
    mock_uow = mocker.MagicMock()
    mock_uow.companies.get_all_company_names_and_edinet_code.return_value = (
        company_name_and_edinet_code_list
    )

    financial_service = FinancialService(mock_uow)

    # When：実行
    result = financial_service.get_company_selection_list()

    # Then：評価
    assert result == company_name_and_edinet_code_list
    mock_uow.companies.get_all_company_names_and_edinet_code.assert_called_once()


def test_save_financial_data_from_dataframe(mocker):
    # Given
    # テスト用ダミーのDataFrame, configを作成
    dummy_input_df = pd.DataFrame({"col1": [1, 2]})
    dummy_standarized_df = pd.DataFrame({"col2": [3, 2]})
    dummy_model_data_bundle = {
        "company": {"edinet_code": "E12345", "company_name": "テスト株式会社"},
        "report": {"fiscal_year": 2023, "quarter_type": "Q4"},
        "items": [{"element_id": "NetSales", "item_name": "売上高"}],
    }
    dummy_financial_data = [{"item_id": 1, "value": 100}]
    dummy_config = {}

    # data_mapperをモック化し、ダミーデータを返却するように設定
    mock_data_mapper = mocker.patch("utils.service.financial_service.data_mapper")
    mock_data_mapper.standardize_raw_data.return_value = dummy_standarized_df
    mock_data_mapper.map_data_to_models.return_value = dummy_model_data_bundle
    mock_data_mapper.financial_data_mapping.return_value = dummy_financial_data
    # UnitOfWorkをモック化
    mock_uow = mocker.MagicMock()
    mock_report = mocker.MagicMock()
    mock_report.report_id = 1
    mock_item1 = mocker.MagicMock()
    mock_item1.item_id = 1
    mock_item1.element_id = "NetSales"
    list_of_items = [mock_item1]

    mock_uow.financial_items.find_by_element_ids.return_value = list_of_items
    mock_uow.financial_reports.upsert.return_value = mock_report.report_id
    # 新規登録シナリオのため、find系メソッドの結果に「見つからない（None）」を設定
    mock_uow.companies.find_by_edinet_code.return_value = None
    mock_uow.financial_items.find_by_element_id.return_value = None
    # serviceの初期化
    financial_service = FinancialService(mock_uow)

    # When:メソッドの実行
    financial_service.save_financial_data_from_dataframe(dummy_input_df, dummy_config)

    # Then:検証
    mock_data_mapper.standardize_raw_data.assert_called_once()
    mock_data_mapper.map_data_to_models.assert_called_once()
    mock_uow.companies.add.assert_called_once()
    mock_uow.financial_items.find_by_element_id.assert_called_once()
    mock_uow.financial_items.add.assert_called_once()
    mock_uow.financial_reports.upsert.assert_called_once()
    mock_uow.financial_data.add.assert_called_once()
    assert mock_uow.session.flush.call_count == 3
