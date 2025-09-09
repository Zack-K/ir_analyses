"""
ジェネリックなリポジトリパターンのための基底クラス。

このクラスは、特定のSQLAlchemyモデルに対する基本的なCRUD（Create, Read,
Update, Delete）操作をカプセル化します。具象リポジトリクラスは、
このクラスを継承し、扱うモデルの型を指定することで、定型的なデータアクセス
ロジックを再利用できます。

トランザクション管理（commit, rollback）は、このクラスの責務外であり、
 呼び出し元のService層で行う必要があります。

Type Parameters:
    T: このリポジトリが扱うSQLAlchemyモデルの型。

Attributes:
    session (Session): データベース操作に使用するSQLAlchemyのセッション。
    model (Type[T]): このリポジトリが操作対象とするモデルクラス。

Example:
    `Company`モデルを扱う具象リポジトリの実装例です。

    ```python
    from sqlalchemy.orm import Session
    from .base_repository import BaseRepository
    from ..db_models import Company

    class CompanyRepository(BaseRepository[Company]):
        def __init__(self, session: Session):
            super().__init__(session, Company)

        def find_by_name(self, name: str) -> list[Company]:
            # ドメイン固有のメソッドをここに追加
    ```
"""

from typing import Type, TypeVar, Generic, Any
from sqlalchemy.orm import Session
from sqlalchemy import select

T = TypeVar("T")


class BaseRepository(Generic[T]):
    def __init__(self, session: Session, model: Type[T]):
        self.session = session
        self.model = model

    def get(self, id: Any) -> T | None:
        return self.session.get(self.model, id)

    def get_all(self) -> list[T]:
        return list(self.session.scalars(select(self.model)).all())

    def add(self, entity: T) -> None:
        self.session.add(entity)

    def upsert(self, entity: T) -> T:
        return self.session.merge(entity)

    def delete(self, entity: T) -> None:
        self.session.delete(entity)
