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

# セレクトボックス用データの取得
engine = st.connection("sql", type="sql").engine
SessionFactory = sessionmaker(bind=engine)
uow_instance = uow.SqlAlchemyUnitOfWork(SessionFactory)
financial_service = FinancialService(uow_instance)
company_list = financial_service.get_company_selection_list()

# 辞書型に変換してキーに企業名とEDINETコードを設定
company_dict = {name: code for name, code in company_list}

# サイドバーにセレクトボックスを設定
selected_company = st.sidebar.selectbox("Choose Company", list(company_dict.keys()))

# サイドバーで選択した企業に対応するEDINET codeから財務データを取得
edinet_code = company_dict[selected_company]
financial_summary = financial_service.get_financial_summary(edinet_code)

if financial_summary:
    # TODO チャートにいれる具体的な計算結果やロジックは後ほど実装予定
    st.header(financial_summary.company_name)
    st.write(financial_summary.period_name)

    # 各種利益率（今期）を3列表示
    #TODO 過去の利益率を取得するメソッドを作成し st.metricのdeltaに入れて比較したい
    col1, col2, col3 = st.columns(3)
    col1.metric(
        "売上高利益率",
        f"{financial_summary.net_profit_rate:.2f}%"
        if financial_summary.net_profit_rate is not None
        else "N/A",
    )
    col2.metric(
        "営業利益率",
        f"{financial_summary.operation_profit_rate:.2f}%"
        if financial_summary.operation_profit_rate is not None
        else "N/A",
    )
    col3.metric(
        "経常利益率",
        f"{financial_summary.ordinary_profit_rate:.2f}%"
        if financial_summary.ordinary_profit_rate is not None
        else "N/A",
    )

    col4, col5 = st.columns(2)
    col6, col7 = st.columns(2)
    col4.metric(
        "売上高",
        f"{financial_summary.net_sales:,}"
        if financial_summary.net_sales is not None
        else "N/A",
    )
    col5.metric(
        "営業利益",
        f"{financial_summary.operating_income:,}"
        if financial_summary.operating_income is not None
        else "N/A",
    )
    col6.metric(
        "経常利益",
        f"{financial_summary.ordinary_income:,}"
        if financial_summary.ordinary_income is not None
        else "N/A",
    )
    col7.metric(
        "純利益",
        f"{financial_summary.net_income:,}"
        if financial_summary.net_income is not None
        else "N/A",
    )
else:
    st.write("データが取得できませんでした。")
