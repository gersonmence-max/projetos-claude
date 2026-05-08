# Admin Panel — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir um painel administrativo unificado integrado à API FastAPI, com autenticação por token secreto, gestão de membros/deals/alertas e métricas do sistema.

**Architecture:** Novos endpoints `/admin/*` no FastAPI existente, protegidos por `require_admin`. Serviço `admin_service.py` centraliza a lógica de negócio. O scanner passa a sincronizar deals no Supabase após salvar no JSON. Frontend em `admin.html` servido diretamente pelo FastAPI.

**Tech Stack:** Python 3.11, FastAPI, Supabase (supabase-py), subprocess (para scan/send), HTML5/JS vanilla, pytest + unittest.mock

---

## Mapa de Arquivos

| Arquivo | Ação | Responsabilidade |
|---------|------|-----------------|
| `clubeusa/services/admin_service.py` | Criar | CRUD admin: membros, deals, alertas, métricas |
| `clubeusa/api/main.py` | Modificar | `require_admin`, `StatusUpdate` schema, endpoints `/admin/*` |
| `dealscanner2/scanner.py` | Modificar | `_sync_deal_to_supabase()` após `save_db()` |
| `admin.html` | Criar | Frontend com 4 abas |
| `clubeusa/.env.example` | Modificar | Adicionar `ADMIN_SECRET=` |
| `tests/test_admin_service.py` | Criar | Testes unitários do serviço admin |

---

## Task 1: Admin Service

**Files:**
- Create: `clubeusa/services/admin_service.py`
- Create: `tests/test_admin_service.py`

- [ ] **Step 1: Escrever testes que falham**

Criar `tests/test_admin_service.py`:

```python
import pytest
from unittest.mock import MagicMock, patch
from datetime import date, timedelta


def _mock_sb():
    return MagicMock()


# ---- get_metrics ----

def test_get_metrics_returns_expected_keys(mocker):
    from services.admin_service import get_metrics
    mock_sb = _mock_sb()
    # members total
    mock_sb.table().select().execute.return_value.data = [
        {"plan": "free", "status": "active"},
        {"plan": "vip",  "status": "active"},
        {"plan": "free", "status": "inactive"},
    ]
    # clicks this week
    mock_sb.table().select().gte().execute.return_value.data = [{}] * 5
    # deals by status
    mock_sb.table().select().eq().execute.return_value.data = [{}] * 3
    # alerts active
    mocker.patch("services.admin_service._supabase", return_value=mock_sb)

    result = get_metrics()
    assert "members" in result
    assert "deals" in result
    assert "engagement" in result
    assert "alerts" in result


# ---- list_members ----

def test_list_members_returns_list(mocker):
    from services.admin_service import list_members
    mock_sb = _mock_sb()
    mock_sb.table().select().order().range().execute.return_value.data = [
        {"id": "m1", "phone_enc": "enc", "name_enc": "enc2", "plan": "free", "status": "active", "points": 100}
    ]
    mocker.patch("services.admin_service._supabase", return_value=mock_sb)
    mocker.patch("services.admin_service._decrypt", return_value="decrypted")

    result = list_members()
    assert isinstance(result, list)
    assert len(result) == 1


# ---- set_member_status ----

def test_set_member_status_returns_true(mocker):
    from services.admin_service import set_member_status
    mock_sb = _mock_sb()
    mock_sb.table().update().eq().execute.return_value.data = [{"id": "m1"}]
    mocker.patch("services.admin_service._supabase", return_value=mock_sb)

    result = set_member_status("m1", "banned")
    assert result is True


def test_set_member_status_invalid_raises(mocker):
    from services.admin_service import set_member_status
    mocker.patch("services.admin_service._supabase", return_value=_mock_sb())

    with pytest.raises(ValueError, match="Status inválido"):
        set_member_status("m1", "suspended")


# ---- approve_deal / reject_deal ----

def test_approve_deal_returns_true(mocker):
    from services.admin_service import approve_deal
    mock_sb = _mock_sb()
    mock_sb.table().update().eq().execute.return_value.data = [{"id": "d1"}]
    mocker.patch("services.admin_service._supabase", return_value=mock_sb)

    assert approve_deal("d1") is True


def test_reject_deal_returns_true(mocker):
    from services.admin_service import reject_deal
    mock_sb = _mock_sb()
    mock_sb.table().update().eq().execute.return_value.data = [{"id": "d1"}]
    mocker.patch("services.admin_service._supabase", return_value=mock_sb)

    assert reject_deal("d1") is True
```

- [ ] **Step 2: Rodar para confirmar falha**

```bash
cd C:\Users\g-fil\Desktop\ClubeUSA
pytest tests/test_admin_service.py -v
```
Esperado: `ModuleNotFoundError: No module named 'services.admin_service'`

- [ ] **Step 3: Implementar admin_service.py**

Criar `clubeusa/services/admin_service.py`:

```python
import os
import logging
from datetime import datetime, timedelta

log = logging.getLogger("admin_service")

VALID_STATUSES = ("active", "inactive", "banned")


def _supabase():
    from supabase import create_client
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])


def _decrypt(token: str) -> str:
    from utils.security import decrypt
    return decrypt(token)


# ============================================================
#  METRICAS
# ============================================================

def get_metrics() -> dict:
    sb = _supabase()
    now = datetime.now()
    week_ago = (now - timedelta(days=7)).isoformat()

    members = sb.table("members").select("plan,status,created_at").execute().data
    total       = len(members)
    active      = sum(1 for m in members if m["status"] == "active")
    vip         = sum(1 for m in members if m["plan"] == "vip")
    new_week    = sum(1 for m in members if m.get("created_at", "") >= week_ago)

    clicks_week = sb.table("clicks").select("id").gte("clicked_at", week_ago).execute().data

    deals = sb.table("deals").select("status,found_at").execute().data
    pending       = sum(1 for d in deals if d["status"] == "pending")
    approved      = sum(1 for d in deals if d["status"] == "approved")
    sent_week     = sum(1 for d in deals if d["status"] == "sent" and d.get("sent_at", "") >= week_ago)

    alerts = sb.table("price_alerts").select("status,triggered_at").execute().data
    alerts_active   = sum(1 for a in alerts if a["status"] == "active")
    alerts_week     = sum(1 for a in alerts if a["status"] == "triggered" and (a.get("triggered_at") or "") >= week_ago)

    from collections import Counter
    top_cat = ""
    if deals:
        cats = [d.get("category") for d in deals if d.get("category")]
        if cats:
            top_cat = Counter(cats).most_common(1)[0][0]

    return {
        "members":    {"total": total, "active": active, "vip": vip, "new_this_week": new_week},
        "deals":      {"pending": pending, "approved": approved, "sent_this_week": sent_week},
        "engagement": {"clicks_this_week": len(clicks_week), "top_category": top_cat},
        "alerts":     {"active": alerts_active, "triggered_this_week": alerts_week},
    }


# ============================================================
#  MEMBROS
# ============================================================

def list_members(
    plan: str = None,
    status: str = None,
    q: str = None,
    limit: int = 50,
    offset: int = 0,
) -> list:
    sb = _supabase()
    query = sb.table("members").select(
        "id,phone_enc,name_enc,email_enc,plan,status,points,level,"
        "referral_count,total_clicks,created_at,group_id"
    ).order("created_at", desc=True).range(offset, offset + limit - 1)

    rows = query.execute().data
    result = []
    for m in rows:
        if plan   and m.get("plan")   != plan:   continue
        if status and m.get("status") != status: continue
        name  = _decrypt(m["name_enc"])  if m.get("name_enc")  else ""
        phone = _decrypt(m["phone_enc"]) if m.get("phone_enc") else ""
        if q and q.lower() not in name.lower() and q not in phone:
            continue
        result.append({**m, "name": name, "phone": phone})
    return result


def get_member(member_id: str) -> dict:
    sb = _supabase()
    row = sb.table("members").select("*").eq("id", member_id).single().execute().data
    if not row:
        return {}
    name  = _decrypt(row["name_enc"])  if row.get("name_enc")  else ""
    phone = _decrypt(row["phone_enc"]) if row.get("phone_enc") else ""
    email = _decrypt(row["email_enc"]) if row.get("email_enc") else ""
    return {**row, "name": name, "phone": phone, "email": email}


def set_member_status(member_id: str, status: str) -> bool:
    if status not in VALID_STATUSES:
        raise ValueError(f"Status inválido. Use: {', '.join(VALID_STATUSES)}")
    sb = _supabase()
    result = sb.table("members").update({"status": status}).eq("id", member_id).execute()
    return len(result.data) > 0


# ============================================================
#  DEALS
# ============================================================

def list_deals(status: str = None) -> list:
    sb = _supabase()
    query = sb.table("deals").select("*").order("score", desc=True)
    if status:
        query = sb.table("deals").select("*").eq("status", status).order("score", desc=True)
    return query.execute().data


def approve_deal(deal_id: str) -> bool:
    sb = _supabase()
    result = sb.table("deals").update({"status": "approved"}).eq("id", deal_id).execute()
    return len(result.data) > 0


def reject_deal(deal_id: str) -> bool:
    sb = _supabase()
    result = sb.table("deals").update({"status": "rejected"}).eq("id", deal_id).execute()
    return len(result.data) > 0


# ============================================================
#  ALERTAS
# ============================================================

def list_admin_alerts() -> list:
    sb = _supabase()
    return (
        sb.table("price_alerts")
        .select("id,member_id,asin,product_title,target_type,target_value,status,created_at,triggered_at")
        .eq("status", "active")
        .order("created_at", desc=True)
        .execute()
        .data
    )
```

- [ ] **Step 4: Rodar testes para confirmar aprovação**

```bash
pytest tests/test_admin_service.py -v
```
Esperado: todos `PASSED`.

- [ ] **Step 5: Commit**

```bash
git add clubeusa/services/admin_service.py tests/test_admin_service.py
git commit -m "feat: add admin_service with members, deals, alerts, metrics"
```

---

## Task 2: Admin Routes na API

**Files:**
- Modify: `clubeusa/api/main.py`
- Modify: `clubeusa/.env.example`

- [ ] **Step 1: Adicionar import FileResponse**

Localizar a linha de imports do FastAPI (linha ~25):
```python
from fastapi.responses import JSONResponse
```
Adicionar `FileResponse` na mesma linha:
```python
from fastapi.responses import JSONResponse, FileResponse
```

- [ ] **Step 2: Adicionar require_admin**

Localizar `require_paid_plan` (linha ~137) e adicionar logo após:

```python
def require_admin(authorization: str = Header(None)):
    """Dependency — valida token de admin via ADMIN_SECRET."""
    secret = os.environ.get("ADMIN_SECRET", "")
    if not secret or authorization != f"Bearer {secret}":
        raise HTTPException(status_code=401, detail="Acesso negado.")
```

- [ ] **Step 3: Adicionar schema StatusUpdate**

Localizar `class AlertFromLink` e adicionar após:

```python
class StatusUpdate(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        if v not in ("active", "inactive", "banned"):
            raise ValueError("Status inválido. Use: active, inactive, banned.")
        return v
```

- [ ] **Step 4: Adicionar todos os endpoints admin**

Adicionar ao final de `main.py` (após os endpoints de alertas):

```python
# ============================================================
#  ROTAS — ADMIN
# ============================================================

@app.get("/admin", include_in_schema=False)
async def admin_panel():
    """Serve o painel admin HTML."""
    import os
    html_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "admin.html")
    return FileResponse(os.path.abspath(html_path))


@app.get("/admin/metrics")
async def admin_metrics(_: str = Depends(require_admin)):
    from services.admin_service import get_metrics
    return get_metrics()


@app.get("/admin/members")
async def admin_list_members(
    plan: str = None, status: str = None, q: str = None,
    limit: int = 50, offset: int = 0,
    _: str = Depends(require_admin),
):
    from services.admin_service import list_members
    return list_members(plan=plan, status=status, q=q, limit=limit, offset=offset)


@app.get("/admin/members/{member_id}")
async def admin_get_member(member_id: str, _: str = Depends(require_admin)):
    from services.admin_service import get_member
    m = get_member(member_id)
    if not m:
        raise HTTPException(status_code=404, detail="Membro não encontrado.")
    return m


@app.post("/admin/members/{member_id}/status")
async def admin_set_member_status(
    member_id: str, body: StatusUpdate, _: str = Depends(require_admin)
):
    from services.admin_service import set_member_status
    try:
        found = set_member_status(member_id, body.status)
        if not found:
            raise HTTPException(status_code=404, detail="Membro não encontrado.")
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/admin/deals")
async def admin_list_deals(status: str = None, _: str = Depends(require_admin)):
    from services.admin_service import list_deals
    return list_deals(status=status)


@app.post("/admin/deals/{deal_id}/approve")
async def admin_approve_deal(deal_id: str, _: str = Depends(require_admin)):
    from services.admin_service import approve_deal
    if not approve_deal(deal_id):
        raise HTTPException(status_code=404, detail="Deal não encontrado.")
    return {"ok": True}


@app.post("/admin/deals/{deal_id}/reject")
async def admin_reject_deal(deal_id: str, _: str = Depends(require_admin)):
    from services.admin_service import reject_deal
    if not reject_deal(deal_id):
        raise HTTPException(status_code=404, detail="Deal não encontrado.")
    return {"ok": True}


@app.post("/admin/deals/scan")
async def admin_scan_deals(_: str = Depends(require_admin)):
    """Dispara varredura Amazon em background."""
    import subprocess, sys
    subprocess.Popen(
        [sys.executable, "scanner.py"],
        cwd=os.path.join(os.path.dirname(__file__), "..", "..", "dealscanner2"),
    )
    return {"ok": True, "message": "Varredura iniciada em background."}


@app.post("/admin/deals/send")
async def admin_send_deals(_: str = Depends(require_admin)):
    """Envia todos os deals aprovados em background."""
    import subprocess, sys
    subprocess.Popen(
        [sys.executable, "-c",
         "from sender import auto_send_approved; auto_send_approved()"],
        cwd=os.path.join(os.path.dirname(__file__), "..", "..", "dealscanner2"),
    )
    return {"ok": True, "message": "Envio iniciado em background."}


@app.get("/admin/alerts")
async def admin_list_alerts(_: str = Depends(require_admin)):
    from services.admin_service import list_admin_alerts
    return list_admin_alerts()
```

- [ ] **Step 5: Atualizar cabeçalho do main.py**

Localizar o bloco de comentário de endpoints no topo (linhas 6-22) e adicionar:

```
#  GET  /admin                   — painel admin HTML
#  GET  /admin/metrics           — snapshot do sistema (admin)
#  GET  /admin/members           — lista membros (admin)
#  GET  /admin/members/{id}      — perfil completo (admin)
#  POST /admin/members/{id}/status — alterar status (admin)
#  GET  /admin/deals             — lista deals (admin)
#  POST /admin/deals/{id}/approve — aprovar deal (admin)
#  POST /admin/deals/{id}/reject  — rejeitar deal (admin)
#  POST /admin/deals/scan        — disparar varredura (admin)
#  POST /admin/deals/send        — enviar aprovados (admin)
#  GET  /admin/alerts            — listar alertas (admin)
```

- [ ] **Step 6: Atualizar .env.example**

Localizar `clubeusa/.env.example` e adicionar ao final:

```
# Admin
ADMIN_SECRET=troque-por-um-token-secreto-longo
```

- [ ] **Step 7: Commit**

```bash
git add clubeusa/api/main.py clubeusa/.env.example
git commit -m "feat: add admin routes and require_admin dependency"
```

---

## Task 3: Scanner → Supabase Sync

**Files:**
- Modify: `dealscanner2/scanner.py`

- [ ] **Step 1: Adicionar função _sync_deal_to_supabase**

Localizar `def save_db(deals):` (linha ~187) em `scanner.py` e adicionar após ela:

```python
def _sync_deal_to_supabase(deal: dict):
    """Sincroniza deal com Supabase. Falhas são silenciosas (não interrompem o scanner)."""
    if not config.SUPABASE_URL or not config.SUPABASE_SERVICE_KEY:
        return
    try:
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
        log.warning(f"Supabase sync falhou para {deal.get('asin', '?')}: {e}")
```

- [ ] **Step 2: Chamar _sync_deal_to_supabase após save_db**

Localizar `save_db(all_deals)` (linha ~562) e adicionar logo após:

```python
    save_db(all_deals)
    for deal in all_new:
        _sync_deal_to_supabase(deal)
    mark_scan_done()
```

- [ ] **Step 3: Verificar que o scanner ainda funciona sem Supabase**

```bash
cd C:\Users\g-fil\Desktop\ClubeUSA\dealscanner2
python scanner.py --help 2>&1 || python -c "from scanner import load_db; print('OK')"
```
Esperado: sem erros (Supabase vazio não quebra nada — função é silenciosa).

- [ ] **Step 4: Commit**

```bash
git add dealscanner2/scanner.py
git commit -m "feat: sync deals to Supabase after each scan"
```

---

## Task 4: Frontend admin.html

**Files:**
- Create: `admin.html` (raiz do projeto)

- [ ] **Step 1: Criar admin.html**

Criar `admin.html` na raiz (`C:\Users\g-fil\Desktop\ClubeUSA\admin.html`):

```html
<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Clube USA — Admin</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: system-ui, sans-serif; background: #0f172a; color: #e2e8f0; min-height: 100vh; }
  header { background: #1e293b; padding: 16px 24px; display: flex; align-items: center; gap: 12px; border-bottom: 1px solid #334155; }
  header h1 { font-size: 18px; font-weight: 700; color: #f8fafc; }
  header span { font-size: 12px; color: #64748b; }
  nav { display: flex; gap: 4px; padding: 16px 24px 0; border-bottom: 1px solid #334155; }
  nav button { background: none; border: none; color: #94a3b8; padding: 10px 16px; cursor: pointer; font-size: 14px; border-bottom: 2px solid transparent; }
  nav button.active { color: #f8fafc; border-bottom-color: #3b82f6; }
  main { padding: 24px; }
  .tab { display: none; }
  .tab.active { display: block; }
  .cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 16px; margin-bottom: 24px; }
  .card { background: #1e293b; border-radius: 8px; padding: 20px; }
  .card .label { font-size: 12px; color: #64748b; text-transform: uppercase; letter-spacing: .05em; }
  .card .value { font-size: 32px; font-weight: 700; margin-top: 4px; }
  table { width: 100%; border-collapse: collapse; font-size: 14px; }
  th { text-align: left; padding: 10px 12px; color: #64748b; font-weight: 500; border-bottom: 1px solid #334155; }
  td { padding: 10px 12px; border-bottom: 1px solid #1e293b; }
  tr:hover td { background: #1e293b; }
  .badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }
  .badge-active   { background: #166534; color: #86efac; }
  .badge-vip      { background: #713f12; color: #fcd34d; }
  .badge-free     { background: #1e3a5f; color: #93c5fd; }
  .badge-pending  { background: #1e3a5f; color: #93c5fd; }
  .badge-approved { background: #166534; color: #86efac; }
  .badge-sent     { background: #374151; color: #9ca3af; }
  .badge-rejected { background: #7f1d1d; color: #fca5a5; }
  .badge-inactive { background: #374151; color: #9ca3af; }
  .badge-banned   { background: #7f1d1d; color: #fca5a5; }
  .badge-triggered{ background: #713f12; color: #fcd34d; }
  .btn { padding: 6px 12px; border-radius: 6px; border: none; cursor: pointer; font-size: 13px; font-weight: 500; }
  .btn-green  { background: #166534; color: #86efac; }
  .btn-red    { background: #7f1d1d; color: #fca5a5; }
  .btn-blue   { background: #1e3a5f; color: #93c5fd; }
  .btn-gray   { background: #334155; color: #cbd5e1; }
  .toolbar { display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; align-items: center; }
  input[type=text], select { background: #1e293b; border: 1px solid #334155; color: #e2e8f0; padding: 8px 12px; border-radius: 6px; font-size: 14px; }
  #token-screen { display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 80vh; gap: 16px; }
  #token-screen h2 { font-size: 20px; }
  #token-screen input { width: 320px; }
  #token-screen button { width: 320px; padding: 10px; background: #3b82f6; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 15px; }
  .msg { padding: 12px 16px; border-radius: 6px; margin-bottom: 16px; font-size: 14px; }
  .msg-error { background: #7f1d1d; color: #fca5a5; }
  .msg-success { background: #166534; color: #86efac; }
</style>
</head>
<body>

<div id="token-screen">
  <h2>🔐 Clube USA Admin</h2>
  <input type="password" id="token-input" placeholder="Token de administrador" />
  <button onclick="saveToken()">Entrar</button>
  <p id="token-error" style="color:#fca5a5;display:none">Token inválido.</p>
</div>

<div id="app" style="display:none">
  <header>
    <h1>Clube USA Admin</h1>
    <span id="header-stats"></span>
    <button class="btn btn-gray" style="margin-left:auto" onclick="logout()">Sair</button>
  </header>
  <nav>
    <button class="active" onclick="showTab('dashboard',this)">Dashboard</button>
    <button onclick="showTab('members',this)">Membros</button>
    <button onclick="showTab('deals',this)">Deals</button>
    <button onclick="showTab('alerts',this)">Alertas</button>
  </nav>
  <main>
    <div id="msg-bar" style="display:none"></div>

    <!-- DASHBOARD -->
    <div id="tab-dashboard" class="tab active">
      <div class="cards" id="metrics-cards"></div>
    </div>

    <!-- MEMBROS -->
    <div id="tab-members" class="tab">
      <div class="toolbar">
        <input type="text" id="m-search" placeholder="Buscar nome ou telefone..." oninput="loadMembers()" style="width:240px" />
        <select id="m-plan" onchange="loadMembers()">
          <option value="">Todos os planos</option>
          <option value="free">Free</option>
          <option value="vip">VIP</option>
        </select>
        <select id="m-status" onchange="loadMembers()">
          <option value="">Todos os status</option>
          <option value="active">Ativo</option>
          <option value="inactive">Inativo</option>
          <option value="banned">Banido</option>
        </select>
      </div>
      <table>
        <thead><tr><th>Nome</th><th>Telefone</th><th>Plano</th><th>Status</th><th>Pontos</th><th>Cliques</th><th>Cadastro</th><th>Ações</th></tr></thead>
        <tbody id="members-body"></tbody>
      </table>
      <div style="margin-top:12px;display:flex;gap:8px">
        <button class="btn btn-gray" id="m-prev" onclick="membersPage(-1)">← Anterior</button>
        <button class="btn btn-gray" id="m-next" onclick="membersPage(1)">Próxima →</button>
      </div>
    </div>

    <!-- DEALS -->
    <div id="tab-deals" class="tab">
      <div class="toolbar">
        <select id="d-status" onchange="loadDeals()">
          <option value="pending">Pendentes</option>
          <option value="approved">Aprovados</option>
          <option value="sent">Enviados</option>
          <option value="rejected">Rejeitados</option>
          <option value="">Todos</option>
        </select>
        <button class="btn btn-blue" onclick="triggerScan()">⟳ Scan Amazon</button>
        <button class="btn btn-green" onclick="triggerSend()">▶ Enviar Aprovados</button>
      </div>
      <table>
        <thead><tr><th>Título</th><th>Preço</th><th>Desconto</th><th>Score</th><th>Fonte</th><th>Status</th><th>Ações</th></tr></thead>
        <tbody id="deals-body"></tbody>
      </table>
    </div>

    <!-- ALERTAS -->
    <div id="tab-alerts" class="tab">
      <table>
        <thead><tr><th>Produto / ASIN</th><th>Tipo</th><th>Alvo</th><th>Status</th><th>Criado em</th></tr></thead>
        <tbody id="alerts-body"></tbody>
      </table>
    </div>
  </main>
</div>

<script>
const API = '';  // mesmo origin

function token() { return localStorage.getItem('admin_token') || ''; }
function authHeader() { return { 'Authorization': 'Bearer ' + token(), 'Content-Type': 'application/json' }; }

function showMsg(text, type='success') {
  const bar = document.getElementById('msg-bar');
  bar.className = 'msg msg-' + type;
  bar.textContent = text;
  bar.style.display = 'block';
  setTimeout(() => bar.style.display = 'none', 4000);
}

async function saveToken() {
  const t = document.getElementById('token-input').value.trim();
  if (!t) return;
  localStorage.setItem('admin_token', t);
  const res = await fetch(API + '/admin/metrics', { headers: { 'Authorization': 'Bearer ' + t } });
  if (res.status === 401) {
    document.getElementById('token-error').style.display = 'block';
    localStorage.removeItem('admin_token');
  } else {
    document.getElementById('token-screen').style.display = 'none';
    document.getElementById('app').style.display = 'block';
    init();
  }
}

function logout() {
  localStorage.removeItem('admin_token');
  location.reload();
}

function showTab(name, btn) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('nav button').forEach(b => b.classList.remove('active'));
  document.getElementById('tab-' + name).classList.add('active');
  btn.classList.add('active');
  if (name === 'members') loadMembers();
  if (name === 'deals')   loadDeals();
  if (name === 'alerts')  loadAlerts();
}

// ---- DASHBOARD ----
async function loadMetrics() {
  const res = await fetch(API + '/admin/metrics', { headers: authHeader() });
  if (!res.ok) return;
  const d = await res.json();
  document.getElementById('metrics-cards').innerHTML = `
    <div class="card"><div class="label">Total Membros</div><div class="value">${d.members.total}</div></div>
    <div class="card"><div class="label">Ativos</div><div class="value">${d.members.active}</div></div>
    <div class="card"><div class="label">VIP</div><div class="value" style="color:#fcd34d">${d.members.vip}</div></div>
    <div class="card"><div class="label">Novos (7d)</div><div class="value">${d.members.new_this_week}</div></div>
    <div class="card"><div class="label">Cliques (7d)</div><div class="value">${d.engagement.clicks_this_week}</div></div>
    <div class="card"><div class="label">Deals Pendentes</div><div class="value" style="color:#93c5fd">${d.deals.pending}</div></div>
    <div class="card"><div class="label">Enviados (7d)</div><div class="value">${d.deals.sent_this_week}</div></div>
    <div class="card"><div class="label">Alertas Ativos</div><div class="value">${d.alerts.active}</div></div>
  `;
  document.getElementById('header-stats').textContent =
    `${d.members.active} ativos · ${d.members.vip} VIP · ${d.deals.pending} deals pendentes`;
}

// ---- MEMBROS ----
let membersOffset = 0;
async function loadMembers() {
  const q      = document.getElementById('m-search').value;
  const plan   = document.getElementById('m-plan').value;
  const status = document.getElementById('m-status').value;
  const params = new URLSearchParams({ limit: 50, offset: membersOffset });
  if (q)      params.set('q', q);
  if (plan)   params.set('plan', plan);
  if (status) params.set('status', status);

  const res = await fetch(`${API}/admin/members?${params}`, { headers: authHeader() });
  if (!res.ok) return;
  const members = await res.json();
  const tbody = document.getElementById('members-body');
  tbody.innerHTML = members.map(m => `
    <tr>
      <td>${m.name || '—'}</td>
      <td>${m.phone || '—'}</td>
      <td><span class="badge badge-${m.plan}">${m.plan}</span></td>
      <td><span class="badge badge-${m.status}">${m.status}</span></td>
      <td>${m.points}</td>
      <td>${m.total_clicks}</td>
      <td>${(m.created_at||'').slice(0,10)}</td>
      <td style="display:flex;gap:4px">
        <button class="btn btn-green" onclick="setStatus('${m.id}','active')">Ativar</button>
        <button class="btn btn-gray"  onclick="setStatus('${m.id}','inactive')">Inativar</button>
        <button class="btn btn-red"   onclick="setStatus('${m.id}','banned')">Banir</button>
      </td>
    </tr>
  `).join('');
  document.getElementById('m-prev').disabled = membersOffset === 0;
  document.getElementById('m-next').disabled = members.length < 50;
}

function membersPage(dir) {
  membersOffset = Math.max(0, membersOffset + dir * 50);
  loadMembers();
}

async function setStatus(id, status) {
  const res = await fetch(`${API}/admin/members/${id}/status`, {
    method: 'POST', headers: authHeader(),
    body: JSON.stringify({ status })
  });
  if (res.ok) { showMsg('Status atualizado.'); loadMembers(); }
  else showMsg('Erro ao atualizar.', 'error');
}

// ---- DEALS ----
async function loadDeals() {
  const status = document.getElementById('d-status').value;
  const params = status ? `?status=${status}` : '';
  const res = await fetch(`${API}/admin/deals${params}`, { headers: authHeader() });
  if (!res.ok) return;
  const deals = await res.json();
  document.getElementById('deals-body').innerHTML = deals.map(d => `
    <tr>
      <td style="max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${d.title}">${d.title}</td>
      <td>$${parseFloat(d.price_now).toFixed(2)}</td>
      <td>${d.discount_pct}%</td>
      <td>${parseFloat(d.score||0).toFixed(0)}</td>
      <td>${d.source}</td>
      <td><span class="badge badge-${d.status}">${d.status}</span></td>
      <td style="display:flex;gap:4px">
        ${d.status === 'pending' ? `
          <button class="btn btn-green" onclick="dealAction('${d.id}','approve')">✓</button>
          <button class="btn btn-red"   onclick="dealAction('${d.id}','reject')">✗</button>
        ` : ''}
      </td>
    </tr>
  `).join('');
}

async function dealAction(id, action) {
  const res = await fetch(`${API}/admin/deals/${id}/${action}`, { method: 'POST', headers: authHeader() });
  if (res.ok) { showMsg(action === 'approve' ? 'Deal aprovado.' : 'Deal rejeitado.'); loadDeals(); }
  else showMsg('Erro.', 'error');
}

async function triggerScan() {
  const res = await fetch(`${API}/admin/deals/scan`, { method: 'POST', headers: authHeader() });
  if (res.ok) showMsg('Varredura iniciada em background.');
  else showMsg('Erro ao iniciar varredura.', 'error');
}

async function triggerSend() {
  const res = await fetch(`${API}/admin/deals/send`, { method: 'POST', headers: authHeader() });
  if (res.ok) showMsg('Envio de deals iniciado em background.');
  else showMsg('Erro ao iniciar envio.', 'error');
}

// ---- ALERTAS ----
async function loadAlerts() {
  const res = await fetch(`${API}/admin/alerts`, { headers: authHeader() });
  if (!res.ok) return;
  const alerts = await res.json();
  document.getElementById('alerts-body').innerHTML = alerts.map(a => `
    <tr>
      <td>${a.product_title || a.asin}</td>
      <td>${a.target_type === 'price' ? 'Preço alvo' : 'Queda %'}</td>
      <td>${a.target_type === 'price' ? '$' : ''}${a.target_value}${a.target_type === 'percent' ? '%' : ''}</td>
      <td><span class="badge badge-${a.status}">${a.status}</span></td>
      <td>${(a.created_at||'').slice(0,10)}</td>
    </tr>
  `).join('');
}

// ---- INIT ----
function init() {
  if (!token()) return;
  document.getElementById('token-screen').style.display = 'none';
  document.getElementById('app').style.display = 'block';
  loadMetrics();
}

init();
</script>
</body>
</html>
```

- [ ] **Step 2: Verificar que o arquivo foi criado**

```bash
ls -la "C:\Users\g-fil\Desktop\ClubeUSA\admin.html"
```
Esperado: arquivo listado com tamanho > 0.

- [ ] **Step 3: Commit**

```bash
git add admin.html
git commit -m "feat: add admin panel frontend"
```

---

## Checklist Final

- [ ] `admin_service.py` criado com todos os testes passando
- [ ] `require_admin` adicionado ao `main.py`
- [ ] 11 endpoints `/admin/*` funcionando
- [ ] `GET /admin` serve `admin.html`
- [ ] `ADMIN_SECRET` adicionado ao `.env.example`
- [ ] Scanner sincroniza deals no Supabase após cada scan
- [ ] `admin.html` abre no browser com as 4 abas
- [ ] Login com token correto funciona; token errado mostra erro
- [ ] Variável `ADMIN_SECRET` configurada no `.env` local para teste
