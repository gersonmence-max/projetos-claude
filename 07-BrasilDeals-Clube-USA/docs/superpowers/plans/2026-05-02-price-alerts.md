# Price Drop Alerts — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permitir que membros com plano pago monitorem até 10 produtos e recebam alertas via WhatsApp quando o preço atingir o alvo definido.

**Architecture:** Nova tabela `price_alerts` no Supabase armazena os alertas. A API FastAPI expõe 4 endpoints protegidos por plano. O scheduler do dealscanner2 verifica alertas a cada ciclo de scan, consulta preços via Amazon PA-API e dispara notificações WhatsApp via Z-API.

**Tech Stack:** Python 3.11, FastAPI, Supabase (supabase-py), Stripe (existente), Z-API WhatsApp, pytest + unittest.mock

---

## Mapa de Arquivos

| Arquivo | Ação | Responsabilidade |
|---------|------|-----------------|
| `clubeusa/db/price_alerts_migration.sql` | Criar | Tabela price_alerts + índices + RLS |
| `clubeusa/services/alert_service.py` | Criar | CRUD de alertas + extração de ASIN |
| `clubeusa/api/main.py` | Modificar | 4 novos endpoints + dependency require_paid_plan |
| `dealscanner2/config.py` | Modificar | Adicionar vars Supabase + ENCRYPTION_KEY |
| `dealscanner2/alert_checker.py` | Criar | Lógica de verificação de preços e disparo |
| `dealscanner2/sender.py` | Modificar | Nova função send_price_alert() |
| `dealscanner2/scheduler.py` | Modificar | Chamar check_price_alerts() no ciclo de scan |
| `painel-membro.html` | Modificar | UI de gestão de alertas |
| `tests/test_alert_service.py` | Criar | Testes unitários do service |
| `tests/test_alert_checker.py` | Criar | Testes unitários do checker |

---

## Task 1: Migration SQL

**Files:**
- Create: `clubeusa/db/price_alerts_migration.sql`

- [ ] **Step 1: Criar arquivo de migration**

Criar `clubeusa/db/price_alerts_migration.sql` com:

```sql
-- price_alerts_migration.sql
-- Executar no Supabase SQL Editor

CREATE TABLE price_alerts (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    member_id     UUID NOT NULL REFERENCES members(id) ON DELETE CASCADE,
    asin          VARCHAR(20) NOT NULL,
    product_title TEXT,
    price_current NUMERIC(10,2),
    target_type   VARCHAR(10) NOT NULL CHECK (target_type IN ('price', 'percent')),
    target_value  NUMERIC(10,2) NOT NULL,
    status        VARCHAR(20) NOT NULL DEFAULT 'active'
                  CHECK (status IN ('active', 'triggered', 'cancelled')),
    triggered_at  TIMESTAMPTZ,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_alerts_member ON price_alerts (member_id);
CREATE INDEX idx_alerts_active ON price_alerts (status) WHERE status = 'active';
CREATE INDEX idx_alerts_asin   ON price_alerts (asin);

ALTER TABLE price_alerts ENABLE ROW LEVEL SECURITY;

CREATE POLICY alerts_own_select ON price_alerts
    FOR SELECT USING (member_id = auth.uid());

CREATE POLICY alerts_own_insert ON price_alerts
    FOR INSERT WITH CHECK (member_id = auth.uid());

CREATE POLICY alerts_own_update ON price_alerts
    FOR UPDATE USING (member_id = auth.uid());
```

- [ ] **Step 2: Aplicar no Supabase**

Abrir Supabase Dashboard → SQL Editor → colar e executar o conteúdo do arquivo.

Verificar com:
```sql
SELECT column_name, data_type FROM information_schema.columns
WHERE table_name = 'price_alerts' ORDER BY ordinal_position;
```
Esperado: 10 colunas listadas (id, member_id, asin, product_title, price_current, target_type, target_value, status, triggered_at, created_at).

- [ ] **Step 3: Commit**

```bash
git add clubeusa/db/price_alerts_migration.sql
git commit -m "feat: add price_alerts table migration"
```

---

## Task 2: Alert Service

**Files:**
- Create: `clubeusa/services/alert_service.py`
- Create: `tests/test_alert_service.py`

- [ ] **Step 1: Configurar pytest**

Criar `tests/__init__.py` (vazio) e `tests/conftest.py`:

```python
# tests/conftest.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'clubeusa'))
```

Instalar dependências de teste:
```bash
pip install pytest pytest-mock
```

- [ ] **Step 2: Escrever testes que falham**

Criar `tests/test_alert_service.py`:

```python
import pytest
from unittest.mock import MagicMock, patch

# ---- extract_asin_from_url ----

def test_extract_asin_dp_format():
    from services.alert_service import extract_asin_from_url
    asin = extract_asin_from_url("https://www.amazon.com/dp/B08N5WRWNW")
    assert asin == "B08N5WRWNW"

def test_extract_asin_gp_product_format():
    from services.alert_service import extract_asin_from_url
    asin = extract_asin_from_url("https://www.amazon.com/gp/product/B08N5WRWNW?ref=something")
    assert asin == "B08N5WRWNW"

def test_extract_asin_with_title_slug():
    from services.alert_service import extract_asin_from_url
    asin = extract_asin_from_url("https://www.amazon.com/Some-Product-Title/dp/B0ABCDE1234/ref=sr")
    assert asin == "B0ABCDE1234"

def test_extract_asin_invalid_url_raises():
    from services.alert_service import extract_asin_from_url
    with pytest.raises(ValueError, match="ASIN não encontrado"):
        extract_asin_from_url("https://www.google.com/search?q=produto")

# ---- create_alert ----

def test_create_alert_succeeds(mocker):
    from services.alert_service import create_alert
    mock_sb = MagicMock()
    mock_sb.table().select().eq().eq().execute.return_value.data = []  # 0 alertas existentes
    mock_sb.table().insert().execute.return_value.data = [{
        "id": "uuid-1", "member_id": "m-1", "asin": "B08N5WRWNW",
        "target_type": "price", "target_value": 29.99, "status": "active"
    }]
    mocker.patch("services.alert_service._supabase", return_value=mock_sb)

    result = create_alert(
        member_id="m-1", asin="B08N5WRWNW",
        target_type="price", target_value=29.99
    )
    assert result["asin"] == "B08N5WRWNW"
    assert result["status"] == "active"

def test_create_alert_raises_on_limit(mocker):
    from services.alert_service import create_alert
    mock_sb = MagicMock()
    mock_sb.table().select().eq().eq().execute.return_value.data = [{}] * 10  # já tem 10
    mocker.patch("services.alert_service._supabase", return_value=mock_sb)

    with pytest.raises(ValueError, match="Limite"):
        create_alert("m-1", "B08N5WRWNW", "price", 29.99)

# ---- cancel_alert ----

def test_cancel_alert_returns_true(mocker):
    from services.alert_service import cancel_alert
    mock_sb = MagicMock()
    mock_sb.table().update().eq().eq().execute.return_value.data = [{"id": "uuid-1"}]
    mocker.patch("services.alert_service._supabase", return_value=mock_sb)

    result = cancel_alert("uuid-1", "m-1")
    assert result is True

def test_cancel_alert_not_found_returns_false(mocker):
    from services.alert_service import cancel_alert
    mock_sb = MagicMock()
    mock_sb.table().update().eq().eq().execute.return_value.data = []
    mocker.patch("services.alert_service._supabase", return_value=mock_sb)

    result = cancel_alert("uuid-inexistente", "m-1")
    assert result is False
```

- [ ] **Step 3: Rodar testes para confirmar falha**

```bash
cd C:\Users\g-fil\Desktop\ClubeUSA
pytest tests/test_alert_service.py -v
```
Esperado: `ModuleNotFoundError: No module named 'services.alert_service'`

- [ ] **Step 4: Implementar alert_service.py**

Criar `clubeusa/services/alert_service.py`:

```python
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
```

- [ ] **Step 5: Rodar testes para confirmar aprovação**

```bash
pytest tests/test_alert_service.py -v
```
Esperado: todos os testes `PASSED`.

- [ ] **Step 6: Commit**

```bash
git add clubeusa/services/alert_service.py tests/test_alert_service.py tests/__init__.py tests/conftest.py
git commit -m "feat: add alert_service with CRUD and ASIN extractor"
```

---

## Task 3: API Endpoints

**Files:**
- Modify: `clubeusa/api/main.py`

- [ ] **Step 1: Adicionar schemas Pydantic**

Localizar o bloco de schemas em `main.py` (linha ~136) e adicionar após `ClickRequest`:

```python
class AlertCreate(BaseModel):
    asin:         str
    target_type:  str
    target_value: float

    @field_validator("target_type")
    @classmethod
    def validate_target_type(cls, v):
        if v not in ("price", "percent"):
            raise ValueError("target_type deve ser 'price' ou 'percent'.")
        return v

    @field_validator("target_value")
    @classmethod
    def validate_target_value(cls, v):
        if v <= 0:
            raise ValueError("target_value deve ser maior que zero.")
        return v

    @field_validator("asin")
    @classmethod
    def validate_asin(cls, v):
        import re
        if not re.match(r'^[A-Z0-9]{10}$', v.strip().upper()):
            raise ValueError("ASIN inválido. Deve ter 10 caracteres alfanuméricos.")
        return v.strip().upper()


class AlertFromLink(BaseModel):
    url:          str
    target_type:  str
    target_value: float

    @field_validator("target_type")
    @classmethod
    def validate_target_type(cls, v):
        if v not in ("price", "percent"):
            raise ValueError("target_type deve ser 'price' ou 'percent'.")
        return v

    @field_validator("target_value")
    @classmethod
    def validate_target_value(cls, v):
        if v <= 0:
            raise ValueError("target_value deve ser maior que zero.")
        return v
```

- [ ] **Step 2: Adicionar dependency require_paid_plan**

Localizar `require_vip` em `main.py` (linha ~126) e adicionar logo abaixo:

```python
def require_paid_plan(member: dict = Depends(get_current_member)) -> dict:
    """Dependency — exige plano pago, sem revelar o nome do plano."""
    if member.get("plan") not in ("vip",):
        raise HTTPException(
            status_code=403,
            detail="Faça upgrade do seu plano para acessar esta funcionalidade."
        )
    return member
```

- [ ] **Step 3: Adicionar os 4 endpoints**

Adicionar ao final de `main.py`, antes do `if __name__ == "__main__"` (se existir), ou ao final do arquivo:

```python
# ============================================================
#  ROTAS — ALERTAS DE PRECO
# ============================================================

@app.post("/alerts", status_code=201)
async def create_alert(body: AlertCreate, member: dict = Depends(require_paid_plan)):
    """Cria alerta de preco para um ASIN."""
    from services.alert_service import create_alert as svc_create
    try:
        result = svc_create(
            member_id    = member["sub"],
            asin         = body.asin,
            target_type  = body.target_type,
            target_value = body.target_value,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/alerts")
async def list_alerts(member: dict = Depends(require_paid_plan)):
    """Lista alertas ativos do membro autenticado."""
    from services.alert_service import list_alerts as svc_list
    return svc_list(member["sub"])


@app.delete("/alerts/{alert_id}", status_code=204)
async def cancel_alert(alert_id: str, member: dict = Depends(require_paid_plan)):
    """Cancela um alerta."""
    from services.alert_service import cancel_alert as svc_cancel
    found = svc_cancel(alert_id, member["sub"])
    if not found:
        raise HTTPException(status_code=404, detail="Alerta não encontrado.")


@app.post("/alerts/from-link", status_code=201)
async def create_alert_from_link(body: AlertFromLink, member: dict = Depends(require_paid_plan)):
    """Recebe URL da Amazon, extrai ASIN e cria alerta."""
    from services.alert_service import extract_asin_from_url, create_alert as svc_create
    try:
        asin   = extract_asin_from_url(body.url)
        result = svc_create(
            member_id    = member["sub"],
            asin         = asin,
            target_type  = body.target_type,
            target_value = body.target_value,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

- [ ] **Step 4: Atualizar cabeçalho do main.py**

Localizar o bloco de comentário de endpoints no topo do arquivo (linha ~8) e adicionar as 4 novas rotas:

```
#  POST /alerts              — criar alerta de preco (plano pago)
#  GET  /alerts              — listar alertas ativos (plano pago)
#  DELETE /alerts/{id}       — cancelar alerta (plano pago)
#  POST /alerts/from-link    — criar alerta via URL Amazon (plano pago)
```

- [ ] **Step 5: Atualizar allow_methods no CORS**

Localizar `allow_methods=["GET", "POST"]` e substituir por:

```python
allow_methods=["GET", "POST", "DELETE"],
```

- [ ] **Step 6: Testar manualmente**

Iniciar a API:
```bash
cd clubeusa && python api/run.py
```

Testar criação com curl (substituir TOKEN por JWT válido de um membro VIP):
```bash
curl -X POST http://localhost:8000/alerts \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"asin":"B08N5WRWNW","target_type":"price","target_value":29.99}'
```
Esperado: `201` com o objeto do alerta criado.

Testar com membro free — esperado: `403` com mensagem de upgrade.

- [ ] **Step 7: Commit**

```bash
git add clubeusa/api/main.py
git commit -m "feat: add price alert endpoints to API"
```

---

## Task 4: Alert Checker no Dealscanner

**Files:**
- Modify: `dealscanner2/config.py`
- Create: `dealscanner2/alert_checker.py`
- Modify: `dealscanner2/sender.py`
- Modify: `dealscanner2/scheduler.py`
- Create: `tests/test_alert_checker.py`

- [ ] **Step 1: Adicionar variáveis Supabase ao config.py**

Adicionar ao final de `dealscanner2/config.py`:

```python
# --- Supabase (para alertas de preco) ---
import os
SUPABASE_URL         = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
ENCRYPTION_KEY       = os.environ.get("ENCRYPTION_KEY", "")
ZAPI_CLIENT_TOKEN    = os.environ.get("ZAPI_CLIENT_TOKEN", "")
```

- [ ] **Step 2: Escrever testes para o checker**

Criar `tests/test_alert_checker.py`:

```python
import pytest
from unittest.mock import MagicMock, patch

# conftest já adiciona clubeusa ao sys.path
# adicionar dealscanner2 também
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'dealscanner2'))


def test_should_trigger_price_type_below_target():
    from alert_checker import should_trigger
    alert = {"target_type": "price", "target_value": 30.00, "price_current": 50.00}
    assert should_trigger(alert, current_price=29.99) is True

def test_should_not_trigger_price_type_above_target():
    from alert_checker import should_trigger
    alert = {"target_type": "price", "target_value": 30.00, "price_current": 50.00}
    assert should_trigger(alert, current_price=31.00) is False

def test_should_trigger_percent_type_sufficient_drop():
    from alert_checker import should_trigger
    alert = {"target_type": "percent", "target_value": 15.0, "price_current": 100.00}
    assert should_trigger(alert, current_price=84.00) is True  # queda de 16%

def test_should_not_trigger_percent_type_insufficient_drop():
    from alert_checker import should_trigger
    alert = {"target_type": "percent", "target_value": 15.0, "price_current": 100.00}
    assert should_trigger(alert, current_price=90.00) is False  # queda de 10%

def test_should_not_trigger_percent_without_price_current():
    from alert_checker import should_trigger
    alert = {"target_type": "percent", "target_value": 15.0, "price_current": None}
    assert should_trigger(alert, current_price=80.00) is False
```

- [ ] **Step 3: Rodar testes para confirmar falha**

```bash
pytest tests/test_alert_checker.py -v
```
Esperado: `ModuleNotFoundError: No module named 'alert_checker'`

- [ ] **Step 4: Criar alert_checker.py**

Criar `dealscanner2/alert_checker.py`:

```python
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
```

- [ ] **Step 5: Adicionar send_price_alert ao sender.py**

Adicionar ao final de `dealscanner2/sender.py`:

```python
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
```

- [ ] **Step 6: Chamar check_price_alerts no scheduler.py**

Localizar a função de scan no `scheduler.py` (a que chama `run_scan`) e adicionar a chamada após o scan:

```python
from alert_checker import check_price_alerts

# Dentro da função de scan, logo após run_scan() ou run_scan_mock():
check_price_alerts()
```

Adicionar também no import do topo do arquivo:
```python
from alert_checker import check_price_alerts
```

- [ ] **Step 7: Rodar testes para confirmar aprovação**

```bash
pytest tests/test_alert_checker.py -v
```
Esperado: todos os testes `PASSED`.

- [ ] **Step 8: Commit**

```bash
git add dealscanner2/config.py dealscanner2/alert_checker.py dealscanner2/sender.py dealscanner2/scheduler.py tests/test_alert_checker.py
git commit -m "feat: add alert checker with price verification and WhatsApp notification"
```

---

## Task 5: Frontend — UI de Alertas

**Files:**
- Modify: `painel-membro.html`

- [ ] **Step 1: Adicionar seção de alertas ao painel**

Localizar no `painel-membro.html` a seção de perfil ou deals do membro e adicionar antes do `</body>`:

```html
<!-- ============ ALERTAS DE PREÇO ============ -->
<section id="alerts-section" style="display:none">
  <h2>🔔 Meus Alertas de Preço</h2>
  <p id="alerts-upgrade-msg" style="display:none">
    <a href="#upgrade">Faça upgrade do seu plano para ativar alertas de preço.</a>
  </p>

  <div id="alerts-content" style="display:none">
    <form id="alert-form">
      <input type="text" id="alert-url" placeholder="Cole o link da Amazon aqui" required />
      <select id="alert-type">
        <option value="price">Preço alvo ($)</option>
        <option value="percent">Queda mínima (%)</option>
      </select>
      <input type="number" id="alert-value" placeholder="Ex: 29.99 ou 15" min="0.01" step="0.01" required />
      <button type="submit">Criar Alerta</button>
    </form>
    <p id="alert-limit-msg"></p>

    <ul id="alerts-list"></ul>
  </div>
</section>

<script>
(function() {
  const API = 'https://clubeusa.com';  // trocar por localhost:8000 em dev

  function getToken() { return localStorage.getItem('token'); }

  async function loadAlerts() {
    const token = getToken();
    if (!token) return;

    const res = await fetch(`${API}/alerts`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });

    const section = document.getElementById('alerts-section');
    section.style.display = 'block';

    if (res.status === 403) {
      document.getElementById('alerts-upgrade-msg').style.display = 'block';
      return;
    }

    document.getElementById('alerts-content').style.display = 'block';
    const alerts = await res.json();
    renderAlerts(alerts);
  }

  function renderAlerts(alerts) {
    const list = document.getElementById('alerts-list');
    list.innerHTML = '';
    const limitMsg = document.getElementById('alert-limit-msg');
    limitMsg.textContent = `${alerts.filter(a => a.status === 'active').length}/10 alertas ativos`;

    alerts.forEach(a => {
      const li = document.createElement('li');
      const label = a.target_type === 'price'
        ? `Avise quando chegar em $${a.target_value}`
        : `Avise quando cair ${a.target_value}%`;
      li.innerHTML = `
        <strong>${a.product_title || a.asin}</strong> — ${label}
        <span class="badge-${a.status}">${a.status}</span>
        ${a.status === 'active'
          ? `<button onclick="cancelAlert('${a.id}')">Cancelar</button>`
          : ''}
      `;
      list.appendChild(li);
    });
  }

  async function cancelAlert(id) {
    await fetch(`${API}/alerts/${id}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${getToken()}` }
    });
    loadAlerts();
  }

  document.getElementById('alert-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const url         = document.getElementById('alert-url').value;
    const target_type = document.getElementById('alert-type').value;
    const target_value = parseFloat(document.getElementById('alert-value').value);

    const res = await fetch(`${API}/alerts/from-link`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${getToken()}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ url, target_type, target_value })
    });

    if (res.ok) {
      document.getElementById('alert-url').value = '';
      document.getElementById('alert-value').value = '';
      loadAlerts();
    } else {
      const err = await res.json();
      alert(err.detail || 'Erro ao criar alerta.');
    }
  });

  loadAlerts();
})();
</script>
```

- [ ] **Step 2: Verificar visualmente no browser**

Abrir `painel-membro.html` no browser. Com token de membro free: verificar que aparece link de upgrade. Com token VIP: verificar que o formulário aparece e os alertas são listados.

- [ ] **Step 3: Commit**

```bash
git add painel-membro.html
git commit -m "feat: add price alerts UI to member panel"
```

---

## Checklist Final

- [ ] Migration aplicada no Supabase
- [ ] `alert_service.py` com todos os testes passando
- [ ] 4 endpoints funcionando na API (201 para VIP, 403 genérico para free)
- [ ] `alert_checker.py` com todos os testes passando
- [ ] `send_price_alert()` integrado ao sender
- [ ] `check_price_alerts()` chamado no ciclo do scheduler
- [ ] UI de alertas visível no painel-membro.html
- [ ] Variáveis `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `ENCRYPTION_KEY` adicionadas ao `.env` do dealscanner2
