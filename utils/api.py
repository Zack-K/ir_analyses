"""EDINET APIを利用した財務データ取得・処理用モジュール"""

import io
import logging
import os
import zipfile
import glob

import chardet
import pandas as pd
import requests

from config.config import API_ENDPOINT, API_DOWNLOAD


# 標準ロガーの取得
logger = logging.getLogger(__name__)


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


def get_company_list(submiting_date: str, api_key: str) -> pd.DataFrame | None:
    """
    財務データの取得したい日付を受取り、その日付に提出された会社名を含むデータフレームを返却する

    submiting_date: str fmt:yyyy-mm-dd
    api_key: str  EDINETのAPIキー(環境変数/config/シークレットから取得予定)

    return: pd.DataFrame or none
    """
    try:
        response = requests.get(
            f"{API_ENDPOINT}/documents.json",
            params={
                "date": submiting_date,
                "type": 2,
                "Subscription-Key": api_key,
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


def fetch_financial_data(sd_df: pd.DataFrame, api_key: str) -> dict:
    """
    財務データを企業ごとにフォルダーに分割、CSVデータをEDINET APIを通じてダウンロードする

    sd_df: pd.DataFrame 「書類一覧API」で取得したデータフレーム
    api_key: str         EDINET APIのAPIキー

    return company_financial_dataframe_dict
    """
    company_name_list = sd_df["filerName"]

    os.makedirs("download", exist_ok=True)

    for name in company_name_list:
        doc_id = get_doc_id(sd_df, name)
        try:
            url = f"{API_DOWNLOAD}/documents/{doc_id}"
            logger.info(url)
            # EDINETの「書類取得API」に接続
            respose = requests.get(
                url,
                {
                    "type": 5,  # 5:csv 2:pdfファイル
                    "Subscription-Key": api_key,
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
                            "ファイルをダウンロードしました。: %s:%s ", 
                            name, doc_id"
                            )
        except requests.exceptions.RequestException as e:
            logger.error("リクエスト中にエラーが発生しました: %s", e)
        except zipfile.BadZipFile as e:
            logger.error("ZIPファイルの処理中にエラーが発生しました: %s", e)

    company_financial_dataframe_dict = {}
    for name in company_name_list:
        docId = get_doc_id(sd_df, name)
        csvfile = glob.glob(f"download/{docId}/XBRL_TO_CSV/*.csv")
        if not csvfile:
            logger.error("CSVファイルが見つかりません: %s", docId)
            continue
        csv_file_path = csvfile[0]
        logger.info(csv_file_path)
        with open(csv_file_path, "rb") as f:
            raw_data = f.read()
            result = chardet.detect(raw_data)
            encoding = result["encoding"]
            logger.info("Detected encoding: %s", encoding)

        company_financial_dataframe_dict[name] = pd.read_csv(
            csv_file_path, encoding=encoding, delimiter="\t"
        )

    return company_financial_dataframe_dict
