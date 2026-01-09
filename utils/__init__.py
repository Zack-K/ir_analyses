"""
IRAnalysesプロジェクト

このパッケージには以下のサービス・モジュールが含まれています:

- service: ビジネスロジックとユースケースを実装するサービス層
- repository: データアクセスと永続化を担当するリポジトリ層
- db_models: SQLAlchemyを使用したデータベースモデル定義
- data_mapper: 外部データソースからDBモデルへの変換ロジック
- parser: テキスト解析のヘルパーモジュール
- api: EDINET APIを利用した財務データ取得・処理
- config_loader: 設定ファイルを読み込むローダー
"""

__version__ = "1.0.0"
__author__ = "IR Analyses Project"

# --- Service Layer ---
from .service.financial_service import FinancialService, FinancialSummaryDTO
from .service.unitofwork import UnitOfWork, SqlAlchemyUnitOfWork

# --- Configuration ---
from .config_loader import ConfigLoader

# --- Database Models ---
from .db_models import Base, Company, Financial_report, Financial_item, Financial_data

# --- EDINET API ---
from .api import get_company_list, fetch_single_company_dataframe, get_doc_id

# パッケージから公開するオブジェクトを__all__で定義
__all__ = [
    # service
    "FinancialService",
    "FinancialSummaryDTO",
    "UnitOfWork",
    "SqlAlchemyUnitOfWork",
    # config
    "ConfigLoader",
    # db_models
    "Base",
    "Company",
    "Financial_report",
    "Financial_item",
    "Financial_data",
    # api
    "get_company_list",
    "fetch_single_company_dataframe",
    "get_doc_id",
]
