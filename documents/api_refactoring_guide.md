# `api.py` リファクタリングガイド

## 1. はじめに - CSVデータの構造分析結果

EDINETからダウンロードしたXBRLをCSVに変換した実データ (`jpcrp040300-q3r-001_E01441-000_2023-12-31_01_2024-02-09.csv`) を分析した結果、当初想定されていた**横持ちデータではなく、既に縦持ち形式に近い構造**であることが判明しました。

これは、データ処理のアーキテクチャを大幅に簡素化できることを意味します。特に、最も複雑と想定された**「横持ちから縦持ちへのデータ変換処理」は不要**です。

この発見に基づき、`api.py`の修正方針を以下のように再定義します。

---

## 2. 修正の基本方針

`api.py`のリファクタリングは、以下の3つの基本方針に沿って進めてください。

### 2.1. データ処理パイプラインの簡素化

CSVデータが既に縦持ちであるため、処理パイプラインは以下のように簡素化されます。

**`①CSV読み込み → ②データマッピング → ③DB永続化`**

`api.py`の責務は、ステップ②の「データマッピング」に集中します。具体的には、pandasで読み込んだDataFrameを、`db_models.py`で定義された各 SQLAlchemyモデル（`Company`, `Financial_report`, `Financial_item`, `Financial_data`）の形式に変換します。

### 2.2. `config.toml`によるマッピング定義の活用

`config.toml`には、XBRLの要素名とDBモデルのカラムとの対応関係が既に定義されています。この情報を活用し、ハードコーディングを排除します。

**`config.toml` の定義箇所:**
```toml
[xbrl_mapping.company]
edinet_code = "jpdei_cor:EDINETCodeDEI"
security_code = "jpdei_cor:SecurityCodeDEI"
industry_code ="jpdei_cor:IndustryCodeWhenConsolidatedFinancialStatementsArePreparedInAccordanceWithIndustrySpecificRegulationsDEI"
company_name = "jpcrp_cor:CompanyNameCoverPage"

[xbrl_mapping.financial_report]
document_type = "jpcrp_cor:DocumentTitleCoverPage"
fiscal_year_and_quarter = "jpcrp_cor:QuarterlyAccountingPeriodCoverPage"
fiscal_year_end = "jpdei_cor:CurrentPeriodEndDateDEI"
filing_date = "jpcrp_cor:FilingDateCoverPage"
```
`financial_items`と`financial_data`については、`config.toml`の補足説明にある通り、動的にデータを生成するため、静的なマッピングは不要です。

### 2.3. DB操作の集約とトランザクション管理

`Company`から`Financial_data`までの一連のデータ登録処理は、必ず単一のトランザクション内で実行する必要があります。これにより、データの一部だけが登録されるといった不整合を防ぎます。

`db_controller.py`に、関連するすべてのデータ（モデルごとの辞書のリストなど）を一度に受け取り、アトミックにDBへ保存する高レベルな関数（例: `save_financial_bundle`）を実装してください。`api.py`は、マッピング処理の完了後、この関数を一度だけ呼び出すようにします。

---

## 3. 各マッピング関数の詳細な修正方針

CSVを `pandas.read_csv(..., sep='\t')` で読み込んだDataFrameを `source_df` と仮定し、各マッピング関数の具体的な修正方針を以下に示します。

### 【対処済み】 `_get_value(source_df: pd.DataFrame, element_id: str, context_id: str = None) -> Any`

*   **役割**: `source_df`から特定の`element_id`と、オプションで`context_id`を持つ行を探し、その`値`カラムの値を返すヘルパー関数。
*   **修正方針**:
    1.  `element_id`でDataFrameをフィルタリングします。
    2.  `context_id`が指定されている場合は、それでさらにフィルタリングします。これにより、同じ`element_id`でもコンテキストが異なるデータを正確に取得できます。
    3.  `iloc[0]`で最初の値を取得します。**値が存在しない場合はエラーをログに記録し、呼び出し元には`None`を返す安全な設計としました。**

### 【対処済み】 `_company_mapping(source_df: pd.DataFrame) -> dict`

*   **役割**: `source_df`から会社情報を抽出し、`Company`モデルに対応する辞書を作成する。
*   **修正方針**:
    1.  `config.toml`の`[xbrl_mapping.company]`セクションからマッピング情報を読み込みます。**設定が見つからない場合は`KeyError`を送出します。**
    2.  定義された各`要素ID`について`_get_value`を呼び出し、`source_df`から値を取得して`Company`モデル用の辞書を構築します。
    3.  **データの取得後、`Company`モデルの必須項目（`edinet_code`, `company_name`）が`None`でないことを検証します。欠損している場合は`ValueError`を送出します。**
    4.  DBへの永続化は`db_controller`に任せるため、この関数は検証済みの辞書を返すことに専念します。

### `_financial_report_mapping(source_df: pd.DataFrame, company_id: int) -> dict`

*   **役割**: `source_df`から報告書情報を抽出し、`Financial_report`モデル用の辞書を作成する。
*   **修正方針**:
    1.  `company_id`を引数で受け取り、生成する辞書に含めます。
    2.  `config.toml`の`[xbrl_mapping.financial_report]`セクションからマッピング情報を読み込み、`_get_value`で値を取得します。
    3.  **会計年度と四半期のパース処理を実装します。**
        *   `config.toml`の`fiscal_year_and_quarter`で指定された要素ID (`jpcrp_cor:QuarterlyAccountingPeriodCoverPage`) の値（例: `第85期第３四半期...`）を取得します。
        *   正規表現 `r"第(\d+)期第([１２３４])四半期"` などを用いて、`fiscal_year` (`85`) と `quarter_type` (`3` -> `Q3`) を抽出します。

### `_financial_item_mapping(source_df: pd.DataFrame) -> list[dict]`

*   **役割**: `source_df`に存在するすべてのユニークな財務項目を抽出し、`Financial_item`モデル用の辞書のリストを作成する。
*   **修正方針**:
    1.  `source_df`から財務項目に該当する行をフィルタリングします（例: `要素ID`が`jppfs_cor:`で始まる行など）。
    2.  `要素ID`をキーにして行を重複排除し、ユニークな財務項目のリストを作成します。
    3.  各項目について、`element_id` (`要素ID`カラム)、`item_name` (`項目名`カラム)、`unit_type` (`ユニットID`カラム) をマッピングした辞書を作成し、リストとして返します。
    4.  `category`は、`config.toml`の補足説明にある通り、`コンテキストID`に含まれるキーワード（`Consolidated`, `NonConsolidated`など）や`要素ID`のプレフィックスから判定するロジックを実装します。

### `_financial_data_mapping(source_df: pd.DataFrame, report_id: int, item_id_map: dict) -> list[dict]`

*   **役割**: `source_df`の各行を`Financial_data`モデル用の辞書のリストに変換する。
*   **修正方針**:
    1.  `report_id`と、`element_id`をキーにDBの`item_id`を値に持つ辞書 (`item_id_map`) を引数で受け取ります。
    2.  財務データに該当する行をループ処理します。
    3.  各行について、以下の情報を抽出・判定して`Financial_data`モデル用の辞書を構築します。
        *   `report_id`: 引数の値をそのまま利用。
        *   `item_id`: `item_id_map`を使い、行の`要素ID`から対応するDBの`item_id`を引きます。
        *   `context_id`: `コンテキストID`カラムの値をそのまま利用。
        *   `period_type`, `consolidated_type`, `duration_type`: `連結・個別`カラムや`期間・時点`カラムの値を、`db_models`で定義されたenum的な文字列（例: `Consolidated`, `NonConsolidated`, `Instant`, `Duration`）に変換してマッピングします。
        *   `value`, `value_text`, `is_numeric`: `値`カラムの内容を検証します。数値に変換可能であれば`value`に格納し`is_numeric`を`True`に、`－`などのテキストであれば`value_text`に格納し`is_numeric`を`False`にします。

---

## 4. 推奨される次のステップ

1.  **`db_controller`の拡張**: `save_financial_bundle`のような、一連の財務データをトランザクション内で一括登録する関数を`db_controller.py`に実装してください。
2.  **マッピング関数の実装**: 本ドキュメントの方針に沿って、`api.py`内の**残りの**マッピング関数（`_financial_report_mapping`など）を実装してください。
3.  **メイン処理フローの構築**: 上記関数群を呼び出し、最終的に`db_controller`の関数にデータを渡す、一連の処理フローを完成させてください。


### `_get_value(source_df: pd.DataFrame, element_id: str, context_id: str = None) -> Any`

*   **役割**: `source_df`から特定の`element_id`と、オプションで`context_id`を持つ行を探し、その`値`カラムの値を返すヘルパー関数。
*   **修正方針**:
    1.  `element_id`でDataFrameをフィルタリングします。
    2.  `context_id`が指定されている場合は、それでさらにフィルタリングします。これにより、同じ`element_id`でもコンテキストが異なるデータを正確に取得できます。
    3.  `iloc[0]`で最初の値を取得します。値が存在しない場合は`None`を返すか、`KeyError`を送出するなどの例外処理を明確に定義してください。

### `_company_mapping(source_df: pd.DataFrame) -> dict`

*   **役割**: `source_df`から会社情報を抽出し、`Company`モデルに対応する辞書を作成する。
*   **修正方針**:
    1.  `config.toml`の`[xbrl_mapping.company]`セクションからマッピング情報を読み込みます。
    2.  定義された各`要素ID`について`_get_value`を呼び出し、`source_df`から値を取得して`Company`モデル用の辞書を構築します。
    3.  DBへの永続化は`db_controller`に任せるため、この関数は辞書を返すことに専念します。

### `_financial_report_mapping(source_df: pd.DataFrame, company_id: int) -> dict`

*   **役割**: `source_df`から報告書情報を抽出し、`Financial_report`モデル用の辞書を作成する。
*   **修正方針**:
    1.  `company_id`を引数で受け取り、生成する辞書に含めます。
    2.  `config.toml`の`[xbrl_mapping.financial_report]`セクションからマッピング情報を読み込み、`_get_value`で値を取得します。
    3.  **会計年度と四半期のパース処理を実装します。**
        *   `config.toml`の`fiscal_year_and_quarter`で指定された要素ID (`jpcrp_cor:QuarterlyAccountingPeriodCoverPage`) の値（例: `第85期第３四半期...`）を取得します。
        *   正規表現 `r"第(\d+)期第([１２３４])四半期"` などを用いて、`fiscal_year` (`85`) と `quarter_type` (`3` -> `Q3`) を抽出します。

### `_financial_item_mapping(source_df: pd.DataFrame) -> list[dict]`

*   **役割**: `source_df`に存在するすべてのユニークな財務項目を抽出し、`Financial_item`モデル用の辞書のリストを作成する。
*   **修正方針**:
    1.  `source_df`から財務項目に該当する行をフィルタリングします（例: `要素ID`が`jppfs_cor:`で始まる行など）。
    2.  `要素ID`をキーにして行を重複排除し、ユニークな財務項目のリストを作成します。
    3.  各項目について、`element_id` (`要素ID`カラム)、`item_name` (`項目名`カラム)、`unit_type` (`ユニットID`カラム) をマッピングした辞書を作成し、リストとして返します。
    4.  `category`は、`config.toml`の補足説明にある通り、`コンテキストID`に含まれるキーワード（`Consolidated`, `NonConsolidated`など）や`要素ID`のプレフィックスから判定するロジックを実装します。

### `_financial_data_mapping(source_df: pd.DataFrame, report_id: int, item_id_map: dict) -> list[dict]`

*   **役割**: `source_df`の各行を`Financial_data`モデル用の辞書のリストに変換する。
*   **修正方針**:
    1.  `report_id`と、`element_id`をキーにDBの`item_id`を値に持つ辞書 (`item_id_map`) を引数で受け取ります。
    2.  財務データに該当する行をループ処理します。
    3.  各行について、以下の情報を抽出・判定して`Financial_data`モデル用の辞書を構築します。
        *   `report_id`: 引数の値をそのまま利用。
        *   `item_id`: `item_id_map`を使い、行の`要素ID`から対応するDBの`item_id`を引きます。
        *   `context_id`: `コンテキストID`カラムの値をそのまま利用。
        *   `period_type`, `consolidated_type`, `duration_type`: `連結・個別`カラムや`期間・時点`カラムの値を、`db_models`で定義されたenum的な文字列（例: `Consolidated`, `NonConsolidated`, `Instant`, `Duration`）に変換してマッピングします。
        *   `value`, `value_text`, `is_numeric`: `値`カラムの内容を検証します。数値に変換可能であれば`value`に格納し`is_numeric`を`True`に、`－`などのテキストであれば`value_text`に格納し`is_numeric`を`False`にします。

---

## 4. 推奨される次のステップ

1.  **`db_controller`の拡張**: `save_financial_bundle`のような、一連の財務データをトランザクション内で一括登録する関数を`db_controller.py`に実装してください。
2.  **マッピング関数の実装**: 本ドキュメントの方針に沿って、`api.py`内の各マッピング関数を実装してください。
3.  **メイン処理フローの構築**: 上記関数群を呼び出し、最終的に`db_controller`の関数にデータを渡す、一連の処理フローを完成させてください。