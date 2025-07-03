"""
IRAnalysesプロジェクトのユーティリティモジュール

このパッケージには以下のモジュールが含まれています:
- api: EDINET APIを利用した財務データ取得・処理  
- analysis: 財務データの分析・可視化
"""

__version__ = "1.0.0"
__author__ = "IR Analyses Project"

# パッケージレベルでのインポート
from .api import *
from .analysis import *
from .db_controller import *

__all__ = [
    # api モジュールからエクスポート
    "get_doc_id",
    "get_company_list",
    "fetch_financial_data", 
    "load_config",
    
    # analysis モジュールからエクスポート
    "calculate_financial_metrics",
    "generate_summary_report",
    "create_visualizations"
    
    # TODO db_controller モジュールからエクスポートを記入予定