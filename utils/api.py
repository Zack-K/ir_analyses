"""EDINET APIを利用した財務データ取得・処理用モジュール"""

import io
import logging
import os
import zipfile
import glob
import toml
import re
import numpy as np
from typing import Union, Optional

import chardet
import pandas as pd
import requests

from utils.db_models import Company, Financial_data, Financial_item, Financial_report
import utils.db_controller as db

# 標準ロガーの取得
logger = logging.getLogger(__name__)



# streamlitの設定読み込み
def load_config(path: str = None) -> dict:
    """
    設定ファイル（config.toml）を読み込む。

    テスト時など、特定のパスから読み込みたい場合はpath引数を指定する。
    指定しない場合は、このファイルの位置を基準にプロジェクトルートを特定し、
    `config/config.toml` を読み込む。

    Args:
        path (str, optional): 読み込む設定ファイルの絶対パス. Defaults to None.

    Returns:
        dict: 設定ファイルの内容。読み込みに失敗した場合は空の辞書。
    """
    paths_to_check = []
    if path:
        # テスト時など、特定のパスが指定された場合
        paths_to_check.append(path)
    else:
        # 通常実行時：このファイルの場所を基準にパスを解決
        try:
            current_file_path = os.path.abspath(__file__)
            utils_dir = os.path.dirname(current_file_path)
            project_root = os.path.dirname(utils_dir)
            default_config_path = os.path.join(project_root, "config", "config.toml")
            paths_to_check.append(default_config_path)
        except NameError:
            # 対話モードなどで __file__ が未定義の場合のフォールバック
            paths_to_check.append("./config/config.toml")


    for config_path in paths_to_check:
        if os.path.exists(config_path):
            try:
                config_data = toml.load(config_path)
                logger.info("設定ファイルを読み込みました: %s", config_path)
                return config_data  # ★成功したら即座に返す
            except Exception as e:
                logger.error("設定ファイルの読み込みに失敗しました: %s, エラー: %s", config_path, e)
                continue # 次の候補パスへ

    logger.warning("有効な設定ファイルが見つかりませんでした。")
    return {} # すべての候補で見つからなかった場合


# 設定の読み込み
config = load_config()


def get_api_key():
    """
    EDINETのAPIキーを取得して、返却する関数

    いずれはホストしている環境によって、APIキーの取得方法を分岐させる予定

    Returns:
       str: 保管しているAPIキーの文字列
    """
    api_key = os.environ.get("EDINET_API_KEY")
    return api_key


def get_doc_id(sd_df: pd.DataFrame, company_name: str) -> str:
    """
    会社名を受取り、それに対応するdocuId(EDINETの書類ID)を返却する関数

    sd_df: pd.DataFrame 会社名とdocIDを含むデータフレーム EDINET「書類一覧API」の返却値
    company_name: str 会社名 sd_dfから値として抽出したもの

    return: str 会社名と対応するdocId これを取得することで企業ごとの財務情報を取得可能
    """
    target_company = sd_df.loc[(sd_df["filerName"] == company_name)]
    if target_company.empty:
        raise ValueError(f"会社名: {company_name} が見つかりませんでした")
    doc_id = target_company["docID"].iloc[0]
    return doc_id


def get_company_list(submiting_date: str) -> pd.DataFrame | None:
    """
    財務データの取得したい日付を受取り、その日付に提出された会社名を含むデータフレームを返却する

    submiting_date: str fmt:yyyy-mm-dd

    return: pd.DataFrame or none
    """
    try:
        API_ENDPOINT = config.get("edinetapi", {}).get("API_ENDPOINT")
        response = requests.get(
            f"{API_ENDPOINT}/documents.json",
            params={
                "date": submiting_date,
                "type": 2,
                "Subscription-Key": get_api_key(),
            },
            timeout=30,
        )
        response.raise_for_status()
        docs_submitted_json = response.json()
    except requests.exceptions.RequestException as e:
        logger.error("APIリクエストでエラー: %s", e)
        return None

    try:
        if "results" in docs_submitted_json:
            sd_df = pd.DataFrame(docs_submitted_json["results"])
            sd_df = sd_df[
                sd_df["docDescription"].str.contains("四半期報告書", na=False)
            ]
            return sd_df
        else:
            logger.error("APIレスポンスに'results'キーがありません。")
            return None
    except (ValueError, KeyError) as e:
        logger.error("データフレーム変換時にエラー: %s", e)
        return None


def fetch_financial_data(sd_df: pd.DataFrame) -> dict:
    """
    財務データを企業ごとにフォルダーに分割、CSVデータをEDINET APIを通じてダウンロードする

    sd_df: pd.DataFrame 「書類一覧API」で取得したデータフレーム

    return company_financial_dataframe_dict
    """
    # TODO ひとまず、テスト用に2件のみ取得 最終的には全件取得して、DataframeごとDBに放り込む
    company_name_list = sd_df["filerName"][:2]
    # company_name_list = sd_df["filerName"]

    os.makedirs("download", exist_ok=True)

    for name in company_name_list:
        doc_id = get_doc_id(sd_df, name)
        try:
            API_DOWNLOAD = config.get("edinetapi", {}).get("API_DOWNLOAD")
            url = f"{API_DOWNLOAD}/documents/{doc_id}"
            logger.info(url)
            # EDINETの「書類取得API」に接続
            respose = requests.get(
                url,
                {
                    "type": 5,  # 5:csv 2:pdfファイル
                    "Subscription-Key": get_api_key(),
                },
                timeout=30,
            )

            # csvファイルをzipで送られてくるので、会社毎にファイルを作成して配置
            logger.info(respose)
            with zipfile.ZipFile(io.BytesIO(respose.content)) as z:
                for file in z.namelist():
                    # TODO 現在は四半期報告書のみに対応、将来的に有価証券報告書にも対応させたい
                    if file.startswith("XBRL_TO_CSV/jpcrp") and file.endswith(".csv"):
                        z.extract(file, path=f"download/{doc_id}")
                        logger.info(
                            "ファイルをダウンロードしました。: %s:%s ", name, doc_id
                        )
        except requests.exceptions.RequestException as e:
            logger.error("リクエスト中にエラーが発生しました: %s", e)
        except zipfile.BadZipFile as e:
            logger.error("ZIPファイルの処理中にエラーが発生しました: %s", e)

    for name in company_name_list:
        doc_id = get_doc_id(sd_df, name)
        csvfile = glob.glob(f"download/{doc_id}/XBRL_TO_CSV/*.csv")
        if not csvfile:
            logger.error("CSVファイルが見つかりません: %s", doc_id)
            continue
        csv_file_path = csvfile[0]
        logger.info(csv_file_path)
        with open(csv_file_path, "rb") as f:
            raw_data = f.read()
            result = chardet.detect(raw_data)
            encoding = result["encoding"]
            logger.info("Detected encoding: %s", encoding)

        company_financial_dataframe = pd.read_csv(
            csv_file_path, encoding=encoding, delimiter="\t"
        )

    return company_financial_dataframe



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
        '要素ID': 'element_id',
        '項目名': 'item_name_jp',
        'コンテキストID': 'context_id',
        '相対年度': 'fiscal_year_relative',
        '連結・個別': 'consolidated_type',
        '期間・時点': 'period_type',
        'ユニットID': 'unit_id',
        '単位': 'unit_name',
        '値': 'original_value'
    }
    df_renamed = df.rename(columns=column_mapping)

    # 値のデータ型変換　文字＝＞数値, 文字データは別のカラムで保持
    df_renamed['value'] = pd.to_numeric(df_renamed['original_value'],
                                        errors='coerce')
    # データ上、小数点が発生するものもあるため下二桁まで表示可能に設定
    pd.set_option('display.float_format', '{:,.2f}'.format)
    df_renamed['is_numeric'] = df_renamed['value'].notna()
    df_renamed['value_text'] = df_renamed["original_value"].where(
        ~df_renamed["is_numeric"])

    df_processed = df_renamed.drop(columns=['original_value'])

    logger.info("データの標準化処理が完了しました。")
    return df_processed


def _get_value(source_df: pd.DataFrame,
               element_id: str,
               context_id: Optional[str] = None) -> Union[float, str, None]:
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
        extract_df = source_df[source_df['element_id'] == element_id]
        logger.info("element_idと一致する行を取得しました")

        if len(extract_df) > 1 and context_id:
            extract_df = extract_df[extract_df['context_id'] == context_id]

        target_row = extract_df.iloc[0]
        #TODO 数値型でも日付は返還しないようにチェックして文字列として保管
        if target_row['is_numeric']:
            extract_value = target_row['value']
            logger.info("element_idと一致する行から数値データを取得しました")
        else:
            extract_value = target_row['value_text']
            logger.info("element_idと一致する行から文字データを取得しました")
        return extract_value
    except (KeyError, IndexError) as e:
        logger.error("値の取得処理中に予期せぬエラーが発生しました (ID: %s): %s", element_id, e)
        return None


def _company_mapping(source_df: pd.DataFrame) -> dict:
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
        mapping_dict = config["xbrl_mapping"]["company"]
    except KeyError as e:
        logger.error("設定ファイルに[\"xbrl_mapping\"][\"company\"]の定義が見つかりません。")
        raise

    # すべてのデータを取得する
    company_data = {
            key: _get_value(source_df, element_id)
            for key, element_id in mapping_dict.items()
        }
    #　必須項目のチェック
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
    financial_item_df = source_df[source_df['element_id'].str.contains("jppfs_cor:", na=False)].copy()

    # 処理対象の行がなければ空のリストを返す
    if financial_item_df.empty:
        return []

    # element_idを基に重複を排除
    financial_item_df = financial_item_df.drop_duplicates(subset=['element_id'])

    # categoryの判定
    financial_item_df['category'] = np.where(
        financial_item_df['consolidated_type'] == "連結",
        'Consolidated',
        'Non-consolidated'
    )

    # DB登録用にカラム名を定義 (元カラム名 -> DBモデルカラム名)
    column_mapping = {
        'element_id': 'element_id',
        'item_name_jp': 'item_name',
        'unit_id': 'unit_type',
        'category': 'category'
    }

    # 必須カラムのリスト
    required_original_columns = list(column_mapping.keys())

    # 必須カラムのみを抽出 (ここでカラムがなければKeyErrorが発生する)
    return_df = financial_item_df[required_original_columns]

    # カラム名をDBモデルに合わせてリネーム
    return_df = return_df.rename(columns=column_mapping)

    # 辞書型のListへ変換して返却
    return return_df.to_dict('records')


def _financial_report_mapping(source_df: pd.DataFrame,
                              company_id: int) -> dict:
    """
    DataFrameから報告書情報を抽出し、Financial_reportモデル用の辞書を作成する。

    `config.toml`の`[xbrl_mapping.financial_report]`セクションの定義に基づき、
    DataFrameから報告書関連の情報をマッピングします。

    特に、`fiscal_year_and_quarter`キーで指定された要素IDの値
    （例: "2025年3月期第３四半期"）から正規表現を用いて会計年度と四半期を抽出し、
    それぞれ`fiscal_year`（String(4)）と`quarter_type`に設定します。

    Args:
        source_df (pd.DataFrame): `standardize_raw_data`で標準化済みのDataFrame。
        company_id (int): この報告書が紐づく会社のID (`companies.company_id`)。

    Returns:
        dict: `Financial_report`モデルに対応する報告書情報の辞書。

    Raises:
        KeyError: `config.toml`に`[xbrl_mapping.financial_report]`セクションが存在しない場合。
        ValueError: 会計年度や四半期の文字列から値のパースに失敗した場合。
    """
    try:
        mapping_dict = config["xbrl_mapping"]["financial_report"]
    except KeyError as e:
        logger.error(
            "設定ファイルに[\"xbrl_mapping\"][\"financial_report\"]の定義が見つかりません。")
        raise

    financial_report_data = {
        key: _get_value(source_df, element_id)
        for key, element_id in mapping_dict.items()
    }

    financial_report_data['company_id'] = company_id

    # 会計年度と四半期情報を取得
    fiscal_year_and_quarter = financial_report_data.get('fiscal_year_and_quarter')

    # 値の検証：Noneや空文字列の場合は不正な値としてエラーを送出
    if fiscal_year_and_quarter is None or fiscal_year_and_quarter == "":
        error_message = f"fiscal_year_and_quarterの値が無効です: '{fiscal_year_and_quarter}'"
        logger.error(error_message)
        raise ValueError(error_message)

    content = str(fiscal_year_and_quarter)

    # 会計年度を抽出（String型で保存）
    fiscal_year = _extract_fiscal_year(content)
    if fiscal_year is not None:
        financial_report_data['fiscal_year'] = fiscal_year
    else:
        logger.error("会計年度の抽出に失敗しました。処理を中断します。")
        raise ValueError(f"会計年度の抽出に失敗しました: '{content}'")

    # 四半期を抽出
    quarter_type = _extract_quarter_type(content)
    if quarter_type is not None:
        financial_report_data['quarter_type'] = quarter_type
    else:
        logger.error("四半期の抽出に失敗しました。処理を中断します。")
        raise ValueError(f"四半期の抽出に失敗しました: '{content}'")

    return financial_report_data


def _extract_fiscal_year(content: str) -> Optional[str]:
    """
    実際のXBRLデータ形式に対応した会計年度抽出
    
    例: "第121期 第３四半期(自  2023年10月１日  至  2023年12月31日)"
    """
    # パターン1: 日付範囲から西暦を抽出
    pattern_date_range = r'自\s*(\d{4})年.*?至\s*(\d{4})年'
    match_date = re.search(pattern_date_range, content)
    if match_date:
        start_year = int(match_date.group(1))
        end_year = int(match_date.group(2))
        # 通常、会計年度は終了年度を使用
        return str(end_year)

    # パターン2: 単純な4桁年度パターン
    pattern_year = r'(\d{4})'
    match_year = re.search(pattern_year, content)
    if match_year:
        year_str = match_year.group(1)
        year_int = int(year_str)
        if 1990 <= year_int <= 2100:
            return year_str

    logger.warning("会計年度の抽出に失敗しました: '%s'", content)
    return None


def _extract_quarter_type(content: str) -> Optional[str]:
    """
    実際のXBRLデータ形式に対応した四半期抽出
    
    例: "第121期 第３四半期(自  2023年10月１日  至  2023年12月31日)"
    """
    pattern_quarter = r'第\s*([0-4０-４一二三四１２３４]+)\s*四半期'
    match_quarter = re.search(pattern_quarter, content)

    if match_quarter is None:
        logger.warning("四半期の抽出に失敗しました: '%s'", content)
        return None

    quarter_text = match_quarter.group(1).strip()
    quarter_num = _convert_quarter_to_number(quarter_text)

    if quarter_num is not None and 1 <= quarter_num <= 4:
        return f"Q{quarter_num}"
    else:
        logger.warning("四半期の変換に失敗しました: '%s' (content: '%s')",
                      quarter_text, content)
        return None


def _convert_quarter_to_number(quarter_text: str) -> Optional[int]:
    """
    抽出した四半期文字列を数値型に変換するヘルパー関数
    
    Args:
        quarter_text (str): 四半期を表す文字列（漢数字、全角数字、半角数字）
        
    Returns:
        Optional[int]: 変換された四半期番号（1-4）。変換できない場合はNone。
    """
    to_number_mapping = {
        "一": 1, "二": 2, "三": 3, "四": 4,
        "１": 1, "２": 2, "３": 3, "４": 4,  # 全角数字
        "1": 1, "2": 2, "3": 3, "4": 4      # 半角数字
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


def _financial_data_mapping(source_df: pd.DataFrame, report_id: int,
                            item_id_map: dict[str, int]) -> list[dict]:
    """
    DataFrameの財務データ行を走査し、Financial_dataモデル用の辞書リストに変換する。

    この関数は、`standardize_raw_data`で処理済みのDataFrameと、永続化済みの
    `report_id`および`item_id_map`を基に、最終的な財務データを作成します。

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
    # TODO 財務データ行のフィルタリング
    # TODO 結果をまとめたリストの初期化〜フィルタリングした行をループ処理
    financial_data_list = []
    # TODO 各行をマッピング キーと値を紐づけ
    financial_data_mapping = {}
    # TODO マッピングした結果を結果リストに追加
    financial_data_list.append(financial_data_mapping)

    return financial_data_list


def map_data_to_models(df) -> dict:
    """
    DBのモデルに対応する値をデータフレームから取得しマッピングする関数
    """

    df = standardize_raw_data(df)
    df = _company_mapping(df)
    df = _financial_report_mapping(df, df['company_id'])
    item_id_map = _financial_item_mapping(df)
    #TODO DBの’Financial_item’にアクセスし、既に登録済みの内容と作成したマップの重複確認
    df = _financial_data_mapping(df, df['report_id'], item_id_map)
    """
    model_data_map = {
        ["Company"]: _company_mapping(df),
        ["Financial_report"]: _financial_report_mapping(df),
        ["Financial_item"]: _financial_item_mapping(df),
        ["Financial_data"]: _financial_data_mapping(df)
    }
    """
    return df

def save_financial_bundle(df: pd.DataFrame) -> bool:
    """
    財務データDataFrameを前処理し、各モデルに対応するデータをDBに保存する関数。

    Args:
        df: pd.DataFrame CSVから変換して作成した企業ごとの財務データ

    Return:
        bool: DBへの保存処理の成否
    """
    try:
        processed_df = standardize_raw_data(df)

        # 2. 縦持ちデータを各モデル用の辞書リストにマッピング
        model_data_map = map_data_to_models(processed_df)

        # 3. トランザクション内で各モデルのデータをDBに挿入
        db.insert(Company,model_data_map["Company"])
        db.insert(Financial_report ,model_data_map["Financial_report"])
        db.insert(Financial_item,model_data_map["Financial_item"])
        db.insert(Financial_data,model_data_map["Financial_data"])

        logger.info("財務データのDB登録に成功しました。")
        return True

    except Exception as e:
        logger.error("財務データのDB登録に失敗しました: %s", e)
        return False
