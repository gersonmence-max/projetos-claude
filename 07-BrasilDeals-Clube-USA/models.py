from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from contextlib import contextmanager

from config import DATABASE_URL
from logging import logger

Base = declarative_base()

class Deal(Base):
    __tablename__ = 'deals'

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    link = Column(String, unique=True, nullable=False)
    affiliate_link = Column(String)
    discount_percentage = Column(Float)
    category = Column(String)
    source = Column(String, default="slickdeals_rss")
    posted_at = Column(DateTime, default=datetime.utcnow)
    posted_channel = Column(String) # This might be removed if PostLog is the primary tracking
    asin = Column(String, index=True) # Amazon Standard Identification Number

    def __repr__(self):
        return f"<Deal(id={self.id}, title='{self.title}', category='{self.category}')>"

class Channel(Base):
    __tablename__ = 'channels'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    telegram_channel_id = Column(String, unique=True, nullable=True) # e.g. -1001234567890
    telegram_group_id = Column(String, unique=True, nullable=True) # e.g. -1001234567890
    whatsapp_numbers = Column(Text, nullable=True) # Comma-separated WhatsApp numbers for the channel/group
    active = Column(Boolean, default=True)

    def __repr__(self):
        return f"<Channel(id={self.id}, name='{self.name}', active={self.active})>"

class PostLog(Base):
    __tablename__ = 'post_logs'

    id = Column(Integer, primary_key=True, index=True)
    deal_id = Column(Integer, nullable=False, index=True) # Foreign key to deals.id (not enforced by ORM directly here, but conceptually linked)
    channel = Column(String, nullable=False) # e.g., 'telegram', 'whatsapp'
    status = Column(String, nullable=False) # 'success', 'error', 'skipped'
    timestamp = Column(DateTime, default=datetime.utcnow)
    error_message = Column(Text, nullable=True)

    def __repr__(self):
        return f"<PostLog(id={self.id}, deal_id={self.deal_id}, channel='{self.channel}', status='{self.status}')>"

class Commission(Base):
    __tablename__ = 'commissions'

    id = Column(Integer, primary_key=True, index=True)
    deal_id = Column(Integer, nullable=False, index=True) # Foreign key to deals.id
    amazon_order_id = Column(String, unique=True, nullable=True) # Amazon order ID for tracking
    amount = Column(Float, nullable=False)
    currency = Column(String, default="BRL") # Assuming BRL for BrasilDeals context
    date_tracked = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Commission(id={self.id}, deal_id={self.deal_id}, amount={self.amount}, date_tracked={self.date_tracked})>"

# Database engine and session setup
try:
    engine = create_engine(DATABASE_URL, pool_size=10, max_overflow=20)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    logger.info("Database engine and session factory created.")
except Exception as e:
    logger.critical(f"Failed to create database engine: {e}")
    raise

@contextmanager
def get_db_session():
    """Provide a transactional scope around a series of operations."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()