"""企業データの分析を行うStreamlitアプリケーション"""

from datetime import datetime
import streamlit as st
from config.config import API_ENDPOINT, API_DOWNLOAD
import logging
import utils.api as api
import utils.analysis as analysis

# 標準loggerの導入
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)% - %(levelname)s - %(message)s'
)
st.title("企業データの統計的分析")

# TODO　日付の渡し方は検討　最終的にスケジュール指定してバッチ実行する
date = "2025-2-11"

all_documents_dataframe = api.get_company_list(date, API_KEY=API_ENDPOINT)
calculate_financial_metrics = api.fetch_financial_data(all_documents_dataframe, API_KEY=API_DOWNLOAD)

results = analysis.calculate_financial_metrics(calculate_financial_metrics["S100SSMQ"])
st.write(analysis.generate_summary_report(results))
analysis.create_visualizations(results)
st.image("安定性指標.png")
st.image("収益性指標.png")
st.image("成長率.png")
