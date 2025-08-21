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
#date = "2024-02-09"
#API_ENDPOINT = config.get("edinetapi", {}).get("API_ENDPOINT", "dummy_key")
#all_documents_dataframe = api.get_company_list(date)
#API_DOWNLOAD = config.get("edinetapi", {}).get("API_DOWNLOAD", "dummy_key")
#financial_data_df = api.fetch_financial_data(all_documents_dataframe)
# calculate_financial_metrics = api.fetch_financial_data(all_documents_dataframe)
# st.dataframe(calculate_financial_metrics)



# 分析内容
# - 収益性ダッシュボード
#    - 売上高の推移
#    - 営業利益の推移
#    - 経常利益の推移
#    - 純利益の推移
#    - 各種利益率の推移（売上高利益率、売上高経常利益率、売上高純利益率）

# セレクトボックス用のリスト
path_list = {
    "株式会社_山梨中央銀行":"./download/S100SPH6/XBRL_TO_CSV/jpcrp040300-q3r-001_E03562-000_2023-12-31_01_2024-02-09.csv",
    "今村証券株式会社":"./download/S100SQAH/XBRL_TO_CSV/jpcrp040300-q3r-001_E30982-000_2023-12-31_01_2024-02-09.csv",
    "日本酸素ホールディングス株式会社":"./download/S100SRF2/XBRL_TO_CSV/jpcrp040300-q3r-001_E00783-000_2023-12-31_01_2024-02-09.csv",
    "株式会社トーアミ":"./download/S100SSHR/XBRL_TO_CSV/jpcrp040300-q3r-001_E01441-000_2023-12-31_01_2024-02-09.csv",
    "四国電力株式会社":"./download/S100SSMQ/XBRL_TO_CSV/jpcrp040300-q3r-001_E04505-000_2023-12-31_01_2024-02-09.csv"
}
path = "./download/S100SSHR/XBRL_TO_CSV/jpcrp040300-q3r-001_E01441-000_2023-12-31_01_2024-02-09.csv"

with open(path, "rb") as f:
    raw_data = f.read()
    result = chardet.detect(raw_data)
    encoding = result["encoding"]
    logger.info("Detected encoding: %s", encoding)

df = pd.read_csv(path, encoding=encoding, delimiter="\t")

standardize_df = api.standardize_raw_data(df)

company_data = api._company_mapping(standardize_df)


# 売上高の推移 NetSalesSummaryOfBusinessResults
sales = "jpcrp_cor:NetSalesSummaryOfBusinessResults"
current_duration = "CurrentYTDDuration"
prior_duration = "Prior1YTDDuration"
last_year_total = "Prior1YearDuration"
sales_current = api._get_value(standardize_df, sales, current_duration)
sales_prior = api._get_value(standardize_df, sales, prior_duration)
sales_last_year = api._get_value(standardize_df, sales, last_year_total)
sales = pd.DataFrame({
    'title': ['今四半期', '前四半期', '前期累計' ],
    'amount (yen)': [sales_current, sales_prior, sales_last_year]
})



# 営業利益の推移 jppfs_cor:OperatingIncome
operation_income = "jppfs_cor:OperatingIncome"
operation_income_current = api._get_value(standardize_df, operation_income, current_duration)
operation_income_prior = api._get_value(standardize_df, operation_income,
                                        prior_duration)


operation_income_df = pd.DataFrame({
    'title': ['今四半期', '前期同四半期'],
    'amount (yen)': [operation_income_current, operation_income_prior]
})


# 経常利益の推移 jpcrp_cor:OrdinaryIncomeLossSummaryOfBusinessResults
ordinary_income = "jpcrp_cor:OrdinaryIncomeLossSummaryOfBusinessResults"
ordinary_income_current = api._get_value(standardize_df, ordinary_income,
                                         current_duration)
ordinary_income_prior = api._get_value(standardize_df, ordinary_income,
                                      prior_duration)

ordinary_income_df = pd.DataFrame({
    'title': ['今四半期', '前期同四半期'],
    'amount (yen)': [ordinary_income_current, ordinary_income_prior]
})



# 純利益の推移 jpcrp_cor:ProfitLossAttributableToOwnersOfParentSummaryOfBusinessResults
profit = "jpcrp_cor:ProfitLossAttributableToOwnersOfParentSummaryOfBusinessResults"
profit_current = api._get_value(standardize_df, profit, current_duration)
profit_prior = api._get_value(standardize_df, profit, prior_duration)

profit_df = pd.DataFrame({
    'title': ['今四半期', '前期同四半期'],
    'amount (yen)': [profit_current, profit_prior]
})


# 各種利益率の推移（売上高利益率、売上高経常利益率、売上高純利益率）



# レイアウト
st.header(f"{company_data['company_name']}")

option = st.checkbox("DataFrameを表示する")

if option:
    st.dataframe(standardize_df)

col1, col2 = st.columns(2)

with col1:
    st.header("売上高")
    st.bar_chart(sales, x="title", x_label="売上高比較", y="amount (yen)", y_label="円")

    st.header("営業利益")
    st.bar_chart(operation_income_df,
             x="title",
             x_label="営業純利益比較",
             y="amount (yen)",
             y_label="円")

with col2:
    st.header("経常利益")
    st.bar_chart(ordinary_income_df,
                x="title",
                x_label="経常利益比較",
                y="amount (yen)",
                y_label="円")

    st.header("純利益")
    st.bar_chart(profit_df,
                x="title",
                x_label="当期純利益比較",
                y="amount (yen)",
                y_label="円")
