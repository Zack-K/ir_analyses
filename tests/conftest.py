import os
from dotenv import load_dotenv
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from utils.db_models import Base, Company, Financial_item, Financial_report, Financial_data

@pytest.fixture(scope="session")
def engine():
    """
    テストセッション全体で1度だけ実行されるエンジン作成のフィクスチャ。
    テーブル作成まで個々で行う。
    """
    load_dotenv()
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME")

    db_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    db_engine = create_engine(db_url)
    
    # テーブルを全て作成（DDL実行）
    Base.metadata.create_all(db_engine)  
    yield db_engine

    # 必要に応じて、テスト終了後にテーブル削除
    Base.metadata.drop_all(db_engine)  

@pytest.fixture(scope="function")
def db_session(engine):
    """
    各テスト関数ごとに新しいセッションを提供するフィクスチャ。
    テスト終了後にロールバックしてクリーンな状態を保つ。
    """
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db: Session = SessionLocal()

    #　既存データの全削除（データの独立性を保つため）
    # テーブルの順序は外部キー制約を考慮して削除、または　TRUNCATE CASCADEを検討
    db.query(Financial_data).delete()
    db.query(Financial_report).delete()
    db.query(Financial_item).delete()
    db.query(Company).delete()    
    db.commit()

    try:
        yield db
    finally:
        db.rollback()  # テスト後に変更をロールバックしてクリーンな状態を保つ
        db.close()     # セッションを閉じる