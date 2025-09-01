"""
Repositoryパターンの各クラスの基礎クラス

* 責務（Do）
1. データベースセッションの保持
2. 汎用CRUD操作の提供
3. 型安全性：具象Repositoryクラスの扱うモデルの型を明示する

* 責務外（Don't）
1. トランザクション管理：commit, rollback, closeは呼び出し元のService層の責務
2. ドメイン固有のビジネスロジック提供：ジェネリクス（TypeVar）を使用して、具象Repositoryクラスのメソッドの引数の型を明示する
"""
import os
import logging
import toml
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, scoped_session, sessionmaker
from sqlalchemy.exc import SQLAlchemyError


def __init__(self, session:Session):
    self.session = session
