"""Unit of Work パターンを実装するためのモジュール。

このモジュールは、データアクセスとトランザクション管理の責務をカプセル化
するための、抽象的な `UnitOfWork` インターフェースと、SQLAlchemyを
利用した具象クラス `SqlAlchemyUnitOfWork` を提供します。

Service層は、このモジュールが提供するUnit of Workを通じて、
データベースとの対話を安全かつ一貫性のある形で行います。
"""
import logging
from abc import ABC, abstractmethod
from types import TracebackType
from typing import Optional, Type

from sqlalchemy.orm import sessionmaker

from utils.repositories.company_repository import CompanyRepository
from utils.repositories.financial_data_repository import FinancialDataRepository
from utils.repositories.financial_item_repository import FinancialItemRepository
from utils.repositories.financial_report_repository import FinancialReportRepository


class UnitOfWork(ABC):
    """Unit of Workパターンを実装するための抽象基底クラス/インターフェイス

    トランザクションの境界を定義し、管理化のリポジトリへのアクセスを提供します。
    このクラスはコンテキストマネージャーとして、`with`ステートメントで使用されることを想定しています。

    Args:
        session_factory (sessionmaker): SQLAlchemyのsessionmakerインスタンス
    Attributes:
        companies(CompanyRepository): Companyモデルを扱うリポジトリ
        financial_items(FinancialItemRepository): FinancialItemモデルを扱うリポジトリ
        financial_reports(FinancialReportRepository): FinancialReportモデルを扱うリポジトリ
        financial_data(FinancialDataRepository): FinancialDataモデルを扱うリポジトリ

    Example:
        with ConcreteUnitOfWork(session_factory) as uow:
            company = uow.companies.get(1)
            # uow.commit()はwithブロックを抜ける際に自動実行される
    """

    def __init__(self, session_factory: sessionmaker):
        self.session_factory = session_factory
        self.committed = False
        self.rollbacked = False

    @abstractmethod
    def __enter__(self):
        pass

    @abstractmethod
    def __exit__(
        self,
        execution_type: Optional[Type[BaseException]],
        execution_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ):
        pass

    @property
    @abstractmethod
    def companies(self) -> CompanyRepository:
        pass

    @property
    @abstractmethod
    def financial_items(
        self,
    ) -> FinancialItemRepository:
        pass

    @property
    @abstractmethod
    def financial_reports(
        self,
    ) -> FinancialReportRepository:
        pass

    @property
    @abstractmethod
    def financial_data(
        self,
    ) -> FinancialDataRepository:
        pass


class SqlAlchemyUnitOfWork(UnitOfWork):
    """SQLAlchemyを用いたUnit of Workの具体的実装"""

    def __init__(self, session_factory: sessionmaker):
        super().__init__(session_factory)

    def __enter__(self) -> "SqlAlchemyUnitOfWork":
        """セッションを開始し、そのセッションを使ってリポジトリ群を初期化・準備すること"""
        self.session = self.session_factory()
        self._companies = CompanyRepository(self.session)
        self._financial_items = FinancialItemRepository(self.session)
        self._financial_reports = FinancialReportRepository(self.session)
        self._financial_data = FinancialDataRepository(self.session)
        return self

    @property
    def companies(self) -> CompanyRepository:
        return self._companies

    @property
    def financial_items(self) -> FinancialItemRepository:
        return self._financial_items

    @property
    def financial_reports(self) -> FinancialReportRepository:
        return self._financial_reports

    @property
    def financial_data(self) -> FinancialDataRepository:
        return self._financial_data

    def __exit__(
        self,
        execution_type: Optional[Type[BaseException]],
        execution_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ):
        """トランザクションのコミットまたはロールバックを行い、セッションを閉じること"""

        if execution_type is None:
            try:
                self.session.commit()
            except Exception as e:
                logging.error(
                    "Commit failed:%s, Rolling back: %s, Trace back:%s",
                    e,
                    execution_value,
                    traceback,
                )
                self.session.rollback()
                raise
        else:
            self.session.rollback()

        self.session.close()
