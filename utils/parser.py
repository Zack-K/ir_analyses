"""
テキスト解析に関連するヘルパー関数群を格納するモジュール。

XBRLデータから特定の情報（会計年度、四半期など）を抽出するための、
再利用可能な関数を提供します。
"""
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

def extract_fiscal_year(content: str) -> Optional[str]:
    """
    実際のXBRLデータ形式に対応した会計年度抽出

    例: "第121期 第３四半期(自  2023年10月１日  至  2023年12月31日)"
    """
    # パターン1: 日付範囲から西暦を抽出
    pattern_date_range = r"自\s*(\d{4})年.*?至\s*(\d{4})年"
    match_date = re.search(pattern_date_range, content)
    if match_date:
        # start_year = int(match_date.group(1))
        end_year = int(match_date.group(2))
        # 通常、会計年度は終了年度を使用
        return str(end_year)

    # パターン2: 単純な4桁年度パターン
    pattern_year = r"(\d{4})"
    match_year = re.search(pattern_year, content)
    if match_year:
        year_str = match_year.group(1)
        year_int = int(year_str)
        if 1990 <= year_int <= 2100:
            return year_str

    logger.warning("会計年度の抽出に失敗しました: '%s'", content)
    return None


def extract_quarter_type(content: str) -> Optional[str]:
    """
    実際のXBRLデータ形式に対応した四半期抽出

    例: "第121期 第３四半期(自  2023年10月１日  至  2023年12月31日)"
    """
    pattern_quarter = r"第\s*([0-4０-４一二三四１２３４]+)\s*四半期"
    match_quarter = re.search(pattern_quarter, content)

    if match_quarter is None:
        logger.warning("四半期の抽出に失敗しました: '%s'", content)
        return None

    quarter_text = match_quarter.group(1).strip()
    quarter_num = convert_quarter_to_number(quarter_text)

    if quarter_num is not None and 1 <= quarter_num <= 4:
        return f"Q{quarter_num}"
    else:
        logger.warning(
            "四半期の変換に失敗しました: '%s' (content: '%s')", quarter_text, content
        )
        return None


def convert_quarter_to_number(quarter_text: str) -> Optional[int]:
    """
    抽出した四半期文字列を数値型に変換するヘルパー関数

    Args:
        quarter_text (str): 四半期を表す文字列（漢数字、全角数字、半角数字）

    Returns:
        Optional[int]: 変換された四半期番号（1-4）。変換できない場合はNone。
    """
    to_number_mapping = {
        "一": 1,
        "二": 2,
        "三": 3,
        "四": 4,
        "１": 1,
        "２": 2,
        "３": 3,
        "４": 4,  # 全角数字
        "1": 1,
        "2": 2,
        "3": 3,
        "4": 4,  # 半角数字
    }

    if quarter_text in to_number_mapping:
        return to_number_mapping[quarter_text]

    # 直接数値変換を試行
    try:
        num = int(quarter_text)
        return num if 1 <= num <= 4 else None
    except ValueError:
        logger.warning("四半期文字列の変換に失敗しました: '%s'", quarter_text)
        return None
    