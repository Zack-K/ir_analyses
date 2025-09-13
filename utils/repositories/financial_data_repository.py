"""
Financial_dataモデルのためのリポジトリクラス。

汎用的なCRUD操作はBaseRepositoryから継承し、
Financial_dataモデルに特化したデータアクセスロジックを提供します。
"""

from typing import List

from sqlalchemy.orm import Session
from sqlalchemy import select

from utils.db_models import Financial_data, Financial_report, Financial_item
from utils.repositories.base_repository import BaseRepository


class FinancialDataRepository(BaseRepository[Financial_data]):
    def __init__(self, session: Session):
        super().__init__(session, Financial_data)

    def find_by_report_id_and_item_names(
        self, report_id: int, item_names: list[str]
    ) -> List[Financial_data]:
        statement = (
            select(self.model)
            .join(Financial_item)
            .where(
                self.model.report_id == report_id,
                Financial_item.item_name.in_(
                    item_names
                ),  # 複数のitem_nameに対応できるようにin_を使用
            )
        )
        result = self.session.scalars(statement).all()
        return result

    def find_by_series_by_company_and_time(
        self, company_id: int, item_id: int
    ) -> list[Financial_data]:
        statement = (
            select(self.model)
            .join(Financial_report)
            .where(
                Financial_report.company_id == company_id, self.model.item_id == item_id
            )
            .order_by(Financial_report.fiscal_year_end)
        )
        result = self.session.scalars(statement).all()
        return result