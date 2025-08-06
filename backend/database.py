from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "sqlite:///./mail_bot.db"
engine = create_engine(DATABASE_URL)
Base = declarative_base()

# Create database tables
Base.metadata.create_all(bind=engine)

def get_db():
    global local_session
    if local_session is None:
        local_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return local_session

class EmailStatistic(Base):
    __tablename__ = "email_statistics"
    id = Column(Integer, primary_key=True, index=True)
    processed = Column(Integer, default=0)
    rule_id = Column(Integer, nullable=False)
    rule_name = Column(String, nullable=False)

class EmailRule(Base):
    __tablename__ = "email_rules"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    condition = Column(String)
    action = Column(String, nullable=False)

class EmailLabel(Base):
    __tablename__ = "email_labels"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)