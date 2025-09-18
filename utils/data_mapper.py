import logging
from typing import Optional, Union
import pandas as pd
import numpy as np

import utils.parser as parser

logger = logging.getLogger(__name__)


def standardize_raw_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    生のDataFrameを、DBモデルにマッピングしやすいように整形・標準化する関数。

    - カラム名を日本語から英語に統一する。
    - '値'カラムを、数値とテキストに分類し、新しいカラムを作成する。

    Args:
        df (pd.DataFrame): CSVから読み込んだ生のDataFrame。

    Returns:
        pd.DataFrame: 整形済みのDataFrame。
    """

    # カラム名を英語化、コード上からアクセスしやすくする
    column_mapping = {
        "要素ID": "element_id",
        "項目名": "item_name_jp",
        "コンテキストID": "context_id",
        "相対年度": "fiscal_year_relative",
        "連結・個別": "consolidated_type",
        "期間・時点": "period_type",
        "ユニットID": "unit_id",
        "単位": "unit_name",
        "値": "original_value",
    }
    df_renamed = df.rename(columns=column_mapping)

    # 値のデータ型変換　文字＝＞数値, 文字データは別のカラムで保持
    df_renamed["value"] = pd.to_numeric(df_renamed["original_value"], errors="coerce")
    # データ上、小数点が発生するものもあるため下二桁まで表示可能に設定
    pd.set_option("display.float_format", "{:,.2f}".format)
    df_renamed["is_numeric"] = df_renamed["value"].notna()
    df_renamed["value_text"] = df_renamed["original_value"].where(
        ~df_renamed["is_numeric"]
    )

    df_processed = df_renamed.drop(columns=["original_value"])

    logger.info("データの標準化処理が完了しました。")
    return df_processed


def _get_value(
    source_df: pd.DataFrame, element_id: str, context_id: Optional[str] = None
) -> Union[float, str, None]:
    """
    標準化されたDataFrameから、特定の要素IDに一致する単一の値を安全に抽出する。

    このヘルパー関数は、`element_id`を必須のキーとしてDataFrameを検索する。
    `context_id`が指定された場合、`element_id`が重複する際の絞り込み条件として使用される。

    検索の結果、行が見つからない場合や、行から値の抽出に失敗した場合は、
    エラーをログに記録し、例外を送出せずに`None`を返す。

    Args:
        source_df (pd.DataFrame): `standardize_raw_data`で標準化済みのDataFrame。
        element_id (str): 抽出したいデータのXBRL要素ID。
        context_id (Optional[str], optional):
            `element_id`だけでは一意に定まらない場合に使用するコンテキストID。
            Defaults to None.

    Returns:
        Union[float, str, None]:
            抽出された値（数値または文字列）。
            対応するデータが見つからない場合は `None`。
    """

    try:
        extract_df = source_df[source_df["element_id"] == element_id]
        logger.info("element_idと一致する行を取得しました")

        if len(extract_df) > 1 and context_id:
            extract_df = extract_df[extract_df["context_id"] == context_id]

        target_row = extract_df.iloc[0]
        if target_row["is_numeric"]:
            extract_value = str(int(target_row["value"]))
            logger.info("element_idと一致する行から数値データを取得しました")
        else:
            extract_value = target_row["value_text"]
            logger.info("element_idと一致する行から文字データを取得しました")
        return extract_value
    except (KeyError, IndexError) as e:
        logger.error(
            "値の取得処理中に予期せぬエラーが発生しました (ID: %s): %s", element_id, e
        )
        return None


def _company_mapping(source_df: pd.DataFrame, config: dict) -> dict:
    """
    source_dfから会社情報を抽出し、Companyモデルに対応するdictを作成する。

    本関数は、`config.toml`の`[xbrl_mapping.company]`に基づいて、
    DataFrameから会社関連の情報を抽出・マッピングします。

    処理中に以下の検証を行い、問題があれば例外を送出します。
    1.  `config.toml`に必須セクションが存在するか
    2.  `Company`モデルの必須項目 (`edinet_code`, `company_name`) が
        DataFrameから取得可能か

    Args:
        source_df (pd.DataFrame): `standardize_raw_data`で標準化済みのDataFrame

    Raises:
        KeyError: `config.toml`に`["xbrl_mapping"]["company"]`セクションが存在しない場合
        ValueError: 必須項目 (`edinet_code`, `company_name`) が`source_df`から見つからなかった場合

    Returns:
        dict: DataFrameから抽出した`Company`モデルに対応する会社情報の辞書
    """
    try:
        mapping_dict = config.get("xbrl_mapping", {}).get("company")
    except KeyError:
        logger.error(
            '設定ファイルに["xbrl_mapping"]["company"]の定義が見つかりません。'
        )
        raise

    # すべてのデータを取得する
    company_data = {
        key: _get_value(source_df, element_id)
        for key, element_id in mapping_dict.items()
    }
    # 必須項目のチェック
    required_keys = ["edinet_code", "company_name"]
    missing_keys = [key for key in required_keys if company_data.get(key) is None]

    if missing_keys:
        error_message = f"必須項目が見つかりませんでした：{','.join(missing_keys)}"
        logger.error(error_message)
        raise ValueError(error_message)

    return company_data


def _financial_item_mapping(source_df: pd.DataFrame) -> list[dict]:
    """
    DataFrameからユニークな財務項目を抽出し、DB登録候補の辞書リストを作成する。

    この関数は、DataFrameから財務項目行をフィルタリングし、重複を除外した上で、
    `Financial_item`モデルのスキーマに準拠した辞書のリストとして整形します。
    DBへの問い合わせや、入力DataFrameの妥当性検証（カラム存在チェックなど）は
    行いません。

    Args:
        source_df (pd.DataFrame): `standardize_raw_data`で処理済みのDataFrame。
            `element_id`, `item_name_jp`, `consolidated_type`, `unit_id`カラムが必須。

    Returns:
        list[dict]: `Financial_item`モデルに対応する財務項目辞書の候補リスト。

    Raises:
        KeyError: `source_df`に必須カラムが欠損している場合に送出されます。
    """
    # dfから財務項目行をフィルタリング
    financial_item_df = source_df[
        source_df["element_id"].str.contains("jppfs_cor:", na=False)
    ].copy()

    # 処理対象の行がなければ空のリストを返す
    if financial_item_df.empty:
        return []

    # element_idを基に重複を排除
    financial_item_df = financial_item_df.drop_duplicates(subset=["element_id"])

    # categoryの判定
    financial_item_df["category"] = np.where(
        financial_item_df["consolidated_type"] == "連結",
        "Consolidated",
        "Non-consolidated",
    )

    # DB登録用にカラム名を定義 (元カラム名 -> DBモデルカラム名)
    column_mapping = {
        "element_id": "element_id",
        "item_name_jp": "item_name",
        "unit_id": "unit_type",
        "category": "category",
    }

    # 必須カラムのリスト
    required_original_columns = list(column_mapping.keys())

    # 必須カラムのみを抽出 (ここでカラムがなければKeyErrorが発生する)
    return_df = financial_item_df[required_original_columns]

    # カラム名をDBモデルに合わせてリネーム
    return_df = return_df.rename(columns=column_mapping)

    # 辞書型のListへ変換して返却
    return return_df.to_dict("records")


def _financial_report_mapping(source_df: pd.DataFrame, config: dict) -> dict:
    """
    DataFrameから報告書情報を抽出し、Financial_reportモデル用の辞書を作成する。

    `config.toml`の`[xbrl_mapping.financial_report]`セクションの定義に基づき、
    DataFrameから報告書関連の情報をマッピングします。

    特に、`fiscal_year_and_quarter`キーで指定された要素IDの値
    （例: "2025年3月期第３四半期"）から正規表現を用いて会計年度と四半期を抽出し、
    それぞれ`fiscal_year`（String(4)）と`quarter_type`に設定します。

    Args:
        source_df (pd.DataFrame): `standardize_raw_data`で標準化済みのDataFrame。

    Returns:
        dict: `Financial_report`モデルに対応する報告書情報の辞書。

    Raises:
        KeyError: `config.toml`に`[xbrl_mapping.financial_report]`セクションが存在しない場合。
        ValueError: 会計年度や四半期の文字列から値のパースに失敗した場合。
    """
    try:
        mapping_dict = config.get("xbrl_mapping", {}).get("financial_report")
    except KeyError:
        logger.error(
            '設定ファイルに["xbrl_mapping"]["financial_report"]の定義が見つかりません。'
        )
        raise

    financial_report_data = {
        key: _get_value(source_df, element_id)
        for key, element_id in mapping_dict.items()
    }

    # 会計年度と四半期情報を取得
    fiscal_year_and_quarter = financial_report_data.get("fiscal_year_and_quarter")

    # 値の検証：Noneや空文字列の場合は不正な値としてエラーを送出
    if fiscal_year_and_quarter is None or fiscal_year_and_quarter == "":
        error_message = (
            f"fiscal_year_and_quarterの値が無効です: '{fiscal_year_and_quarter}'"
        )
        logger.error(error_message)
        raise ValueError(error_message)

    content = str(fiscal_year_and_quarter)

    # 会計年度を抽出（String型で保存）
    fiscal_year = parser.extract_fiscal_year(content)
    if fiscal_year is not None:
        financial_report_data["fiscal_year"] = fiscal_year
    else:
        logger.error("会計年度の抽出に失敗しました。処理を中断します。")
        raise ValueError(f"会計年度の抽出に失敗しました: '{content}'")

    # 四半期を抽出
    quarter_type = parser.extract_quarter_type(content)
    if quarter_type is not None:
        financial_report_data["quarter_type"] = quarter_type
    else:
        logger.error("四半期の抽出に失敗しました。処理を中断します。")
        raise ValueError(f"四半期の抽出に失敗しました: '{content}'")

    return financial_report_data


def financial_data_mapping(
    source_df: pd.DataFrame, report_id: int, item_id_map: dict[str, int]
) -> list[dict]:
    """
    DataFrameの財務データ行を走査し、Financial_dataモデル用の辞書リストに変換する。

    この関数は、`standardize_raw_data`で処理済みのDataFrameと、永続化済みの
    `report_id`および`item_id_map`を基に、最終的な財務データを作成します。

    item_idがDBで確定後にService層から呼び出し、実行が行われます。

    Args:
        source_df (pd.DataFrame): `standardize_raw_data`で標準化済みのDataFrame。
        report_id (int): この財務データが紐づく報告書のID (financial_reports.report_id)。
        item_id_map (dict[str, int]): XBRLの要素IDをキー、DBのitem_idを値とする辞書。
            このマップは、source_df内の全ての財務項目を網羅している必要があります。

    Returns:
        list[dict]: `Financial_data`モデルのスキーマに準拠した財務データ辞書のリスト。

    Note:
        パフォーマンスより可読性を優先し、行のループ処理を採用しています。
        データ量が極端に多い場合は、将来的にベクトル化などの最適化を検討する可能性があります。
    """

    standardize_df = source_df[
        source_df["element_id"].str.contains("jppfs_cor:", na=False)
    ]
    financial_data_list = []

    for index, row in standardize_df.iterrows():
        data_dict = {
            "report_id": report_id,
            "item_id": item_id_map[row["element_id"]],
            "duration_type": "Duration"
            if "Duration" in row["context_id"]
            else "Instant",
            "context_id": row["context_id"],
            "period_type": row["period_type"],
            "consolidated_type": row["consolidated_type"],
            "value": row["value"],
            "value_text": row["value_text"],
            "is_numeric": row["is_numeric"],
        }
        financial_data_list.append(data_dict)

    return financial_data_list


def map_data_to_models(df: pd.DataFrame, config: dict) -> dict:
    """
    DBのモデルに対応する値をデータフレームから取得しマッピングする関数
    """

    standardize_df = standardize_raw_data(df)
    company_dict = _company_mapping(standardize_df, config)
    financial_report_dict = _financial_report_mapping(standardize_df, config)
    financial_item_mapping_list = _financial_item_mapping(standardize_df)
    mapping_data_bundle = {
        "company": company_dict,
        "report": financial_report_dict,
        "items": financial_item_mapping_list,
    }
    return mapping_data_bundle
