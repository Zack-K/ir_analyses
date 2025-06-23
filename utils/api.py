import os
import requests
import zipfile
import io
import chardet
import glob
import pandas as pd
from config.config import API_ENDPOINT, API_DOWNLOAD
import logging

# 標準ロガーの取得
logger = logging.getLogger(__name__)

"""
会社名を受取り、それに対応するdocuId(EDINETの書類ID)を返却する関数

sd_df: pd.DataFrame 会社名とdocIDを含むデータフレーム EDINET「書類一覧API」の返却値
company_name: str 会社名 sd_dfから値として抽出したもの

return: str 会社名と対応するdocId これを取得することで企業ごとの財務情報を取得可能
"""
def get_doc_id(sd_df, company_name:str):
    target_company = sd_df.loc[(sd_df["filerName"] == company_name)]
    if target_company.empty:
        raise ValueError(f"会社名: {company_name} が見つかりませんでした")
    doc_id = target_company["docID"].iloc[0]
    return doc_id


"""
財務データの取得したい日付を受取り、その日付に提出された会社名を含むデータフレームを返却する

submiting_date: str fmt:yyyy-mm-dd
API_KEY: str  EDINETのAPIキー(環境変数/config/シークレットから取得予定)

return: pd.DataFrame or none
"""
def get_company_list(submiting_date: str, API_KEY: str) -> pd.DataFrame | None:

    try:
        # 「書類一覧API」のリクエストURLを作成
        response = requests.get(
            f"{API_ENDPOINT}/documents.json",
            params={"date": submiting_date, "type": 2,  # 1=メタデータのみ、2=提出書類一覧及びメタデータ 
            "Subscription-Key": API_KEY},
            timeout=30,  # 30秒のタイムアウトを設定
        )
        response.raise_for_status()
        docs_submitted_json = response.json()
    except Exception as e:
        logger.error(f"APIに接続できませんでした。:{e}")


    # 取得データの確認
    if "results" in docs_submitted_json:
        sd_df = pd.DataFrame(docs_submitted_json["results"])
        # TODO　ph2では、四半期報告書だけでなく有価証券報告書も取得分析可能にする
        sd_df = sd_df[sd_df["docDescription"].str.contains("四半期報告書", na=False)]
        return sd_df
    else:
        logger.error("データが取得できませんでした。")
        return None


"""
財務データを企業ごとにフォルダーに分割、CSVデータをEDINET APIを通じてダウンロードする

sd_df: pd.DataFrame 「書類一覧API」で取得したデータフレーム
API_KEY: str         EDINET APIのAPIキー

return company_financial_dataframe_dict
"""
def fetch_financial_data(sd_df: pd.DataFrame, API_KEY: str) -> dict:
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
                    "Subscription-Key": API_KEY,
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
                        logger.info(f"{name}:{doc_id}のファイルをダウンロードしました")
        except requests.exceptions.RequestException as e:
            logger.error(f"リクエスト中にエラーが発生しました: {e}")
        except zipfile.BadZipFile as e:
            logger.error(f"ZIPファイルの処理中にエラーが発生しました: {e}")

    company_financial_dataframe_dict = {}
    for name in company_name_list:
        docId = get_doc_id(name)
        csvfile = glob.glob(f"download/{docId}/XBRL_TO_CSV/*.csv")
        if not csvfile:
            logger.error(f"CSVファイルが見つかりません: {docId}")
            continue
        csv_file_path = csvfile[0]
        logger.info(csv_file_path)
        with open(csv_file_path, "rb") as f:
            raw_data = f.read()
            result = chardet.detect(raw_data)
            encoding = result["encoding"]
            logger.info(f"Detected encoding: {encoding}")

        company_financial_dataframe_dict[name] = pd.read_csv(csv_file_path, encoding=encoding, delimiter="\t")

    return company_financial_dataframe_dict