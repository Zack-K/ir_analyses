"""EDINET APIを利用した財務データ取得・処理用モジュール"""

import io
import logging
import os
import zipfile
import glob
import toml

import chardet
import pandas as pd
import requests

from utils.db_models import Company, Financial_data, Financial_item, Financial_report
import utils.db_controller as db

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


def extract_dataframe_for_each_models(model: type, df: pd.DataFrame):
    """
    指定モデルに必要なカラムをDataFrameから抽出する関数

    Args:
        model: type 抽出するモデル SQLAlchemyモデルクラス
        df:pd.DataFrame 財務データがまとめられている対象のDataFrame
    Return:
        df[model]:pd.DataFrame modelに必要なカラムのみを抽出したDataFrame

    """

    model = model

    match model.__name__:
        case "Company":
            # Companyモデルに
            columns = { 
                ["edinet_code"]:["jpdei_cor:EDINETCodeDEI"],
                ["security_code"]:["jpdei_cor:SecurityCodeDEI"],
                ["industry_code"]:["jpdei_cor:IndustryCodeWhenConsolidatedFinancialStatementsArePreparedInAccordanceWithIndustrySpecificRegulationsDEI"],
                ["company_name"]:["jpcrp_cor:CompanyNameCoverPage"],
            }
               
            ]

            # TODO DataFrameから上記 columsに対応する値を抽出、dfに設定
            df

            return df[columns]

        case "Financial_data":
            # Financial_dataモデルに必要なDataFrameの要素IDを明示
            columns = {
                ["period_type"]:[],
                ["consolidated_type"]:[],
                ["duration_type"]:[],
                ["value"]:[],
                ["value_text"]:[],
                ["is_numeric"]:[],
            }
            # TODO DataFrameから上記 columsに対応する値を抽出、dfに設定

            return df[columns]
        case "Financial_items":
            # Financial_itemモデルに必要なDataFrameの要素IDを明示
            columns = {
                ["elemenem_namet_id"]:[], # これ何だっけ？必要？
                ["item_name"]:["jpcrp_cor:DocumentTitleCoverPage"],
                ["category"]:[],
                # カテゴリってどうやって取得する？
                ["unit_type"]:[]
                # 会計基準が日本なら円、米国ならドルにする？ Lambda式でif文の判定する？
            }

            # TODO DataFrameから上記 columsに対応する値を抽出、dfに設定

            return df[columns]

        case "Financial_report":
            # Financial_reportモデルに必要なDataFrameの要素IDを明示
            columns = {
                ["document_type"]:["jpcrp_cor:DocumentTitleCoverPage"],
                ["fiscal_year"]:["jpcrp_cor:QuarterlyAccountingPeriodCoverPage"], # 会計年度の判定はどうする？ロジック必要？ Lambda式でif文の判定する？
                ["quarter_type"]:["jpcrp_cor:QuarterlyAccountingPeriodCoverPage"], # 会計期間の判定はどうする？ロジック必要？Lambda式でif文の判定する？
                ["fiscal_year_end"]:["jpdei_cor:CurrentPeriodEndDateDEI"],
                ["filing_date"]:["jpcrp_cor:FilingDateCoverPage"],
            }

            # TODO DataFrameから上記 columsに対応する値を抽出、dfに設定

            return df[columns]


def dataframe_to_dict(df: pd.DataFrame) -> bool:
    """
    CSVから作成した財務データのpd.DataFrameをモデルごとにInsert可能なDictとして変換する関数

    Args:
        df: pd.DataFrame CSVから変換して作成した企業ごとの財務データ（データフレーム）

    Return:
        bool: すべてのモデルへのInsertの成功結果 成功:True, 失敗:False
    """

    # それぞれのモデルそ関数に引き渡し、返却されたDataFrameをdictに変換
    company_values = extract_dataframe_for_each_models(Company, df).to_dict()
    financial_data_values = extract_dataframe_for_each_models(
        Financial_data, df
    ).to_dict()
    financial_item_values = extract_dataframe_for_each_models(
        Financial_item, df
    ).to_dict()
    financial_report_values = extract_dataframe_for_each_models(
        Financial_report, df
    ).to_dict()

    try:
        db.insert(Company, company_values)
        db.insert(Financial_item, financial_item_values)
        db.insert(Financial_report, financial_report_values)
        db.insert(Financial_data, financial_data_values)

    except Exception as e:
        logger.error("財務データのDB登録に失敗しました: %s", e)
        return False
    finally:
        return True
