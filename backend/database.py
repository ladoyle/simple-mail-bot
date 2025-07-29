from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "sqlite:///./mail_bot.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class EmailStatistic(Base):
    __tablename__ = "email_statistics"
    id = Column(Integer, primary_key=True, index=True)
    processed = Column(Integer, default=0)
    rule_id = Column(Integer, nullable=False)
    rule_name = Column(String, nullable=False)

class EmailRule(Base):
    __tablename__ = "email_rules"
    id = Column(Integer, primary_key=True, index=True)
    rule_name = Column(String, unique=True, index=True)
    condition = Column(String)
    action = Column(String, nullable=False)
