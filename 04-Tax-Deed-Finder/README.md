# LandHQ

Monitor automatizado de imóveis em leilão fiscal (tax deed) nos EUA, focado na estratégia de owner financing.

## O que faz

- Coleta lotes de leilão de 50 condados em 6 estados (TX, GA, TN, AR, FL, NC) toda madrugada às 2h
- Enriquece cada imóvel com dados públicos gratuitos: FEMA flood zone, wetlands, tornado, elevação, acesso por estrada, distância de cidades
- Pesquisa ônus no Clerk's Office de cada condado (Passo 6 — liens)
- Aplica 8 filtros automáticos de exclusão
- Calcula score 0–100 por regras matemáticas
- Executa análise fina com IA (Anthropic) apenas para score ≥ 70
- Calcula ROI de owner financing para cada imóvel
- Envia alertas por email para score ≥ 75
- Apresenta tudo num dashboard em português com filtros avançados

---

## Arquitetura — 7 Passos do Método Deed Hunter

| # | Passo | Ferramenta |
|---|-------|-----------|
| 1 | Identificação | Scrapers Bid4Assets / GovEase / RealAuction |
| 2 | Acesso físico | OpenStreetMap Overpass API + OSRM |
| 3 | Risco natural | FEMA NFHL + FWS Wetlands + NOAA + USGS |
| 4 | Valuação | Rentcast API (score ≥ 50) |
| 5 | Mercado | Census Bureau ACS5 |
| 6 | Cartório (liens) | Tyler Technologies / Fidlar portals |
| 7 | Decisão final | Score 0–100 + Anthropic claude-sonnet-4 + Owner Financing |

---

## Estrutura do projeto

```
landhq/
├── apps/
│   ├── api/main.py            # FastAPI — 13 endpoints
│   └── web/                   # Next.js 14 — dashboard em português
│       ├── app/
│       │   ├── page.tsx                  # Home: resumo + oportunidades quentes
│       │   ├── imoveis/page.tsx          # Lista com 14 filtros + CSV export
│       │   ├── imoveis/[id]/page.tsx     # Detalhe: 7 passos + liens + OF calc
│       │   ├── salvos/page.tsx           # Imóveis salvos com notas
│       │   ├── analytics/page.tsx        # Distribuição de scores
│       │   └── configuracoes/page.tsx    # Toggle condados + pipeline manual
│       └── components/
│           ├── DeedHunterSteps.tsx       # Timeline visual dos 7 passos
│           ├── LiensPanel.tsx            # Tabela de ônus do cartório
│           ├── OwnerFinancingCalc.tsx    # Calculadora interativa (sliders)
│           ├── FilterPanel.tsx           # Painel com 14 filtros
│           ├── ParcelTable.tsx           # Tabela + 7 bolinhas de status
│           ├── ScoreBadge.tsx
│           └── RiskBadges.tsx
├── scrapers/
│   ├── bid4assets.py          # Playwright autenticado
│   ├── govease.py             # Playwright + interceptação XHR
│   └── realauction.py         # Playwright + paginação
├── enrichers/
│   ├── fema_flood.py          # FEMA National Flood Hazard Layer
│   ├── wetlands.py            # FWS Wetlands Mapper
│   ├── noaa_tornado.py        # NOAA tornado histórico por estado
│   ├── usgs_elevation.py      # USGS EPQS — slope estimation
│   ├── osm_access.py          # OSM Overpass — tipo de estrada
│   ├── osrm_distance.py       # OSRM — drive time para 36 cidades
│   ├── census.py              # Census ACS5 — demografia dos 50 condados
│   ├── assessor.py            # Assessor do condado (REST ou scraping)
│   ├── rentcast.py            # Rentcast AVM — valor de mercado
│   └── liens.py               # Clerk's Office — detecção e classificação de liens
├── analyzer/
│   ├── scoring.py             # 8 filtros automáticos + score 0–100
│   ├── owner_financing.py     # Calculadora ROI owner financing
│   └── ai_analysis.py         # Anthropic API — análise fina em português
├── scheduler/jobs.py          # Pipeline completo + APScheduler 2h
├── db/
│   ├── schema.sql             # 8 tabelas + indexes
│   ├── counties_seed.sql      # 50 condados com FIPS codes
│   └── migrations/
│       └── 001_parcel_liens.sql  # Tabela parcel_liens + view summary
├── tests/
│   ├── test_scoring.py        # 23 testes de filtros e score
│   ├── test_owner_financing.py # 6 testes de calculadora
│   └── test_liens.py          # 30 testes de liens
├── .env.example
└── requirements.txt
```

---

## Pré-requisitos

- Python 3.11+
- Node.js 18+
- Conta no [Supabase](https://supabase.com) (gratuito)
- Conta no [Anthropic](https://console.anthropic.com) (análise IA)
- Conta no [Rentcast](https://rentcast.io) — $29/mês (valuação de mercado)
- Conta no [Resend](https://resend.com) (alertas email — plano gratuito)

---

## Instalação

### 1. Configurar variáveis de ambiente

```bash
cp .env.example .env
```

Edite `.env` com suas credenciais:

```env
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_SERVICE_KEY=eyJ...
ANTHROPIC_API_KEY=sk-ant-...
RENTCAST_API_KEY=...
RESEND_API_KEY=re_...
ALERT_EMAIL=seu@email.com
BID4ASSETS_EMAIL=seu@email.com
BID4ASSETS_PASSWORD=...
GOVEASE_EMAIL=seu@email.com
GOVEASE_PASSWORD=...
REALAUCTION_EMAIL=seu@email.com
REALAUCTION_PASSWORD=...
```

### 2. Banco de dados (Supabase)

No SQL Editor do Supabase, execute em ordem:

```sql
-- 1. Schema principal
-- Cole o conteúdo de db/schema.sql

-- 2. Seed dos 50 condados
-- Cole o conteúdo de db/counties_seed.sql

-- 3. Tabela de liens
-- Cole o conteúdo de db/migrations/001_parcel_liens.sql
```

### 3. Backend Python

```bash
pip install -r requirements.txt
playwright install chromium
```

### 4. Frontend Next.js

```bash
cd apps/web
npm install
```

---

## Rodar localmente

**Backend (FastAPI):**
```bash
cd apps/api
python main.py
# Disponível em http://localhost:8000
```

**Frontend (Next.js):**
```bash
cd apps/web
npm run dev
# Disponível em http://localhost:3000
```

**Executar pipeline manualmente** (sem esperar às 2h):
```bash
# Via API
curl -X POST http://localhost:8000/api/pipeline/run

# Ou direto no Python
python -c "
import asyncio
from scheduler.jobs import run_pipeline
asyncio.run(run_pipeline())
"
```

**Rodar testes:**
```bash
python -m pytest tests/ -v
# 59 testes — scoring, owner financing, liens
```

---

## Condados monitorados (50)

| Estado | Condados |
|--------|---------|
| Texas (15) | Kaufman, Montgomery, Bastrop, Caldwell, Ellis, Rockwall, Hays, Comal, Liberty, Chambers, Denton, Fort Bend, Guadalupe, Wilson, Collin |
| Georgia (11) | Dawson, Jackson, Pickens, Cherokee, Forsyth, Barrow, Walton, Hall, Henry, Paulding, Newton |
| Tennessee (4) | Rutherford, Williamson, Wilson, Maury |
| Arkansas (4) | Benton, Washington, Saline, Faulkner |
| Florida (10) | Polk, Pasco, Hernando, Volusia, Marion, St. Johns, Flagler, Osceola, Lake, Alachua |
| North Carolina (6) | Wake, Johnston, Cabarrus, Union, Iredell, Chatham |

Para adicionar um novo condado: inserir uma linha na tabela `counties`. Sem alterar código.

---

## Score 0–100

| Componente | Pontos |
|-----------|--------|
| Desconto sobre valor de mercado | 0–40 |
| Crescimento populacional (3 anos) | 0–20 |
| Acesso por estrada | 0–20 |
| Tamanho e usabilidade | 0–10 |
| Lance mínimo | 0–10 |

**Thresholds:**
- Score ≥ 50 → busca valor de mercado no Rentcast
- Score ≥ 70 → análise fina com Anthropic API
- Score ≥ 75 → alerta por email via Resend

---

## Filtros automáticos de exclusão

Um imóvel é descartado automaticamente se qualquer condição for verdadeira:

1. Flood zone A, AE, AO, AH ou VE (FEMA)
2. Mais de 50% da área em wetlands (FWS)
3. Imóvel landlocked (sem acesso legal)
4. Sem estrada de acesso (OSM)
5. Valor avaliado pelo assessor < $200
6. Área < 0,1 acres
7. Liens sobreviventes ao tax deed com valor > $500 (Clerk's Office)
8. Mais de 2h de drive de cidade com 50k+ habitantes (OSRM)

---

## Liens — Passo 6 do Método Deed Hunter

O `enrichers/liens.py` pesquisa o portal do Clerk's Office de cada condado e classifica cada documento encontrado:

**Tipos detectados:** IRS Federal, Imposto Estadual, HOA, Hospitalar, Código Municipal, Judicial, Empreiteiro, Outro

**Regras de sobrevivência ao tax deed por estado:**

| Tipo | TX | GA | TN | AR | FL | NC |
|------|----|----|----|----|----|----|
| IRS Federal | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Imposto Estadual | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| HOA | ✓ | ✗ | ✗ | ✗ | ✓ | ✗ |
| Judicial / Empreiteiro / Hospital | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |

**Base legal:** IRS liens — 26 U.S.C. §7425. HOA Florida — Ch. 720/718.

---

## Calculadora Owner Financing

Para cada imóvel com score ≥ 50:

```
Preço de revenda = Valor de mercado × 65%
Entrada          = Preço de revenda × 10%
Saldo financiado = Preço de revenda − Entrada
Parcela mensal   = Saldo / 24 meses
Retorno total    = Entrada + (Parcela × 24)
ROI              = (Retorno total / Lance mínimo − 1) × 100%
```

Os parâmetros são ajustáveis interativamente no dashboard (sliders de 40–90% de revenda, 5–30% de entrada, 12–60 meses).

---

## APIs utilizadas

| API | Custo | Uso |
|-----|-------|-----|
| FEMA NFHL | Gratuita | Flood zone |
| FWS Wetlands | Gratuita | Cobertura de wetlands |
| NOAA Weather API | Gratuita | Risco de tornado |
| USGS EPQS | Gratuita | Elevação e inclinação |
| OSM Overpass | Gratuita | Tipo de estrada |
| OSRM | Gratuita | Tempo de drive |
| Census Bureau ACS5 | Gratuita | Demografia |
| Tyler Tech / Fidlar | Pública | Clerk's Office liens |
| Rentcast | $29/mês | Valor de mercado |
| Anthropic claude-sonnet-4 | Por uso | Análise fina (score ≥ 70) |
| Resend | Gratuito | Alertas email |

---

## Deploy em produção

### Arquitetura de hospedagem

```
Supabase (PostgreSQL)  ←→  Railway (FastAPI + APScheduler)  ←→  Vercel (Next.js)
   banco de dados              backend + pipeline diário           dashboard
```

---

### Passo 1 — Supabase (banco de dados)

1. Crie uma conta em [supabase.com](https://supabase.com) → New Project
2. No **SQL Editor**, execute em ordem:
   - Conteúdo de `db/schema.sql`
   - Conteúdo de `db/counties_seed.sql`
   - Conteúdo de `db/migrations/001_parcel_liens.sql`
3. Em **Project Settings → API**, copie:
   - `Project URL` → `SUPABASE_URL`
   - `service_role` secret → `SUPABASE_SERVICE_KEY`

---

### Passo 2 — Railway (backend Python + scheduler)

1. Crie uma conta em [railway.app](https://railway.app)
2. Instale o CLI:
   ```bash
   npm install -g @railway/cli
   railway login
   ```
3. Na raiz do projeto:
   ```bash
   railway init          # cria o projeto no Railway
   railway up            # faz o deploy usando o Dockerfile
   ```
4. No painel do Railway → seu serviço → **Variables**, adicione todas as variáveis do `.env.example`:
   - `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`
   - `ANTHROPIC_API_KEY`
   - `RENTCAST_API_KEY`
   - `RESEND_API_KEY`, `ALERT_EMAIL`
   - `BID4ASSETS_EMAIL`, `BID4ASSETS_PASSWORD`
   - `GOVEASE_EMAIL`, `GOVEASE_PASSWORD`
   - `REALAUCTION_EMAIL`, `REALAUCTION_PASSWORD`
   - `ENVIRONMENT=production`
   - `ENABLE_SCHEDULER=true`
5. Após o deploy, copie a URL pública gerada (ex: `landhq-api.up.railway.app`)

> O Railway detecta o `Dockerfile` automaticamente. O APScheduler sobe junto com a API e executa o pipeline diário às 2h.

---

### Passo 3 — Vercel (frontend Next.js)

1. Crie uma conta em [vercel.com](https://vercel.com)
2. Instale o CLI:
   ```bash
   npm install -g vercel
   ```
3. Dentro de `apps/web`:
   ```bash
   cd apps/web
   vercel
   ```
   - Framework: Next.js (detectado automaticamente)
   - Root directory: `apps/web`
4. No painel da Vercel → seu projeto → **Settings → Environment Variables**:
   - `NEXT_PUBLIC_API_URL` = URL do Railway (ex: `https://landhq-api.up.railway.app`)
5. Redeploy para aplicar a variável:
   ```bash
   vercel --prod
   ```

---

### Passo 4 — Configurar CORS

Após ter a URL do Vercel (ex: `https://landhq.vercel.app`), volte no Railway e adicione:
```
FRONTEND_URL=https://landhq.vercel.app
```
O Railway fará redeploy automático.

---

### Verificar que está funcionando

```bash
# API respondendo
curl https://landhq-api.up.railway.app/health
# → {"status":"ok","service":"landhq-api"}

# Pipeline manual via API
curl -X POST https://landhq-api.up.railway.app/api/pipeline/run
# → {"status":"started","message":"Pipeline iniciado em background"}
```

Abra o dashboard no Vercel e em **Configurações** clique em **Executar pipeline agora** para o primeiro carregamento de dados.

---

## Endpoints da API

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/parcels` | Lista com 14 filtros e paginação |
| GET | `/api/parcels/{id}` | Detalhe completo |
| GET | `/api/parcels/{id}/liens` | Liens do Clerk's Office |
| GET | `/api/dashboard/summary` | Cards do home |
| GET | `/api/counties` | Lista de condados |
| PATCH | `/api/counties/{id}` | Ativar/desativar condado |
| GET | `/api/saved` | Imóveis salvos |
| POST | `/api/saved` | Salvar imóvel |
| DELETE | `/api/saved/{id}` | Remover salvo |
| PATCH | `/api/saved/{id}/notes` | Atualizar notas |
| GET | `/api/analytics` | Distribuição de scores |
| POST | `/api/pipeline/run` | Acionar pipeline manualmente |
