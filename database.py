from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# 🚨 PASTE YOUR SUPABASE URI HERE 🚨
# Note: If your Supabase string starts with exactly "postgres://", 
# you MUST change it to "postgresql://" for SQLAlchemy to read it correctly.
SQLALCHEMY_DATABASE_URL = "postgresql://postgres.iwbnrjimwrpxksfzdpvq:1kS1Rz7IBLD3s9lR@aws-1-ap-northeast-2.pooler.supabase.com:5432/postgres"

# We removed connect_args={"check_same_thread": False} because that is only for SQLite
engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()