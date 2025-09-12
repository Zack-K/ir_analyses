"""
Companyモデルのためのリポジトリクラス。
汎用的なCRUD操作はBaseRepositoryから継承し、
Companyモデルに特化したデータアクセスロジックを提供します。
"""

from typing import List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select

from utils.db_models import Company
from utils.repositories.base_repository import BaseRepository


class CompanyRepository(BaseRepository[Company]):
    def __init__(self, session: Session):
        super().__init__(session, Company)

    def get_all_company_names_and_edinet_code(self) -> List[Tuple[str, str]]:
        """すべての企業名とそのEDINETコードを取得する"""
        result_rows = self.session.execute(
            select(Company.company_name, Company.edinet_code)
        ).all()

        return [tuple(row) for row in result_rows]
