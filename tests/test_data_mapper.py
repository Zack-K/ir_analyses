import pytest
import pandas as pd

from utils.data_mapper import standardize_raw_data

@pytest.fixture(scope="function")
def financial_data():
    raw_data = {
          "値": ["100", "－", "200.5"],
          # ↓↓↓ 他のカラムは、関数がエラーにならないためのダミーデータです
          "要素ID": ["ID_A", "ID_B", "ID_C"],
          "項目名": ["売上", "利益", "コスト"],
          "コンテキストID": ["c1", "c2", "c3"],
          "相対年度": [0, 0, 0],
          "連結・個別": ["連結", "連結", "連結"],
          "期間・時点": ["期間", "期間", "期間"],
          "ユニットID": ["JPY", "JPY", "JPY"],
          "単位": ["円", "円", "円"],
      }
    raw_df = pd.DataFrame(raw_data)
    return raw_df

def test_standardize_raw_data_handles_hyphen(financial_data):
    processed_df = standardize_raw_data(financial_data)

    excepted_value = 100.0
    # 正常系：100は100.0と正しく変換されていること
    assert processed_df["value"].iloc[0] == excepted_value
    # 正常系： "－" 値はNaNとなること
    assert pd.isna(processed_df["value"].iloc[1])
    # 正常系："－"は数値型でないこと Falseであること
    assert not processed_df["is_numeric"].iloc[1]