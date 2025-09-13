"""企業データの分析を行うStreamlitアプリケーション"""

import sys
import os
from pathlib import Path
import toml
import logging

import matplotlib.pyplot as pt

import pandas as pd
import streamlit as st

from sqlalchemy.orm import sessionmaker

from utils.service.financial_service import FinancialService
import utils.service.unitofwork as uow

# 環境対応型パス設定（Streamlitベストプラクティス）
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 安全なモジュールインポート
try:
    import utils.api as api
except ImportError as e:
    st.error(f"モジュールのインポートに失敗しました: {e}")
    st.info("プロジェクトルートから 'streamlit run app/app.py' で実行してください")
    st.stop()

# 標準loggerの導入
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levellevel)s - %(message)s"
)
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

# セレクトボックス用のリスト
engine = st.connection("sql", type="sql").engine
SessionFactory = sessionmaker(bind=engine)
uow_instance = uow.SqlAlchemyUnitOfWork(SessionFactory)
financial_service = FinancialService(uow_instance)
company_list = financial_service.get_company_selection_list()

# 辞書型に変換してキーに企業名とEDINETコードを設定したい
company_dict = {name: code for name, code in company_list}

# TODO 最終的にここはDBから値を取得して企業名を絞り込む時に使うため変更予定
selected_company = st.sidebar.selectbox("Choose Company", list(company_dict.keys()))

edinet_code = company_dict[selected_company]
