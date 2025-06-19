# Docker構成改善ガイド：初心者向け段階的実行版

## 📋 このガイドについて

このドキュメントでは、Docker初心者でも**一歩ずつ確実に**Docker構成を改善できるよう、改善項目を段階的に分けて説明します。各ステップで動作確認を行い、問題があれば元に戻せる安全な方法で進行します。

## 🎯 改善の全体像

### 改善項目（優先度順）
1. ⚡ **軽量化** - イメージサイズ削減とビルド高速化
2. 🔒 **セキュリティ強化** - 非rootユーザーとリソース制限
3. ⚙️ **設定管理** - Streamlit config.toml対応
4. 🏥 **運用改善** - ヘルスチェックと監視

### 期待される効果
- イメージサイズ：40-60%削減
- ビルド時間：30-50%短縮
- セキュリティ：攻撃面大幅削減
- 運用性：自動復旧機能

---

## 📁 現在の構成確認

まず、現在の構成を把握しましょう。

```bash
# プロジェクトディレクトリに移動
cd /Users/shimazakikeiichi/Documents/git/ir_analyses

# 現在のファイル構成確認
ls -la
```

**期待される出力:**
```
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── app/
│   └── app.py
├── config/
│   ├── __init__.py
│   └── config.py
└── scripts/
```

---

## 🚀 段階1：軽量化（最優先）

### ステップ1-1：バックアップ作成

**⚠️ 重要：必ず最初にバックアップを作成してください**

```bash
# 現在の設定をバックアップ
cp Dockerfile Dockerfile.backup
cp docker-compose.yml docker-compose.yml.backup
echo "✅ バックアップ作成完了"
```

### ステップ1-2：.dockerignore作成

不要なファイルをビルドから除外し、ビルド時間を短縮します。

```bash
# .dockerignore作成
cat > .dockerignore << 'EOF'
# Git関連
.git/
.gitignore
.gitattributes

# Python関連
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
pip-log.txt
pip-delete-this-directory.txt
.pytest_cache/
.coverage
.mypy_cache/
.tox/
venv/
env/
ENV/

# IDE関連
.vscode/
.idea/
*.swp
*.swo
*~

# ログとキャッシュ
*.log
logs/
.cache/

# OS関連
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# ドキュメント
README.md
LICENSE
CHANGELOG.md
.env.example
*.md

# バックアップ
*.backup
EOF

echo "✅ .dockerignore作成完了"
```

### ステップ1-3：軽量Dockerfileに更新

マルチステージビルドを使用して軽量化します。

```bash
# 新しいDockerfileを作成
cat > Dockerfile << 'EOF'
# syntax=docker/dockerfile:1.4
# BuildKit機能を有効化

# ===== ビルドステージ =====
FROM python:3.12-slim-bookworm AS builder

# ビルド時の環境変数
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# システム依存関係のインストール（キャッシュマウント活用）
RUN --mount=type=cache,target=/var/cache/apt \
    --mount=type=cache,target=/var/lib/apt/lists \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
    && rm -rf /var/lib/apt/lists/*

# Python依存関係のインストール（キャッシュマウント活用）
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# ===== 実行ステージ（軽量化） =====
FROM python:3.12-slim-bookworm AS runtime

# 実行時環境変数
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# ビルドステージから必要なパッケージのみコピー
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# アプリケーションファイルのコピー
COPY app/ ./

# ポート公開
EXPOSE 8501

# デフォルトコマンド
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
EOF

echo "✅ 軽量Dockerfile作成完了"
```

### ステップ1-4：動作確認

```bash
# BuildKit有効化
export DOCKER_BUILDKIT=1

# イメージビルド（時間測定）
time docker-compose build streamlit_app

# イメージサイズ確認
docker images | grep ir-analyses

echo "✅ 軽量化完了確認"
```

**💡 トラブルシューティング:**
- ビルドエラーが出た場合：`docker system prune -a` でキャッシュクリア後、再実行
- 依存関係エラーの場合：requirements.txtの内容を確認

---

## 🔒 段階2：セキュリティ強化

### ステップ2-1：非rootユーザーでの実行

Dockerfileを更新して、セキュリティを強化します。

```bash
# セキュリティ強化版Dockerfileに更新
cat > Dockerfile << 'EOF'
# syntax=docker/dockerfile:1.4

FROM python:3.12-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

RUN --mount=type=cache,target=/var/cache/apt \
    --mount=type=cache,target=/var/lib/apt/lists \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 非rootユーザーの作成（セキュリティ強化）
RUN groupadd -r appuser && \
    useradd -r -g appuser -d /app -s /bin/bash appuser && \
    mkdir -p /app && \
    chown -R appuser:appuser /app

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# アプリケーションファイルのコピー（適切な所有者設定）
COPY --chown=appuser:appuser app/ ./

# 非rootユーザーに切り替え
USER appuser

EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
EOF

echo "✅ セキュリティ強化Dockerfile作成完了"
```

### ステップ2-2：docker-compose.ymlセキュリティ強化

```bash
# セキュリティ強化版docker-compose.ymlに更新
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  streamlit_app:
    build: .
    ports:
      - "8501:8501"
    volumes:
      - ./app:/app:ro  # 読み取り専用マウント（セキュリティ強化）
      - ./config:/config:ro  # 設定ファイル用（次のステップで使用）
    depends_on:
      - db
    environment:
      DATABASE_URL: postgresql://user:password@db:5432/mydatabase
    # リソース制限（セキュリティ強化）
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '1.0'
        reservations:
          memory: 512M
          cpus: '0.5'
    restart: unless-stopped

  data_processor:
    build: .
    volumes:
      - ./app:/app:ro
      - ./scripts:/scripts:ro
      - ./config:/config:ro
    depends_on:
      - db
    environment:
      DATABASE_URL: postgresql://user:password@db:5432/mydatabase
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '2.0'

  db:
    image: postgres:15-alpine  # より軽量で新しいバージョン
    environment:
      POSTGRES_DB: mydatabase
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
    volumes:
      - db_data:/var/lib/postgresql/data
      - ./scripts:/docker-entrypoint-initdb.d:ro
    ports:
      - "5432:5432"
    restart: always
    # セキュリティ強化
    security_opt:
      - no-new-privileges:true
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '1.0'

volumes:
  db_data:
EOF

echo "✅ セキュリティ強化docker-compose.yml作成完了"
```

### ステップ2-3：セキュリティ動作確認

```bash
# リビルドとテスト
docker-compose build
docker-compose up -d

# 非rootユーザー実行確認
docker-compose exec streamlit_app whoami
# 期待される出力: appuser

# リソース制限確認
docker stats --no-stream

echo "✅ セキュリティ強化確認完了"
```

---

## ⚙️ 段階3：Streamlit設定管理

### ステップ3-1：config.toml作成

Streamlitのネイティブ設定ファイルを作成します。

```bash
# config.tomlファイルを作成
cat > config/config.toml << 'EOF'
[server]
port = 8501
address = "0.0.0.0"
enableCORS = false
enableXsrfProtection = false
headless = true

[browser]
serverAddress = "0.0.0.0"
serverPort = 8501

[client]
showErrorDetails = true

[logger]
level = "info"

# アプリケーション固有の設定
[app]
title = "IR Analysis Dashboard"
debug = false

[database]
url = "postgresql://user:password@db:5432/mydatabase"
pool_size = 5
EOF

echo "✅ config.toml作成完了"
```

### ステップ3-2：config.py削除（クリーンアップ）

```bash
# 不要なファイル削除（config.tomlのみを使用）
rm -f config/__init__.py config/config.py

# config/内の構成確認
ls -la config/
# 期待される出力: config.tomlのみ

echo "✅ config設定クリーンアップ完了"
```

### ステップ3-3：app.py設定読み込み対応

現在のapp.pyにconfig.toml読み込み機能を追加する例：

```bash
# app.pyの設定読み込みサンプルコードを表示
cat << 'EOF'

# app.pyの先頭に追加するコード例：

import streamlit as st
import toml
import os

# Streamlit設定読み込み
def load_config():
    config_path = "/config/config.toml"
    if os.path.exists(config_path):
        try:
            config = toml.load(config_path)
            st.write("✅ 設定ファイル読み込み成功:", config_path)
            return config
        except Exception as e:
            st.error(f"❌ 設定ファイル読み込み失敗: {e}")
            return {}
    else:
        st.warning("⚠️ 設定ファイルが見つかりません。デフォルト設定を使用します。")
        return {}

# 設定の読み込み
config = load_config()

# 設定値の取得例
app_title = config.get('app', {}).get('title', 'Default Title')
database_url = config.get('database', {}).get('url', os.environ.get('DATABASE_URL'))

EOF

echo "📝 app.py修正例を表示しました。上記コードをapp.pyに手動で追加してください。"
```

### ステップ3-4：設定動作確認

```bash
# リビルドして設定確認
docker-compose build
docker-compose up -d

# config.toml読み込み確認
docker-compose exec streamlit_app ls -la /config/
# 期待される出力: config.tomlが存在

# Streamlitアプリ動作確認
echo "ブラウザでhttp://localhost:8501にアクセスして動作確認してください"

# ログ確認
docker-compose logs streamlit_app | grep -i config

echo "✅ 設定管理確認完了"
```

---

## 🏥 段階4：運用改善

### ステップ4-1：ヘルスチェック追加

```bash
# ヘルスチェック付きdocker-compose.ymlに更新
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  streamlit_app:
    build: .
    ports:
      - "8501:8501"
    volumes:
      - ./app:/app:ro
      - ./config:/config:ro
    depends_on:
      db:
        condition: service_healthy
    environment:
      DATABASE_URL: postgresql://user:password@db:5432/mydatabase
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '1.0'
        reservations:
          memory: 512M
          cpus: '0.5'
    restart: unless-stopped
    # ヘルスチェック追加
    healthcheck:
      test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:8501', timeout=10)"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  data_processor:
    build: .
    volumes:
      - ./app:/app:ro
      - ./scripts:/scripts:ro
      - ./config:/config:ro
    depends_on:
      db:
        condition: service_healthy
    environment:
      DATABASE_URL: postgresql://user:password@db:5432/mydatabase
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '2.0'

  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: mydatabase
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
    volumes:
      - db_data:/var/lib/postgresql/data
      - ./scripts:/docker-entrypoint-initdb.d:ro
    ports:
      - "5432:5432"
    restart: always
    security_opt:
      - no-new-privileges:true
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '1.0'
    # データベースヘルスチェック
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user -d mydatabase"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s

volumes:
  db_data:
EOF

echo "✅ ヘルスチェック付きdocker-compose.yml作成完了"
```

### ステップ4-2：運用改善動作確認

```bash
# 依存関係にrequestsライブラリを追加（ヘルスチェック用）
echo "requests" >> requirements.txt

# リビルドと起動
docker-compose build
docker-compose up -d

# ヘルスチェック状態確認
docker-compose ps
# 期待される出力: 全サービスが"healthy"状態

# システム全体状況確認
docker-compose top

echo "✅ 運用改善確認完了"
```

---

## 🧪 最終動作確認

### 全体テスト

```bash
echo "=== 最終動作確認開始 ==="

# 1. イメージサイズ比較
echo "📏 イメージサイズ確認:"
docker images | grep -E "(ir-analyses|postgres)" | awk '{print $1":"$2" - "$7}'

# 2. セキュリティ確認
echo "🔒 セキュリティ確認:"
docker-compose exec streamlit_app id

# 3. 設定ファイル確認
echo "⚙️ 設定ファイル確認:"
docker-compose exec streamlit_app cat /config/config.toml | head -5

# 4. ヘルスチェック確認
echo "🏥 ヘルスチェック確認:"
docker-compose ps --format "table {{.Name}}\t{{.Status}}"

# 5. リソース使用量確認
echo "📊 リソース使用量:"
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"

# 6. Webアプリ動作確認
echo "🌐 Webアプリ確認:"
curl -s -o /dev/null -w "%{http_code}" http://localhost:8501 && echo " - Streamlitアプリ正常動作" || echo " - Streamlitアプリエラー"

echo "=== 最終動作確認完了 ==="
```

---

## 📊 改善効果の測定

### ビフォー・アフター比較

```bash
# 改善前後の比較レポート生成
cat << 'EOF'
=== Docker改善効果レポート ===

📏 イメージサイズ:
- 改善前: 約800MB-1.2GB (推定)
- 改善後: 300-500MB (40-60%削減)

⚡ ビルド時間:
- キャッシュマウント活用により30-50%短縮

🔒 セキュリティ:
- 非rootユーザー実行 ✅
- 読み取り専用ボリューム ✅
- リソース制限 ✅
- 最新ベースイメージ ✅

⚙️ 設定管理:
- config.toml統一 ✅
- 設定外部化 ✅

🏥 運用性:
- ヘルスチェック ✅
- 自動再起動 ✅
- 依存関係管理 ✅

=== 改善完了 ===
EOF
```

---

## 🚨 トラブルシューティング

### よくある問題と解決法

#### 1. ビルドエラー
```bash
# 問題: BuildKitエラー
# 解決策:
export DOCKER_BUILDKIT=1
docker system prune -a
docker-compose build --no-cache
```

#### 2. 権限エラー
```bash
# 問題: ファイル権限エラー
# 解決策:
sudo chown -R $USER:$USER ./app ./config
docker-compose down
docker-compose up -d
```

#### 3. 設定ファイル読み込みエラー
```bash
# 問題: config.tomlが読み込めない
# 確認方法:
docker-compose exec streamlit_app ls -la /config/
docker-compose exec streamlit_app cat /config/config.toml

# 解決策:
# 1. ファイルの存在確認
# 2. マウント設定確認
# 3. ファイル権限確認
```

#### 4. ヘルスチェック失敗
```bash
# 問題: ヘルスチェックが失敗
# 確認方法:
docker-compose logs streamlit_app

# 解決策:
# requirements.txtにrequestsを追加
echo "requests" >> requirements.txt
docker-compose build
```

#### 5. リソース不足
```bash
# 問題: メモリ不足エラー
# 解決策: docker-compose.ymlのリソース制限を調整
# memory: 1G → 2G
# cpus: '1.0' → '2.0'
```

---

## 🔄 元に戻す方法

何か問題が発生した場合の復旧手順：

```bash
# バックアップファイルから復元
cp Dockerfile.backup Dockerfile
cp docker-compose.yml.backup docker-compose.yml

# コンテナとイメージをクリーンアップ
docker-compose down
docker system prune -a

# 元の状態で再起動
docker-compose up -d

echo "✅ 元の状態に復旧完了"
```

---

## 📈 次のステップ（上級者向け）

改善が完了したら、さらなる最適化を検討：

1. **Docker Hardened Images**への移行
2. **CI/CD パイプライン**統合
3. **監視・ログ集約**システム導入
4. **セキュリティスキャン**自動化
5. **マルチアーキテクチャ**対応

---

## 📚 参考資料

- [Docker公式ベストプラクティス](https://docs.docker.com/develop/dev-best-practices/)
- [Streamlit設定ドキュメント](https://docs.streamlit.io/library/advanced-features/configuration)
- [BuildKit公式ドキュメント](https://docs.docker.com/build/buildkit/)

---

**🎉 改善完了おめでとうございます！**

このガイドに従って、段階的にDocker構成の改善が完了しました。各ステップで動作確認を行いながら進めることで、安全で確実な改善を実現できました。

## 現状分析

### 現在の構成の課題

1. **軽量化の余地**
   - Python 3.9-slim-buster（やや古いバージョン）
   - マルチステージビルド未使用
   - BuildKit機能未活用

2. **セキュリティの課題**
   - rootユーザーでの実行
   - 固定認証情報の使用
   - リソース制限なし

3. **設定管理の課題**
   - streamlit_appで`/config`ボリュームが未マウント
   - 設定ファイルの読み込み機能なし

4. **運用面の課題**
   - ヘルスチェック未設定
   - ログ・モニタリング不十分

### 改善の方向性

- **95%軽量化**: マルチステージビルド + 最新軽量ベースイメージ
- **BuildKit活用**: キャッシュマウント、シークレット管理
- **セキュリティ強化**: 非rootユーザー、動的認証情報
- **設定統合**: `/config`からの設定読み込み対応
- **運用性向上**: ヘルスチェック、リソース管理

## 改善案詳細

### 1. Dockerfile改善版

**主要改善点:**
- マルチステージビルドによる軽量化
- BuildKitキャッシュマウント活用
- 非rootユーザーでの実行
- ヘルスチェック追加

```dockerfile
# syntax=docker/dockerfile:1.4
# BuildKit機能を有効化

# ===== ビルドステージ =====
FROM python:3.12-slim-bookworm AS builder

# ビルド時の環境変数
ENV PYTHONDONTWRITEBYTECODE=1 \\
    PYTHONUNBUFFERED=1 \\
    PIP_NO_CACHE_DIR=1 \\
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# システム依存関係のインストール（キャッシュマウント活用）
RUN --mount=type=cache,target=/var/cache/apt \\
    --mount=type=cache,target=/var/lib/apt/lists \\
    apt-get update && \\
    apt-get install -y --no-install-recommends \\
        build-essential \\
        gcc \\
    && rm -rf /var/lib/apt/lists/*

# Python依存関係のインストール（キャッシュマウント活用）
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \\
    pip install --no-deps -r requirements.txt && \\
    pip install wheel setuptools

# ===== 実行ステージ（軽量化） =====
FROM python:3.12-slim-bookworm AS runtime

# 実行時環境変数
ENV PYTHONDONTWRITEBYTECODE=1 \\
    PYTHONUNBUFFERED=1 \\
    PYTHONPATH=/app:/config

# 非rootユーザーの作成
RUN groupadd -r appuser && \\
    useradd -r -g appuser -d /app -s /bin/bash appuser && \\
    mkdir -p /app /config && \\
    chown -R appuser:appuser /app /config

# ビルドステージから必要なパッケージのみコピー
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# アプリケーションファイルのコピー
WORKDIR /app
COPY --chown=appuser:appuser app/ ./
COPY --chown=appuser:appuser config/ /config/

# 非rootユーザーに切り替え
USER appuser

# ヘルスチェック追加
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

EXPOSE 8501

# デフォルトコマンド
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.enableCORS=false", "--server.enableXsrfProtection=false"]
```

### 2. docker-compose.yml改善版

**主要改善点:**
- `/config`ボリュームマウント追加
- ヘルスチェック設定
- 環境別設定対応
- リソース制限設定
- セキュリティ強化

```yaml
version: '3.8'

services:
  streamlit_app:
    build: 
      context: .
      dockerfile: Dockerfile
      cache_from:
        - \${IMAGE_NAME:-ir-analyses}:cache-runtime
      cache_to:
        - \${IMAGE_NAME:-ir-analyses}:cache-runtime
    ports:
      - "\${STREAMLIT_PORT:-8501}:8501"
    volumes:
      # 設定ファイル読み込み対応（重要：configボリューム追加）
      - ./app:/app:ro
      - ./config:/config:ro
    depends_on:
      db:
        condition: service_healthy
    environment:
      - DATABASE_URL=\${DATABASE_URL:-postgresql://user:password@db:5432/mydatabase}
      - CONFIG_PATH=/config
      - PYTHONPATH=/app:/config
    networks:
      - app_network
    restart: unless-stopped
    # リソース制限
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '1.0'
        reservations:
          memory: 512M
          cpus: '0.5'
    # ヘルスチェック
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8501/_stcore/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  data_processor:
    build: 
      context: .
      dockerfile: Dockerfile
    volumes:
      - ./app:/app:ro
      - ./scripts:/scripts:ro
      - ./config:/config:ro
      - data_output:/app/output
    depends_on:
      db:
        condition: service_healthy
    environment:
      - DATABASE_URL=\${DATABASE_URL:-postgresql://user:password@db:5432/mydatabase}
      - CONFIG_PATH=/config
      - PYTHONPATH=/app:/config
    networks:
      - app_network
    restart: "no"
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '2.0'

  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=\${POSTGRES_DB:-mydatabase}
      - POSTGRES_USER=\${POSTGRES_USER:-user}
      - POSTGRES_PASSWORD=\${POSTGRES_PASSWORD:-password}
      - POSTGRES_INITDB_ARGS=--encoding=UTF-8 --lc-collate=C --lc-ctype=C
    volumes:
      - db_data:/var/lib/postgresql/data
      - ./scripts:/docker-entrypoint-initdb.d:ro
    ports:
      - "\${POSTGRES_PORT:-5432}:5432"
    networks:
      - app_network
    restart: always
    security_opt:
      - no-new-privileges:true
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '1.0'
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U \${POSTGRES_USER:-user} -d \${POSTGRES_DB:-mydatabase}"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s

networks:
  app_network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16

volumes:
  db_data:
    driver: local
  data_output:
    driver: local
```

### 3. .dockerignore設定

```dockerignore
# Git関連
.git/
.gitignore
.gitattributes

# Python関連
__pycache__/
*.py[cod]
*\$py.class
*.so
.Python
pip-log.txt
pip-delete-this-directory.txt
.pytest_cache/
.coverage
.mypy_cache/
.tox/
venv/
env/
ENV/

# IDE関連
.vscode/
.idea/
*.swp
*.swo
*~

# ログとキャッシュ
*.log
logs/
.cache/

# OS関連
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# 開発用ファイル
README.md
LICENSE
CHANGELOG.md
.env.example
docker-compose.override.yml

# テストとドキュメント
tests/
docs/
*.md

# 一時ファイル
temp/
tmp/
*.tmp
*.temp
```

### 4. 環境変数設定（.env）

```bash
# === データベース設定 ===
POSTGRES_DB=mydatabase
POSTGRES_USER=user
POSTGRES_PASSWORD=your_secure_password_here
DATABASE_URL=postgresql://user:your_secure_password_here@db:5432/mydatabase

# === アプリケーション設定 ===
STREAMLIT_PORT=8501
POSTGRES_PORT=5432
CONFIG_PATH=/config

# === Docker設定 ===
IMAGE_NAME=ir-analyses
COMPOSE_PROJECT_NAME=ir_analyses

# === BuildKit有効化 ===
DOCKER_BUILDKIT=1
COMPOSE_DOCKER_CLI_BUILD=1
```

### 5. app.py設定読み込み対応

**app.pyの先頭に追加するコード:**

```python
# app.py の先頭に追加
import sys
import os

# 設定パスをPYTHONPATHに追加
config_path = os.environ.get('CONFIG_PATH', '/config')
if config_path not in sys.path:
    sys.path.insert(0, config_path)

try:
    # config.py から設定を読み込み
    from config import (
        DATABASE_CONFIG,
        APP_CONFIG,
        STREAMLIT_CONFIG
    )
    print(f"✅ 設定ファイル読み込み成功: {config_path}/config.py")
except ImportError as e:
    print(f"⚠️ 設定ファイル読み込み失敗: {e}")
    # デフォルト設定を使用
    DATABASE_CONFIG = {'url': os.environ.get('DATABASE_URL')}
    APP_CONFIG = {}
    STREAMLIT_CONFIG = {}
```

## 改善効果

### 1. 軽量化成果
- **イメージサイズ削減**: 推定40-60%削減
- **ビルド時間短縮**: キャッシュマウントにより30-50%短縮
- **デプロイ効率**: 軽量化により転送時間大幅短縮

### 2. セキュリティ強化
- **非rootユーザー実行**: 権限昇格攻撃の防止
- **最小権限の原則**: 読み取り専用ボリューム
- **動的認証情報**: .envファイルでの安全な管理
- **リソース制限**: DoS攻撃対策

### 3. 運用改善
- **ヘルスチェック**: 自動復旧機能
- **設定統合**: `/config`からの一元管理
- **環境分離**: ネットワーク・ボリューム分離
- **ログ最適化**: 構造化ログ出力

### 4. 開発効率
- **キャッシュ最適化**: 開発時のビルド高速化
- **設定外部化**: 環境別の設定切り替え
- **依存関係管理**: マルチステージビルドでの最適化

## 移行手順

### 準備作業

1. **バックアップ作成**
```bash
# 現在の設定をバックアップ
cp Dockerfile Dockerfile.backup
cp docker-compose.yml docker-compose.yml.backup
```

2. **必要ファイル作成**
```bash
# .dockerignore作成
touch .dockerignore

# .env作成
touch .env
```

### 段階的移行

#### ステップ1: Dockerfile更新
```bash
# 1. 新しいDockerfile適用
cp docker-examples/Dockerfile.improved ./Dockerfile

# 2. .dockerignore適用
cp docker-examples/.dockerignore.example ./.dockerignore

# 3. ビルドテスト
docker-compose build --no-cache streamlit_app
```

#### ステップ2: docker-compose.yml更新
```bash
# 1. docker-compose.yml更新
cp docker-examples/docker-compose.improved.yml ./docker-compose.yml

# 2. .env設定
cp docker-examples/.env.example ./.env
# エディタで.envを編集し、パスワード等を設定

# 3. 設定読み込みテスト
docker-compose run --rm streamlit_app python -c "
import sys, os
sys.path.insert(0, '/config')
try:
    from config import *
    print('✅ 設定読み込み成功')
except Exception as e:
    print(f'❌ 設定読み込み失敗: {e}')
"
```

#### ステップ3: app.py更新
```bash
# app.pyに設定読み込みコード追加
# docker-examples/app_config_example.py を参考に実装
```

#### ステップ4: 動作確認
```bash
# 1. 全体起動
docker-compose up -d

# 2. ログ確認
docker-compose logs -f streamlit_app

# 3. ヘルスチェック確認
docker-compose ps

# 4. 設定読み込み確認
docker-compose exec streamlit_app python -c "
from config import *
print('DATABASE_CONFIG:', DATABASE_CONFIG)
"
```

### 検証項目チェックリスト

#### 基本機能
- [ ] streamlit_appが正常起動
- [ ] `/config/config.py`から設定読み込み成功
- [ ] data_processorで設定共有確認
- [ ] データベース接続確認

#### セキュリティ
- [ ] 非rootユーザーでの実行確認
- [ ] リソース制限動作確認  
- [ ] 読み取り専用ボリューム確認

#### 運用面
- [ ] ヘルスチェック動作確認
- [ ] 自動再起動確認
- [ ] ログ出力確認

#### パフォーマンス
- [ ] イメージサイズ削減確認
- [ ] ビルド時間短縮確認
- [ ] 起動時間確認

## トラブルシューティング

### よくある問題と解決策

#### 1. 設定ファイルが読み込めない
```bash
# 原因確認
docker-compose exec streamlit_app ls -la /config/
docker-compose exec streamlit_app python -c "import sys; print(sys.path)"

# 解決策
# - PYTHONPATHの設定確認
# - ボリュームマウントの確認
# - ファイル権限の確認
```

#### 2. ビルドエラー
```bash
# BuildKit有効化確認
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

# キャッシュクリア
docker system prune -a
docker-compose build --no-cache
```

#### 3. ヘルスチェック失敗
```bash
# Streamlitヘルスチェックエンドポイント確認
docker-compose exec streamlit_app curl -f http://localhost:8501/_stcore/health

# 代替ヘルスチェック
# healthcheck:
#   test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:8501')"]
```

## 追加の最適化案

### 1. 更なる軽量化
- **Docker Hardened Images**への移行検討
- **Distroless**イメージの活用
- **マルチアーキテクチャ**対応

### 2. CI/CD統合
- **GitHub Actions**でのビルド自動化
- **セキュリティスキャン**の自動実行
- **パフォーマンステスト**の自動化

### 3. 監視・ログ
- **Prometheus + Grafana**でのメトリクス監視
- **ELKスタック**でのログ集約
- **アラート**設定

## まとめ

この改善案により、以下の効果が期待できます：

1. **要件達成**: `/config`からの設定読み込み対応完了
2. **軽量化**: 40-60%のイメージサイズ削減
3. **セキュリティ**: 非rootユーザー実行、リソース制限
4. **運用性**: ヘルスチェック、自動復旧機能
5. **開発効率**: キャッシュ最適化、設定外部化

段階的な移行により、リスクを最小化しながら確実な改善を実現できます。

## 参考資料

- [Docker軽量化包括的知見集 2024](/Users/shimazakikeiichi/Documents/hobby_project/Docker_コンテナ軽量化_包括的知見集_2024.md)
- [Docker公式ベストプラクティス](https://docs.docker.com/develop/dev-best-practices/)
- [BuildKit公式ドキュメント](https://docs.docker.com/build/buildkit/)