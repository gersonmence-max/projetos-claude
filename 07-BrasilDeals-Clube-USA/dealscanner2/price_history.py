# ============================================================
#  price_history.py — Historico de preco interno
#
#  Sem API externa. O sistema rastreia o menor preco
#  ja visto por ASIN no proprio banco de dados.
#
#  Com o tempo fica mais preciso — depois de 30 dias
#  voce ja tem contexto real de variacao de preco.
# ============================================================

import json
from datetime import datetime, timedelta
from pathlib import Path

import config


def load_history():
    p = Path(config.PRICE_HISTORY_FILE)
    return json.loads(p.read_text()) if p.exists() else {}


def save_history(h):
    Path(config.PRICE_HISTORY_FILE).write_text(
        json.dumps(h, indent=2, ensure_ascii=False)
    )


def record_price(asin, price_now, price_was=None):
    """
    Registra o preco atual de um ASIN.
    Guarda historico de entradas com timestamp.
    """
    h = load_history()

    if asin not in h:
        h[asin] = {"entries": [], "lowest_ever": price_now, "highest_ever": price_now}

    entry = {
        "price":    price_now,
        "was":      price_was,
        "date":     datetime.now().isoformat(),
    }
    h[asin]["entries"].append(entry)

    # Atualiza extremos
    if price_now < h[asin]["lowest_ever"]:
        h[asin]["lowest_ever"] = price_now
    if price_now > h[asin]["highest_ever"]:
        h[asin]["highest_ever"] = price_now

    # Guarda apenas ultimas 90 entradas por ASIN (memoria)
    h[asin]["entries"] = h[asin]["entries"][-90:]

    save_history(h)


def get_price_context(asin, price_now):
    """
    Retorna um contexto textual do preco atual vs historico.

    Exemplos de retorno:
      "menor preco em 45 dias"
      "preco normal — ja esteve mais barato"
      "preco mais alto do historico"
      None  (se nao ha historico suficiente)
    """
    h = load_history()

    if asin not in h:
        return None

    entries = h[asin].get("entries", [])
    if len(entries) < 3:
        return None   # historico insuficiente ainda

    lowest_ever = h[asin].get("lowest_ever", price_now)

    # Preco mais baixo nos ultimos 30/60/90 dias
    now = datetime.now()
    prices_30d = []
    prices_60d = []
    prices_90d = []

    for e in entries:
        try:
            d = datetime.fromisoformat(e["date"])
            p = e["price"]
            days_ago = (now - d).days
            if days_ago <= 30:  prices_30d.append(p)
            if days_ago <= 60:  prices_60d.append(p)
            if days_ago <= 90:  prices_90d.append(p)
        except Exception:
            continue

    # Verifica se e o menor preco no periodo
    tolerance = 0.02  # 2% de margem

    if prices_30d and price_now <= min(prices_30d) * (1 + tolerance):
        return "menor preco em 30 dias"

    if prices_60d and price_now <= min(prices_60d) * (1 + tolerance):
        return "menor preco em 60 dias"

    if prices_90d and price_now <= min(prices_90d) * (1 + tolerance):
        return "menor preco em 90 dias"

    if price_now <= lowest_ever * (1 + tolerance):
        return "menor preco ja registrado"

    # Verifica queda recente
    if len(prices_30d) >= 2:
        avg_30d = sum(prices_30d) / len(prices_30d)
        drop_pct = (avg_30d - price_now) / avg_30d * 100
        if drop_pct >= 15:
            return f"queda de {drop_pct:.0f}% vs media recente"

    return None


def get_stats(asin):
    """Retorna dict com estatisticas do historico de um ASIN."""
    h = load_history()
    if asin not in h or not h[asin]["entries"]:
        return None

    entries  = h[asin]["entries"]
    prices   = [e["price"] for e in entries]
    return {
        "lowest_ever":  h[asin]["lowest_ever"],
        "highest_ever": h[asin]["highest_ever"],
        "avg":          round(sum(prices) / len(prices), 2),
        "entries":      len(entries),
        "first_seen":   entries[0]["date"][:10],
        "last_seen":    entries[-1]["date"][:10],
    }
