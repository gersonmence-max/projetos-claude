# ============================================================
#  bestbuy_api.py — BestBuy Products API + Rakuten Affiliate
#
#  API oficial gratuita: developer.bestbuy.com
#  Affiliate: via Rakuten (linkshare.com)
# ============================================================

import logging
import requests
import config

log = logging.getLogger("bestbuy_api")

BESTBUY_API_URL = "https://api.bestbuy.com/v1/products"


def search_bestbuy(query: str, num_items: int = 10) -> tuple:
    """
    Busca produtos na BestBuy com desconto.
    Retorna (items, erro).
    """
    if not config.BESTBUY_API_KEY or "SUA_" in config.BESTBUY_API_KEY:
        return [], "BestBuy API Key nao configurada."

    # BestBuy API usa formato de query especial
    # salePrice < regularPrice = produto em promocao
    search_filter = (
        f"(search={query.replace(' ','+')})"
        f"&(salePrice<regularPrice)"
        f"&(onSale=true)"
    )

    params = {
        "apiKey":   config.BESTBUY_API_KEY,
        "show":     "sku,name,salePrice,regularPrice,customerReviewAverage,customerReviewCount,image,url,onSale,percentSavings",
        "pageSize": num_items,
        "sort":     "customerReviewCount.dsc",
        "format":   "json",
    }

    try:
        url  = f"{BESTBUY_API_URL}({search_filter})"
        resp = requests.get(url, params=params, timeout=15)

        if resp.status_code == 403:
            return [], "BestBuy API Key invalida."
        if resp.status_code != 200:
            return [], f"BestBuy API erro {resp.status_code}"

        data  = resp.json()
        items = data.get("products", [])
        return items, None

    except Exception as e:
        return [], f"Erro BestBuy: {e}"


def build_affiliate_url(product_url: str) -> str:
    """Gera URL de afiliado BestBuy via Rakuten."""
    if config.BESTBUY_PUBLISHER_ID and "SEU_" not in config.BESTBUY_PUBLISHER_ID:
        import urllib.parse
        encoded = urllib.parse.quote(product_url, safe='')
        return (
            f"https://click.linksynergy.com/deeplink"
            f"?id={config.BESTBUY_PUBLISHER_ID}"
            f"&mid=608"
            f"&murl={encoded}"
        )
    return product_url


def parse_bestbuy_item(item: dict) -> dict | None:
    """Parseia item da BestBuy para formato padrao."""
    try:
        sku      = str(item.get("sku", ""))
        title    = item.get("name")
        if not title or not sku:
            return None

        price_now = float(item.get("salePrice") or 0)
        price_was = float(item.get("regularPrice") or 0)

        if not price_now or not price_was or price_was <= price_now:
            return None

        discount_pct = round((1 - price_now / price_was) * 100)
        if discount_pct < config.MIN_DISCOUNT_PCT:
            return None
        if price_now > config.MAX_PRICE or price_now < config.MIN_PRICE:
            return None

        rating  = float(item.get("customerReviewAverage") or 0)
        reviews = int(item.get("customerReviewCount") or 0)

        if rating  > 0 and rating  < config.MIN_RATING:  return None
        if reviews > 0 and reviews < config.MIN_REVIEWS:  return None

        image       = item.get("image")
        product_url = item.get("url", f"https://www.bestbuy.com/site/{sku}.p")
        if not product_url.startswith("http"):
            product_url = "https://www.bestbuy.com" + product_url

        affiliate_url = build_affiliate_url(product_url)

        return {
            "source":       "bestbuy",
            "source_id":    sku,
            "title":        title,
            "price_now":    price_now,
            "price_was":    price_was,
            "discount_pct": discount_pct,
            "rating":       rating,
            "reviews":      reviews,
            "image_url":    image,
            "product_url":  product_url,
            "affiliate_url": affiliate_url,
        }

    except Exception as e:
        log.debug(f"Erro parse BestBuy: {e}")
        return None
