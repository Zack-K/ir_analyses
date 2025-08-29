"""
Repositoryパターンの各クラスの基礎クラス

責務
(1)データベースセッションの保持
(2)汎用CRUD操作
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
