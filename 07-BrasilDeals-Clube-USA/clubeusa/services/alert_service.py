import os
import re
import logging

log = logging.getLogger("alert_service")

MAX_ACTIVE_ALERTS = 10


def _supabase():
    from supabase import create_client
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])


def extract_asin_from_url(url: str) -> str:
    patterns = [
        r'/dp/([A-Z0-9]{10})',
        r'/gp/product/([A-Z0-9]{10})',
        r'[?&]asin=([A-Z0-9]{10})',
    ]
    for pattern in patterns:
        m = re.search(pattern, url)
        if m:
            return m.group(1)
    raise ValueError("ASIN não encontrado na URL. Use uma URL direta da Amazon (ex: amazon.com/dp/ASIN).")


def create_alert(
    member_id: str,
    asin: str,
    target_type: str,
    target_value: float,
    product_title: str = None,
    price_current: float = None,
) -> dict:
    sb = _supabase()
    existing = (
        sb.table("price_alerts")
        .select("id")
        .eq("member_id", member_id)
        .eq("status", "active")
        .execute()
    )
    if len(existing.data) >= MAX_ACTIVE_ALERTS:
        raise ValueError(f"Limite de {MAX_ACTIVE_ALERTS} alertas ativos atingido.")

    result = (
        sb.table("price_alerts")
        .insert({
            "member_id":     member_id,
            "asin":          asin,
            "product_title": product_title,
            "price_current": price_current,
            "target_type":   target_type,
            "target_value":  target_value,
        })
        .execute()
    )
    return result.data[0]


def list_alerts(member_id: str) -> list:
    sb = _supabase()
    result = (
        sb.table("price_alerts")
        .select("*")
        .eq("member_id", member_id)
        .neq("status", "cancelled")
        .order("created_at", desc=True)
        .execute()
    )
    return result.data


def cancel_alert(alert_id: str, member_id: str) -> bool:
    sb = _supabase()
    result = (
        sb.table("price_alerts")
        .update({"status": "cancelled"})
        .eq("id", alert_id)
        .eq("member_id", member_id)
        .execute()
    )
    return len(result.data) > 0
