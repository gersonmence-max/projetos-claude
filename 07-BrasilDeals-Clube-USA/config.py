import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# TELEGRAM
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")
TELEGRAM_GROUP_ID = os.getenv("TELEGRAM_GROUP_ID") # Optional

# WHATSAPP (Twilio)
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")
WHATSAPP_TEST_NUMBER = os.getenv("WHATSAPP_TEST_NUMBER")

# AMAZON
AMAZON_PARTNER_TAG = os.getenv("AMAZON_PARTNER_TAG")
# For full PA-API integration, these would also be needed:
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AMAZON_HOST = os.getenv("AMAZON_HOST", "webservices.amazon.com.br")

# DATABASE
DATABASE_URL = os.getenv("DATABASE_URL")

# LOGGING
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE_PATH = os.getenv("LOG_FILE_PATH", "logs/clubeusa.log")

# SCRAPER
SLICKDEALS_RSS_FEED = "https://slickdeals.net/deals/feed/" # Example RSS feed for testing.
# In a real BrasilDeals/ClubeUSA context, this would be a Brazilian deals feed.

# Create logs directory if it doesn't exist
os.makedirs(os.path.dirname(LOG_FILE_PATH), exist_ok=True)