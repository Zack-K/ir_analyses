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
from typing import Literal
from dataclasses import dataclass

import utils.service.unitofwork as uow


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