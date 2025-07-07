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
from sqlalchemy.orm import scoped_session, sessionmaker


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
    try:
        # 環境変数からDB接続情報を取得    
        db_user = os.getenv("DB_USER", "user")
        db_password = os.getenv("DB_PASSWORD", "password")
        db_host = os.getenv("DB_HOST", "db")  # Docker環境では"db"
        db_port = os.getenv("DB_PORT", "5432")
        db_name = os.getenv("DB_NAME", "mydatabase")



        # TODO SQLAlchemyでPostgreSQLに接続するための設定を記載する
        connection_rul = f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        engine = create_engine(
                                connection_rul, 
                                encoding = "utf-8", 
                                echo=True
                                )
        logger.info("DBエンジン作成成功")
        return engine


    except ImportError:
        logger.error("SQLAlchemyがインストールされていません。 pip install sqlalchemy psycopg2-binary を実行してください。")
        return None
    except Exception as e:
        logger.error(f"DBエンジン作成失敗: {e}")
        return None



def create_session():
    """
        DBセッションを作成する関数

        return:
            session：DB接続で開始したセッションオブジェクト
    """
    # DBエンジン取得関数を実行
    ENGINE = get_db_engine()

    # Sessionの作成
    session = scoped_session(
        sessionmaker(
            autocommit = False, # 自動でcommitしない
            autoflush = False,# InsertやUpdateの更新系処理をしてもsession.commit()するまで実行しない
            bind = ENGINE
        )
    )
    return session
