-- =====================================================
-- IR Analysis Database Schema
-- 作成日: 2025年
-- 目的: 企業財務データの分析用データベース
-- 対象DB: PostgreSQL 15+
-- =====================================================


-- DROP SCHEMA public;

COMMENT ON SCHEMA public IS 'standard public schema';

-- =====================================================
-- 既存オブジェクトのクリーンアップ
-- =====================================================

-- シーケンスの削除（依存関係を考慮した順序）
DROP SEQUENCE IF EXISTS public.companies_company_id_seq CASCADE;
DROP SEQUENCE IF EXISTS public.financial_data_data_id_seq CASCADE;
DROP SEQUENCE IF EXISTS public.financial_items_item_id_seq CASCADE;
DROP SEQUENCE IF EXISTS public.financial_reports_report_id_seq CASCADE;

-- テーブルの削除（外部キー制約を考慮した順序）
DROP TABLE IF EXISTS public.financial_data CASCADE;
DROP TABLE IF EXISTS public.financial_reports CASCADE;
DROP TABLE IF EXISTS public.financial_items CASCADE;
DROP TABLE IF EXISTS public.companies CASCADE;

-- =====================================================
-- シーケンス作成
-- =====================================================

-- 企業マスタ用シーケンス
CREATE SEQUENCE public.companies_company_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647  -- int4の最大値
	START 1
	CACHE 1
	NO CYCLE;

-- Permissions

ALTER SEQUENCE public.companies_company_id_seq OWNER TO "user";
GRANT ALL ON SEQUENCE public.companies_company_id_seq TO "user";

-- 財務データ用シーケンス（大量データ対応のためint8使用）
-- DROP SEQUENCE public.financial_data_data_id_seq;

CREATE SEQUENCE public.financial_data_data_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807  -- int8の最大値
	START 1
	CACHE 1
	NO CYCLE;

-- Permissions

ALTER SEQUENCE public.financial_data_data_id_seq OWNER TO "user";
GRANT ALL ON SEQUENCE public.financial_data_data_id_seq TO "user";

-- 財務項目マスタ用シーケンス
-- DROP SEQUENCE public.financial_items_item_id_seq;

CREATE SEQUENCE public.financial_items_item_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;

-- Permissions

ALTER SEQUENCE public.financial_items_item_id_seq OWNER TO "user";
GRANT ALL ON SEQUENCE public.financial_items_item_id_seq TO "user";

-- 財務報告書用シーケンス
-- DROP SEQUENCE public.financial_reports_report_id_seq;

CREATE SEQUENCE public.financial_reports_report_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;

-- Permissions

ALTER SEQUENCE public.financial_reports_report_id_seq OWNER TO "user";
GRANT ALL ON SEQUENCE public.financial_reports_report_id_seq TO "user";

-- =====================================================
-- テーブル定義
-- =====================================================

-- 企業マスタテーブル
-- 目的: EDINETから取得した企業基本情報を管理
-- 想定レコード数: 約4,000社（上場企業）

-- Drop table

-- DROP TABLE public.companies;

CREATE TABLE public.companies ( 
					company_id int4 GENERATED ALWAYS AS IDENTITY NOT NULL,  -- 主キー（自動採番）
					edinet_code varchar(6) NOT NULL,                        -- EDINET企業コード（一意）
					security_code varchar(5) NULL,                          -- 証券コード（5桁）
					company_name varchar(200) NOT NULL,                     -- 企業名
					industry_code varchar(10) NULL,                         -- 業種コード
					created_at timestamptz DEFAULT now() NULL,              -- 作成日時
					updated_at timestamptz DEFAULT now() NULL,              -- 更新日時
					CONSTRAINT companies_edinet_code_key UNIQUE (edinet_code),  -- EDINETコードの一意制約
					CONSTRAINT companies_pkey PRIMARY KEY (company_id)      -- 主キー制約
					);

-- テーブルコメント
COMMENT ON TABLE public.companies IS '企業マスタテーブル - EDINETから取得した企業基本情報';
COMMENT ON COLUMN public.companies.company_id IS '企業ID（主キー）';
COMMENT ON COLUMN public.companies.edinet_code IS 'EDINET企業コード（6桁、一意）';
COMMENT ON COLUMN public.companies.security_code IS '証券コード（5桁）';
COMMENT ON COLUMN public.companies.company_name IS '企業名';
COMMENT ON COLUMN public.companies.industry_code IS '業種コード';

CREATE INDEX idx_companies_edinet_code ON public.companies USING btree (edinet_code);

-- Permissions

ALTER TABLE public.companies OWNER TO "user";
GRANT ALL ON TABLE public.companies TO "user";

-- 財務項目マスタテーブル
-- 目的: XBRLで定義される財務項目の定義を管理
-- 想定レコード数: 約10,000項目

-- public.financial_items definition

-- Drop table

-- DROP TABLE public.financial_items;

CREATE TABLE public.financial_items ( 
					item_id int4 GENERATED ALWAYS AS IDENTITY NOT NULL,     -- 主キー（自動採番）
					element_id varchar(300) NOT NULL,                       -- XBRL要素ID（一意）
					item_name varchar(300) NOT NULL,                        -- 項目名
					category varchar(50) NULL,                              -- カテゴリ（BS/PL/CF等）
					unit_type varchar(20) NULL,                             -- 単位タイプ（円、株等）
					created_at timestamptz DEFAULT now() NULL,              -- 作成日時
					updated_at timestamptz DEFAULT now() NULL,              -- 更新日時
					CONSTRAINT financial_items_element_id_key UNIQUE (element_id),  -- 要素IDの一意制約
					CONSTRAINT financial_items_pkey PRIMARY KEY (item_id)   -- 主キー制約
					);

-- テーブルコメント
COMMENT ON TABLE public.financial_items IS '財務項目マスタテーブル - XBRLで定義される財務項目の定義';
COMMENT ON COLUMN public.financial_items.item_id IS '項目ID（主キー）';
COMMENT ON COLUMN public.financial_items.element_id IS 'XBRL要素ID（一意）';
COMMENT ON COLUMN public.financial_items.item_name IS '財務項目名';
COMMENT ON COLUMN public.financial_items.category IS 'カテゴリ（BS:貸借対照表、PL:損益計算書、CF:キャッシュフロー等）';
COMMENT ON COLUMN public.financial_items.unit_type IS '単位タイプ（円、株、パーセント等）';

CREATE INDEX idx_items_element_id ON public.financial_items USING btree (element_id);

-- Permissions

ALTER TABLE public.financial_items OWNER TO "user";
GRANT ALL ON TABLE public.financial_items TO "user";

-- 財務報告書テーブル
-- 目的: 企業の財務報告書のメタデータを管理

-- public.financial_reports definition

-- Drop table

-- DROP TABLE public.financial_reports;

CREATE TABLE public.financial_reports ( 
					report_id int4 GENERATED ALWAYS AS IDENTITY NOT NULL,   -- 主キー（自動採番）
					company_id int4 NOT NULL,                               -- 企業ID（外部キー）
					document_type varchar(50) NOT NULL,                     -- 書類種別（四半期報告書等）
					fiscal_year varchar(4) NOT NULL,                        -- 会計年度
					quarter_type varchar(10) NULL,                          -- 四半期種別（Q1/Q2/Q3/Q4）
					fiscal_year_end date NOT NULL,                          -- 会計年度末日
					filing_date date NULL,                                  -- 提出日
					created_at timestamptz DEFAULT now() NULL,              -- 作成日時
					updated_at timestamptz DEFAULT now() NULL,              -- 更新日時
					CONSTRAINT financial_reports_pkey PRIMARY KEY (report_id),  -- 主キー制約
					CONSTRAINT financial_reports_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(company_id) ON DELETE CASCADE);  -- 外部キー制約

-- テーブルコメント
COMMENT ON TABLE public.financial_reports IS '財務報告書テーブル - 企業の財務報告書のメタデータ';
COMMENT ON COLUMN public.financial_reports.report_id IS '報告書ID（主キー）';
COMMENT ON COLUMN public.financial_reports.company_id IS '企業ID（companiesテーブルへの外部キー）';
COMMENT ON COLUMN public.financial_reports.document_type IS '書類種別（四半期報告書、有価証券報告書等）';
COMMENT ON COLUMN public.financial_reports.fiscal_year IS '会計年度（YYYY形式）';
COMMENT ON COLUMN public.financial_reports.quarter_type IS '四半期種別（Q1:第1四半期、Q2:第2四半期、Q3:第3四半期、Q4:通期）';
COMMENT ON COLUMN public.financial_reports.fiscal_year_end IS '会計年度末日';
COMMENT ON COLUMN public.financial_reports.filing_date IS 'EDINETへの提出日';

CREATE INDEX idx_reports_company_fiscal ON public.financial_reports USING btree (company_id, fiscal_year);

-- Permissions

ALTER TABLE public.financial_reports OWNER TO "user";
GRANT ALL ON TABLE public.financial_reports TO "user";

-- 財務データテーブル
-- 目的: 実際の財務数値を管理（最も大きなテーブル）
-- 想定レコード数: 約1,600万件/年（16,000報告書 × 1,000項目）

-- public.financial_data definition

-- Drop table

-- DROP TABLE public.financial_data;

CREATE TABLE public.financial_data ( 
					data_id int8 GENERATED ALWAYS AS IDENTITY NOT NULL,     -- 主キー（自動採番、int8使用）
					report_id int4 NOT NULL,                                -- 報告書ID（外部キー）
					item_id int4 NOT NULL,                                  -- 項目ID（外部キー）
					context_id varchar(300) NULL,                           -- XBRLコンテキストID
					period_type varchar(50) NOT NULL,                       -- 期間種別（Duration/Instant）
					consolidated_type varchar(10) NOT NULL,                 -- 連結種別（Consolidated/NonConsolidated）
					duration_type varchar(10) NOT NULL,                     -- 期間タイプ（Year/Quarter等）
					value numeric(20) NULL,                                 -- 数値（最大20桁）
					value_text text NULL,                                   -- テキスト値（数値以外の場合）
					is_numeric bool DEFAULT true NULL,                      -- 数値フラグ
					created_at timestamptz DEFAULT now() NULL,              -- 作成日時
					updated_at timestamptz DEFAULT now() NULL,              -- 更新日時
					CONSTRAINT financial_data_pkey PRIMARY KEY (data_id),   -- 主キー制約
					CONSTRAINT financial_data_item_id_fkey FOREIGN KEY (item_id) REFERENCES public.financial_items(item_id) ON DELETE CASCADE,  -- 外部キー制約
					CONSTRAINT financial_data_report_id_fkey FOREIGN KEY (report_id) REFERENCES public.financial_reports(report_id) ON DELETE CASCADE);  -- 外部キー制約

-- テーブルコメント
COMMENT ON TABLE public.financial_data IS '財務データテーブル - 実際の財務数値を管理（最も大きなテーブル）';
COMMENT ON COLUMN public.financial_data.data_id IS 'データID（主キー）';
COMMENT ON COLUMN public.financial_data.report_id IS '報告書ID（financial_reportsテーブルへの外部キー）';
COMMENT ON COLUMN public.financial_data.item_id IS '項目ID（financial_itemsテーブルへの外部キー）';
COMMENT ON COLUMN public.financial_data.context_id IS 'XBRLコンテキストID（期間・連結種別等の情報を含む）';
COMMENT ON COLUMN public.financial_data.period_type IS '期間種別（Duration:期間、Instant:時点）';
COMMENT ON COLUMN public.financial_data.consolidated_type IS '連結種別（Consolidated:連結、NonConsolidated:個別）';
COMMENT ON COLUMN public.financial_data.duration_type IS '期間タイプ（Year:年度、Quarter:四半期等）';
COMMENT ON COLUMN public.financial_data.value IS '数値（最大20桁、NULLの場合はvalue_textを使用）';
COMMENT ON COLUMN public.financial_data.value_text IS 'テキスト値（数値以外のデータ）';
COMMENT ON COLUMN public.financial_data.is_numeric IS '数値フラグ（true:数値、false:テキスト）';

CREATE INDEX idx_data_period_type ON public.financial_data USING btree (period_type, consolidated_type);
CREATE INDEX idx_data_report_item ON public.financial_data USING btree (report_id, item_id);

-- Permissions

ALTER TABLE public.financial_data OWNER TO "user";
GRANT ALL ON TABLE public.financial_data TO "user";

-- =====================================================
-- スキーマ権限設定
-- =====================================================

-- Permissions

GRANT ALL ON SCHEMA public TO pg_database_owner;
GRANT USAGE ON SCHEMA public TO public;