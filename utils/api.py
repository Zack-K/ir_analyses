"""EDINET APIを利用した財務データ取得・処理用モジュール"""

import io
import logging
import os
import zipfile
import glob
import toml
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
        '相対年度': 'fisical_year_relative',
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
    財務データのDataFram 'source_df' から
    特定の`element_id`と、オプションで`context_id`を持つ行を探し、
    その`値`カラムの値を返すヘルパー関数

    Args:
        source_df : pandas.DataFrame 値取得元の財務データ
        element_id : str 値取得条件となる項目ID
        context_id : str 項目IDが重複した場合にわたすコンテンツID(初期値：None)
    Rerturn:
        Union[float, str, None]: 財務データから取得した値。数値、文字列、または見つからない場合はNone。
    """

    try:
        extract_df = source_df[source_df['element_id'] == element_id]
        logger.info("element_idと一致する行を取得しました")

        if len(extract_df) > 1 and context_id:
            extract_df = extract_df[extract_df['context_id'] == context_id]

        target_row = extract_df.iloc[0]
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
    source_dfから会社情報を抽出し、Companyモデルに対応するdictを作るヘルパー関数
   
    Args:
        source_df:pandas.DataFrame 値取得元の財務データ 

    Rerturn:
        dict Companyモデルへの値登録用辞書
    """
    try:
        mapping_dict = config["xbrl_mapping"]["company"]
    except KeyError as e:
        logger.error("設定ファイルに[\"xbrl_mapping\"][\"company\"]の定義が見つかりません。")
        return {}
    

    company_data = {
            key: _get_value(source_df, element_id)
            for key, element_id in mapping_dict.item()
        }
    
    return company_data


def _financial_item_mapping(source_df: pd.DataFrame) -> dict:
    mapping_dict = {}
    return mapping_dict


def _financial_report_mapping(source_df: pd.DataFrame) -> dict:
    mapping_dict = {}
    return mapping_dict

def _financial_data_mapping(source_df: pd.DataFrame) -> dict:
    mapping_dict = {}
    return mapping_dict


def map_data_to_models(df) -> dict:
    """
    DBのモデルに対応する値をデータフレームから取得しマッピングする関数
    """
    
    df = standardize_raw_data(df)
    df = _company_mapping(df)
    """
    model_data_map = {
        ["Company"]: _company_mapping(df),
        ["Financial_report"]: _financial_report_mapping(df),
        ["Financial_item"]: _financial_item_mapping(df),
        ["Financial_data"]: _financial_data_mapping(df)
    }
    """
    return df

def save_financial_data_to_db(df: pd.DataFrame) -> bool:
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
