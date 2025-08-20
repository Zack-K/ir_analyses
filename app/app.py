"""企業データの分析を行うStreamlitアプリケーション"""

import sys
import os
from pathlib import Path
import toml
import logging
import chardet
import matplotlib.pyplot as pt

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

# TODO　日付の渡し方は検討　最終的にスケジュール指定してバッチ実行する
# date = "2024-02-09"
# API_ENDPOINT = config.get("edinetapi", {}).get("API_ENDPOINT", "dummy_key")
# all_documents_dataframe = api.get_company_list(date)
# API_DOWNLOAD = config.get("edinetapi", {}).get("API_DOWNLOAD", "dummy_key")
# calculate_financial_metrics = api.fetch_financial_data(all_documents_dataframe)
# st.dataframe(calculate_financial_metrics)



# 分析内容
# - 収益性ダッシュボード
#    - 売上高の推移
#    - 営業利益の推移
#    - 経常利益の推移
#    - 純利益の推移
#    - 各種利益率の推移（売上高利益率、売上高経常利益率、売上高純利益率）


path = "app/download/S100SSHR/XBRL_TO_CSV/jpcrp040300-q3r-001_E01441-000_2023-12-31_01_2024-02-09.csv"

with open(path, "rb") as f:
    raw_data = f.read()
    result = chardet.detect(raw_data)
    encoding = result["encoding"]
    logger.info("Detected encoding: %s", encoding)

df = pd.read_csv(path, encoding=encoding, delimiter="\t")

standardize_df = api.standardize_raw_data(df)

company_data = api._company_mapping(standardize_df)



st.title(f"{company_data['company_name']}")


st.dataframe(standardize_df)


# 売上高の推移 NetSalesSummaryOfBusinessResults
sales_current = (api._get_value(standardize_df,
                               'jpcrp_cor:NetSalesSummaryOfBusinessResults',
                               'CurrentYTDDuration'))
sales_prior = api._get_value(standardize_df,
                             'jpcrp_cor:NetSalesSummaryOfBusinessResults',
                             'Prior1YTDDuration')
sales_last_year = api._get_value(standardize_df,
                               'jpcrp_cor:NetSalesSummaryOfBusinessResults',
                               'Prior1YearDuration')
sales = pd.DataFrame({
    'title': ['今四半期', '前四半期', '前期' ],
    'amount (yen)': [sales_current, sales_prior, sales_last_year]
})

st.bar_chart(sales, x="title", x_label="売上高比較", y="amount (yen)", y_label="円")

# 営業利益の推移 jppfs_cor:OperatingIncome


# 経常利益の推移 jppfs_cor:OrdinaryIncome

# 純利益の推移 jppfs_cor:IncomeBeforeIncomeTaxes
income_bedore_tax_prior_1year_duration = api._get_value(
    standardize_df, 'jppfs_cor:IncomeBeforeIncomeTaxes', 'Prior1YTDDuration')
income_bedore_tax_current_duration = api._get_value(
    standardize_df, 'jppfs_cor:IncomeBeforeIncomeTaxes', 'CurrentYTDDuration')

income_bedore_tax = pd.DataFrame({
    'title': ['今四半期', '前期同四半期'],
    'amount (yen)': [
        income_bedore_tax_current_duration,
        income_bedore_tax_prior_1year_duration
    ]
})

st.bar_chart(income_bedore_tax, x="title", x_label="税引前当期純利益比較", y="amount (yen)", y_label="円")
# 各種利益率の推移（売上高利益率、売上高経常利益率、売上高純利益率）
