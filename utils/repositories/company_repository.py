"""
Companyモデルのためのリポジトリクラス。
汎用的なCRUD操作はBaseRepositoryから継承し、
Companyモデルに特化したデータアクセスロジックを提供します。
"""

from sqlalchemy.orm import Session
from sqlalchemy import select

from utils.db_models import Company
from utils.repositories.base_repository import BaseRepository


class CompanyRepository(BaseRepository[Company]):
    def __init__(self, session: Session):
        super().__init__(session, Company)

    def get_all_company_names(self) -> list[str]:
        return list(self.session.scalars(select(Company.company_name)).all())
