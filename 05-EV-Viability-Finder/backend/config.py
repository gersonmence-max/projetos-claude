# backend/config.py
import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
REGRID_API_KEY: str = os.getenv("REGRID_API_KEY", "")

DEFAULT_MAX_PRICE: float = 500_000
DEFAULT_MIN_ACRES: float = 1.0
DEFAULT_MIN_DISCOUNT_PCT: float = 10.0
DEFAULT_MAX_PRICE_PER_ACRE: float = 10_000
