# ============================================================
#  target_api.py — Target Affiliate (via Impact.com)
#
#  Target nao tem API publica de produtos.
#  Estrategia: captura deals via Slickdeals RSS (que ja cobre Target)
#  + gera link de afiliado via Impact.com quando detectar URL Target
# ============================================================

import re
import logging
import requests
import config

log = logging.getLogger("target_api")


def build_affiliate_url(product_url: str) -> str:
    """
    Gera URL de afiliado Target via Impact.com.
    Requer publisher ID do Impact.com.
    """
    if not config.TARGET_PUBLISHER_ID or "SEU_" in config.TARGET_PUBLISHER_ID:
        return product_url

    import urllib.parse
    encoded = urllib.parse.quote(product_url, safe='')
    return (
        f"https://goto.target.com/c/{config.TARGET_PUBLISHER_ID}/t/0"
        f"?u={encoded}"
    )


def is_target_url(url: str) -> bool:
    """Verifica se URL é do Target."""
    return "target.com" in url.lower()


def enhance_target_deal(deal: dict) -> dict:
    """
    Melhora um deal do Target capturado via Slickdeals
    adicionando o link de afiliado correto.
    """
    if is_target_url(deal.get("product_url", "")):
        deal["affiliate_url"] = build_affiliate_url(deal["product_url"])
        deal["source"] = "target"
    return deal


# Categorias que Target é especialmente forte
TARGET_CATEGORIES = [
    "home decor",
    "kitchen",
    "clothing",
    "baby",
    "toys",
    "beauty",
    "food",
    "bedding",
    "furniture",
]

# Comissoes Target por categoria (via Impact.com)
TARGET_COMMISSIONS = {
    "apparel":         8.0,
    "shoes":           8.0,
    "accessories":     8.0,
    "beauty":          5.0,
    "baby":            5.0,
    "home":            5.0,
    "kitchen":         5.0,
    "toys":            5.0,
    "electronics":     1.0,
    "video_games":     1.0,
    "default":         5.0,
}


def get_commission_rate(category: str) -> float:
    """Retorna taxa de comissao estimada para categoria."""
    cat_lower = (category or "").lower()
    for key, rate in TARGET_COMMISSIONS.items():
        if key in cat_lower:
            return rate
    return TARGET_COMMISSIONS["default"]
