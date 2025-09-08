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


    def find_by_company_id(self, company_id:int) -> list[Financial_report]:
        statement = select(Financial_report).where(Financial_report.company_id == company_id)
        result = self.session.scalars(statement).all()
        return result