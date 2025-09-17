import os
import sys
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from utils.api import get_company_list, fetch_single_company_dataframe
from utils.service.unitofwork import SqlAlchemyUnitOfWork
from utils.service.financial_service import FinancialService
from utils.config_loader import ConfigLoader

"""
データインポート用スクリプト
$ docker compose exec data_processor env PYTHONPATH=/app python /scripts/import_financial_data.py YYYY-MM-DD
"""

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(
            "実行時引数にダウンロードするファイルの提出日を入力してください。: python ./import_financial_data.py YYYY-MM-DD"
        )
        exit(1)
    # 1. configを読み込む
    config_loader = ConfigLoader()
    config_data = config_loader.config
    # 2. db接続準備 uowとfinancial_serviceのインスタンス立ち上げ
    db_url = os.environ.get("DATABASE_URL")
    engine = create_engine(db_url)
    session_factory = sessionmaker(bind=engine)

    uow = SqlAlchemyUnitOfWork(session_factory)
    service = FinancialService(uow)

    # 3. apiにアクセスし企業リストをDataFrameで取得
    submit_date = sys.argv[1]
    company_df = get_company_list(submit_date, config_data)
    # 4. ループ処理でget_doc_id, fetch_single_company_dataframeを利用しつつデータ永続化を1件ずつ実施
    if company_df is not None:
        for index, row in company_df.iterrows():
            doc_id = row["docID"]
            print(f"Processing {row['filerName']} (docID:{doc_id})")

            single_company_df = fetch_single_company_dataframe(doc_id, config_data)
            if single_company_df is not None:
                service.save_financial_data_from_dataframe(
                    single_company_df, config_data
                )
                print(f" -> Saved.")
            else:
                print(f" -> Failed to Fatch data.")
