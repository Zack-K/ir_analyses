# DBからStreamlitへのデータ可視化連携ガイド

## 1. 全体像：推奨アーキテクチャ

> **【重要】**
> このドキュメントは、DBからのデータ読み取りを実装した際の**最終的な理想形**を示しています。
> 今回のリファクタリングでは、まずUIとService層の分離を優先します。Service層は当面、**既存のCSVファイルからデータを読み取ります。**
>
> DBからのデータ読み取り機能の実装は、本リファクタリング完了後の、将来の拡張ステップとして計画されています。



`api_refactoring_guide.md`で提案した**3層アーキテクチャ（Controller/View, Service, Repository）**は、データ永続化だけでなく、DBからデータを読み出してUIに表示する際にも非常に有効です。

データ可視化における理想的な連携フローは以下のようになります。

```
[ app.py (Streamlit UI) ]  <-- DTO / DataFrame -->  [ Serviceレイヤー ]  <-- モデルオブジェクト -->  [ Repositoryレイヤー ]  <-- (SQLAlchemy ORM) -->  [ DB ]
         |                                                    |                                        |
      (View)                                            (ビジネスロジック)                             (データアクセス)
- ユーザー操作受付                                    - 複数のRepositoryを組合せ                  - DBへの具体的なクエリ発行
- Serviceの呼び出し                                   - データ加工・計算                          - モデルオブジェクトを返却
- 結果の表示                                          - 表示形式へのデータ変換 (DTO化)
```

このアーキテクチャの目的は、各レイヤーの責務を明確に分離し、関心事を分離することです。
- `app.py`は**「どのように見せるか」**に集中します。
- `Service`は**「何を見せるか（どのようなビジネス価値を提供するか）」**に集中します。
- `Repository`は**「どこからデータを取ってくるか」**に集中します。

## 2. 現状の`app.py`の課題

現在の`app.py`は、ローカルCSVを読み込み、`utils/api.py`の低レベルな関数（`_get_value`など）を直接呼び出して、UIロジックとデータ抽出ロジックが混在しています。これは密結合であり、DB連携への移行やロジックの変更を困難にします。

## 3. SQLAlchemyと連携するための各レイヤーの役割

### 3.1. `app.py` (View層) のあるべき姿

`app.py`は、ユーザーインターフェースの構築と、Serviceレイヤーの呼び出しに特化すべきです。

- **役割**:
    1.  `st.selectbox`などでユーザーからの入力を受け付けます。
    2.  入力された情報（例: 会社ID）を基に、**Serviceレイヤー**のメソッドを呼び出します。
    3.  Serviceから返却された、表示に最適化されたデータ（DataFrameやDTO）を使って、`st.bar_chart`などでグラフを描画します。
- **ポイント**: `app.py`は、RepositoryやSQLAlchemyのSessionを**一切意識しません**。

**【実装イメージ (Before -> After)】**
```python
# --- Before (現状のapp.py) ---
# apiの内部関数を直接呼び出し、UI側でロジックを組み立てている
sales_current = api._get_value(standardize_df, "jpcrp_cor:NetSalesSummaryOfBusinessResults", "CurrentYTDDuration")
sales_prior = api._get_value(standardize_df, "jpcrp_cor:NetSalesSummaryOfBusinessResults", "Prior1YTDDuration")
sales_df = pd.DataFrame({"title": ["今四半期", "前四半期"], "amount": [sales_current, sales_prior]})
st.bar_chart(sales_df)


# --- After (st.connection を活用した理想のapp.py) ---
import streamlit as st
# from services import FinancialService
# from uow import UnitOfWork # Unit of Work パターンを導入する場合

# 1. st.connectionでDB接続を確立し、セッションを取得
#    接続情報は .streamlit/secrets.toml で管理
conn = st.connection("my_db", type="sql")
session = conn.session

# 2. 取得したセッションを使ってService/UoWをインスタンス化（依存性の注入）
# uow = UnitOfWork(session)
# financial_service = FinancialService(uow)
#
# ※UoW を使わない場合
# from repositories import CompanyRepository, FinancialDataRepository
# company_repo = CompanyRepository(session)
# data_repo = FinancialDataRepository(session)
# financial_service = FinancialService(company_repo, data_repo)


# 3. Serviceに必要な情報を渡して呼び出す
#    Serviceの読み取りメソッドには @st.cache_data を付けるとさらに良い
sales_summary_df = financial_service.get_sales_summary(company_id="E01234")

# 4. 返ってきたデータをそのまま表示する
st.header("売上高")
st.bar_chart(sales_summary_df, x="period", y="sales")
```

### 3.2. `Service`レイヤーの新設

`app.py`と`Repository`層の間に位置し、アプリケーションのビジネスロジックを担当します。

- **役割**:
    1.  **ビジネスロジックの実行:** `app.py`からの要求に基づき、アプリケーション固有のルール、計算、判断を行います。
    2.  **データ永続化の調整:** `Unit of Work`パターンを通じてリポジトリを呼び出し、データ操作の順序や組み合わせを制御します。
    3.  **データ変換（マッピング）:** Repositoryから受け取ったDBモデルを、UIが表示しやすい形式（DataFrameやDTO）に変換して返却します。
- **ポイント**: 複雑なデータ取得や計算ロジックはここにカプセル化されます。

**【実装イメージ (`services/financial_service.py`)】**
```python
from dataclasses import dataclass

# DTOを定義
@dataclass
class SalesSummaryDTO:
    period: str
    sales: int

class FinancialService:
    def __init__(self, session):
        # Repositoryを初期化
        self.company_repo = CompanyRepository(session)
        self.data_repo = FinancialDataRepository(session)

    def get_sales_summary(self, company_edinet_code: str) -> list[SalesSummaryDTO]:
        # 1. Repositoryを使って会社情報を取得
        company = self.company_repo.find_by_edinet_code(company_edinet_code)
        if not company:
            return []

        # 2. Repositoryを使って時系列データを取得
        #    (find_sales_time_seriesのような専用メソッドをRepositoryに用意)
        sales_data = self.data_repo.find_sales_time_series(company.company_id)

        # 3. モデルオブジェクトのリストをDTOのリストに変換・加工
        #    (この変換ロジックがServiceの価値)
        dto_list = [
            SalesSummaryDTO(period=d.report.fiscal_year, value=d.value)
            for d in sales_data
        ]
        
        return sorted(dto_list, key=lambda d: d.period)
```

### 3.3. `Repository`レイヤーの役割（読み取り）

DBからデータを取得するクエリに特化します。

- **役割**:
    1.  Service層からの要求に基づき、SQLAlchemyの`Session`を使ってクエリを発行します。
    2.  JOINやフィルタ、集計など、複雑なデータ取得処理をカプセル化します。
    3.  結果を**モデルオブジェクト**のリストとしてService層に返します。
- **ポイント**: `db_models.py`に`relationship`が定義されていると、JOINを伴うクエリが非常に直感的かつ安全に記述できます。

**【実装イメージ (`repositories/financial_data_repository.py`)】**
```python
from sqlalchemy.orm import joinedload

class FinancialDataRepository:
    def __init__(self, session):
        self.session = session

    def find_sales_time_series(self, company_id: int) -> list[Financial_data]:
        # relationshipがあるので、JOINを明示的に書かずに済む
        return (
            self.session.query(Financial_data)
            .join(Financial_report)
            .join(Financial_item)
            .filter(Financial_report.company_id == company_id)
            .filter(Financial_item.item_name == "売上高") # またはelement_idで指定
            .options(joinedload(Financial_data.report)) # N+1問題対策
            .order_by(Financial_report.fiscal_year_end.asc())
            .all()
        )
```

## 4. まとめ

StreamlitとSQLAlchemyをクリーンに連携させるには、**`app.py`が直接DBやORMに触れない**ことが重要です。`Service`と`Repository`という中間層を設けることで、それぞれの関心事が分離され、テストが容易で保守性の高いアプリケーションを構築できます。

このアーキテクチャに従ってリファクタリングを進めることを強く推奨します。
