# ============================================================
#  ebay_api.py — eBay Browse API + Partner Network
#
#  eBay tem API oficial gratuita (Browse API)
#  Credencial: App ID obtido em developer.ebay.com
#  Link afiliado: via rover.ebay.com com campaign ID
# ============================================================

import logging
import requests
import config

log = logging.getLogger("ebay_api")

EBAY_API_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"


def get_ebay_token() -> str | None:
    """Obtem token OAuth do eBay usando App ID."""
    if not config.EBAY_APP_ID or "SEU_" in config.EBAY_APP_ID:
        return None

    import base64
    # eBay usa Client Credentials flow
    # App ID = Client ID, precisamos do Client Secret tambem
    # Por ora usa token publico limitado
    return None


def search_ebay(query: str, num_items: int = 10) -> tuple:
    """
    Busca itens no eBay com desconto.
    Retorna (items, erro).
    """
    if not config.EBAY_APP_ID or "SEU_" in config.EBAY_APP_ID:
        return [], "eBay App ID nao configurado."

    headers = {
        "Authorization": f"Bearer {get_ebay_token()}",
        "Content-Type":  "application/json",
        "X-EBAY-C-MARKETPLACE-ID": "EBAY_US",
    }

    params = {
        "q":      query,
        "limit":  num_items,
        "filter": "buyingOptions:{FIXED_PRICE},conditions:{NEW}",
        "sort":   "price",
    }

    try:
        resp = requests.get(EBAY_API_URL, headers=headers, params=params, timeout=15)
        if resp.status_code == 401:
            return [], "eBay token invalido. Verifique o App ID."
        if resp.status_code != 200:
            return [], f"eBay API erro {resp.status_code}"

        data  = resp.json()
        items = data.get("itemSummaries", [])
        return items, None

    except Exception as e:
        return [], f"Erro eBay: {e}"


def build_affiliate_url(item_id: str, product_url: str) -> str:
    """Gera URL de afiliado eBay via rover.ebay.com"""
    if config.EBAY_CAMPAIGN_ID and "SEU_" not in config.EBAY_CAMPAIGN_ID:
        import urllib.parse
        encoded = urllib.parse.quote(product_url, safe='')
        return (
            f"https://rover.ebay.com/rover/1/711-53200-19255-0/1"
            f"?ff3=4&pub=5575{config.EBAY_CAMPAIGN_ID}"
            f"&toolid=10001&campid={config.EBAY_CAMPAIGN_ID}"
            f"&customid={config.EBAY_CUSTOM_ID}"
            f"&mpre={encoded}"
        )
    return product_url


def parse_ebay_item(item: dict) -> dict | None:
    """Parseia item do eBay para formato padrao."""
    try:
        item_id = item.get("itemId", "")
        title   = item.get("title")
        if not title or not item_id:
            return None

        # Preco
        price_obj = item.get("price", {})
        price_now = float(price_obj.get("value", 0))
        if not price_now:
            return None

        # eBay nao sempre tem preco original — pula se nao tiver
        original = None
        for label in item.get("additionalImages", []):
            pass
        # Tenta pegar via marketingPrice
        mkt = item.get("marketingPrice", {})
        if mkt:
            orig = mkt.get("originalPrice", {})
            if orig:
                original = float(orig.get("value", 0))

        if not original or original <= price_now:
            return None

        discount_pct = round((1 - price_now / original) * 100)
        if discount_pct < config.MIN_DISCOUNT_PCT:
            return None
        if price_now > config.MAX_PRICE or price_now < config.MIN_PRICE:
            return None

        # Rating — eBay nao tem rating por produto na Browse API
        # Usa seller feedback como proxy
        seller      = item.get("seller", {})
        feedback    = seller.get("feedbackPercentage", "0")
        rating      = float(feedback) / 20 if feedback else 0  # converte % para escala 5

        image       = item.get("image", {}).get("imageUrl")
        product_url = item.get("itemWebUrl", f"https://www.ebay.com/itm/{item_id}")
        affiliate_url = build_affiliate_url(item_id, product_url)

        return {
            "source":       "ebay",
            "source_id":    item_id,
            "title":        title,
            "price_now":    price_now,
            "price_was":    original,
            "discount_pct": discount_pct,
            "rating":       round(rating, 1),
            "reviews":      0,
            "image_url":    image,
            "product_url":  product_url,
            "affiliate_url": affiliate_url,
        }

    except Exception as e:
        log.debug(f"Erro parse eBay: {e}")
        return None
