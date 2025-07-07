from sqlalchemy.schema import Column
from sqlalchemy.types import String, Integer, DateTime, Numeric, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import ForeignKey

class Base(DeclarativeBase):
    """ベースクラス作成"""
    pass

class Company(Base):
     """会社テーブルのクラス"""
     __tablename__ = "companies"
     company_id = Column(Integer, primary_key=True)
     edinet_code = Column(String(6), nullable=False)
     security_code = Column(String(5))
     industry_code = Column(String(10))
     create_at = Column(DateTime, nullable=False)
     update_at = Column(DateTime, nullable=False)

class Financial_data(Base):
    """財務情報テーブルのクラス"""
    __tablename__ = "financial_data"
    data_id = Column(Integer, primary_key=True )
    report_id = Column(Integer, ForeignKey("financial_reports.report_id"),  nullable=False)
    item_id = Column(Integer,  ForeignKey("financial_items.item_id"), nullable=False)
    context_id = Column(String(100))
    period_type = Column(String(50), nullable=False)
    consolidated_type = Column(String(10), nullable=False)
    duration_type = Column(String(10), nullable=False)
    value = Column(Numeric(20))
    value_text = Column(Text)
    is_numeric = Column(Boolean, server_default=True)
    create_at = Column(DateTime, nullable=False)
    update_at = Column(DateTime, nullable=False)


class Financial_item(Base):
    """財務項目マスタテーブル"""
    __tablename__ = "financial_items"
    item_id = Column(Integer, primary_key=True) 
    element_id = Column(String(300))
    item_name = Column(String(300))
    category = Column(String(50))
    unit_type = Column(String(20))
    create_at = Column(DateTime, nullable=False)
    update_at = Column(DateTime, nullable=False)


class Financial_report(Base):
    """財務報告書のマスターテーブル"""
    __tablename__ = "financial_reports"
    report_id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.company_id"), nullable=False)
    document_type = Column(String(50), nullable=False)
    fiscal_year = Column(String(4), nullable=False)
    quarter_type = Column(String(10))
    fiscal_year_end = Column(DateTime, nullable=False)
    filing_date = Column(DateTime)
    create_at = Column(DateTime, nullable=False)
    update_at = Column(DateTime, nullable=False)