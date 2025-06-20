import os
import requests
import zipfile
import io
import chardet
import glob
import pandas as pd
from config.config import API_ENDPOINT, API_DOWNLOAD

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

return: pd.DataFrame or str
"""
def get_company_list(submiting_date: str, API_KEY: str):

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
        return f"APIリクエストでエラー: {e}"


    # 取得データの確認
    if "results" in docs_submitted_json:
        sd_df = pd.DataFrame(docs_submitted_json["results"])
        # TODO　ph2では、四半期報告書だけでなく有価証券報告書も取得分析可能にする
        sd_df = sd_df[sd_df["docDescription"].str.contains("四半期報告書", na=False)]
        return sd_df
    else:
        err_message = "データが取得できませんでした。"
        return err_message


"""
財務データを企業ごとにフォルダーに分割、CSVデータをEDINET APIを通じてダウンロードする


"""
def get_financial_data(sd_df, API_KEY: str):

    # TODO　現状ベタ打ちで2件のみ取得しているが、データフレームの行数分取得するようにする
    company_name_list = sd_df["filerName"][:2]

    os.makedirs("download", exist_ok=True)

    for name in company_name_list:
        doc_id = get_doc_id(sd_df, name)
        try:
            url = f"{API_DOWNLOAD}/documents/{doc_id}"
            print(url)
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
            print(respose)
            with zipfile.ZipFile(io.BytesIO(respose.content)) as z:
                for file in z.namelist():
                    if file.startswith("XBRL_TO_CSV/jpcrp") and file.endswith(".csv"):
                        z.extract(file, path=f"download/{doc_id}")
                        print(f"{name}:{doc_id}のファイルをダウンロードしました")
        except requests.exceptions.RequestException as e:
            print(f"リクエスト中にエラーが発生しました: {e}")
        except zipfile.BadZipFile as e:
            print(f"ZIPファイルの処理中にエラーが発生しました: {e}")

    dfs = {}

    for name in company_name_list:
        docId = get_doc_id(name)
        csvfile = glob.glob(f"download/{docId}/XBRL_TO_CSV/*.csv")
        if not csvfile:
            print(f"CSVファイルが見つかりません: {docId}")
            continue
        csv_file_path = csvfile[0]
        print(csv_file_path)
        with open(csv_file_path, "rb") as f:
            raw_data = f.read()
            result = chardet.detect(raw_data)
            encoding = result["encoding"]
            print(f"Detected encoding: {encoding}")

        dfs[name] = name
        dfs[docId] = pd.read_csv(csv_file_path, encoding=encoding, delimiter="\t")