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
from typing import Literal, List, Tuple
from dataclasses import dataclass

import utils.service.unitofwork as uow
from utils.repositories.company_repository import CompanyRepository


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


class FinancialService:
    def __init__(self, uow: uow.UnitOfWork):
        self.uow = uow

    # step2. データ取得処理 get_financial_summaryを定義する
    def get_financial_summary(self,company_name:str, FinancialSummaryDTO) -> FinancialSummaryDTO:
        """
        責務：
            1. 企業情報の取得
            2. 財務報告の特定
            3. 主要財務データの取得
            4. ビジネスロジック（利益率計算）の実行
            5. DTOへのマッピングと返却
        """
        # 1.企業情報の取得 
        # 2. 財務報告の特定　UIから選択された企業名を取得
        # 3. 主要財務データを取得　repositoryに企業名を渡してデータ取得
        # 4. ビジネスロジックの計算　app.pyの計算ロジックを移植してDTOに合わせて修正
        # 5.DTOマッピングと返却　初期化後にビジネスロジックで計算した内容を渡す
        dto = FinancialSummaryDTO()

        return dto

    def get_company_selection_list(self) -> List[Tuple[str, str]]:
        """UIに企業名セレクションリストを渡すために担当リポジトリクラスに依頼するメソッド"""
        # リポジトリの初期化
        with self.uow:
            # 担当リポジトリクラスへのデータ取得依頼
            company_selection_list = self.uow.companies.get_all_company_names_and_edinet_code()
        return company_selection_list