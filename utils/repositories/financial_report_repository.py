"""
Financial_reportモデルのためのリポジトリクラス。
汎用的なCRUD操作はBaseRepositoryから継承し、                                                                                                                                                                     │
Financial_reportモデルに特化したデータアクセスロジックを提供します。
"""     

from sqlalchemy.orm import Session
from sqlalchemy import select

from utils.db_models import Financial_report
from utils.repositories.base_repository import BaseRepository

class FinancialReportRepository(BaseRepository[Financial_report]):
    def __init__(self, session:Session):
        super().__init__(session, Financial_report)


    def find_latest_by_company_id(self, company_id:int) -> Financial_report | None:
        statement = select(Financial_report).where(Financial_report.company_id == company_id).order_by(Financial_report.fiscal_year.desc())
        result = self.session.scalars(statement).first()
        return result
