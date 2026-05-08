import telegram
from twilio.rest import Client
import asyncio

from config import (
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID,
    TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_NUMBER,
    WHATSAPP_TEST_NUMBER # Using for tests, in production, this would be dynamic
)
from database import log_post, get_channel_config
from logging import logger

async def send_telegram_message(chat_id: str, message: str) -> bool:
    """Envia MENSAGEM REAL para um canal/grupo Telegram."""
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN is not configured. Cannot send Telegram message.")
        return False
    if not chat_id:
        logger.error("Telegram chat_id is missing. Cannot send Telegram message.")
        return False

    try:
        bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
        await bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode=telegram.constants.ParseMode.HTML,
            disable_web_page_preview=False
        )
        logger.info(f"Telegram message sent successfully to {chat_id}.")
        return True
    except telegram.error.TelegramError as e:
        logger.error(f"Error sending Telegram message to {chat_id}: {e}")
        return False
    except Exception as e:
        logger.error(f"An unexpected error occurred while sending Telegram message to {chat_id}: {e}")
        return False

def send_whatsapp_message(phone_number: str, message: str) -> str | None:
    """Envia MENSAGEM REAL para WhatsApp via Twilio."""
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN or not TWILIO_WHATSAPP_NUMBER:
        logger.error("Twilio credentials (SID, Token, WhatsApp Number) are not configured. Cannot send WhatsApp message.")
        return None
    if not phone_number or not phone_number.startswith("whatsapp:"):
        logger.error(f"Invalid WhatsApp phone number format: '{phone_number}'. Must start with 'whatsapp:+<country_code><number>'.")
        return None

    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        response = client.messages.create(
            from_=TWILIO_WHATSAPP_NUMBER,
            body=message,
            to=phone_number
        )
        logger.info(f"WhatsApp message sent successfully to {phone_number}. SID: {response.sid}")
        return response.sid
    except Exception as e:
        logger.error(f"Error sending WhatsApp message to {phone_number}: {e}")
        return None

async def notify_channels(deal: dict):
    """
    Notifies configured channels (Telegram, WhatsApp) with a real deal message.
    Logs the status of each sending attempt.
    """
    deal_id = deal.get('id')
    if not deal_id:
        logger.error("Cannot notify channels: Deal ID is missing.")
        return

    message = deal.get('formatted_message')
    if not message:
        logger.error(f"Cannot notify channels for deal {deal_id}: Formatted message is missing.")
        return

    channel_config = get_channel_config('Clube USA') # Assuming 'Clube USA' is the main channel
    if not channel_config or not channel_config.active:
        logger.warning("Main channel 'Clube USA' is not found or not active. Skipping notifications.")
        return

    # Send to Telegram
    telegram_channel_id = channel_config.telegram_channel_id if channel_config.telegram_channel_id != 'NOT_CONFIGURED' else None
    if telegram_channel_id:
        try:
            telegram_success = await send_telegram_message(telegram_channel_id, message)
            await asyncio.sleep(0.5) # Small delay to avoid API rate limits, adjust as needed
            if telegram_success:
                log_post(deal_id, 'telegram', 'success')
            else:
                log_post(deal_id, 'telegram', 'error', 'Failed to send')
        except Exception as e:
            log_post(deal_id, 'telegram', 'error', str(e))
            logger.error(f"Unhandled error sending Telegram message for deal {deal_id}: {e}")
    else:
        logger.warning(f"Telegram channel ID for 'Clube USA' not configured. Skipping Telegram notification for deal {deal_id}.")
        log_post(deal_id, 'telegram', 'skipped', 'Channel ID not configured')

    # Send to WhatsApp (using a test number for now as channel_config.whatsapp_numbers is typically a list for groups)
    # For a real WhatsApp channel implementation, 'whatsapp_numbers' would be parsed into individual recipient numbers.
    whatsapp_numbers_str = channel_config.whatsapp_numbers if channel_config.whatsapp_numbers != 'NOT_CONFIGURED' else None
    if whatsapp_numbers_str and WHATSAPP_TEST_NUMBER:
        # Assuming WHATSAPP_TEST_NUMBER as the target for now for simplicity,
        # in a real setup, whatsapp_numbers_str could be a comma-separated list
        # and each number would be processed.
        target_whatsapp_number = f"whatsapp:{WHATSAPP_TEST_NUMBER.replace(' ', '').replace('-', '')}"
        try:
            # Twilio's API is synchronous, run in executor to avoid blocking the async event loop
            whatsapp_sid = await asyncio.to_thread(send_whatsapp_message, target_whatsapp_number, message)
            if whatsapp_sid:
                log_post(deal_id, 'whatsapp', 'success', whatsapp_sid)
            else:
                log_post(deal_id, 'whatsapp', 'error', 'Failed to send')
        except Exception as e:
            log_post(deal_id, 'whatsapp', 'error', str(e))
            logger.error(f"Unhandled error sending WhatsApp message for deal {deal_id}: {e}")
    else:
        logger.warning(f"WhatsApp numbers or WHATSAPP_TEST_NUMBER for 'Clube USA' not configured. Skipping WhatsApp notification for deal {deal_id}.")
        log_post(deal_id, 'whatsapp', 'skipped', 'WhatsApp configuration missing')