# ============================================================
#  slickdeals_api.py — Slickdeals RSS Feed
#
#  Completamente gratuito, sem API key, sem limite.
#  Agrega deals de TODOS os marketplaces:
#  Amazon, Walmart, Target, Costco, BestBuy, etc.
#
#  O melhor: deals ja foram filtrados por humanos reais.
#  So aparecem no feed quando tem votos suficientes.
# ============================================================

import re
import logging
import hashlib
import requests
import xml.etree.ElementTree as ET
from datetime import datetime

import config

log = logging.getLogger("slickdeals")

# Feeds RSS do Slickdeals
FEEDS = {
    "frontpage":   "https://slickdeals.net/newsearch.php?mode=frontpage&searcharea=deals&searchin=first&rss=1",
    "popular":     "https://slickdeals.net/newsearch.php?mode=popdeals&searcharea=deals&searchin=first&rss=1",
    "electronics": "https://slickdeals.net/newsearch.php?mode=frontpage&searcharea=deals&searchin=first&rss=1&forumid[]=9",
    "hot":         "https://slickdeals.net/newsearch.php?mode=frontpage&searcharea=deals&searchin=first&rss=1&forumid[]=30",
}

# Marketplaces que rastreamos via Slickdeals
TRACKED_STORES = {
    "amazon":   "amazon.com",
    "walmart":  "walmart.com",
    "target":   "target.com",
    "bestbuy":  "bestbuy.com",
    "costco":   "costco.com",
    "homedepot":"homedepot.com",
    "kohls":    "kohls.com",
    "macys":    "macys.com",
    "nike":     "nike.com",
    "adidas":   "adidas.com",
}


def fetch_feed(feed_name: str = "popular") -> tuple:
    """
    Busca feed RSS do Slickdeals.
    Retorna (items, erro).
    """
    url = FEEDS.get(feed_name, FEEDS["popular"])
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; ClubUSA/1.0; RSS Reader)",
        "Accept":     "application/rss+xml, application/xml, text/xml",
    }

    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            return [], f"Slickdeals RSS erro {resp.status_code}"

        root  = ET.fromstring(resp.content)
        items = root.findall(".//item")
        return items, None

    except Exception as e:
        return [], f"Erro Slickdeals: {e}"


def extract_price(text: str) -> float | None:
    """Extrai preco de texto como '$29.99' ou '29.99'."""
    if not text:
        return None
    match = re.search(r'\$[\d,]+\.?\d*', text)
    if match:
        return float(match.group().replace("$","").replace(",",""))
    return None


def extract_discount(text: str) -> int:
    """Extrai desconto de texto como '50% off' ou '-30%'."""
    match = re.search(r'(\d+)%\s*off', text, re.IGNORECASE)
    if match:
        return int(match.group(1))
    match = re.search(r'-(\d+)%', text)
    if match:
        return int(match.group(1))
    return 0


def detect_store(title: str, description: str) -> str:
    """Detecta qual loja pelo conteudo do deal."""
    text = (title + " " + description).lower()
    for store, domain in TRACKED_STORES.items():
        if domain.split(".")[0] in text or store in text:
            return store
    return "other"


def build_affiliate_url(url: str, store: str) -> str:
    """
    Adiciona tag de afiliado na URL baseado na loja detectada.
    Se nao tiver credencial, retorna URL original.
    """
    if not url:
        return url

    if store == "amazon" and config.AMAZON_PARTNER_TAG and "SEU_" not in config.AMAZON_PARTNER_TAG:
        # Adiciona tag Amazon
        sep = "&" if "?" in url else "?"
        if "tag=" not in url:
            return f"{url}{sep}tag={config.AMAZON_PARTNER_TAG}"

    elif store == "walmart" and config.WALMART_PUBLISHER_ID and "SEU_" not in config.WALMART_PUBLISHER_ID:
        sep = "&" if "?" in url else "?"
        return f"{url}{sep}wmlspartner={config.WALMART_PUBLISHER_ID}"

    return url


def parse_slickdeals_item(item: ET.Element) -> dict | None:
    """Parseia item do RSS Slickdeals para formato padrao."""
    try:
        title = item.findtext("title", "").strip()
        desc  = item.findtext("description", "").strip()
        link  = item.findtext("link", "").strip()
        guid  = item.findtext("guid", link).strip()

        if not title:
            return None

        # Remove HTML do description
        clean_desc = re.sub(r'<[^>]+>', ' ', desc)
        full_text  = title + " " + clean_desc

        # Extrai preco atual
        price_now = extract_price(full_text)
        if not price_now:
            return None

        # Extrai preco original (procura "was $X" ou "reg $X" ou "retail $X")
        was_match = re.search(
            r'(?:was|reg(?:ular)?|retail|msrp|list|orig(?:inal)?)\s*:?\s*\$[\d,]+\.?\d*',
            full_text, re.IGNORECASE
        )
        price_was = extract_price(was_match.group() if was_match else "") if was_match else None

        # Calcula desconto
        discount_pct = extract_discount(full_text)
        if not discount_pct and price_was and price_was > price_now:
            discount_pct = round((1 - price_now / price_was) * 100)

        if discount_pct < config.MIN_DISCOUNT_PCT:
            return None
        if price_now > config.MAX_PRICE or price_now < config.MIN_PRICE:
            return None

        # Detecta loja e gera link de afiliado
        store         = detect_store(title, clean_desc)
        affiliate_url = build_affiliate_url(link, store)

        # ID unico baseado no guid
        deal_id = hashlib.md5(guid.encode()).hexdigest()[:10]

        # Extrai votos/popularidade se disponivel
        thumbs_match = re.search(r'(\d+)\s*thumb', full_text, re.IGNORECASE)
        popularity   = int(thumbs_match.group(1)) if thumbs_match else 0

        return {
            "source":       f"slickdeals_{store}",
            "source_id":    deal_id,
            "title":        title[:120],
            "price_now":    price_now,
            "price_was":    price_was,
            "discount_pct": discount_pct,
            "rating":       0.0,
            "reviews":      0,
            "popularity":   popularity,
            "image_url":    None,
            "product_url":  link,
            "affiliate_url": affiliate_url,
            "store":        store,
            "description":  clean_desc[:300],
        }

    except Exception as e:
        log.debug(f"Erro parse Slickdeals: {e}")
        return None


def fetch_all_feeds() -> list:
    """
    Busca todos os feeds e retorna lista de deals parseados.
    Deduplica por source_id.
    """
    all_items = []
    seen_ids  = set()

    for feed_name in ["popular", "frontpage", "hot"]:
        items, err = fetch_feed(feed_name)
        if err:
            log.warning(f"Feed '{feed_name}': {err}")
            continue

        for item in items:
            parsed = parse_slickdeals_item(item)
            if parsed and parsed["source_id"] not in seen_ids:
                seen_ids.add(parsed["source_id"])
                all_items.append(parsed)

        log.info(f"Slickdeals '{feed_name}': {len(items)} itens no feed")

    log.info(f"Slickdeals total: {len(all_items)} deals unicos")
    return all_items
