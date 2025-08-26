# `api.py` リファクタリングガイド (v3.0 - ORM/Repositoryパターン適用版)

## 1. はじめに

このドキュメントは、`utils/api.py`のマッピング機能およびデータ永続化処理を、SQLAlchemyのORM機能を最大限に活用したモダンな設計（Repositoryパターン）へとリファクタリングするための方針を定義します。

**v2.0からの主な変更点:**
- **ORM中心設計**: データ操作の単位を辞書やDataFrameから **SQLAlchemyモデルオブジェクト** に移行します。
- **Repositoryパターンの導入**: `db_controller.py`を廃止し、DBとのやり取りを責務とする`Repository`層を新設します。
- **Serviceレイヤーの導入**: `api.py`と`Repository`層の間に、ビジネスロジックを担う`Service`層を設けます。

---

## 2. 修正の基本方針

リファクタリングは、以下の4つの基本方針に沿って進めます。

### 2.1. データ処理パイプラインの再定義

新しいアーキテクチャにおける処理パイプラインは以下のようになります。

**`①CSV読み込み → ②モデルオブジェクトへのマッピング → ③Serviceレイヤー経由で永続化`**

`api.py`の責務は、ステップ②の「DataFrameからモデルオブジェクトへのマッピング」に集中します。

### 2.2. ORMオブジェクト中心設計への移行

各マッピング関数 (`_..._mapping`) は、辞書を返すのではなく、**初期化されたSQLAlchemyモデルオブジェクト**を返却するように変更します。これにより、型安全性が向上し、コードが直感的になります。

### 2.3. `config.toml`によるマッピング定義の活用 (変更なし)

引き続き`config.toml`の`[xbrl_mapping]`セクションを活用し、ハードコーディングを排除します。

### 2.4. ServiceとRepositoryによる責務分離とトランザクション管理

- **Repository層**: 各モデルに対するCRUD操作（DBとの直接対話）に特化します。
- **Service層**: 複数のRepositoryを呼び出し、Upsertロジックや差分更新など、一連のビジネスロジックを組み立てます。**トランザクション管理はService層が責任を持ちます。**
- **`api.py`**: Service層のメソッドを呼び出すだけの、薄いコントローラー層となります。

### 2.5. 現状の実装状況と課題 (As-Is Analysis)

リファクタリングに着手する前の、各関連ファイルの実装状況と課題を以下にまとめます。

#### `utils/db_models.py`
- **できていること (Done):**
    - 4つの主要モデル(`Company`, `Financial_report`, `Financial_item`, `Financial_data`)の基本的なスキーマ（カラム、型、制約）が定義済み。
- **課題・未実装なこと (To-Do):**
    - **リレーションシップ未定義:** モデル間の関連を表現する `relationship` が定義されておらず、ORMの利点を活かせない。
    - **インデックス未設定:** 検索キーとなるカラム (`edinet_code`等) にインデックスが設定されておらず、パフォーマンス上の懸念がある。

#### `utils/db_controller.py`
- **できていること (Done):**
    - `insert`, `read`, `update`, `delete` といった手続き的なCRUD関数が実装済み。
- **課題・未実装なこと (To-Do):**
    - **Repositoryパターン未導入:** 設計が古く、本ガイドの方針であるRepositoryパターンに移行する必要がある。
    - **不適切なI/O:** `read`がDataFrameを返すなど、ORMオブジェクト中心の設計思想と乖離している。
    - **不十分なトランザクション管理:** 関数ごとにセッションが生成・破棄され、複数の操作をまとめるトランザクション管理ができない。

#### `utils/api.py`
- **できていること (Done):**
    - EDINET APIからのデータ取得、ZIP展開、CSV読み込み、基本的な前処理 (`standardize_raw_data`) は実装済み。
    - `_company_mapping`, `_financial_report_mapping`, `_financial_item_mapping` は、**辞書を返す形**で実装済み。
- **課題・未実装なこと (To-Do):**
    - **コアロジックの欠損:** `_financial_data_mapping` が未実装であり、全体の処理が完結しない。
    - **古い設計への依存:** `save_financial_bundle` は `db_controller.py` を直接呼び出す古い設計のままであり、機能しない。
    - **設計思想の不一致:** マッピング関数がモデルオブジェクトではなく辞書を返しており、ORM中心設計への移行が必要。
    - **Serviceレイヤーの不在:** ビジネスロジックを担うService層が存在しない。

---

## 3. 各マッピング関数のリファクタリング方針

`source_df`（標準化済みDataFrame）を引数にとる各マッピング関数の修正方針です。

### `_company_mapping(source_df: pd.DataFrame) -> Company`

- **役割**: `source_df`から会社情報を抽出し、`Company`モデルオブジェクトを作成して返す。
- **修正方針**:
    1. `config.toml`に基づき`_get_value`で各情報を取得します。
    2. `return Company(**company_data)` のように、取得したデータで`Company`オブジェクトを初期化して返します。

### `_financial_report_mapping(source_df: pd.DataFrame) -> Financial_report`

- **役割**: `source_df`から報告書情報を抽出し、`Financial_report`モデルオブジェクトを作成して返す。
- **修正方針**:
    1. `config.toml`に基づき情報を取得し、会計年度・四半期をパースします。
    2. `company_id`は引数で受け取るのではなく、後続のService層で設定するため、この段階では`None`で構いません。
    3. `return Financial_report(**report_data)` のように、`Financial_report`オブジェクトを初期化して返します。

### `_financial_item_mapping(source_df: pd.DataFrame) -> list[Financial_item]`

- **役割**: `source_df`からユニークな財務項目をすべて抽出し、`Financial_item`モデルオブジェクトのリストを作成して返す。
- **修正方針**:
    1. `element_id`で重複排除したDataFrameを作成します。
    2. 各行をループし、`Financial_item`オブジェクトを初期化してリストに追加します。
    3. **DBとの差分確認は行いません。** この関数の責務は、あくまでDataFrameからの情報抽出に限定します。

### `_financial_data_mapping(source_df: pd.DataFrame) -> list[Financial_data]`

- **役割**: `source_df`の財務データ行を`Financial_data`モデルオブジェクトのリストに変換する。
- **修正方針**:
    1. 財務データに該当する行をフィルタリングします。
    2. 各行をループし、`Financial_data`オブジェクトを初期化してリストに追加します。
    3. `report_id`と`item_id`はこの段階では設定せず、後続のService層で設定します。

---

## 4. Service/Repository層による永続化フロー

`save_financial_bundle`は`FinancialService`のようなクラスのメソッドとして再設計されます。

### 4.1. `FinancialService.save_bundle(df: pd.DataFrame)` の処理フロー

このメソッドは、セッションとトランザクションの管理下で、以下の処理を統括します。

1.  **データ標準化・マッピング**:
    - `standardize_raw_data`を呼び出します。
    - `_..._mapping`関数群を呼び出し、DataFrameから各モデルオブジェクト（`company_obj`, `report_obj`, `item_obj_list`, `data_obj_list`）を生成します。

2.  **会社情報のUpsert**:
    - `CompanyRepository.get_or_create(company_obj)` を呼び出し、DBに会社情報を永続化し、管理された`Company`オブジェクト（IDが設定済み）を取得します。

3.  **財務項目マスターの差分更新**:
    - `FinancialItemRepository.find_by_element_ids([...])` を呼び出し、`item_obj_list`のうちDBに既に存在する項目を取得します。
    - 存在しない新規項目のみを `FinancialItemRepository.bulk_save(new_items)` で一括登録します。
    - `FinancialItemRepository.find_by_element_ids([...])` を再度呼び出し、**全項目の`element_id`と`item_id`の対応マップ**を作成します。

4.  **報告書と財務データの永続化**:
    - 取得した`company.company_id`を`report_obj.company_id`に設定します。
    - `FinancialReportRepository.save(report_obj)` を呼び出し、報告書を永続化して`report_id`を取得します。
    - `data_obj_list`をループし、各`data_obj`に`report_id`と、対応マップから引いた`item_id`を設定します。
    - `FinancialDataRepository.bulk_save(data_obj_list)` を呼び出し、財務データを一括登録します。

### 4.2. 各Repositoryに必要なメソッド例

- **`CompanyRepository`**:
    - `get_or_create(company: Company) -> Company`: `edinet_code`で存在確認し、なければ追加して`Company`オブジェクトを返す。
- **`FinancialItemRepository`**:
    - `find_by_element_ids(element_ids: list[str]) -> list[Financial_item]`: 複数の`element_id`で項目を検索する。
    - `bulk_save(items: list[Financial_item])`: 複数の項目を一括で保存する。
- **`FinancialReportRepository`**:
    - `save(report: Financial_report) -> Financial_report`: 報告書を保存する。
- **`FinancialDataRepository`**:
    - `bulk_save(data_list: list[Financial_data])`: 複数の財務データを一括で保存する。

この設計により、`api.py`はデータ変換に、Serviceはビジネスロジックに、RepositoryはDBアクセスにそれぞれ専念でき、非常に見通しが良く、テストしやすい構造が実現します。
