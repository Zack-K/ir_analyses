from sqlalchemy.schema import Column
from sqlalchemy.types import (
    String,
    Integer,
    DateTime,
    Numeric,
    Text,
    Boolean,
    BigInteger,
    Date,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import ForeignKey
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    """ベースクラス作成"""

    pass


class Company(Base):
    """会社テーブルのクラス"""

    __tablename__ = "companies"

    company_id = Column(Integer, primary_key=True, autoincrement=True)
    edinet_code = Column(String(6), nullable=False, unique=True)
    security_code = Column(String(5), nullable=True)
    industry_code = Column(String(10), nullable=True)
    company_name = Column(String(200), nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=True
    )
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=True
    )


class Financial_data(Base):
    """財務情報テーブルのクラス"""

    __tablename__ = "financial_data"
    data_id = Column(BigInteger, primary_key=True, autoincrement=True)
    report_id = Column(
        Integer, ForeignKey("financial_reports.report_id"), nullable=False
    )
    item_id = Column(Integer, ForeignKey("financial_items.item_id"), nullable=False)
    context_id = Column(String(100), nullable=True)
    period_type = Column(String(50), nullable=False)
    consolidated_type = Column(String(10), nullable=False)
    duration_type = Column(String(10), nullable=False)
    value = Column(Numeric(20), nullable=True)
    value_text = Column(Text, nullable=True)
    is_numeric = Column(Boolean, server_default="true", nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=True
    )
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=True
    )


class Financial_item(Base):
    """財務項目マスタテーブル"""

    __tablename__ = "financial_items"
    item_id = Column(Integer, primary_key=True, autoincrement=True)
    element_id = Column(String(300), nullable=False, unique=True)
    item_name = Column(String(300), nullable=False)
    category = Column(String(50), nullable=True)
    unit_type = Column(String(20), nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=True
    )
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=True
    )


class Financial_report(Base):
    """財務報告書のマスターテーブル"""

    __tablename__ = "financial_reports"
    report_id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("companies.company_id"), nullable=False)
    document_type = Column(String(50), nullable=False)
    fiscal_year = Column(String(4), nullable=False)
    quarter_type = Column(String(10), nullable=True)
    fiscal_year_end = Column(Date, nullable=False)
    filing_date = Column(Date, nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=True
    )
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=True
    )
