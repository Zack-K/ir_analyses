# テスト実行ガイド（Docker環境）

## 概要
本ガイドは、Docker 環境でのテスト実行フロー、特に `conftest.py` を使用したテスト DB スキーマ初期化について説明します。テストは `mydatabase_test` DB を使用し、`_test` サフィックスで安全性を確保しています。

---

## 1. テスト環境の起動と初期化フロー

### 1.1. テスト用 Docker Compose の起動
```bash
# テスト環境用コンテナの起動（バックグラウンド）
docker compose up --build -d
```

**確認コマンド：**
```bash
docker compose ps
```

期待される出力：
```
NAME                    STATUS
ir_analyses-db-1        Up (healthy)
ir_analyses-streamlit_app-1  Up
ir_analyses-data_processor-1 Up
```

---

## 2. テスト DB スキーマの初期化

### 2.1. `conftest.py` を使用した自動スキーマ初期化

テスト実行時に、`conftest.py` の `engine` フィクスチャが自動的に DB スキーマを初期化します。手動初期化は不要です。

#### 動作フロー
1. `conftest.py::engine` フィクスチャ実行
   - `.env` から `DB_NAME_TEST=mydatabase_test` を取得
   - DB 名が `_test` で終わることを検証
   - `Base.metadata.create_all()` でテーブル作成
2. 各テスト実行後、`drop_all()` でスキーマ削除

### 2.2. 手動スキーマ初期化（オプション）

必要に応じて、`bypass_import_csv.py` の `--init-only` オプションを使用：

#### Linux / macOS
```bash
# テスト用 DB のみスキーマを作成（CSVロードは実施しない）
docker compose exec data_processor \
  env PYTHONPATH=/app python /scripts/bypass_import_csv.py --init-only
```

#### Windows PowerShell
```powershell
# -T フラグで TTY を無効化し、バッククォート (`) で行継続
docker compose exec -T data_processor `
  python /scripts/bypass_import_csv.py --init-only
```

**実行結果の例：**
```
✓ テーブルスキーマを初期化しました
✓ --init-only オプションが指定されたため、スキーマ初期化のみを実行しました
✓ DB スキーマ初期化完了
```

**注意：**
- **Linux/macOS**: `env PYTHONPATH=/app` で環境変数を設定してコマンドを実行
- **Windows PowerShell**: `DATABASE_URL` は `docker-compose.yml` で定義済みのため、`PYTHONPATH` は暗黙的に設定されます（`.env` ファイルから読み込まれます）

---

## 3. テストの実行

### 3.1. 全テストの実行

#### Linux / macOS
```bash
# Docker コンテナ内で pytest を実行
docker compose exec streamlit_app pytest tests/
```

#### Windows PowerShell
```powershell
docker compose exec -T streamlit_app pytest tests/
```

**期待される動作フロー：**

1. `conftest.py::engine` フィクスチャ が実行
   - `.env` から `DB_NAME_TEST=mydatabase_test` を取得
   - DB 名が `_test` で終わることを検証
   - `Base.metadata.create_all()` でテーブルを再作成
2. 各テスト関数ごとに `db_session` フィクスチャが実行
   - 既存データをすべて削除（データ独立性を保証）
   - 新しいセッションを提供
3. テスト実行
4. セッション自動ロールバック
5. 次のテストへ
6. 最後に `drop_all()` でスキーマを削除

### 3.2. 特定のテストファイルのみ実行

#### Linux / macOS
```bash
# repositories テストのみ実行
docker compose exec streamlit_app \
  pytest tests/repositories/test_company_repository.py -v

# service テストのみ実行
docker compose exec streamlit_app \
  pytest tests/service/test_financial_service.py -v
```

#### Windows PowerShell
```powershell
# repositories テストのみ実行
docker compose exec -T streamlit_app `
  pytest tests/repositories/test_company_repository.py -v

# service テストのみ実行
docker compose exec -T streamlit_app `
  pytest tests/service/test_financial_service.py -v
```

### 3.3. 特定のテスト関数のみ実行

#### Linux / macOS
```bash
# 関数名で絞り込み
docker compose exec streamlit_app \
  pytest tests/ -k "test_find_by_edinet_code" -v
```

#### Windows PowerShell
```powershell
# 関数名で絞り込み
docker compose exec -T streamlit_app `
  pytest tests/ -k "test_find_by_edinet_code" -v
```

---

## 4. テスト DB にシードデータを含める（オプション）

### 4.1. CSV ファイル付きでのロード

テスト用サンプル CSV を `download/` ディレクトリに配置している場合：

#### Linux / macOS
```bash
# スキーマ作成 + CSV ロード（フル初期化）
docker compose exec data_processor \
  env PYTHONPATH=/app python /scripts/bypass_import_csv.py
```

#### Windows PowerShell
```powershell
# スキーマ作成 + CSV ロード（フル初期化）
docker compose exec -T data_processor `
  python /scripts/bypass_import_csv.py
```

**実行結果の例：**
```
✓ テーブルスキーマを初期化しました
✓ /app/download/S100SSHR/XBRL_TO_CSV/jpcrp040300-q3r-001_E01441-000_2023-12-31_01_2024-02-09.csv -> Saved.
✓ 全データロード完了
```

---

## 5. テスト完了後のクリーンアップ

### 5.1. コンテナの停止と削除

```bash
# コンテナを停止・削除（ボリュームは保持）
docker compose down

# ボリュームも含めて完全削除
docker compose down -v
```

---

## 6. トラブルシューティング

### 6.1. DB 接続エラー

**エラー例：**
```
sqlalchemy.exc.OperationalError: (psycopg2.OperationalError) 
connection to server at "db" (172.18.0.2), port 5432 failed: 
FATAL: database "mydatabase_test" does not exist
```

**対策：**
```bash
# スキーマ初期化を再実行
docker compose exec data_processor \
  env PYTHONPATH=/app python /scripts/bypass_import_csv.py --init-only
```

### 6.2. 環境変数が設定されていないエラー

**エラー例：**
```
ValueError: 環境変数が設定されていません: DB_USER, DB_PASSWORD, DB_NAME_TEST
```

**対策：**
`.env` ファイルで以下の変数を確認：
```
DB_USER=user
DB_PASSWORD=password
DB_HOST=db
DB_PORT=5432
DB_NAME_TEST=mydatabase_test
```

### 6.3. `_test` サフィックスチェック失敗

**エラー例：**
```
ValueError: 安全のため、テスト用DB名は、"_test"で終わる必要があります。
```

**対策：**
`.env` の `DB_NAME_TEST` が `_test` で終わることを確認：
```
# 正しい例
DB_NAME_TEST=mydatabase_test

# 間違った例
DB_NAME_TEST=mydatabase
```

---

## 7. 推奨運用パターン

### 7.1. 開発者向け：ローカルテスト

#### Linux / macOS
```bash
# 1. テスト環境起動
docker compose up --build -d

# 2. DB スキーマ初期化（conftest.py が自動で処理するため不要）
# 必要に応じて手動実行: docker compose exec data_processor env PYTHONPATH=/app python /scripts/bypass_import_csv.py --init-only

# 3. 全テスト実行
docker compose exec streamlit_app pytest tests/ -v

# 4. クリーンアップ
docker compose down
```

#### Windows PowerShell
```powershell
# 1. テスト環境起動
docker compose up --build -d

# 2. DB スキーマ初期化（conftest.py が自動で処理するため不要）
# 必要に応じて手動実行: docker compose exec -T data_processor python /scripts/bypass_import_csv.py --init-only

# 3. 全テスト実行
docker compose exec -T streamlit_app pytest tests/ -v

# 4. クリーンアップ
docker compose down
```

### 7.2. CI/CD パイプライン向け（GitHub Actions）

```yaml
# .github/workflows/test.yml の例
- name: Start test DB
  run: docker compose up --build -d

- name: Run pytest
  run: docker compose exec -T streamlit_app pytest tests/

- name: Cleanup
  run: docker compose down -v
```

> **注意：** CI 環境では `-T` フラグを使用して TTY の割り当てを無効化します（Windows PowerShell / Linux 共通）。スキーマ初期化は conftest.py が自動で処理します。

---

## 8. テスト実行フローの図示

```plaintext
┌─────────────────────────────────────────┐
│ docker-compose -f docker-compose_test.yml up
└────────────────┬────────────────────────┘
                 │
                 ▼
        ┌────────────────────┐
        │ PostgreSQL 起動     │
        │ mydatabase_test    │
        │ (POSTGRES_DB_TEST) │
        └────────┬───────────┘
                 │
                 ▼
    ┌────────────────────────────────────┐
    │ conftest.py::engine フィクスチャ     │
    │ → DB_NAME_TEST 取得 & _test 検証     │
    │ → Base.metadata.create_all()        │
    │ → すべてのテーブルを作成            │
    └────────┬───────────────────────────┘
             │
             ▼
    ┌────────────────────────────────────┐
    │ pytest tests/                       │
    │ 1. engine フィクスチャ (session)    │
    │ 2. db_session フィクスチャ (func)   │
    │ 3. 各テスト実行                     │
    │ 4. ロールバック & クリーンアップ    │
    └────────┬───────────────────────────┘
             │
             ▼
    ┌────────────────────────────────────┐
    │ conftest.py → drop_all()           │
    │ → すべてのテーブルを削除            │
    └────────┬───────────────────────────┘
             │
             ▼
    ┌────────────────────────────────────┐
    │ docker-compose down                 │
    │ → コンテナ停止・削除                │
    └────────────────────────────────────┘
```

---

## 9. 参考資料

- [tests/conftest.py](../tests/conftest.py) - pytest フィクスチャ定義
- [scripts/bypass_import_csv.py](../scripts/bypass_import_csv.py) - DB 初期化スクリプト
- [docker-compose.yml](../docker-compose.yml) - Docker Compose 設定
- [documents/System_Architecture_Design.md](./System_Architecture_Design.md#7-テスト環境の分離とテスト実行フロー) - システム設計ドキュメント
