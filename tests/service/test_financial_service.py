"""
FinancialServiceの各メソッドの機能をテストします。
"""

import pytest

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

