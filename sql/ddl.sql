-- DBEAVERからDDLを自動生成したもの
-- DROP SCHEMA public;

COMMENT ON SCHEMA public IS 'standard public schema';

-- シーケンスの削除
DROP SEQUENCE IF EXISTS public.companies_company_id_seq CASCADE;
DROP SEQUENCE IF EXISTS public.financial_data_data_id_seq CASCADE;
DROP SEQUENCE IF EXISTS public.financial_items_item_id_seq CASCADE;
DROP SEQUENCE IF EXISTS public.financial_reports_report_id_seq CASCADE;

-- テーブルの削除
DROP TABLE IF EXISTS public.financial_data CASCADE;
DROP TABLE IF EXISTS public.financial_reports CASCADE;
DROP TABLE IF EXISTS public.financial_items CASCADE;
DROP TABLE IF EXISTS public.companies CASCADE;

-- シーケンス作成
CREATE SEQUENCE public.companies_company_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;

-- Permissions

ALTER SEQUENCE public.companies_company_id_seq OWNER TO "user";
GRANT ALL ON SEQUENCE public.companies_company_id_seq TO "user";

-- DROP SEQUENCE public.financial_data_data_id_seq;

CREATE SEQUENCE public.financial_data_data_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;

-- Permissions

ALTER SEQUENCE public.financial_data_data_id_seq OWNER TO "user";
GRANT ALL ON SEQUENCE public.financial_data_data_id_seq TO "user";

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

-- public.companies definition

-- Drop table

-- DROP TABLE public.companies;

CREATE TABLE public.companies ( 
					company_id serial4 NOT NULL, 
					edinet_code varchar(6) NOT NULL, 
					security_code varchar(5) NULL, 
					company_name varchar(200) NOT NULL, 
					industry_code varchar(10) NULL, 
					created_at timestamptz DEFAULT now() NULL, 
					updated_at timestamptz DEFAULT now() NULL, 
					CONSTRAINT companies_edinet_code_key UNIQUE (edinet_code), 
					CONSTRAINT companies_pkey PRIMARY KEY (company_id)
					);
CREATE INDEX idx_companies_edinet_code ON public.companies USING btree (edinet_code);

-- Permissions

ALTER TABLE public.companies OWNER TO "user";
GRANT ALL ON TABLE public.companies TO "user";


-- public.financial_items definition

-- Drop table

-- DROP TABLE public.financial_items;

CREATE TABLE public.financial_items ( 
					item_id serial4 NOT NULL, 
					element_id varchar(300) NOT NULL, 
					item_name varchar(300) NOT NULL, 
					category varchar(50) NULL, 
					unit_type varchar(20) NULL, 
					created_at timestamptz DEFAULT now() NULL, 
					updated_at timestamptz DEFAULT now() NULL, 
					CONSTRAINT financial_items_element_id_key UNIQUE (element_id), 
					CONSTRAINT financial_items_pkey PRIMARY KEY (item_id)
					);
CREATE INDEX idx_items_element_id ON public.financial_items USING btree (element_id);

-- Permissions

ALTER TABLE public.financial_items OWNER TO "user";
GRANT ALL ON TABLE public.financial_items TO "user";


-- public.financial_reports definition

-- Drop table

-- DROP TABLE public.financial_reports;

CREATE TABLE public.financial_reports ( 
					report_id serial4 NOT NULL, 
					company_id int4 NOT NULL, 
					document_type varchar(50) NOT NULL, 
					fiscal_year varchar(4) NOT NULL, 
					quarter_type varchar(10) NULL, 
					fiscal_year_end date NOT NULL, 
					filing_date date NULL, 
					created_at timestamptz DEFAULT now() NULL, 
					updated_at timestamptz DEFAULT now() NULL, 
					CONSTRAINT financial_reports_pkey PRIMARY KEY (report_id), 
					CONSTRAINT financial_reports_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(company_id) ON DELETE CASCADE);
CREATE INDEX idx_reports_company_fiscal ON public.financial_reports USING btree (company_id, fiscal_year);

-- Permissions

ALTER TABLE public.financial_reports OWNER TO "user";
GRANT ALL ON TABLE public.financial_reports TO "user";


-- public.financial_data definition

-- Drop table

-- DROP TABLE public.financial_data;

CREATE TABLE public.financial_data ( 
					data_id bigserial NOT NULL, 
					report_id int4 NOT NULL, 
					item_id int4 NOT NULL, 
					context_id varchar(100) NULL, 
					period_type varchar(50) NOT NULL, 
					consolidated_type varchar(10) NOT NULL, 
					duration_type varchar(10) NOT NULL, 
					value numeric(20) NULL, 
					value_text text NULL, 
					is_numeric bool DEFAULT true NULL, 
					created_at timestamptz DEFAULT now() NULL, 
					updated_at timestamptz DEFAULT now() NULL, 
					CONSTRAINT financial_data_pkey PRIMARY KEY (data_id),
					CONSTRAINT financial_data_item_id_fkey FOREIGN KEY (item_id) REFERENCES public.financial_items(item_id) ON DELETE CASCADE, 
					CONSTRAINT financial_data_report_id_fkey FOREIGN KEY (report_id) REFERENCES public.financial_reports(report_id) ON DELETE CASCADE);
CREATE INDEX idx_data_period_type ON public.financial_data USING btree (period_type, consolidated_type);
CREATE INDEX idx_data_report_item ON public.financial_data USING btree (report_id, item_id);

-- Permissions

ALTER TABLE public.financial_data OWNER TO "user";
GRANT ALL ON TABLE public.financial_data TO "user";




-- Permissions

GRANT ALL ON SCHEMA public TO pg_database_owner;
GRANT USAGE ON SCHEMA public TO public;