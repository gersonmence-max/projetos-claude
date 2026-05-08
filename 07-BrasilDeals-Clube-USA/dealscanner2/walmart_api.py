# ============================================================
#  walmart_api.py — Walmart Affiliate API
#
#  Walmart tem duas formas de buscar produtos:
#  1. Open API (sem credencial) — busca basica
#  2. Affiliate API via Impact.com — com link de afiliado
#
#  Usamos a Open API para buscar + geramos link de afiliado
#  com o publisher ID do Impact.com
# ============================================================

import logging
import requests
import config

log = logging.getLogger("walmart_api")

WALMART_SEARCH_URL = "https://developer.api.walmart.com/api-proxy/service/affil/product/v2/search"
WALMART_BASE_URL   = "https://www.walmart.com"


def search_walmart(query: str, num_items: int = 10) -> tuple:
    """
    Busca produtos na Walmart com desconto.
    Retorna (items, erro).
    """
    # Walmart Open API nao precisa de credencial para busca
    # Usamos endpoint publico de busca
    url = "https://www.walmart.com/search/api"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept":     "application/json",
        "Referer":    "https://www.walmart.com",
    }
    
    params = {
        "query":    query,
        "sort":     "best_match",
        "numItems": num_items,
    }

    try:
        resp = requests.get(
            "https://www.walmart.com/search",
            params={"q": query, "sort": "best_seller"},
            headers=headers,
            timeout=15
        )
        
        # Walmart retorna HTML — usamos API alternativa
        # API publica nao-oficial que ainda funciona
        api_url = f"https://www.walmart.com/search/api?query={query}&sort=best_match&numItems={num_items}"
        resp2 = requests.get(api_url, headers=headers, timeout=15)
        
        if resp2.status_code == 200:
            try:
                data = resp2.json()
                items = data.get("items", []) or data.get("searchResult", {}).get("items", [])
                if items:
                    return items, None
            except Exception:
                pass
        
        # Fallback: usar endpoint de departamento
        return [], "Walmart API requer configuracao adicional. Use Slickdeals como fonte."
        
    except Exception as e:
        return [], f"Erro Walmart: {e}"


def build_affiliate_url(product_url: str, item_id: str) -> str:
    """
    Gera URL de afiliado Walmart.
    Com publisher ID: via Impact.com
    Sem publisher ID: link direto (sem comissao)
    """
    if config.WALMART_PUBLISHER_ID and "SEU_" not in config.WALMART_PUBLISHER_ID:
        # Link via Impact.com com rastreamento
        return (
            f"https://goto.walmart.com/c/{config.WALMART_PUBLISHER_ID}/t/{item_id}"
            f"?u={product_url}"
        )
    # Link direto sem comissao (funciona mas nao rastreia)
    return f"https://www.walmart.com/ip/{item_id}"


def parse_walmart_item(item: dict) -> dict | None:
    """Parseia item da Walmart para formato padrao."""
    try:
        item_id   = str(item.get("itemId") or item.get("id", ""))
        title     = item.get("name") or item.get("title")
        if not title or not item_id:
            return None

        # Preco
        price_info = item.get("priceInfo") or item.get("price") or {}
        price_now  = None
        price_was  = None

        if isinstance(price_info, dict):
            price_now = price_info.get("currentPrice") or price_info.get("price")
            price_was = price_info.get("wasPrice") or price_info.get("listPrice")
        elif isinstance(price_info, (int, float)):
            price_now = float(price_info)

        if not price_now:
            price_now = item.get("salePrice") or item.get("price")
        if not price_was:
            price_was = item.get("msrp") or item.get("wasPrice")

        if not price_now:
            return None

        price_now = float(str(price_now).replace("$","").replace(",",""))
        price_was = float(str(price_was).replace("$","").replace(",","")) if price_was else None

        if not price_was or price_was <= price_now:
            return None

        discount_pct = round((1 - price_now / price_was) * 100)
        if discount_pct < config.MIN_DISCOUNT_PCT:
            return None
        if price_now > config.MAX_PRICE or price_now < config.MIN_PRICE:
            return None

        # Rating
        rating  = float(item.get("averageRating") or item.get("rating") or 0)
        reviews = int(item.get("numReviews") or item.get("reviewCount") or 0)

        if rating  > 0 and rating  < config.MIN_RATING:  return None
        if reviews > 0 and reviews < config.MIN_REVIEWS:  return None

        # Imagem
        image = item.get("imageUrl") or item.get("thumbnail")
        if image and not image.startswith("http"):
            image = "https:" + image

        product_url   = f"https://www.walmart.com/ip/{item_id}"
        affiliate_url = build_affiliate_url(product_url, item_id)

        return {
            "source":       "walmart",
            "source_id":    item_id,
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
        log.debug(f"Erro parse Walmart: {e}")
        return None
