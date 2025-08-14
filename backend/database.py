import os

from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'mail_bot.db')}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    local_session = SessionLocal()
    try:
        yield local_session
    finally:
        local_session.close()


class EmailStatistic(Base):
    __tablename__ = "email_statistics"
    timestamp = Column(Integer, primary_key=True)
    processed = Column(Integer, default=0)
    rule_id = Column(Integer, nullable=False)
    rule_name = Column(String, nullable=False)


class EmailRule(Base):
    __tablename__ = "email_rules"
    id = Column(Integer, primary_key=True, index=True)
    gmail_id = Column(String, nullable=False)
    name = Column(String, unique=True)
    criteria = Column(String)
    action = Column(String, nullable=False)


class EmailLabel(Base):
    __tablename__ = "email_labels"
    id = Column(Integer, primary_key=True, index=True)
    gmail_id = Column(String, nullable=False)
    name = Column(String, nullable=False)


# Create database tables
Base.metadata.create_all(bind=engine)
