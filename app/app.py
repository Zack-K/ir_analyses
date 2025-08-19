"""企業データの分析を行うStreamlitアプリケーション"""

import sys
import os
from pathlib import Path
import toml
import logging

import pandas as pd
import streamlit as st

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
    level=logging.INFO, 
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
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

# タイトルの取得
app_title = config.get("app", {}).get("title", "Default Title")
st.title(app_title)
"""
# TODO　日付の渡し方は検討　最終的にスケジュール指定してバッチ実行する
date = "2024-02-09"
API_ENDPOINT = config.get("edinetapi", {}).get("API_ENDPOINT", "dummy_key")
all_documents_dataframe = api.get_company_list(date)
API_DOWNLOAD = config.get("edinetapi", {}).get("API_DOWNLOAD", "dummy_key")
calculate_financial_metrics = api.fetch_financial_data(all_documents_dataframe)

st.dataframe(calculate_financial_metrics)

"""

"""
分析内容
- 収益性ダッシュボード
    - 売上高の推移
    - 営業利益の推移
    - 経常利益の推移
    - 純利益の推移
    - 各種利益率の推移（売上高利益率、売上高経常利益率、売上高純利益率）
"""

df = pd.read_csv("C:\Users\NDY09\Documents\ir_analyses\documents\test.csv")

st.dataframe(df)