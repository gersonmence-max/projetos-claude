# ============================================================
#  sender.py — Formatacao e envio com suporte a fuso + plano
# ============================================================

import json
import time
import random
import logging
import requests
from datetime import datetime
from pathlib import Path

import config

log = logging.getLogger("sender")


def format_message(deal: dict, lang: str = "pt") -> str:
    """Formata mensagem com contexto de preco e badge de loja."""
    stars  = int(deal.get("rating", 0))
    star_s = "★" * stars + f" {deal['rating']}" if stars else ""
    rev    = f"{deal['reviews']:,}" if deal.get("reviews") else ""
    ctx    = deal.get("price_context")
    src    = deal.get("source_label", "")
    comm   = deal.get("commission_est", 0)

    if lang == "es":
        lines = [f"*{deal['title'][:80]}*", ""]
        if ctx:
            lines += [f"*{ctx.upper()}*", ""]
        lines += [
            f"Antes: ~${deal['price_was']:.2f}~   Ahora: *${deal['price_now']:.2f}*",
            f"Descuento: *{deal['discount_pct']}% OFF*",
        ]
        if star_s:
            lines.append(f"Calificacion: {star_s}  ({rev} resenas)")
        lines += ["", deal["affiliate_url"], "",
                  f"_Club USA — Score {deal.get('score','')} ({deal.get('score_label','')}) · {src}_"]
    else:
        lines = [f"*{deal['title'][:80]}*", ""]
        if ctx:
            lines += [f"*{ctx.upper()}*", ""]
        lines += [
            f"De: ~${deal['price_was']:.2f}~   Por: *${deal['price_now']:.2f}*",
            f"Desconto: *{deal['discount_pct']}% OFF*",
        ]
        if star_s:
            lines.append(f"Avaliacao: {star_s}  ({rev} reviews)")
        lines += ["", deal["affiliate_url"], "",
                  f"_Clube USA — Score {deal.get('score','')} ({deal.get('score_label','')}) · {src}_"]

    return "\n".join(lines)


def _send_whatsapp(message: str, phone: str = None) -> bool:
    """Envia mensagem via Z-API."""
    target = phone or config.WHATSAPP_GROUP_ID

    if not config.WHATSAPP_API_URL or not target:
        log.info(f"[DRY-RUN] Para: {target or 'grupo'}\n{message}\n{'—'*40}")
        return True

    try:
        r = requests.post(
            config.WHATSAPP_API_URL,
            json={"phone": target, "message": message},
            headers={"Client-Token": os.environ.get("ZAPI_CLIENT_TOKEN","")},
            timeout=10,
        )
        return r.status_code == 200
    except Exception as e:
        log.error(f"Erro WhatsApp: {e}")
        return False


def load_db():
    p = Path(config.DB_FILE)
    return json.loads(p.read_text()) if p.exists() else []

def save_db(deals):
    Path(config.DB_FILE).write_text(json.dumps(deals, indent=2, ensure_ascii=False))

def load_sent():
    p = Path(config.SENT_FILE)
    return set(json.loads(p.read_text())) if p.exists() else set()

def save_sent(ids):
    Path(config.SENT_FILE).write_text(json.dumps(list(ids)))


def send_deal_by_id(deal_id: str, phone: str = None) -> tuple:
    """Envia deal especifico pelo ID."""
    db   = load_db()
    sent = load_sent()
    for deal in db:
        if deal["id"] == deal_id:
            if deal["id"] in sent:
                return False, "Ja enviado."
            ok = _send_whatsapp(format_message(deal), phone=phone)
            if ok:
                deal["status"]  = "sent"
                deal["sent_at"] = datetime.now().isoformat()
                sent.add(deal["id"])
                save_db(db)
                save_sent(sent)
                return True, "Enviado."
            return False, "Erro no envio."
    return False, "Deal nao encontrado."


def auto_send_approved() -> int:
    """Envia todos os deals aprovados com delay anti-spam."""
    db   = load_db()
    sent = load_sent()
    n    = 0
    pending = [d for d in db if d["status"] == "approved" and d["id"] not in sent]

    for i, deal in enumerate(pending):
        ok = _send_whatsapp(format_message(deal))
        if ok:
            deal["status"]  = "sent"
            deal["sent_at"] = datetime.now().isoformat()
            sent.add(deal["id"])
            n += 1
        if i < len(pending) - 1:
            delay = random.randint(config.SEND_DELAY_MIN, config.SEND_DELAY_MAX)
            log.info(f"Aguardando {delay}s...")
            time.sleep(delay)

    save_db(db)
    save_sent(sent)
    log.info(f"Auto-send: {n} enviados.")
    return n


def send_price_alert(alert: dict, current_price: float, phone: str, lang: str = "pt") -> bool:
    """Envia notificacao de alerta de preco via WhatsApp."""
    title        = alert.get("product_title") or alert["asin"]
    price_before = alert.get("price_current")
    asin         = alert["asin"]
    affiliate    = f"https://www.amazon.com/dp/{asin}?tag={config.AMAZON_PARTNER_TAG}"

    if price_before:
        drop_pct = round((price_before - current_price) / price_before * 100)
        price_line = (
            f"Era: ~${price_before:.2f}~   Agora: *${current_price:.2f}*\n"
            f"Queda de *{drop_pct}% OFF* ↓"
            if lang != "es" else
            f"Antes: ~${price_before:.2f}~   Ahora: *${current_price:.2f}*\n"
            f"Bajó *{drop_pct}% OFF* ↓"
        )
    else:
        price_line = f"Agora: *${current_price:.2f}*" if lang != "es" else f"Ahora: *${current_price:.2f}*"

    if lang == "es":
        msg = (
            f"🔔 *Alerta de Precio — Club USA*\n\n"
            f"{title[:80]}\n\n"
            f"{price_line}\n\n"
            f"👉 {affiliate}"
        )
    else:
        msg = (
            f"🔔 *Alerta de Preço — Clube USA*\n\n"
            f"{title[:80]}\n\n"
            f"{price_line}\n\n"
            f"👉 {affiliate}"
        )

    return _send_whatsapp(msg, phone=phone)
