# ============================================================
#  scanner.py — Clube USA Multi-Marketplace Scanner
#
#  Fontes:
#    1. Amazon PA-API (oficial)
#    2. Walmart (open API)
#    3. eBay Browse API (oficial)
#    4. BestBuy Products API (oficial)
#    5. Target (via Slickdeals RSS)
#    6. Slickdeals RSS (agrega todos os marketplaces)
#
#  Score engine unificado 0-100
#  Auto-aprovacao inteligente
#  Cache anti-abuse
#  Historico de preco interno
# ============================================================

import json
import time
import logging
import hashlib
from datetime import datetime, timedelta
from pathlib import Path

import config
from amazon_api      import search_items      as amazon_search
from walmart_api     import search_walmart, parse_walmart_item
from ebay_api        import search_ebay, parse_ebay_item
from bestbuy_api     import search_bestbuy, parse_bestbuy_item
from slickdeals_api  import fetch_all_feeds
from target_api      import enhance_target_deal
from price_history   import record_price, get_price_context

Path("data").mkdir(exist_ok=True)
Path("logs").mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(config.LOG_FILE),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("scanner")

# ============================================================
#  BADGES DE FONTE — exibidos no painel
# ============================================================
SOURCE_BADGES = {
    "amazon":            {"label": "Amazon",   "color": "#FF9900"},
    "walmart":           {"label": "Walmart",  "color": "#0071DC"},
    "ebay":              {"label": "eBay",     "color": "#86B817"},
    "bestbuy":           {"label": "BestBuy",  "color": "#003087"},
    "target":            {"label": "Target",   "color": "#CC0000"},
    "slickdeals_amazon": {"label": "Amazon",   "color": "#FF9900"},
    "slickdeals_walmart":{"label": "Walmart",  "color": "#0071DC"},
    "slickdeals_target": {"label": "Target",   "color": "#CC0000"},
    "slickdeals_bestbuy":{"label": "BestBuy",  "color": "#003087"},
    "slickdeals_costco": {"label": "Costco",   "color": "#005DAA"},
    "slickdeals_other":  {"label": "Deal",     "color": "#666666"},
}

# ============================================================
#  COMISSOES POR FONTE (para calcular receita estimada)
# ============================================================
COMMISSION_RATES = {
    "amazon":   0.04,
    "walmart":  0.03,
    "ebay":     0.03,
    "bestbuy":  0.01,
    "target":   0.05,
    "default":  0.03,
}

def get_commission(source: str, price: float) -> float:
    """Calcula comissao estimada."""
    base = source.split("_")[0] if "_" in source else source
    rate = COMMISSION_RATES.get(base, COMMISSION_RATES["default"])
    return round(price * rate, 2)

# ============================================================
#  CATEGORIAS AMAZON
# ============================================================
AMAZON_CATEGORIES = [
    ("electronics deals",        "Electronics"),
    ("bluetooth headphones",     "Electronics"),
    ("smart home devices",       "Alexa"),
    ("laptop accessories",       "Computers"),
    ("phone accessories",        "Electronics"),
    ("gaming accessories",       "VideoGames"),
    ("kitchen appliances sale",  "Kitchen"),
    ("air fryer",                "Kitchen"),
    ("coffee maker",             "Kitchen"),
    ("robot vacuum",             "Appliances"),
    ("vitamins supplements",     "HealthPersonalCare"),
    ("protein powder",           "HealthPersonalCare"),
    ("fitness equipment",        "SportingGoods"),
    ("skincare deals",           "Beauty"),
    ("baby products deals",      "Baby"),
    ("diapers",                  "Baby"),
    ("kids toys",                "Toys"),
    ("running shoes",            "Shoes"),
    ("power tools deals",        "Tools"),
    ("dog food deals",           "PetSupplies"),
    ("car accessories",          "Automotive"),
    ("amazon basics deals",      "All"),
]

# Queries compartilhadas entre Walmart, eBay, BestBuy
SHARED_QUERIES = [
    "electronics sale",
    "headphones deal",
    "air fryer sale",
    "robot vacuum deal",
    "gaming deal",
    "kitchen appliance sale",
    "fitness equipment deal",
    "baby products sale",
    "power tools deal",
    "smart tv sale",
]

# ============================================================
#  SCORE ENGINE UNIFICADO
# ============================================================
def compute_score(discount_pct, rating, reviews, price, source="amazon", popularity=0):
    """
    Score 0-100 ponderado.
    Slickdeals recebe bonus por ter sido validado por humanos.
    """
    # Desconto (0-35)
    if   discount_pct >= 70: s_d = 35
    elif discount_pct >= 50: s_d = 28 + (discount_pct - 50) * 0.35
    elif discount_pct >= 30: s_d = 18 + (discount_pct - 30) * 0.5
    elif discount_pct >= 20: s_d = 10 + (discount_pct - 20) * 0.8
    else:                    s_d = 0

    # Rating (0-25)
    if rating > 0:
        if   rating >= 4.8: s_r = 25
        elif rating >= 4.5: s_r = 20 + (rating - 4.5) * 16.7
        elif rating >= 3.8: s_r = 10 + (rating - 3.8) * 14.3
        else:               s_r = max(0, rating * 3)
    else:
        s_r = 12  # sem rating = neutro

    # Reviews (0-20)
    if   reviews >= 100_000: s_v = 20
    elif reviews >= 10_000:  s_v = 15 + (reviews - 10_000)  / 90_000 * 5
    elif reviews >= 1_000:   s_v = 10 + (reviews - 1_000)   / 9_000  * 5
    elif reviews >= 100:     s_v = 5  + (reviews - 100)     / 900    * 5
    elif reviews > 0:        s_v = 2
    else:                    s_v = 8  # sem reviews = neutro

    # Preco acessivel (0-10)
    if   price <= 15:  s_p = 10
    elif price <= 30:  s_p = 9
    elif price <= 60:  s_p = 7
    elif price <= 100: s_p = 5
    elif price <= 200: s_p = 3
    else:              s_p = 1

    # Bonus Slickdeals — validado por humanos (0-10)
    s_human = 0
    if "slickdeals" in source:
        s_human = min(10, popularity / 10) if popularity > 0 else 5

    total = s_d + s_r + s_v + s_p + s_human
    return round(min(total, 100), 1)


def score_label(s):
    if s >= 85: return "Excelente"
    if s >= 70: return "Otimo"
    if s >= 55: return "Bom"
    if s >= 40: return "Ok"
    return "Fraco"

# ============================================================
#  DB LOCAL
# ============================================================
def load_db():
    p = Path(config.DB_FILE)
    return json.loads(p.read_text()) if p.exists() else []

def save_db(deals):
    Path(config.DB_FILE).write_text(
        json.dumps(deals, indent=2, ensure_ascii=False)
    )

def _sync_deal_to_supabase(deal: dict, sb=None):
    """Sincroniza deal com Supabase. Falhas são silenciosas (não interrompem o scanner)."""
    if not config.SUPABASE_URL or not config.SUPABASE_SERVICE_KEY:
        return
    try:
        if sb is None:
            from supabase import create_client
            sb = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
        sb.table("deals").upsert({
            "id":            deal["id"],
            "asin":          deal.get("asin", ""),
            "title":         deal["title"],
            "price_now":     deal["price_now"],
            "price_was":     deal.get("price_was"),
            "discount_pct":  int(deal.get("discount_pct", 0)),
            "rating":        deal.get("rating"),
            "reviews":       deal.get("reviews"),
            "score":         float(deal.get("score", 0)),
            "price_context": deal.get("price_context"),
            "affiliate_url": deal["affiliate_url"],
            "category":      deal.get("category"),
            "source":        deal.get("source", "amazon"),
            "status":        deal.get("status", "pending"),
            "auto_approved": bool(deal.get("auto_approved", False)),
        }, on_conflict="id").execute()
    except Exception as e:
        log.warning(f"Supabase sync falhou para {deal.get('source','?')}:{deal.get('id','?')}: {e}")

def load_sent():
    p = Path(config.SENT_FILE)
    return set(json.loads(p.read_text())) if p.exists() else set()

def save_sent(ids):
    Path(config.SENT_FILE).write_text(json.dumps(list(ids)))

# ============================================================
#  CACHE
# ============================================================
def can_scan(force=False):
    if force:
        return True, None
    p = Path(config.CACHE_FILE)
    if not p.exists():
        return True, None
    cache = json.loads(p.read_text())
    last  = datetime.fromisoformat(cache.get("last_scan","2000-01-01"))
    delta = datetime.now() - last
    wait  = timedelta(minutes=config.SCAN_CACHE_MINUTES)
    if delta < wait:
        remaining = int((wait - delta).total_seconds() / 60)
        return False, f"Aguarde {remaining} min para proxima varredura."
    return True, None

def mark_scan_done():
    Path(config.CACHE_FILE).write_text(
        json.dumps({"last_scan": datetime.now().isoformat()})
    )

# ============================================================
#  AUTO-APROVACAO
# ============================================================
def should_auto_approve(deal):
    if not config.AUTO_APPROVE_ENABLED:
        return False
    return (
        deal["score"]        >= config.AUTO_APPROVE_MIN_SCORE and
        deal.get("reviews",0) >= config.AUTO_APPROVE_MIN_REVIEWS and
        deal["discount_pct"] >= config.AUTO_APPROVE_MIN_DISCOUNT
    )

# ============================================================
#  NORMALIZADOR UNIVERSAL
#  Converte qualquer formato para o schema padrao
# ============================================================
def normalize_deal(raw: dict, query: str = "") -> dict | None:
    """
    Recebe um item parseado de qualquer marketplace
    e normaliza para o schema unico do sistema.
    """
    try:
        source      = raw.get("source", "unknown")
        source_id   = raw.get("source_id", "")
        title       = raw.get("title", "")
        price_now   = raw.get("price_now")
        price_was   = raw.get("price_was")
        discount_pct= raw.get("discount_pct", 0)
        rating      = raw.get("rating", 0.0)
        reviews     = raw.get("reviews", 0)
        image_url   = raw.get("image_url")
        affiliate_url = raw.get("affiliate_url", raw.get("product_url",""))
        popularity  = raw.get("popularity", 0)

        if not title or not price_now or not affiliate_url:
            return None

        # Filtros basicos
        if discount_pct < config.MIN_DISCOUNT_PCT: return None
        if price_now    > config.MAX_PRICE:         return None
        if price_now    < config.MIN_PRICE:         return None
        if rating  > 0 and rating  < config.MIN_RATING  and reviews > 200: return None

        # Score
        score = compute_score(discount_pct, rating, reviews, price_now, source, popularity)
        if score < config.MIN_SCORE:
            return None

        # ID unico por fonte+produto
        raw_id = f"{source}:{source_id}"
        deal_id = hashlib.md5(raw_id.encode()).hexdigest()[:12]

        # Historico de preco
        record_price(deal_id, price_now, price_was)
        price_context = get_price_context(deal_id, price_now)

        # Badge da fonte
        badge = SOURCE_BADGES.get(source, {"label": source.title(), "color": "#888"})

        # Comissao estimada
        commission_est = get_commission(source, price_now)

        # Target via Slickdeals — melhora URL
        if source == "slickdeals_target":
            raw = enhance_target_deal(raw)
            affiliate_url = raw.get("affiliate_url", affiliate_url)

        deal = {
            "id":              deal_id,
            "source":          source,
            "source_id":       source_id,
            "source_label":    badge["label"],
            "source_color":    badge["color"],
            "title":           title,
            "price_now":       price_now,
            "price_was":       price_was,
            "discount_pct":    discount_pct,
            "rating":          rating,
            "reviews":         reviews,
            "score":           score,
            "score_label":     score_label(score),
            "price_context":   price_context,
            "image_url":       image_url,
            "affiliate_url":   affiliate_url,
            "commission_est":  commission_est,
            "query":           query,
            "found_at":        datetime.now().isoformat(),
            "status":          "pending",
            "auto_approved":   False,
        }

        if should_auto_approve(deal):
            deal["status"]       = "approved"
            deal["auto_approved"] = True

        return deal

    except Exception as e:
        log.debug(f"Erro normalize: {e}")
        return None

# ============================================================
#  VARREDURA AMAZON
# ============================================================
def scan_amazon(existing_ids):
    log.info("--- Varrendo Amazon ---")
    new_deals = []

    if "SUA_ACCESS_KEY" in config.AMAZON_ACCESS_KEY:
        log.warning("Amazon: credenciais nao configuradas. Pulando.")
        return new_deals

    errors = 0
    for keywords, index in AMAZON_CATEGORIES:
        items, err = amazon_search(
            config.AMAZON_ACCESS_KEY,
            config.AMAZON_SECRET_KEY,
            config.AMAZON_PARTNER_TAG,
            keywords, search_index=index, item_count=10,
        )
        if err:
            log.warning(f"Amazon '{keywords}': {err}")
            errors += 1
            if errors >= 3:
                log.error("Amazon: muitos erros. Verifique credenciais.")
                break
            time.sleep(2)
            continue

        errors = 0
        for item in (items or []):
            raw = _parse_amazon_item(item, keywords)
            if not raw:
                continue
            deal = normalize_deal(raw, keywords)
            if deal and deal["id"] not in existing_ids:
                new_deals.append(deal)
                existing_ids.add(deal["id"])
                _log_deal(deal)

        time.sleep(1.1)

    log.info(f"Amazon: {len(new_deals)} novos deals")
    return new_deals


def _parse_amazon_item(item, query):
    """Converte item PA-API para formato raw."""
    try:
        asin  = item.get("ASIN")
        title = item.get("ItemInfo",{}).get("Title",{}).get("DisplayValue")
        if not asin or not title:
            return None

        listings = item.get("Offers",{}).get("Listings",[])
        if not listings:
            return None

        l         = listings[0]
        price_now = l.get("Price",{}).get("Amount")
        price_was = l.get("SavingBasis",{}).get("Amount")
        if not price_now:
            return None

        price_now = float(price_now)
        price_was = float(price_was) if price_was else None
        if not price_was or price_was <= price_now:
            return None

        rev  = item.get("CustomerReviews",{})
        rating  = float(rev.get("StarRating",{}).get("Value",0) or 0)
        reviews = int(rev.get("Count",{}).get("Value",0) or 0)
        image   = item.get("Images",{}).get("Primary",{}).get("Medium",{}).get("URL")

        return {
            "source":       "amazon",
            "source_id":    asin,
            "title":        title,
            "price_now":    price_now,
            "price_was":    price_was,
            "discount_pct": round((1 - price_now / price_was) * 100),
            "rating":       rating,
            "reviews":      reviews,
            "image_url":    image,
            "affiliate_url": f"https://www.amazon.com/dp/{asin}?tag={config.AMAZON_PARTNER_TAG}",
        }
    except Exception:
        return None

# ============================================================
#  VARREDURA WALMART
# ============================================================
def scan_walmart(existing_ids):
    log.info("--- Varrendo Walmart ---")
    new_deals = []

    if "SEU_" in config.WALMART_PUBLISHER_ID:
        log.info("Walmart: publisher ID nao configurado. Pulando API direta.")
        return new_deals

    for query in SHARED_QUERIES[:5]:  # limita para nao sobrecarregar
        items, err = search_walmart(query, num_items=8)
        if err:
            log.warning(f"Walmart '{query}': {err}")
            continue

        for item in (items or []):
            raw  = parse_walmart_item(item)
            if not raw:
                continue
            deal = normalize_deal(raw, query)
            if deal and deal["id"] not in existing_ids:
                new_deals.append(deal)
                existing_ids.add(deal["id"])
                _log_deal(deal)

        time.sleep(0.8)

    log.info(f"Walmart: {len(new_deals)} novos deals")
    return new_deals

# ============================================================
#  VARREDURA EBAY
# ============================================================
def scan_ebay(existing_ids):
    log.info("--- Varrendo eBay ---")
    new_deals = []

    if "SEU_" in config.EBAY_APP_ID:
        log.info("eBay: App ID nao configurado. Pulando.")
        return new_deals

    for query in SHARED_QUERIES[:5]:
        items, err = search_ebay(query, num_items=8)
        if err:
            log.warning(f"eBay '{query}': {err}")
            continue

        for item in (items or []):
            raw  = parse_ebay_item(item)
            if not raw:
                continue
            deal = normalize_deal(raw, query)
            if deal and deal["id"] not in existing_ids:
                new_deals.append(deal)
                existing_ids.add(deal["id"])
                _log_deal(deal)

        time.sleep(0.8)

    log.info(f"eBay: {len(new_deals)} novos deals")
    return new_deals

# ============================================================
#  VARREDURA BESTBUY
# ============================================================
def scan_bestbuy(existing_ids):
    log.info("--- Varrendo BestBuy ---")
    new_deals = []

    if "SUA_" in config.BESTBUY_API_KEY:
        log.info("BestBuy: API Key nao configurada. Pulando.")
        return new_deals

    for query in ["electronics", "headphones", "laptop", "tv", "camera"][:4]:
        items, err = search_bestbuy(query, num_items=8)
        if err:
            log.warning(f"BestBuy '{query}': {err}")
            continue

        for item in (items or []):
            raw  = parse_bestbuy_item(item)
            if not raw:
                continue
            deal = normalize_deal(raw, query)
            if deal and deal["id"] not in existing_ids:
                new_deals.append(deal)
                existing_ids.add(deal["id"])
                _log_deal(deal)

        time.sleep(0.8)

    log.info(f"BestBuy: {len(new_deals)} novos deals")
    return new_deals

# ============================================================
#  VARREDURA SLICKDEALS (Amazon + Walmart + Target + Costco + mais)
# ============================================================
def scan_slickdeals(existing_ids):
    log.info("--- Varrendo Slickdeals RSS ---")
    new_deals = []

    if not config.SLICKDEALS_ENABLED:
        return new_deals

    raw_items = fetch_all_feeds()

    for raw in raw_items:
        deal = normalize_deal(raw, raw.get("store",""))
        if deal and deal["id"] not in existing_ids:
            new_deals.append(deal)
            existing_ids.add(deal["id"])
            _log_deal(deal)

    log.info(f"Slickdeals: {len(new_deals)} novos deals")
    return new_deals

# ============================================================
#  VARREDURA PRINCIPAL
# ============================================================
def run_scan(force=False):
    log.info("=== Iniciando varredura multi-marketplace ===")

    ok, msg = can_scan(force)
    if not ok:
        log.warning(f"Cache: {msg}")
        return [], msg

    existing_db  = load_db()
    existing_ids = {d["id"] for d in existing_db}
    all_new      = []

    # Roda cada marketplace
    # Slickdeals sempre roda (gratuito) — cobre Target, Costco, e mais
    all_new += scan_slickdeals(existing_ids)

    # APIs oficiais rodam se configuradas
    all_new += scan_amazon(existing_ids)
    all_new += scan_walmart(existing_ids)
    all_new += scan_ebay(existing_ids)
    all_new += scan_bestbuy(existing_ids)

    # Merge e ordena
    all_deals = existing_db + all_new
    all_deals.sort(key=lambda d: (
        {"pending":0,"approved":1,"sent":3,"rejected":4}.get(d["status"],2),
        -d.get("score",0)
    ))
    all_deals = all_deals[:config.TOP_N_DEALS * 2]

    save_db(all_deals)
    if all_new and config.SUPABASE_URL and config.SUPABASE_SERVICE_KEY:
        try:
            from supabase import create_client
            _sb = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
            for deal in all_new:
                _sync_deal_to_supabase(deal, _sb)
        except Exception as e:
            log.warning(f"Supabase client init falhou: {e}")
    mark_scan_done()

    auto = sum(1 for d in all_new if d.get("auto_approved"))

    # Resumo por fonte
    by_source = {}
    for d in all_new:
        src = d.get("source_label", d.get("source","?"))
        by_source[src] = by_source.get(src, 0) + 1

    log.info(f"=== Varredura concluida: {len(all_new)} novos deals ({auto} auto-aprovados) ===")
    for src, count in sorted(by_source.items(), key=lambda x:-x[1]):
        log.info(f"  {src}: {count} deals")

    return all_new, None


def _log_deal(deal):
    auto = "[AUTO]" if deal.get("auto_approved") else "[PEND]"
    ctx  = f" [{deal['price_context']}]" if deal.get("price_context") else ""
    src  = deal.get("source_label", deal.get("source","?"))
    log.info(
        f"  {auto} [{src}] score={deal['score']} "
        f"-{deal['discount_pct']}% "
        f"${deal['price_now']:.2f}"
        f"{ctx} — {deal['title'][:45]}"
    )

# ============================================================
#  MOCK MULTI-MARKETPLACE
# ============================================================
def run_scan_mock():
    log.info("=== Modo MOCK multi-marketplace ===")
    from datetime import datetime as dt

    mock = [
        {
            "id":"am1","source":"amazon","source_id":"B08N5WRWNW",
            "source_label":"Amazon","source_color":"#FF9900",
            "title":"Echo Dot (4th Gen) Smart Speaker with Alexa",
            "price_now":22.99,"price_was":49.99,"discount_pct":54,
            "rating":4.7,"reviews":847203,"score":88,"score_label":"Excelente",
            "price_context":"menor preco em 60 dias","image_url":None,
            "affiliate_url":f"https://www.amazon.com/dp/B08N5WRWNW?tag={config.AMAZON_PARTNER_TAG}",
            "commission_est":0.92,"query":"smart home","found_at":dt.now().isoformat(),
            "status":"approved","auto_approved":True,
        },
        {
            "id":"wm1","source":"walmart","source_id":"114215867",
            "source_label":"Walmart","source_color":"#0071DC",
            "title":"Ninja AF101 Air Fryer 4 Quart, Black",
            "price_now":59.00,"price_was":99.00,"discount_pct":40,
            "rating":4.6,"reviews":28400,"score":76,"score_label":"Otimo",
            "price_context":None,"image_url":None,
            "affiliate_url":"https://www.walmart.com/ip/114215867",
            "commission_est":1.77,"query":"air fryer","found_at":dt.now().isoformat(),
            "status":"pending","auto_approved":False,
        },
        {
            "id":"bb1","source":"bestbuy","source_id":"6501700",
            "source_label":"BestBuy","source_color":"#003087",
            "title":"Apple AirPods Pro (2nd Generation) with MagSafe Case",
            "price_now":179.99,"price_was":249.99,"discount_pct":28,
            "rating":4.8,"reviews":12400,"score":73,"score_label":"Otimo",
            "price_context":"menor preco em 30 dias","image_url":None,
            "affiliate_url":"https://www.bestbuy.com/site/6501700.p",
            "commission_est":1.80,"query":"headphones","found_at":dt.now().isoformat(),
            "status":"pending","auto_approved":False,
        },
        {
            "id":"sd1","source":"slickdeals_target","source_id":"sd_tgt_1",
            "source_label":"Target","source_color":"#CC0000",
            "title":"KitchenAid Artisan 5-Qt Stand Mixer — Multiple Colors",
            "price_now":249.99,"price_was":449.99,"discount_pct":44,
            "rating":4.8,"reviews":0,"score":72,"score_label":"Otimo",
            "price_context":"menor preco ja registrado","image_url":None,
            "affiliate_url":"https://www.target.com/p/kitchenaid-artisan/-/A-14766013",
            "commission_est":12.50,"query":"kitchen","found_at":dt.now().isoformat(),
            "status":"pending","auto_approved":False,
        },
        {
            "id":"eb1","source":"ebay","source_id":"ebay_123",
            "source_label":"eBay","source_color":"#86B817",
            "title":"DEWALT 20V MAX Cordless Drill Driver Kit, Compact",
            "price_now":79.00,"price_was":139.00,"discount_pct":43,
            "rating":4.8,"reviews":42300,"score":80,"score_label":"Excelente",
            "price_context":None,"image_url":None,
            "affiliate_url":"https://www.ebay.com/itm/123456",
            "commission_est":2.37,"query":"power tools","found_at":dt.now().isoformat(),
            "status":"approved","auto_approved":True,
        },
        {
            "id":"sd2","source":"slickdeals_costco","source_id":"sd_cos_1",
            "source_label":"Costco","source_color":"#005DAA",
            "title":"Dyson V15 Detect Cordless Vacuum Cleaner",
            "price_now":499.99,"price_was":749.99,"discount_pct":33,
            "rating":4.7,"reviews":0,"score":65,"score_label":"Otimo",
            "price_context":None,"image_url":None,
            "affiliate_url":"https://www.costco.com/dyson-v15.html",
            "commission_est":0,"query":"vacuum","found_at":dt.now().isoformat(),
            "status":"pending","auto_approved":False,
        },
        {
            "id":"am2","source":"amazon","source_id":"B07FZ8S74R",
            "source_label":"Amazon","source_color":"#FF9900",
            "title":"Pampers Swaddlers Diapers Size 3, 204 Count",
            "price_now":34.94,"price_was":54.99,"discount_pct":36,
            "rating":4.8,"reviews":187500,"score":82,"score_label":"Excelente",
            "price_context":"menor preco em 90 dias","image_url":None,
            "affiliate_url":f"https://www.amazon.com/dp/B07FZ8S74R?tag={config.AMAZON_PARTNER_TAG}",
            "commission_est":1.57,"query":"diapers","found_at":dt.now().isoformat(),
            "status":"approved","auto_approved":True,
        },
        {
            "id":"wm2","source":"walmart","source_id":"55678912",
            "source_label":"Walmart","source_color":"#0071DC",
            "title":"iRobot Roomba i4 EVO Robot Vacuum Wi-Fi Connected",
            "price_now":129.99,"price_was":274.99,"discount_pct":53,
            "rating":4.3,"reviews":28200,"score":79,"score_label":"Otimo",
            "price_context":"menor preco ja registrado","image_url":None,
            "affiliate_url":"https://www.walmart.com/ip/55678912",
            "commission_est":3.90,"query":"robot vacuum","found_at":dt.now().isoformat(),
            "status":"pending","auto_approved":False,
        },
    ]

    save_db(mock)
    log.info(f"Mock: {len(mock)} deals de {len(set(d['source_label'] for d in mock))} marketplaces")
    return mock


if __name__ == "__main__":
    import sys
    if "--mock" in sys.argv:
        run_scan_mock()
    else:
        deals, err = run_scan(force="--force" in sys.argv)
        if err:
            print(f"Erro: {err}")
