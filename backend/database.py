import os

from sqlalchemy import create_engine, Column, Integer, String, JSON
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
    id = Column(Integer, primary_key=True, index=True)
    email_address = Column(String, primary_key=True)
    timestamp = Column(Integer, default=0)
    processed = Column(Integer, default=0)
    rule_id = Column(Integer, nullable=False)
    rule_name = Column(String, nullable=False)


class EmailRule(Base):
    __tablename__ = "email_rules"
    id = Column(Integer, primary_key=True, index=True)
    email_address = Column(String, default="")
    gmail_id = Column(String, nullable=False)
    name = Column(String, default="")
    criteria = Column(String, default="")
    addLabelIds = Column(JSON, nullable=False, default=list)
    removeLabelIds = Column(JSON, nullable=False, default=list)
    forward = Column(String, default="")


class EmailLabel(Base):
    __tablename__ = "email_labels"
    id = Column(Integer, primary_key=True, index=True)
    email_address = Column(String, default="")
    gmail_id = Column(String, nullable=False)
    name = Column(String, nullable=False)
    text_color = Column(String, default="#000000")
    background_color = Column(String, default="#FFFFFF")


class AuthorizedUsers(Base):
    __tablename__ = "authorized_users"
    id = Column(Integer, default=0, index=True)
    email = Column(String, primary_key=True, default="")
    last_history_id = Column(String, default="")


# Create database tables
Base.metadata.create_all(bind=engine)
