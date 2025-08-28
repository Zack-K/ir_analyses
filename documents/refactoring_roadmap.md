# リファクタリング作業順序ガイド

> **注意：このファイルは「IR分析プロジェクト 完成版ロードマップ・設計方針（統合版）」と同じ現行方針に基づいています。重複・古い設計ではなく、現行設計の補足・実装ガイドとして活用するため、`old`フォルダに移動しないでください。今後もdocuments配下で管理してください。**

提示された3つのドキュメント（`api_refactoring_guide.md`, `app_refactoring_guide.md`, `db_and_sqlalchemy_review.md`）を精査し、リファクタリングの理想的な作業順序を提案します。

これらのドキュメントは、現状の課題を解決し、アプリケーションをモダンで保守性の高い3層アーキテクチャ（View, Service, Repository）へと進化させるための、一貫した計画を示しています。

以下の順序で作業を進めることで、各層の依存関係を解決しながら、手戻りなく効率的にリファクタリングを進めることができます。

---

### **推奨作業順序**

#### **ステップ1: 【基盤】DBモデルの強化**

最初に、データ構造の核となるモデル定義を強化し、ORMの能力を最大限に引き出す準備をします。これは後続のすべての作業の基礎となります。

*   **目的**:
    *   モデル間の関連性を定義し、データアクセスを直感的にする。
    *   検索パフォーマンスを向上させる。
*   **具体的な作業**:
    1.  `utils/db_models.py` を開き、各モデルクラスに `relationship` を追加して、テーブル間の関連を定義します（例: `Company.reports`, `Financial_report.company`）。
    2.  頻繁な検索対象となるカラム（`edinet_code`, `element_id`, 外部キーなど）に `index=True` を設定します。
*   **主参照ガイド**: `old/db_and_sqlalchemy_review.md`


#### **ステップ2: 【データアクセス層】Repositoryパターンの導入**

次に、手続き的なDB操作（`db_controller.py`）を、責務が明確なオブジェクト指向のRepositoryパターンに置き換えます。

*   **目的**:
    *   DBとの対話ロジックをカプセル化し、テスト容易性を向上させる。
    *   データアクセス層のインターフェースをモデルオブジェクト中心に統一する。
*   **具体的な作業**:
    1.  `utils/db_controller.py` を廃止します。
    2.  `utils/` 配下に `repositories` ディレクトリを新設します。
    3.  各モデル（`Company`, `Financial_item`等）に対応するRepositoryクラスを `repositories` 内に作成します。
    4.  各Repositoryに、`find_by_...`, `save`, `get_or_create` (Upsertロジック) といったDB操作メソッドを実装します。
*   **主参照ガイド**: `old/db_and_sqlalchemy_review.md`, `old/api_refactoring_guide.md`


#### **ステップ3: 【ビジネスロジック層】Service層の構築とデータ永続化フローの再設計**

Repositoryが整ったので、それらを利用してビジネスロジックを組み立てるService層を構築します。

*   **目的**:
    *   複数のDB操作を伴う複雑なビジネスロジック（特にデータ永続化）とトランザクション管理をService層に集約する。
    *   `api.py` の責務を「データマッピング」に限定し、見通しを良くする。
*   **具体的な作業**:
    1.  `utils/` 配下に `services` ディレクトリを新設します。
    2.  `FinancialService` クラスを作成し、`save_financial_bundle` に相当するメソッドを実装します。このメソッド内でRepositoryを呼び出し、一連の永続化処理を単一トランザクションで実行します。
    3.  `utils/api.py` をリファクタリングし、`_..._mapping` 関数群が辞書ではなくSQLAlchemyモデルオブジェクトを返すように修正します。
    4.  `api.py` の永続化処理を、`FinancialService` のメソッド呼び出しに置き換えます。
*   **主参照ガイド**: `old/api_refactoring_guide.md`


#### **ステップ4: 【プレゼンテーション層】UIとバックエンドのクリーンな連携**

バックエンドの3層アーキテクチャが完成したことを受け、UI (`app.py`) をリファクタリングします。

*   **目的**:
    *   UIロジックとビジネスロジックを完全に分離する。
    *   `app.py` がService層のみに依存する、クリーンな構造を実現する。
*   **具体的な作業**:
    1.  `app/app.py` をリファクタリングし、DBやRepositoryへの直接アクセスをすべて削除します。
    2.  代わりに `FinancialService` を呼び出し、表示に必要なデータを取得するように変更します。（必要であれば、ServiceにUI向けのデータ取得メソッドを追加します）
    3.  Serviceから返されたDataFrameやDTO（Data Transfer Object）を用いて、Streamlitコンポーネント（グラフ等）を描画します。
*   **主参照ガイド**: `old/app_refactoring_guide.md`


#### **ステップ5: 【品質保証】テストの全体的な刷新**

最後に、新しいアーキテクチャの品質を保証するため、テストコードを全面的に刷新します。

*   **目的**:
    *   新しいRepository層とService層の動作を保証する。
    *   高速で独立したテスト環境を構築する。
*   **具体的な作業**:
    1.  `tests/test_db_controller.py` を廃止し、`tests/repositories` や `tests/services` といった新しいテスト構造を作成します。
    2.  アサーションの対象を、DataFrameではなくモデルオブジェクトのプロパティ検証に変更します。
    3.  テストごとにトランザクションをロールバックする手法を導入し、テストの独立性と速度を向上させます。
*   **主参照ガイド**: `old/db_and_sqlalchemy_review.md`

この5ステップの順序で進めることで、堅牢で保守性の高いアプリケーションへと着実に移行できるでしょう。
