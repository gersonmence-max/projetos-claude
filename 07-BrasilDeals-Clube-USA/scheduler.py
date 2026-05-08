from apscheduler.schedulers.background import BackgroundScheduler
import asyncio
from datetime import datetime

from scraper import scrape_slickdeals_rss
from deal_processor import filter_deals, format_deal_message
from messenger import notify_channels
from database import init_db, save_deal, get_channel_config
from logging import logger

scheduler = BackgroundScheduler(timezone='America/Sao_Paulo') # Changed from America/New_York to Sao_Paulo for BrasilDeals context

async def run_scraper_cycle():
    """Executes a complete cycle: scrape → filter → format → post → log."""
    logger.info("Starting scraper cycle.")
    try:
        # 1. Scrape deals
        raw_deals = await scrape_slickdeals_rss()
        if not raw_deals:
            logger.info("No new deals scraped to process.")
            return

        # 2. Filter deals (e.g., discount > 50%)
        filtered_deals = filter_deals(raw_deals, min_discount_percentage=50)
        if not filtered_deals:
            logger.info("No deals passed the filter (min_discount_percentage=50%).")
            return

        logger.info(f"Processing {len(filtered_deals)} filtered deals.")

        # 3. Process and post each deal
        for deal in filtered_deals:
            deal_id = deal.get('id') # Should be present from save_deal in scraper.py
            if not deal_id:
                logger.error(f"Deal has no ID, skipping posting: {deal.get('title')}")
                continue

            deal['formatted_message'] = format_deal_message(deal)

            # 4. Post to channels and log status
            await notify_channels(deal)

        logger.info("Scraper cycle completed successfully.")

    except Exception as e:
        logger.critical(f"An unexpected error occurred during scraper cycle: {e}", exc_info=True)
        # In a real production system, you might want to send an alert here
        # e.g., via Telegram to an admin group.
        # await send_telegram_message(config.TELEGRAM_GROUP_ID, f"CRITICAL ERROR in scraper cycle: {e}")

def start_scheduler():
    """Initializes the database and starts the scheduler."""
    logger.info("Initializing database...")
    init_db() # Ensure DB is ready before scheduling jobs

    logger.info("Adding scraper job to scheduler.")
    # Rodar 4x/dia: 6AM, 10AM, 2PM, 6PM (local time, America/Sao_Paulo)
    scheduler.add_job(
        run_scraper_cycle,
        'cron',
        hour='6,10,14,18',
        minute=0,
        id='clubeusa_scraper_job',
        name='Clube USA Scraper Cycle'
    )

    logger.info("Starting scheduler...")
    scheduler.start()
    logger.info("Scheduler started. Press Ctrl+C to exit.")

    try:
        # Keep the main thread alive
        asyncio.get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler shutting down...")
        scheduler.shutdown()
        logger.info("Scheduler shut down successfully.")

if __name__ == '__main__':
    start_scheduler()