"""
DBコントローラー用モジュール
"""
import os
import logging
import toml

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.schema import Column
from sqlalchemy.types import String, Integer, DateTime
from sqlalcemy.orm import sessionmaker


# 標準ロガーの取得
logger = logging.getLogger(__name__)


# streamlitの設定読み込み
def load_config():
    """環境に応じて設定ファイルを読み込む関数

    Returns:
        dict: 設定ファイルの内容、または空のdict
    """
    # 環境に応じた設定ファイルパスを試行
    config_paths = [
        "/config/config.toml",  # Docker環境
        "./config/config.toml",  # ローカル環境（プロジェクトルートから実行）
        "config/config.toml",  # ローカル環境（相対パス）
    ]

    for config_path in config_paths:
        if os.path.exists(config_path):
            try:
                config = toml.load(config_path)
                logger.info("設定ファイル読み込み成功:%s", config_path)
                return config
            except Exception as e:
                logger.error("設定ファイル読み込み失敗:%s", e)
                continue

    logger.warning("設定ファイルが見つかりません。デフォルト設定を使用します。")
    return {}

# 設定の読み込み
config = load_config()

def get_db_engine():
    """
    DBエンジンを作成する関数

    Returns:
        sqlalchemy.engine.Engine: 作成したDBエンジン
    """
    # TODO SQLAlchemyでPostgreSQLに接続するための設定を記載する
    engine = create_engine(f"postgresql+psycopg2://user:password@localhost:5432/mydatabase")
    return engine

# モデルクラスを作るためのベースクラスを作成
Base = declarative_base()

# セッションを作成
Session = sessionmaker(get_db_engine)
session = SessionClass()


# TODO テーブルごとのモデルクラスを以下に作成
class Campany(Base):
    """
    会社テーブルのクラス
    """
    __tablename__ = "companies"
    company_id = Column(Integer, primary_key=True)
    edinet_code = Column(String(6), nullable=False)
    security_code = Column(String(5))
    industory_code = Column(String(10))
    create_at = Column(DateTime, nullable=False)
    update_at = Column(DateTime, nullable=False)


