"""財務関連のビジネスロジックを担う、サービス層のモジュール。

このモジュールは、アプリケーションの主要なユースケースを実装する`FinancialService`
クラスと、UIとのデータ連携に用いるDTO（Data Transfer Object）群を提供します。

3層アーキテクチャにおけるビジネスロジック層として、プレゼンテーション層（UI）と
データアクセス層（Repository）を分離する役割を担います。`FinancialService`は、
`UnitOfWork`パターンを通じてデータ永続化の調整を行い、ビジネスロジックを実行し、
結果をDTOに変換して返します。

Attributes:
    FinancialSummaryDTO: 単一期間における財務サマリーを保持するDTO。
    FinancialService: 財務関連のビジネスロジックをカプセル化したサービスクラス。

Example:
    # uowはUnitOfWorkの具象インスタンス
    financial_service = FinancialService(uow)
    with uow:
        summaries = financial_service.get_financial_summary("E01234")
        # `with`ブロックを抜ける際に、uowが自動的にトランザクションを管理する

"""

from typing import Literal, List, Tuple, Optional
from dataclasses import dataclass
import pandas as pd

import utils.service.unitofwork as uow
import utils.data_mapper as data_mapper
from utils.db_models import Company, Financial_item, Financial_report, Financial_data


@dataclass
class FinancialSummaryDTO:
    # 企業・財務期間情報
    company_name: str
    period_name: str
    fiscal_year: int
    quarter_type: Literal["Q1", "Q2", "Q3", "Q4"]

    # 計算数値として保存する財務データ
    net_sales: float | None
    operating_income: float | None
    ordinary_income: float | None
    net_income: float | None

    # 計算済みの利益率
    operation_profit_rate: float | None
    ordinary_profit_rate: float | None
    net_profit_rate: float | None


# 主要財務項目リスト
_SUMMARY_ITEMS = ["売上高", "営業利益", "経常利益", "当期純利益"]


class FinancialService:
    def __init__(self, uow: uow.UnitOfWork):
        self.uow = uow

    def get_financial_summary(
        self, edinet_code: str
    ) -> Optional[FinancialSummaryDTO] | None:
        """指定されたEDINETコードの企業について、最新の財務サマリーを生成する。

        企業情報、最新の財務報告、および関連する主要財務データをデータベースから
        取得します。売上高や各利益、それらに基づく利益率を計算し、結果を
        FinancialSummaryDTOに格納して返します。

        Args:
            edinet_code: 企業のEDINETコード。

        Returns:
            企業が見つかった場合は、財務サマリー情報を含むFinancialSummaryDTO。
            見つからない場合はNone。
        """
        # 1.企業情報の取得
        # 2. 財務報告の特定　UIから選択された企業名をedinet_codeから取得
        # 3. 主要財務データを取得　repositoryにedinet_codeを渡してデータ取得
        with self.uow:
            company_info = self.uow.companies.find_by_edinet_code(edinet_code)
            if company_info is None:
                return None

            financial_report = self.uow.financial_reports.find_latest_by_company_id(
                company_info.company_id
            )

            financial_data = self.uow.financial_data.find_by_report_id_and_item_names(
                financial_report.report_id, _SUMMARY_ITEMS
            )

            # 4.DTOマッピング
            data_map = {data.item.item_name: data.value for data in financial_data}

            dto = FinancialSummaryDTO(
                company_name=company_info.company_name,
                period_name=f"{financial_report.fiscal_year} {financial_report.quarter_type}",
                fiscal_year=int(financial_report.fiscal_year),
                quarter_type=financial_report.quarter_type,
                net_sales=data_map.get("売上高"),
                operating_income=data_map.get("営業利益"),
                ordinary_income=data_map.get("経常利益"),
                net_income=data_map.get("純利益"),
                operation_profit_rate=None,
                ordinary_profit_rate=None,
                net_profit_rate=None,
            )
        # 5. ビジネスロジック（利益率計算）の実行
        # 営業利益率
        if dto.operating_income and dto.net_sales and dto.net_sales != 0:
            dto.operation_profit_rate = dto.operating_income / dto.net_sales * 100
        # 経常利益率
        if dto.ordinary_income and dto.net_sales and dto.net_sales != 0:
            dto.ordinary_profit_rate = dto.ordinary_income / dto.net_sales * 100
        # 当期純利益率
        if dto.net_income and dto.net_sales and dto.net_sales != 0:
            dto.net_profit_rate = dto.net_income / dto.net_sales * 100
        return dto

    def get_company_selection_list(self) -> List[Tuple[str, str]]:
        """UIに企業名セレクションリストを渡すために担当リポジトリクラスに依頼するメソッド"""
        # リポジトリの初期化
        with self.uow:
            # 担当リポジトリクラスへのデータ取得依頼
            company_selection_list = (
                self.uow.companies.get_all_company_names_and_edinet_code()
            )
        return company_selection_list

    def save_financial_data_from_dataframe(self, df: pd.DataFrame, config: dict):
        standarized_df = data_mapper.standardize_raw_data(df)
        # 1. data_mapperを呼び出し変数に格納する
        model_data_bundle = data_mapper.map_data_to_models(standarized_df, config)
        # 2. unit of workを呼び出し、トランザクションの開始
        with self.uow:
            # 3. Companyオブジェクトに辞書を保存、テーブルにデータを登録
            company_data = model_data_bundle["company"]
            company = self.uow.companies.find_by_edinet_code(
                company_data["edinet_code"]
            )
            if company:
                # データが存在する場合はupsert(更新)
                company.edinet_code = company_data.get(
                    "edinet_code", company.edinet_code
                )
                company.security_code = company_data.get(
                    "security_code", company.security_code
                )
                company.industry_code = company_data.get(
                    "industry_code", company.industry_code
                )
                company.company_name = company_data.get(
                    "company_name", company.company_name
                )
            else:
                # データが存在しない場合はadd(新規登録)としてオブジェクトを新規作成
                company = Company(**company_data)
                self.uow.companies.add(company)
            self.uow.session.flush()
            company_id = company.company_id

            # 4. Financial_itemのリストの存在チェックと登録処理
            for financial_item in model_data_bundle["items"]:
                if (
                    self.uow.financial_items.find_by_element_id(
                        financial_item["element_id"]
                    )
                    is None
                ):
                    financial_item_data = Financial_item(**financial_item)
                    self.uow.financial_items.add(financial_item_data)
            self.uow.session.flush()
            # 5. Financial_itemからelement_idとitem_idのリストを作成してマッピング
            element_ids = [item["element_id"] for item in model_data_bundle["items"]]
            financial_items = self.uow.financial_items.find_by_element_ids(element_ids)
            item_id_map = {
                financial_item.element_id: financial_item.item_id
                for financial_item in financial_items
            }

            # 6. Financial_reportの登録
            model_data_bundle["report"].update({"company_id": company_id})
            financial_report = Financial_report(**model_data_bundle["report"])
            financial_report = self.uow.financial_reports.upsert(financial_report)
            self.uow.session.flush()
            # 7. Financial_dataをマッピングするため、data_mapperを呼び出し、対応メソッドを実行
            financial_data_map = data_mapper.financial_data_mapping(
                standarized_df, financial_report.report_id, item_id_map
            )
            # 8. Financial_dataにループ処理して登録処理
            for register_data_dict in financial_data_map:
                financial_data = Financial_data(**register_data_dict)
                self.uow.financial_data.add(financial_data)
