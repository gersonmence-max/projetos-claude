# Price Drop Alerts — Design Spec
**Data:** 2026-05-02  
**Status:** Aprovado

---

## Visão Geral

Funcionalidade exclusiva para membros com plano pago que permite monitorar produtos e receber alertas via WhatsApp quando o preço atingir um alvo definido pelo próprio membro.

Membros sem plano pago visualizam a funcionalidade no painel mas recebem um convite genérico de upgrade — sem qualquer menção a planos ou níveis.

---

## Banco de Dados

Nova tabela `price_alerts` no Supabase:

```sql
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
```

**Limite:** máximo 10 alertas com `status = 'active'` por membro. Validado na API antes de inserir.

---

## API Endpoints

Todos os endpoints exigem JWT válido. Membros sem plano pago recebem `403` com mensagem genérica de upgrade (sem mencionar plano ou nível).

| Método | Rota | Descrição |
|--------|------|-----------|
| `POST` | `/alerts` | Cria alerta com ASIN + tipo + valor alvo |
| `GET` | `/alerts` | Lista alertas ativos do membro autenticado |
| `DELETE` | `/alerts/{alert_id}` | Cancela um alerta |
| `POST` | `/alerts/from-link` | Recebe URL da Amazon, extrai ASIN, cria alerta |

### Payload `POST /alerts`
```json
{
  "asin": "B08N5WRWNW",
  "target_type": "price",
  "target_value": 29.99
}
```

### Payload `POST /alerts/from-link`
```json
{
  "url": "https://www.amazon.com/dp/B08N5WRWNW",
  "target_type": "percent",
  "target_value": 15
}
```

### Extração de ASIN
A URL da Amazon é parseada com regex para extrair o ASIN:
- `amazon.com/dp/{ASIN}`
- `amazon.com/gp/product/{ASIN}`

URLs encurtadas (`a.co`) não são suportadas na v1 — o membro deve enviar a URL completa do produto.

---

## Verificação de Preços

A função `check_price_alerts()` é adicionada ao `dealscanner2/scheduler.py` e executada junto com cada ciclo de scan (6am ET + slots diários).

### Fluxo
1. Busca todos os alertas com `status = 'active'`
2. Agrupa por ASIN para evitar chamadas duplicadas à Amazon PA-API
3. Para cada ASIN, consulta preço atual via `amazon_api.py`
4. Compara com o alvo de cada membro:
   - `target_type = 'price'` → dispara se `preco_atual <= target_value`
   - `target_type = 'percent'` → dispara se queda `>= target_value %` vs `price_current`
5. Se condição atingida:
   - Envia mensagem WhatsApp via `sender.py`
   - Atualiza `status = 'triggered'` e `triggered_at = NOW()`

### Reagrupamento de chamadas de API
Se 5 membros monitoram o mesmo ASIN, a API da Amazon é consultada apenas 1 vez por ciclo.

---

## Notificação WhatsApp

Mensagem enviada ao membro quando o alerta dispara:

```
🔔 Alerta de Preço — Clube USA

[Nome do produto]
Era: $XX.XX → Agora: $XX.XX
Queda de X% ↓

👉 [link afiliado]
```

Após disparar, o alerta muda para `triggered`. O membro pode reativar manualmente pelo painel ou criar um novo alerta para o mesmo produto.

---

## Arquivos Afetados

| Arquivo | Mudança |
|---------|---------|
| `clubeusa/db/schema.sql` | Nova tabela `price_alerts` |
| `clubeusa/api/main.py` | 4 novos endpoints |
| `dealscanner2/scheduler.py` | Nova função `check_price_alerts()` |
| `dealscanner2/sender.py` | Nova função `send_price_alert()` |
| `painel-membro.html` | UI de gestão de alertas |

---

## Restrições e Limites

- Máximo 10 alertas ativos por membro
- Verificação limitada ao ciclo do scanner (não é tempo real)
- Membro sem plano pago vê a feature mas não pode ativar
- Alerta dispara uma vez e fica como `triggered` — reativação é manual
