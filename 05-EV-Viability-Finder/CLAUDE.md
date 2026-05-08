# CLAUDE.md — Buscador de Terrenos

## O que é

Ferramenta local para encontrar terrenos baratos em Alabama (AL) e Arkansas (AR). Raspa listagens do Zillow, enriquece com FEMA e Regrid, aplica filtros e pontua com IA.

## Como Rodar

```bash
# Terminal 1 — Backend (roda em http://localhost:8000)
cd backend
pip install -r requirements.txt
cp .env.example .env      # adicionar ANTHROPIC_API_KEY
uvicorn main:app --reload --port 8000

# Terminal 2 — Frontend (roda em http://localhost:5173)
cd frontend
npm install
npm run dev
```

## Arquitetura

- **Backend:** FastAPI + SQLite (SQLAlchemy ORM)
- **Frontend:** React + Vite + TypeScript + Tailwind CSS + Framer Motion
- **Banco:** `backend/terrenos.db` (criado automaticamente)

## Fluxo do Pipeline

```
Zillow scraper (AL+AR)
County GIS scraper (ArcGIS REST)
    ↓
FEMA enricher (zona de inundação)
Regrid enricher (dados de parcela — opcional)
    ↓
Filtros (preço, acres, FEMA zona X, desconto, preço/acre)
    ↓
Scorer simplificado (0-100): A(desconto 50pts) + B(liquidez 35pts) + C(FEMA 15pts)
Classificação: FORTE / MODERADO / FRACO / EVITAR
    ↓
Banco SQLite → API REST → Frontend
```

## Variáveis de Ambiente (`backend/.env`)

| Variável | Obrigatório | Descrição |
|---|---|---|
| `ANTHROPIC_API_KEY` | Sim (para IA) | Chave da API Claude |
| `REGRID_API_KEY` | Não | Chave Regrid — sem ela filtros de desconto ficam desabilitados |

## Estrutura de Arquivos

```
backend/
├── main.py              # FastAPI app entry point
├── database.py          # SQLite engine + SessionLocal + get_db
├── models.py            # Property, PipelineRun (SQLAlchemy)
├── config.py            # Carrega .env
├── filters.py           # FilterConfig + apply_filters
├── scorer.py            # calculate_score + generate_ai_analysis
├── scrapers/
│   ├── zillow.py        # Zillow (AL + AR, 5 páginas, rate-limited)
│   └── county_gis.py   # ArcGIS REST dos condados
├── enrichers/
│   ├── fema.py          # msc.fema.gov API
│   └── regrid.py        # app.regrid.com API
└── routes/
    ├── properties.py    # GET /properties/, GET /properties/{id}
    └── pipeline.py      # POST /pipeline/run, GET /pipeline/status/{id} (SSE), GET /pipeline/history

frontend/src/
├── types.ts             # Property, PipelineRun, PropertyFilters interfaces
├── api/                 # client.ts, properties.ts, pipeline.ts
├── lib/utils.ts         # formatCurrency, formatAcres, Google Maps URLs
├── components/          # Layout, ScoreBadge, VerdictBadge, FilterPanel, PropertyTable, PipelineLog
└── pages/               # Dashboard, PropertyDetail, Pipeline
```

## Testes

```bash
cd backend
pytest tests/ -v
# Testes cobrem: aplicação de filtros, cálculo do score com 3 componentes (desconto, liquidez, FEMA), e classificação FORTE/MODERADO/FRACO/EVITAR
```

## Notas Técnicas

- Scrapers usam rate limiting (2-5s entre páginas) para evitar bloqueios
- Análise Claude (AI) está desabilitada por padrão no pipeline (economiza tokens)
- URLs de listagem têm constraint `UNIQUE` — duplicatas são ignoradas silenciosamente
- Pipeline é disparado manualmente pelo frontend (sem agendamento automático)
- SSE (Server-Sent Events) para atualizações em tempo real do pipeline
- Bare imports (`from database import Base`) — app roda de dentro do `backend/`
