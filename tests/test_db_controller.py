"""
/utils/db_controller.py のCRUD機能をテストコード

実行方法
1. Dockerの立ち上げ
$ docker compose up -d

2. Dcokerコンテナ環境に入る
$docker compose exec streamlit_app /bin/bash 


3. コンテナ環境内でテスト実行
$ python ./tests/test_db_controller.py
"""

import sys
import os
# utilsをimportするための設定
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


import sqlalchemy
from utils.db_controller import insert, delete, create_session
from utils.db_models import Company


def run_insert_test(test_data, expected_result, test_name):
    print(f"\n=== {test_name} ===")
    result = insert(Company, test_data)
    print(f"戻り値: {result}")
    print(f"期待値: {expected_result}")
    if result == expected_result:
        print("テスト成功")
    else:
        print("テスト失敗")


def run_delete_test(filter_by, expected_result, test_name):
    print(f"\n=== {test_name} ===")
    result = delete(Company, filter_by)
    print(f"戻り値: {result}")
    print(f"期待値: {expected_result}")
    if result == expected_result:
        print("テスト成功")
    else:
        print("テスト失敗")


def clean_up_test_data(model, edinet_code):
    session = create_session()
    # edinet_codeでレコードを検索
    company = session.query(model).filter_by(edinet_code=edinet_code).first()
    try:
        if company:
            session.delete(company)
            session.commit()
            print(f"テストデータ削除完了: {edinet_code}")
        else:
            print(f"削除対象データが見つかりません: {edinet_code}")
    except Exception as e:
        session.rollback()
        print(f"削除中にエラーが発生しました: {e}")
    finally:
        session.close()


def test_insert_function():
    print("=== Company Create機能 簡易動作確認 ===")
    print("データベース接続を確認してください。")

    model = Company
    valid_company_data = {
        "edinet_code": "E00000",      # 必須、6文字以内
        "company_name": "テスト株式会社",  # 必須、200文字以内
        "security_code": "0000",      # 任意、5文字以内
        "industry_code": "1234"       # 任意、10文字以内
    }
    # 必須項目不足
    missing_required_data = {
        "company_name": "テスト株式会社"
        # edinet_codeが不足
    }

    # 制約違反
    duplicate_edinet_code = {
        "edinet_code": "E00000",      # 既存のコードと重複
        "company_name": "重複テスト株式会社"
    }

    # テスト前クリーンアップ
    clean_up_test_data(model, valid_company_data["edinet_code"])
    clean_up_test_data(model, duplicate_edinet_code["edinet_code"])

    # 正常系テスト
    run_insert_test(valid_company_data, True, "正常系: 有効なデータ")


    # 異常系テスト
    run_insert_test(missing_required_data, False, "異常系: 必須項目不足")
    run_insert_test(duplicate_edinet_code, False, "異常系: 重複制約違反")

    # テスト実行前クリーンアップ
    clean_up_test_data(model, valid_company_data["edinet_code"])
    clean_up_test_data(model, duplicate_edinet_code["edinet_code"])


def test_delete_function():
    print("=== Company Delete機能 簡易動作確認 ===")
    print("データベース接続を確認してください。")

    model = Company

    # テストデータ
    test_company_data = {
        "edinet_code": "E99999",  # テスト用のEDINETコード
        "company_name": "削除テスト株式会社",  # テスト用の会社名
        "security_code": "9999",  # テスト用の証券コード
        "industry_code": "9999"  # テスト用の業種コード
    }

    print("\n=== テストデータ準備 ===")
    insert_result = insert(model, test_company_data)
    if not insert_result:
        print("テストデータの挿入に失敗しました。テストを中止します。")
        return

    # 正常系テスト：存在するデータの削除
    run_delete_test({"edinet_code": "E99999"}, True, "正常系: 存在するデータの削除")

    # 異常系テスト：存在しないデータの削除
    run_delete_test({"edinet_code": "E99999"}, False, "異常系: 存在しないデータの削除")

    # 複数条件での削除テスト
    run_delete_test({"edinet_code": "E99999", "company_name": "削除テスト株式会社"}, False, "異常系: 複数条件での削除（データなし）")

    # テストデータのクリーンアップ（念のため）
    clean_up_test_data(model, test_company_data["edinet_code"])


if __name__ == '__main__':
    #test_insert_function()
    test_delete_function()
