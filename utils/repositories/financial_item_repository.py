"""
Financial_itemモデルのためのリポジトリクラス。                                                                                                           │
汎用的なCRUD操作はBaseRepositoryから継承し、                                                                                                               │
Financial_itemモデルに特化したデータアクセスロジックを提供します。  
"""
from sqlalchemy.orm import Session
from sqlalchemy import select

from utils.db_models import Financial_item
from utils.repositories.base_repository import BaseRepository

class FinancialItemRepository(BaseRepository[Financial_item]):
    def __init__(self, session: Session):
        super().__init__(session, Financial_item)

    def find_by_element_id(self, element_id:str) -> Financial_item | None:
        statement = select(Financial_item).where(Financial_item.element_id == element_id)
        result = self.session.scalars(statement).scalar_one_or_none()
        return result
