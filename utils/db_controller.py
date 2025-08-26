"""
DBコントローラー用モジュール
"""

import os
import logging
import toml
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.exc import SQLAlchemyError
import utils.db_models as db_models
import pandas as pd

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
            except (toml.TomlDecodeError, OSError, FileNotFoundError) as e:
                # ファイルの読み込み失敗に関わる例外を取得し、ログを残す
                logger.error("設定ファイル読み込み失敗:%s", str(e))
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
        db_host = os.getenv("DB_HOST", "db").strip()  # Docker環境では"db"
        db_port = os.getenv("DB_PORT", "5432")
        db_name = os.getenv("DB_NAME", "mydatabase")

        # TODO SQLAlchemyでPostgreSQLに接続するための設定を記載する
        connection_rul = f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        engine = create_engine(connection_rul, echo=True, connect_args={'options': '-c client_encoding=utf8'})
        logger.info("DBエンジン作成成功")
        return engine

    except ImportError:
        logger.error(
            "SQLAlchemyがインストールされていません。 pip install sqlalchemy psycopg2-binary を実行してください。"
        )
        return None
    except Exception as e:
        logger.error("DBエンジン作成失敗: %s", e)
        return None


def create_session():
    """
    DBセッションを作成する関数

    Returns:
        session：DB接続で開始したセッションオブジェクト
    """
    # DBエンジン取得関数を実行
    ENGINE = get_db_engine()

    # Sessionの作成
    session = scoped_session(
        sessionmaker(
            autocommit=False,  # 自動でcommitしない
            autoflush=False,  # InsertやUpdateの更新系処理をしてもsession.commit()するまで実行しない
            bind=ENGINE,
        )
    )
    return session


def insert(model: type, data: dict[str, Any]) -> bool:
    """
    DBにINSERTを行う関数

    Args:
        model:SQLAlchemyのモデルクラス（テーブル）
        data: 挿入するデータ（カラム名:値の辞書）

    Returns:
        bool: 成功時True、失敗時False
    """
    session = create_session()

    try:
        instance = model(**data)
        session.add(instance)
        session.commit()
        logger.debug("[INSERT SUCCESS] table=%s, data=%s", model.__tablename__, data)
        return True
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(
            "[INSERT FAIL] table=%s, data=%s", model.__tablename__, data, exc_info=True
        )
        return False
    finally:
        session.close()


def read(model: type, condition: dict[str, Any]) -> pd.DataFrame:
    """
    DBから条件に合致するレコードを取得し、pandas.DataFrameで返す関数

    Args:
        model: SQLAlchemyのモデルクラス（テーブル）
        condition: 検索条件（カラム名:値の辞書）

    Returns:
        pd.DataFrame: 条件に合致したレコードを格納したDataFrame。
            - レコードが存在しない場合や例外発生時は空のDataFrameを返す。
            - DataFrameのカラム名はモデルの属性名に対応。
            - SQLAlchemyの内部属性（_sa_instance_state）は自動的に除去される。
            - streamlit等でのデータ可視化・グラフ化にそのまま利用可能。
    """
    session = create_session()
    try:
        results = session.query(model).filter_by(**condition).all()
        # 取得した結果をpandasのDataFrameに変換
        df = pd.DataFrame([result.__dict__ for result in results])
        # sqlalchemyの内部属性（不要なデータ）を削除
        if "_sa_instance_state" in df.columns:
            df = df.drop(columns=["_sa_instance_state"])
        
        logger.debug(
            "[READ SUCCESS] table=%s, condition=%s, count=%d",
            model.__tablename__,
            condition,
            len(results),
        )
        return df
    except SQLAlchemyError as e:
        logger.error(
            "[READ FAIL] table=%s, condition=%s",
            model.__tablename__,
            condition,
            exc_info=True,
        )
        return pd.DataFrame()
    finally:
        session.close()


def update(model: type, filter_by: dict[str, Any], update_data: dict[str, Any]) -> bool:
    """
    DBのレコードを更新する関数

    Args:
        model: SQLAlchemyのモデルクラス（テーブル）
        filter_by: 更新対象の条件（カラム名:値の辞書）
        update_data: 更新内容（カラム名:値の辞書）

    Returns:
        bool: 成功時True、失敗時False
    """
    session = create_session()
    try:
        instance = session.query(model).filter_by(**filter_by).first()
        if instance:
            for key, value in update_data.items():
                setattr(instance, key, value)
            session.commit()
            logger.debug(
                "[UPDATE SUCCESS] table=%s, filter=%s, update=%s",
                getattr(model, "__tablename__", str(model)),
                filter_by,
                update_data,
            )
            return True
        else:
            logger.debug(
                "[UPDATE FAIL] table=%s, filter=%s (対象なし)",
                getattr(model, "__tablename__", str(model)),
                filter_by,
            )
            return False
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(
            "[UPDATE FAIL] table=%s, filter=%s, update=%s",
            getattr(model, "__tablename__", str(model)),
            filter_by,
            update_data,
            exc_info=True,
        )
        return False
    finally:
        session.close()


def delete(model: type, filter_by: dict[str, Any]) -> bool:
    """
    DBに該当する条件のレコードを参照し、該当レコードをDELETEする関数

    Args:
        model:SQLAlchemyのモデルクラス（テーブル）
        data:削除するデータ（カラム名:値の辞書）

    ※今回はカスケード削除（関連する子レコードも同時削除）に対応するために、Deleteのクエリは直接生成は行わない
    ※複数削除が必要になった場合は、要設計変更

    Returns:
        bool: 成功時True、失敗時False
    """
    session = create_session()
    try:
        instance = session.query(model).filter_by(**filter_by).first()
        if instance:
            session.delete(instance)
            session.commit()
            logger.debug(
                "[DELETE SUCCESS] table=%s, data=%s", model.__tablename__, filter_by
            )
            return True
        else:
            logger.debug(
                "[DELETE FAIL] table=%s, data=%s", model.__tablename__, filter_by
            )
            return False
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(
            "[DELETE FAIL] table=%s, data=%s",
            model.__tablename__,
            filter_by,
            exc_info=True,
        )
        return False
    finally:
        session.close()
