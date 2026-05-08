# ============================================================
#  alert_checker.py — Verificacao de alertas de preco VIP
# ============================================================

import os
import logging
from datetime import datetime

import config

log = logging.getLogger("alert_checker")


def _supabase():
    from supabase import create_client
    return create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)


def _decrypt_phone(phone_enc: str) -> str:
    from cryptography.fernet import Fernet
    f = Fernet(config.ENCRYPTION_KEY.encode())
    return f.decrypt(phone_enc.encode()).decode()


def should_trigger(alert: dict, current_price: float) -> bool:
    """Retorna True se o alerta deve disparar dado o preco atual."""
    if alert["target_type"] == "price":
        return current_price <= alert["target_value"]

    if alert["target_type"] == "percent":
        if not alert.get("price_current"):
            return False
        drop_pct = (alert["price_current"] - current_price) / alert["price_current"] * 100
        return drop_pct >= alert["target_value"]

    return False


def check_price_alerts():
    """Verifica todos os alertas ativos e dispara notificações se necessário."""
    if not config.SUPABASE_URL or not config.SUPABASE_SERVICE_KEY:
        log.warning("Supabase não configurado — alertas ignorados.")
        return

    sb = _supabase()

    alerts = sb.table("price_alerts").select("*").eq("status", "active").execute().data
    if not alerts:
        log.info("Nenhum alerta ativo para verificar.")
        return

    log.info(f"Verificando {len(alerts)} alertas ativos...")

    # Agrupa por ASIN para evitar chamadas duplicadas à Amazon
    asins = list({a["asin"] for a in alerts})
    prices = {}

    from amazon_api import search_amazon
    for asin in asins:
        try:
            results = search_amazon(asin, max_results=1)
            if results:
                prices[asin] = results[0]["price_now"]
        except Exception as e:
            log.error(f"Erro ao buscar preco ASIN {asin}: {e}")

    triggered_count = 0
    for alert in alerts:
        asin = alert["asin"]
        if asin not in prices:
            continue

        current_price = prices[asin]
        if not should_trigger(alert, current_price):
            continue

        # Busca telefone do membro
        try:
            member = (
                sb.table("members")
                .select("phone_enc, language")
                .eq("id", alert["member_id"])
                .single()
                .execute()
            )
            if not member.data:
                continue

            phone = _decrypt_phone(member.data["phone_enc"])
            lang  = member.data.get("language", "pt")

            from sender import send_price_alert
            send_price_alert(alert, current_price, phone, lang=lang)

            sb.table("price_alerts").update({
                "status":       "triggered",
                "triggered_at": datetime.now().isoformat(),
            }).eq("id", alert["id"]).execute()

            triggered_count += 1
            log.info(f"Alerta disparado: {alert['id']} — {asin} a ${current_price}")

        except Exception as e:
            log.error(f"Erro ao processar alerta {alert['id']}: {e}")

    log.info(f"Alertas disparados: {triggered_count}/{len(alerts)}")
