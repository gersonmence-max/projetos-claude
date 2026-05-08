from sqlalchemy.exc import IntegrityError
from datetime import datetime

from models import Base, engine, Deal, PostLog, Commission, Channel, get_db_session
from logging import logger

def init_db():
    """Create all tables in the database."""
    try:
        Base.metadata.create_all(engine)
        logger.info("Database tables created successfully.")

        with get_db_session() as session:
            # Ensure the main channel 'Clube USA' exists
            existing_channel = session.query(Channel).filter_by(name='Clube USA').first()
            if not existing_channel:
                new_channel = Channel(
                    name='Clube USA',
                    telegram_channel_id='NOT_CONFIGURED', # Will be updated by user
                    whatsapp_numbers='NOT_CONFIGURED', # Will be updated by user
                    active=True
                )
                session.add(new_channel)
                session.commit() # Commit here to get ID and avoid issues in main session
                logger.info("Default 'Clube USA' channel added to database.")
            else:
                logger.info("'Clube USA' channel already exists in database.")

    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise

def save_deal(deal_dict: dict) -> int | None:
    """
    Save a deal to the database, returning its ID.
    Detects and avoids duplicates based on the 'link'.
    """
    with get_db_session() as session:
        existing_deal = session.query(Deal).filter_by(link=deal_dict['link']).first()
        if existing_deal:
            logger.debug(f"Deal '{deal_dict['title']}' already exists. Skipping.")
            return existing_deal.id

        new_deal = Deal(
            title=deal_dict['title'],
            description=deal_dict.get('description'),
            link=deal_dict['link'],
            affiliate_link=deal_dict.get('affiliate_link'),
            discount_percentage=deal_dict.get('discount_percentage'),
            category=deal_dict.get('category'),
            source=deal_dict.get('source', 'slickdeals_rss'),
            asin=deal_dict.get('asin')
        )
        try:
            session.add(new_deal)
            session.flush() # Flush to get the ID before commit
            logger.info(f"Deal '{new_deal.title}' saved with ID: {new_deal.id}")
            return new_deal.id
        except IntegrityError:
            session.rollback()
            logger.warning(f"Integrity error when saving deal '{new_deal.title}'. Possible race condition for duplicate link. Skipping.")
            # Attempt to retrieve existing deal if it was just created by another process
            existing_deal_after_failure = session.query(Deal).filter_by(link=deal_dict['link']).first()
            if existing_deal_after_failure:
                return existing_deal_after_failure.id
            return None # Should not happen if IntegrityError is due to link

def log_post(deal_id: int, channel: str, status: str, error_message: str | None = None):
    """Log that a deal was attempted to be posted to a channel."""
    with get_db_session() as session:
        log_entry = PostLog(
            deal_id=deal_id,
            channel=channel,
            status=status,
            timestamp=datetime.utcnow(),
            error_message=error_message
        )
        session.add(log_entry)
        logger.info(f"Post log recorded for Deal ID {deal_id} on {channel}: {status}")

def save_commission(deal_id: int, amount: float, amazon_order_id: str | None = None, currency: str = "BRL"):
    """Log earned commission."""
    with get_db_session() as session:
        commission_entry = Commission(
            deal_id=deal_id,
            amazon_order_id=amazon_order_id,
            amount=amount,
            currency=currency,
            date_tracked=datetime.utcnow()
        )
        session.add(commission_entry)
        logger.info(f"Commission logged for Deal ID {deal_id}, amount: {amount} {currency}")

def get_channel_config(channel_name: str = 'Clube USA') -> Channel | None:
    """Retrieve channel configuration from the database."""
    with get_db_session() as session:
        return session.query(Channel).filter_by(name=channel_name).first()