# `api.py` リファクタリングガイド (v2.0)

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
*   **修正方針**: `element_id`とオプショナルな`context_id`でDataFrameをフィルタリングし、安全に値を取得するロジックが実装済みです。

### 【対処済み】 `_company_mapping(source_df: pd.DataFrame) -> dict`

*   **役割**: `source_df`から会社情報を抽出し、`Company`モデルに対応する辞書を作成する。
*   **修正方針**: `config.toml`の定義に基づき、`_get_value`を呼び出して会社情報辞書を構築し、必須項目を検証するロジックが実装済みです。

### 【対処済み】 `_financial_report_mapping(source_df: pd.DataFrame, company_id: int) -> dict`

*   **役割**: `source_df`から報告書情報を抽出し、`Financial_report`モデル用の辞書を作成する。
*   **修正方針**: `config.toml`の定義と`company_id`を基に報告書情報辞書を構築し、正規表現ヘルパーを用いて会計年度と四半期をパースするロジックが実装済みです。

### `_financial_item_mapping` と関連処理

`financial_items`はマスターテーブルであり、`element_id`にユニーク制約があるため、単純にCSVの項目を毎回登録することはできません。そのため、**「DBとの差分をチェックし、存在しない項目のみを登録する」**というロジックが不可欠です。

この処理は、`_financial_item_mapping`関数と、それを呼び出す上位の処理フロー（例: `save_financial_data_to_db`）とで、以下のように役割を分担します。

#### `_financial_item_mapping(source_df: pd.DataFrame) -> list[dict]` の修正方針

この関数の責務は、**DBを意識せず、DataFrameからの情報抽出と整形に専念します。**

1.  **役割**: `source_df`に存在するすべてのユニークな財務項目を抽出し、`Financial_item`モデルのスキーマに準拠した辞書の**候補リスト**を作成する。
2.  **実装**: 
    1.  `source_df`から財務項目に該当する行をフィルタリングします（例: `element_id`が`jppfs_cor:`で始まる行など）。
    2.  `element_id`をキーにして行を重複排除し（`df.drop_duplicates(subset=['element_id'])`）、ユニークな財務項目のリストを作成します。
    3.  各項目について、`element_id`、`item_name_jp` (-> `item_name`)、`unit_id` (-> `unit_type`) をマッピングした辞書を作成します。
    4.  `category`は、`context_id`に含まれるキーワード（`Consolidated`, `NonConsolidated`など）や`element_id`のプレフィックスから判定するロジックを実装します。
    5.  作成した辞書のリストを返します。


### `_financial_data_mapping(source_df: pd.DataFrame, report_id: int, item_id_map: dict) -> list[dict]`

*   **役割**: `source_df`の各行を`Financial_data`モデル用の辞書のリストに変換する。
*   **修正方針**:
    1.  `report_id`と、`element_id`をキーにDBの`item_id`を値に持つ辞書 (`item_id_map`) を引数で受け取ります。
    2.  財務データに該当する行（例: `element_id`が`jppfs_cor:`で始まる行）のみを対象にループ処理します。
    3.  各行について、以下の情報を抽出・判定して`Financial_data`モデル用の辞書を構築します。
        *   `report_id`: 引数の値をそのまま利用。
        *   `item_id`: `item_id_map`を使い、行の`element_id`から対応するDBの`item_id`を引きます。`map`に存在しない`element_id`はエラーとして記録するか、スキップします。
        *   `context_id`, `period_type`, `consolidated_type`: DataFrameの各カラムから値をそのまま、あるいは`db_models`のenum型に合わせて変換してマッピングします。
        *   `value`, `value_text`, `is_numeric`: `standardize_raw_data`で処理済みの各カラムから値をマッピングします。

---

## 4. メイン処理フローとDB永続化の実装方針

現在の`save_financial_data_to_db`は未実装であり、これをリファクタリングの最終目標として完成させます。以下に、`api.py`と`db_controller.py`に実装すべき処理フローと関数を示します。

### 4.1. `api.py`のメイン処理フロー (`save_financial_bundle`)

`save_financial_data_to_db`を`save_financial_bundle`に改名し、以下のロジックを実装します。

```python
# in api.py
def save_financial_bundle(df: pd.DataFrame) -> bool:
    # 1. データ標準化
    processed_df = standardize_raw_data(df)

    # 2. 会社情報の取得とDB永続化
    company_data = _company_mapping(processed_df)
    company_id = db.get_or_create_company(company_data)
    if not company_id:
        logger.error("会社の取得または作成に失敗しました。")
        return False

    # 3. 財務項目マスターの取得と差分登録
    # 3-1. CSVから候補リストを作成
    item_candidates = _financial_item_mapping(processed_df)
    candidate_element_ids = [item['element_id'] for item in item_candidates]

    # 3-2. DBから既存項目を取得
    existing_items_map = db.get_items_by_element_ids(candidate_element_ids)
    existing_element_ids = set(existing_items_map.keys())

    # 3-3. 新規項目のみを抽出してDBに登録
    new_items_to_insert = [item for item in item_candidates if item['element_id'] not in existing_element_ids]
    if new_items_to_insert:
        db.bulk_insert_items(new_items_to_insert)

    # 3-4. 完全なIDマップを作成
    # 再度DBから全項目を取得して、最新のIDで完全なマップを作成
    final_item_id_map = db.get_items_by_element_ids(candidate_element_ids)

    # 4. 財務報告書と財務データのマッピング
    report_data = _financial_report_mapping(processed_df, company_id)
    # report_dataからfiscal_year_and_quarterを削除
    report_data.pop('fiscal_year_and_quarter', None)

    # _financial_data_mappingを呼び出す前に、reportをDBに保存してreport_idを取得する必要がある
    # これはsave_financial_bundleの責務

    # 5. トランザクション内で一括保存
    # report_dataと、これから作成するfinancial_data_listをdb_controllerに渡す
    # financial_data_list = _financial_data_mapping(processed_df, report_id, final_item_id_map)
    # return db.save_report_and_data(report_data, financial_data_list)
    return True # 未実装のため暫定
```

### 4.2. `db_controller.py`の拡張

上記の処理フローを実現するため、`db_controller.py`に以下の高レベルな関数を実装する必要があります。

1.  **`get_or_create_company(company_data: dict) -> int`**
    *   **役割**: `edinet_code`をキーに`companies`テーブルを検索します。
    *   **存在する場合**: そのレコードの`company_id`を返します。
    *   **存在しない場合**: `company_data`を使って新しいレコードを挿入し、その新しい`company_id`を返します。
    *   **利点**: 冪等性（べきとうせい）を保証し、同じ会社が重複して登録されるのを防ぎます。

2.  **`get_items_by_element_ids(element_ids: list[str]) -> dict[str, int]`**
    *   **役割**: `element_id`のリストを受け取り、`financial_items`テーブルを検索します。
    *   **処理**: `WHERE element_id IN (...)`句を使い、一度のクエリで効率的に検索します。
    *   **返り値**: `{element_id: item_id}` の形式の辞書を返します。

3.  **`bulk_insert_items(items: list[dict]) -> bool`**
    *   **役割**: `Financial_item`モデル用の辞書のリストを受け取り、`bulk_insert_mappings`などを使って効率的に一括挿入します。

4.  **`save_report_and_data(report_data: dict, data_list: list[dict]) -> bool`**
    *   **役割**: トランザクション内で財務報告書と関連データをアトミックに保存します。
    *   **処理**:
        1.  トランザクションを開始します。
        2.  `report_data`を`financial_reports`テーブルに挿入し、新しい`report_id`を取得します。
        3.  `data_list`内のすべての辞書に、取得した`report_id`を追加します。
        4.  `data_list`を`financial_data`テーブルに一括挿入します。
        5.  トランザクションをコミットします。エラーが発生した場合はロールバックします。
