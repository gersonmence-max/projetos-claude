import pytest
import asyncio
from datetime import datetime, timedelta

from config import (
    TELEGRAM_CHANNEL_ID, TELEGRAM_BOT_TOKEN,
    TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_NUMBER, WHATSAPP_TEST_NUMBER,
    DATABASE_URL
)
from database import init_db, get_db_session
from models import Deal, PostLog, Commission
from messenger import send_telegram_message, send_whatsapp_message
from scraper import scrape_slickdeals_rss
from deal_processor import filter_deals, format_deal_message, extract_asin_from_amazon_url
from logging import logger

# Fixture for database cleanup and session
@pytest.fixture(scope="module", autouse=True)
def setup_database():
    if not DATABASE_URL or "user:password@host" in DATABASE_URL:
        pytest.skip("DATABASE_URL not configured in .env. Skipping database tests.")

    # Ensure DB is initialized before tests
    init_db()
    with get_db_session() as session:
        # Clear data from previous runs if any
        session.query(Commission).delete()
        session.query(PostLog).delete()
        session.query(Deal).delete()
        session.commit()
    logger.info("Database cleaned for integration tests.")
    yield
    # Cleanup after all tests in the module (optional, can be commented out to inspect data)
    with get_db_session() as session:
        session.query(Commission).delete()
        session.query(PostLog).delete()
        session.query(Deal).delete()
        session.commit()
    logger.info("Database cleaned after integration tests.")

@pytest.mark.asyncio
async def test_telegram_connection():
    """Confirms that the Telegram bot can send a real message."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHANNEL_ID or TELEGRAM_CHANNEL_ID == 'NOT_CONFIGURED':
        pytest.skip("Telegram credentials or channel ID not configured. Skipping Telegram test.")

    test_message = f"🤖 Teste de conexão do Clube USA Telegram! ({datetime.now().strftime('%H:%M')})"
    logger.info(f"Attempting to send Telegram test message to {TELEGRAM_CHANNEL_ID}...")
    success = await send_telegram_message(TELEGRAM_CHANNEL_ID, test_message)
    assert success is True, "Telegram message sending failed."
    logger.info("Telegram connection test passed.")

@pytest.mark.asyncio
async def test_whatsapp_connection():
    """Confirms that the WhatsApp bot can send a real message via Twilio."""
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN or not TWILIO_WHATSAPP_NUMBER or not WHATSAPP_TEST_NUMBER:
        pytest.skip("Twilio or WhatsApp test number not configured. Skipping WhatsApp test.")

    test_message = f"🤖 Teste de conexão do Clube USA WhatsApp! ({datetime.now().strftime('%H:%M')})"
    target_whatsapp_number = f"whatsapp:{WHATSAPP_TEST_NUMBER.replace(' ', '').replace('-', '')}"
    logger.info(f"Attempting to send WhatsApp test message to {WHATSAPP_TEST_NUMBER}...")
    # send_whatsapp_message is synchronous, run in thread
    sid = await asyncio.to_thread(send_whatsapp_message, target_whatsapp_number, test_message)
    assert sid is not None, "WhatsApp message sending failed."
    logger.info("WhatsApp connection test passed.")

def test_database_connection():
    """Confirms that the DB is accessible and a session can be obtained."""
    if not DATABASE_URL or "user:password@host" in DATABASE_URL:
        pytest.skip("DATABASE_URL not configured. Skipping database test.")
    with get_db_session() as session:
        assert session is not None, "Failed to get a database session."
        # Try a simple query to ensure connection is live
        session.query(Deal).limit(1).all()
    logger.info("Database connection test passed.")

@pytest.mark.asyncio
async def test_scraper():
    """Executes the scraper and confirms it returns deals."""
    logger.info("Running scraper test...")
    deals = await scrape_slickdeals_rss()
    assert len(deals) > 0, "Scraper did not return any deals."
    # Check if deals have expected keys after processing
    for deal in deals:
        assert 'title' in deal
        assert 'link' in deal
        assert 'id' in deal # 'id' should be added by save_deal
        assert 'affiliate_link' in deal
        if "amazon.com" in deal['link']:
            assert 'asin' in deal
    logger.info(f"Scraper test passed, {len(deals)} deals found and processed.")

def test_deal_processor_functions():
    """Tests deal filtering, ASIN extraction, and message formatting."""
    sample_deal = {
        'title': 'Amazing Gadget 70% Off Amazon!',
        'description': 'A very cool gadget description.',
        'link': 'https://www.amazon.com.br/Amazing-Gadget-ASIN1234567/dp/B08XYZ1234',
        'discount_percentage': 70.0,
        'category': 'Electronics',
        'posted_at': datetime.now() - timedelta(hours=1)
    }

    # Test filter_deals
    filtered = filter_deals([sample_deal], min_discount_percentage=50)
    assert len(filtered) == 1
    assert filtered[0]['title'] == sample_deal['title']

    filtered_low_discount = filter_deals([sample_deal], min_discount_percentage=80)
    assert len(filtered_low_discount) == 0

    # Test extract_asin_from_amazon_url
    asin = extract_asin_from_amazon_url(sample_deal['link'])
    assert asin == 'B08XYZ1234'
    assert extract_asin_from_amazon_url('https://example.com/not-amazon') is None

    # Test format_deal_message (will include affiliate link if AMAZON_PARTNER_TAG is set)
    formatted_message = format_deal_message(sample_deal)
    assert 'Amazing Gadget 70% OFF' in formatted_message
    assert 'Ver Oferta Agora!' in formatted_message
    assert '#Electronics' in formatted_message
    assert '🔗 <a href=' in formatted_message
    assert 'https://www.amazon.com.br/Amazing-Gadget-ASIN1234567/dp/B08XYZ1234?tag=' in formatted_message
    logger.info("Deal processor functions test passed.")

@pytest.mark.asyncio
async def test_end_to_end_cycle(setup_database):
    """
    Full cycle test: scrape -> filter -> post -> log -> database validation.
    This test relies on external services (RSS, Telegram, Twilio) if credentials are set.
    """
    logger.info("Starting end-to-end cycle test...")

    # Initial DB state
    with get_db_session() as session:
        initial_deal_count = session.query(Deal).count()
        initial_post_log_count = session.query(PostLog).count()
        initial_commission_count = session.query(Commission).count()

    # Scrape deals
    raw_deals = await scrape_slickdeals_rss()
    assert len(raw_deals) > 0, "Scraper did not return any deals for E2E test."
    logger.info(f"E2E: Scraped {len(raw_deals)} deals.")

    # Filter deals (assuming some will pass)
    filtered_deals = filter_deals(raw_deals, min_discount_percentage=50)
    assert len(filtered_deals) > 0, "No deals passed filter for E2E test."
    logger.info(f"E2E: {len(filtered_deals)} deals passed filter.")

    posted_deal_ids = []
    for deal in filtered_deals:
        deal_id = deal.get('id')
        assert deal_id is not None, "Deal should have an ID after save_deal."
        posted_deal_ids.append(deal_id)

        # Format message
        deal['formatted_message'] = format_deal_message(deal)

        # Post to Telegram (if configured)
        if TELEGRAM_BOT_TOKEN and TELEGRAM_CHANNEL_ID and TELEGRAM_CHANNEL_ID != 'NOT_CONFIGURED':
            telegram_success = await send_telegram_message(TELEGRAM_CHANNEL_ID, deal['formatted_message'])
            if telegram_success:
                log_post(deal_id, 'telegram', 'success')
            else:
                log_post(deal_id, 'telegram', 'error', 'E2E test: Telegram failed.')
            await asyncio.sleep(0.5) # Prevent rate limits

        # Post to WhatsApp (if configured)
        if TWILIO_ACCOUNT_SID and WHATSAPP_TEST_NUMBER:
            target_whatsapp_number = f"whatsapp:{WHATSAPP_TEST_NUMBER.replace(' ', '').replace('-', '')}"
            whatsapp_sid = await asyncio.to_thread(send_whatsapp_message, target_whatsapp_number, deal['formatted_message'])
            if whatsapp_sid:
                log_post(deal_id, 'whatsapp', 'success', whatsapp_sid)
            else:
                log_post(deal_id, 'whatsapp', 'error', 'E2E test: WhatsApp failed.')
            await asyncio.sleep(0.5) # Prevent rate limits

    # Validate database state after posting
    with get_db_session() as session:
        final_deal_count = session.query(Deal).count()
        final_post_log_count = session.query(PostLog).count()

        assert final_deal_count > initial_deal_count, "No new deals were saved to DB."
        # At least one post log entry per deal if any channel is configured
        if TELEGRAM_BOT_TOKEN or TWILIO_ACCOUNT_SID:
            assert final_post_log_count >= initial_post_log_count + len(filtered_deals), \
                "No post logs were recorded or not enough for filtered deals."

        # Check if deals marked as 'success' exist in logs
        for deal_id in posted_deal_ids:
            if TELEGRAM_BOT_TOKEN and TELEGRAM_CHANNEL_ID != 'NOT_CONFIGURED':
                telegram_log_exists = session.query(PostLog).filter_by(deal_id=deal_id, channel='telegram', status='success').first() is not None
                if TELEGRAM_BOT_TOKEN and TELEGRAM_CHANNEL_ID != 'NOT_CONFIGURED': # Only assert if supposed to post
                    assert telegram_log_exists, f"No successful Telegram post log for deal {deal_id}."

            if TWILIO_ACCOUNT_SID and WHATSAPP_TEST_NUMBER:
                whatsapp_log_exists = session.query(PostLog).filter_by(deal_id=deal_id, channel='whatsapp', status='success').first() is not None
                if TWILIO_ACCOUNT_SID and WHATSAPP_TEST_NUMBER: # Only assert if supposed to post
                    assert whatsapp_log_exists, f"No successful WhatsApp post log for deal {deal_id}."

    logger.info("End-to-end cycle test passed.")