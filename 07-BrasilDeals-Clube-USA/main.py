import asyncio
from datetime import datetime

from config import TELEGRAM_CHANNEL_ID, WHATSAPP_TEST_NUMBER
from database import init_db, save_deal, log_post
from scraper import scrape_slickdeals_rss
from deal_processor import filter_deals, format_deal_message
from messenger import send_telegram_message, send_whatsapp_message
from logging import logger

async def main():
    """
    Main function to run a single full cycle of scraping, processing, and posting deals.
    This is useful for initial setup verification and testing.
    For continuous operation, use scheduler.py.
    """
    logger.info("Starting a single full cycle execution of Clube USA.")

    # 1. Initialize DB
    init_db()

    # 2. Scrape deals
    logger.info("Fetching raw deals from RSS...")
    raw_deals = await scrape_slickdeals_rss()
    if not raw_deals:
        logger.warning("No raw deals fetched. Exiting main cycle.")
        return

    # 3. Filter deals (e.g., discount > 50%)
    logger.info("Filtering deals...")
    filtered_deals = filter_deals(raw_deals, min_discount_percentage=50)
    if not filtered_deals:
        logger.info("No deals passed the filter criteria. Exiting main cycle.")
        return

    logger.info(f"Processing {len(filtered_deals)} filtered deals for posting.")

    # 4. For each filtered deal: format, save to DB (if not already), and post
    for deal in filtered_deals:
        deal_id = deal.get('id') # Should already be present from scraper.py's save_deal
        if not deal_id:
            logger.error(f"Deal '{deal.get('title')}' has no ID after scrape. Skipping.")
            continue

        # 5. Format message
        msg = format_deal_message(deal)

        # 6. Post to Telegram
        if TELEGRAM_CHANNEL_ID and TELEGRAM_CHANNEL_ID != 'NOT_CONFIGURED':
            try:
                logger.info(f"Attempting to post deal {deal_id} to Telegram channel {TELEGRAM_CHANNEL_ID}.")
                telegram_success = await send_telegram_message(TELEGRAM_CHANNEL_ID, msg)
                if telegram_success:
                    log_post(deal_id, 'telegram', 'success')
                else:
                    log_post(deal_id, 'telegram', 'error', 'Failed to send message via Telegram API.')
            except Exception as e:
                log_post(deal_id, 'telegram', 'error', f'Unhandled Telegram error: {e}')
                logger.error(f"Unhandled error posting deal {deal_id} to Telegram: {e}")
        else:
            log_post(deal_id, 'telegram', 'skipped', 'TELEGRAM_CHANNEL_ID not configured.')
            logger.warning(f"TELEGRAM_CHANNEL_ID not configured. Skipping Telegram post for deal {deal_id}.")

        # 7. Post to WhatsApp (using WHATSAPP_TEST_NUMBER for this one-off run)
        if WHATSAPP_TEST_NUMBER and WHATSAPP_TEST_NUMBER != 'NOT_CONFIGURED':
            target_whatsapp_number = f"whatsapp:{WHATSAPP_TEST_NUMBER.replace(' ', '').replace('-', '')}"
            try:
                logger.info(f"Attempting to post deal {deal_id} to WhatsApp number {WHATSAPP_TEST_NUMBER}.")
                # send_whatsapp_message is synchronous, use asyncio.to_thread
                whatsapp_sid = await asyncio.to_thread(send_whatsapp_message, target_whatsapp_number, msg)
                if whatsapp_sid:
                    log_post(deal_id, 'whatsapp', 'success', whatsapp_sid)
                else:
                    log_post(deal_id, 'whatsapp', 'error', 'Failed to send message via Twilio WhatsApp API.')
            except Exception as e:
                log_post(deal_id, 'whatsapp', 'error', f'Unhandled WhatsApp error: {e}')
                logger.error(f"Unhandled error posting deal {deal_id} to WhatsApp: {e}")
        else:
            log_post(deal_id, 'whatsapp', 'skipped', 'WHATSAPP_TEST_NUMBER not configured.')
            logger.warning(f"WHATSAPP_TEST_NUMBER not configured. Skipping WhatsApp post for deal {deal_id}.")

        await asyncio.sleep(1) # Small delay between posts to avoid rate limits

    logger.info("Single full cycle execution finished.")

if __name__ == '__main__':
    asyncio.run(main())