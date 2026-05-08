# Admin Panel — Design Spec
**Data:** 2026-05-03  
**Status:** Aprovado

---

## Visão Geral

Painel administrativo unificado integrado à API FastAPI existente. Acesso via `GET /admin` que serve uma página HTML única com 4 abas: Dashboard (métricas), Membros, Deals e Alertas. Autenticação por token secreto via variável de ambiente.

O `painel.py` atual é aposentado — toda sua funcionalidade migra para a API unificada.

---

## Autenticação

Nova variável de ambiente `ADMIN_SECRET` no `.env`. Todos os endpoints `/admin/*` verificam o header:

```
Authorization: Bearer <ADMIN_SECRET>
```

Nova dependency em `main.py`:

```python
def require_admin(authorization: str = Header(None)):
    secret = os.environ.get("ADMIN_SECRET", "")
    if not secret or authorization != f"Bearer {secret}":
        raise HTTPException(status_code=401, detail="Acesso negado.")
```

O `admin.html` pede o token no primeiro acesso, salva em `localStorage`. Se o token for inválido, limpa e pede novamente.

---

## Banco de Dados

O `scanner.py` passa a fazer upsert dos deals na tabela `deals` do Supabase (já existente no `schema.sql`), além de manter o `data/deals.json` local como fallback. A tabela Supabase é a fonte de verdade para o admin.

Nenhuma migration necessária — a tabela `deals` já existe.

---

## Endpoints

### Autenticação da página
```
GET  /admin          → serve admin.html (sem autenticação — o token é validado pelo JS)
```

### Métricas
```
GET  /admin/metrics  → snapshot do sistema (requer token admin)
```

Retorna:
```json
{
  "members":    { "total": 0, "active": 0, "vip": 0, "new_this_week": 0 },
  "deals":      { "pending": 0, "approved": 0, "sent_this_week": 0 },
  "engagement": { "clicks_this_week": 0, "top_category": "" },
  "alerts":     { "active": 0, "triggered_this_week": 0 }
}
```

### Membros
```
GET  /admin/members              → lista paginada (limit=50, offset=0), filtros: plan, status, q (busca nome)
GET  /admin/members/{id}         → perfil completo com PII descriptografada
POST /admin/members/{id}/status  → body: {"status": "active"|"inactive"|"banned"}
```

### Deals
```
GET  /admin/deals                → lista com filtro: status=pending|approved|sent|rejected
POST /admin/deals/{id}/approve   → aprova deal
POST /admin/deals/{id}/reject    → rejeita deal
POST /admin/deals/scan           → dispara varredura Amazon (chama scanner)
POST /admin/deals/send           → envia todos os deals aprovados (chama sender)
```

### Alertas
```
GET  /admin/alerts               → lista todos os alertas ativos com member_id e produto
```

---

## Serviço Admin

Novo arquivo `clubeusa/services/admin_service.py` com funções para cada operação. Mantém o padrão `_supabase()` do projeto.

Funções:
- `get_metrics() -> dict`
- `list_members(plan, status, q, limit, offset) -> list`
- `get_member(member_id) -> dict` (com decrypt de PII)
- `set_member_status(member_id, status) -> bool`
- `list_deals(status) -> list`
- `approve_deal(deal_id) -> bool`
- `reject_deal(deal_id) -> bool`
- `list_admin_alerts() -> list`

---

## Atualização do Scanner

Em `dealscanner2/scanner.py`, após salvar no `deals.json`, fazer upsert no Supabase:

```python
def _sync_deal_to_supabase(deal: dict):
    """Sincroniza deal com Supabase (upsert por asin+source)."""
    if not config.SUPABASE_URL:
        return
    try:
        from supabase import create_client
        sb = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
        sb.table("deals").upsert({
            "id":           deal["id"],
            "asin":         deal["asin"],
            "title":        deal["title"],
            "price_now":    deal["price_now"],
            "price_was":    deal.get("price_was"),
            "discount_pct": deal["discount_pct"],
            "rating":       deal.get("rating"),
            "reviews":      deal.get("reviews"),
            "score":        deal.get("score", 0),
            "affiliate_url": deal["affiliate_url"],
            "category":     deal.get("category"),
            "source":       deal.get("source", "amazon"),
            "status":       deal.get("status", "pending"),
            "auto_approved": deal.get("auto_approved", False),
        }, on_conflict="id").execute()
    except Exception as e:
        log.warning(f"Supabase sync falhou para {deal.get('asin')}: {e}")
```

Erros de sync não interrompem o scanner — são silenciosos (warning no log).

---

## Frontend (`admin.html`)

Arquivo na raiz do projeto, servido por:

```python
from fastapi.responses import FileResponse

@app.get("/admin", include_in_schema=False)
async def admin_panel():
    return FileResponse("admin.html")
```

4 abas:
- **Dashboard** — cards com métricas principais
- **Membros** — tabela com busca, filtros de plano/status, botão de alterar status
- **Deals** — cards de deals pendentes com Aprovar/Rejeitar + botões Scan e Enviar Todos
- **Alertas** — tabela de alertas ativos

---

## Arquivos Afetados

| Arquivo | Ação |
|---------|------|
| `clubeusa/api/main.py` | Adicionar `require_admin`, `FileResponse` import, endpoints `/admin/*` |
| `clubeusa/services/admin_service.py` | Criar — lógica de negócio do admin |
| `dealscanner2/scanner.py` | Adicionar `_sync_deal_to_supabase()` após salvar no JSON |
| `admin.html` | Criar — frontend do painel |
| `clubeusa/.env.example` | Adicionar `ADMIN_SECRET=` |
| `dealscanner2/painel.py` | Aposentar (não deletar ainda — manter como referência) |

---

## Restrições

- `GET /admin` não exige token (serve o HTML) — o token é validado via JS nas chamadas à API
- Decrypt de PII apenas nos endpoints admin (protegidos por `require_admin`)
- Erros de sync Supabase no scanner não interrompem a varredura
- `painel.py` mantido no repositório como referência até o admin estar estável em produção
