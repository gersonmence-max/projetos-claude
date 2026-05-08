# ============================================================
#  config.py — Clube USA Deal Scanner
#  Configure suas credenciais aqui
# ============================================================

# --- Amazon PA-API ---
AMAZON_ACCESS_KEY  = "SUA_ACCESS_KEY_AQUI"
AMAZON_SECRET_KEY  = "SUA_SECRET_KEY_AQUI"
AMAZON_PARTNER_TAG = "clubeusa-20"

# --- Walmart Affiliate (via Impact.com) ---
WALMART_PUBLISHER_ID = "SEU_PUBLISHER_ID_AQUI"
WALMART_API_KEY      = "SUA_API_KEY_WALMART_AQUI"

# --- eBay Partner Network ---
EBAY_APP_ID      = "SEU_APP_ID_EBAY_AQUI"
EBAY_CAMPAIGN_ID = "SEU_CAMPAIGN_ID_AQUI"
EBAY_CUSTOM_ID   = "clubeusa"

# --- Target Affiliate (via Impact.com) ---
TARGET_PUBLISHER_ID = "SEU_PUBLISHER_ID_TARGET_AQUI"

# --- BestBuy Affiliate (via Rakuten) ---
BESTBUY_API_KEY      = "SUA_API_KEY_BESTBUY_AQUI"
BESTBUY_PUBLISHER_ID = "SEU_PUBLISHER_ID_BESTBUY_AQUI"

# --- Slickdeals RSS (sem credencial) ---
SLICKDEALS_ENABLED = True

# ============================================================
#  FILTROS DE QUALIDADE
# ============================================================
MIN_DISCOUNT_PCT = 20
MIN_RATING       = 3.8
MIN_REVIEWS      = 50
MAX_PRICE        = 600.0
MIN_PRICE        = 5.0
TOP_N_DEALS      = 150
MIN_SCORE        = 40

# --- Auto-aprovacao ---
AUTO_APPROVE_ENABLED      = True
AUTO_APPROVE_MIN_SCORE    = 85
AUTO_APPROVE_MIN_REVIEWS  = 500
AUTO_APPROVE_MIN_DISCOUNT = 30

# --- Cache de scan (minutos entre varreduras) ---
SCAN_CACHE_MINUTES = 60

# --- Delay de envio anti-spam (segundos) ---
SEND_DELAY_MIN = 30
SEND_DELAY_MAX = 120

# --- Historico de preco ---
PRICE_HISTORY_FILE  = "data/price_history.json"
PRICE_CONTEXT_LABEL = True

# --- WhatsApp ---
WHATSAPP_API_URL  = ""
WHATSAPP_GROUP_ID = ""

# --- Arquivos ---
DB_FILE    = "data/deals.json"
SENT_FILE  = "data/sent_ids.json"
LOG_FILE   = "logs/scanner.log"
CACHE_FILE = "data/scan_cache.json"

# --- Supabase (para alertas de preco) ---
import os
SUPABASE_URL         = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
ENCRYPTION_KEY       = os.environ.get("ENCRYPTION_KEY", "")
ZAPI_CLIENT_TOKEN    = os.environ.get("ZAPI_CLIENT_TOKEN", "")
