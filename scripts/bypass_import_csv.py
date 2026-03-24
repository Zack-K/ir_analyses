"""
データベースの初期化およびCSVデータの一括インポートスクリプト。

このスクリプトは以下を順次実行します：
1. 実行時にテーブルが存在しない場合、定義済みモデルに基づきDDLを実行（初期化）
2. `download`ディレクトリ内の全CSVファイルを再帰的に検索
3. 各CSVファイルをPandasのDataFrameに変換し、DBに永続化

主に環境構築時の初回データ導入や、API利用できない環境でのバックアップや復元に利用します。

実行方法：
$ docker compose exec data_processor env PYTHONPATH=/app python /scripts/bypass_import_csv.py
"""

import os
import glob
import logging
import chardet

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from utils.db_models import Base
from utils.service.unitofwork import SqlAlchemyUnitOfWork
from utils.service.financial_service import FinancialService
from utils.config_loader import ConfigLoader

logger = logging.getLogger(__name__)


def get_download_dir(__file__) -> str:
    # ダウンロードフォルダーのパスを取得
    current_file_path = os.path.abspath(__file__)
    scripts_dir = os.path.dirname(current_file_path)
    project_root = os.path.dirname(scripts_dir)

    download_dir = os.path.join(project_root, "download")
    return download_dir


if __name__ == "__main__":
    download_dir = get_download_dir(__file__)

    # configを読み込み、DB接続情報を取得
    config_loader = ConfigLoader()
    config_data = config_loader.config
    # db enginとsessionを作成し、uowをインスタンス化
    bs_url = os.environ.get("DATABASE_URL")
    engine = create_engine(bs_url)
    # DDLを実行してテーブルを作成
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False)

    # download配下にあるフォルダーを再帰的に確認、csvファイルをpd.DataFrameに変換
    download_list = glob.glob(f"{download_dir}/**/*.csv", recursive=True)

    # ループ処理内で、1件ずつデータ永続化処理を呼び出し
    for financial_data_csv in download_list:
        uow = SqlAlchemyUnitOfWork(session_factory)
        # financialserviceもインスタンス化
        service = FinancialService(uow)

        with open(financial_data_csv, "rb") as f:
            raw_data = f.read()
            result = chardet.detect(raw_data)
            encoding = result["encoding"]
            logger.info("Detected encoding: %s", encoding)

            company_df = pd.read_csv(
                financial_data_csv, encoding=encoding, delimiter="\t"
            )
            if not company_df.empty:
                with uow:
                    service.save_financial_data_from_dataframe(company_df, config_data)
                    print(" -> Saved.")
            else:
                print(" -> Failed to Save data.")
