# Especificação: Buscador de Terrenos

**Data:** 2026-04-12  
**Status:** Aprovado  
**Stack:** FastAPI + SQLite + React + Vite + shadcn/ui

---

## Visão Geral

Sistema local de busca e análise de terrenos nos estados de Alabama (AL) e Arkansas (AR). Raspa listagens do Zillow/Realtor.com, enriquece com dados públicos de parcelas dos condados (GIS), dados de zona de inundação FEMA e dados de parcela via Regrid. Aplica filtros configuráveis, pontua automaticamente cada terreno (0–100) e usa o Claude para gerar análise textual dos melhores.

O usuário opera tudo pelo frontend — sem agendamento automático. O pipeline é disparado manualmente.

---

## Arquitetura

```
buscador-de-terrenos/
├── backend/
│   ├── main.py              # FastAPI entry point
│   ├── database.py          # SQLite + SQLAlchemy
│   ├── models.py            # ORM: Property, PipelineRun
│   ├── scrapers/
│   │   ├── zillow.py        # Scraper Zillow/Realtor.com (AL + AR)
│   │   └── county_gis.py   # ArcGIS REST dos condados
│   ├── enrichers/
│   │   ├── fema.py          # FEMA flood zone API
│   │   └── regrid.py        # Regrid parcel API
│   ├── filters.py           # Filtros automáticos configuráveis
│   ├── scorer.py            # Score numérico + análise Claude API
│   ├── routes/
│   │   ├── properties.py    # GET /properties
│   │   ├── pipeline.py      # POST /pipeline/run + GET /pipeline/status
│   │   └── details.py       # GET /properties/{id}
│   └── requirements.txt
└── frontend/
    ├── src/
    │   ├── pages/
    │   │   ├── Dashboard.tsx      # Tabela principal com filtros
    │   │   ├── PropertyDetail.tsx # Detalhe + análise AI + botões Google
    │   │   └── Pipeline.tsx       # Status e histórico do pipeline
    │   ├── components/
    │   └── api/
    └── package.json
```

**Fluxo de dados:**
```
Scraper (Zillow + GIS) → banco raw → FEMA enricher → Regrid enricher → Filtros → Scorer → frontend
```

Cada etapa atualiza o `PipelineRun` com contadores em tempo real. O frontend consome via Server-Sent Events (SSE).

---

## Modelo de Dados

### Tabela `properties`

| Campo | Tipo | Descrição |
|---|---|---|
| `id` | INTEIRO PK | Auto incremento |
| `source` | TEXTO | `"zillow"` ou `"realtor"` |
| `state` | TEXTO | `"AL"` ou `"AR"` |
| `county` | TEXTO | Nome do condado |
| `address` | TEXTO | Endereço completo |
| `lat` | DECIMAL | Latitude (para Street View) |
| `lng` | DECIMAL | Longitude (para Street View) |
| `price` | DECIMAL | Preço listado (USD) |
| `acres` | DECIMAL | Tamanho em acres |
| `price_per_acre` | DECIMAL | Calculado: price / acres |
| `avg_price_per_acre` | DECIMAL | Média regional (via Regrid) |
| `discount_pct` | DECIMAL | % abaixo da média regional |
| `fema_zone` | TEXTO | Zona de inundação (`"X"`, `"AE"`, `"VE"`, etc.) |
| `has_road_access` | BOOLEANO | Acesso a estrada pública |
| `utilities_available` | BOOLEANO | Água/luz disponíveis |
| `zoning` | TEXTO | Classificação de zoneamento |
| `score` | DECIMAL | Pontuação 0–100 |
| `ai_analysis` | TEXTO | JSON com análise do Claude |
| `listing_url` | TEXTO | Link original da listagem |
| `scraped_at` | DATA/HORA | Quando foi raspado |
| `passed_filters` | BOOLEANO | Passou nos filtros automáticos |

### Tabela `pipeline_runs`

| Campo | Tipo | Descrição |
|---|---|---|
| `id` | INTEIRO PK | Auto incremento |
| `started_at` | DATA/HORA | Início da execução |
| `finished_at` | DATA/HORA | Fim (nulo se em andamento) |
| `status` | TEXTO | `"rodando"`, `"concluído"`, `"erro"` |
| `scraped` | INTEIRO | Total raspados |
| `enriched` | INTEIRO | Total enriquecidos |
| `filtered` | INTEIRO | Total que passaram nos filtros |
| `scored` | INTEIRO | Total pontuados |
| `error_msg` | TEXTO | Mensagem de erro (se houver) |

---

## Scrapers

### Zillow / Realtor.com
- Biblioteca: `httpx` + `BeautifulSoup`
- Rotação de user-agent para evitar bloqueios
- Busca por `lot/land` em AL e AR
- Paginação automática
- Campos capturados: endereço, preço, acres, URL, condado, estado, lat/lng

### County GIS (ArcGIS REST)
- APIs públicas ArcGIS dos condados de AL e AR
- Complementa com: zoneamento, acesso a estradas, utilidades
- Matching por endereço ou coordenadas

---

## Enriquecimento

### FEMA
- API pública: `msc.fema.gov`
- Entrada: coordenadas (lat/lng) ou endereço
- Retorna: zona de inundação oficial
- Zona `X` = sem risco especial (passa nos filtros)
- Zonas `AE`, `VE`, `A` = risco alto (reprovado nos filtros)

### Regrid
- API paga (chave configurável via `.env`)
- Retorna: acres reais, valor avaliado, uso do solo, infraestrutura
- Se chave ausente: filtros de desconto e preço/acre ficam desabilitados na UI com aviso

---

## Filtros Configuráveis

Todos ajustáveis pelo frontend. Aplicados sequencialmente:

| Filtro | Padrão | Descrição |
|---|---|---|
| Preço máximo | $500.000 | Exclui acima desse valor total |
| Tamanho mínimo | 1 acre | Exclui terrenos menores |
| Desconto mínimo | 10% | Só mostra X% abaixo da média regional |
| Preço/acre máximo | $10.000 | Exclui acima desse valor por acre |
| Zona FEMA | Apenas X | Exclui qualquer risco de inundação (fixo, não opcional) |

Os filtros de desconto e preço/acre são desabilitados automaticamente se Regrid não estiver configurado.

---

## AI Scorer

### Score numérico (0–100)

| Critério | Peso | Lógica |
|---|---|---|
| Desconto em relação à média regional | 35% | Maior desconto = maior pontuação |
| Preço por acre | 25% | Menor preço/acre = maior pontuação |
| Zona FEMA | 20% | Zona X = máximo; outras = zero |
| Tamanho do terreno | 10% | Maior área = mais pontos (até teto) |
| Acesso a estrada + utilidades | 10% | Bônus por infraestrutura disponível |

### Análise textual Claude

- Ativada apenas para terrenos com **score ≥ 70**
- Modelo: Claude API (claude-sonnet-4-6)
- Prompt recebe todos os dados do terreno
- Resposta JSON com:
  - `resumo`: string (2–3 frases)
  - `pontos_positivos`: lista de strings
  - `pontos_atencao`: lista de strings
  - `veredicto`: `"Oportunidade forte"` | `"Merece análise"` | `"Cautela"`
- Análise salva no banco, não re-gerada a cada visita

---

## Frontend

**Stack:** React + Vite + TypeScript + shadcn/ui + Tailwind CSS + Framer Motion  
**Tema:** Dark mode premium — visual bonito, fluido, legível e moderno. Animações suaves em transições de página e cards. Tipografia clara. Hierarquia visual forte com uso de cores para destacar score e veredicto.

### Tela 1 — Dashboard (tela principal)

- Tabela ordenada por score decrescente
- Colunas: Score | Estado | Condado | Endereço | Acres | Preço | Preço/Acre | Desconto | Zona FEMA | Veredicto Claude
- Filtros no topo (ajustáveis em tempo real)
- Clique na linha → abre detalhe da propriedade

### Tela 2 — Detalhe da Propriedade

Seções:
1. **Dados básicos:** endereço, preço, acres, preço/acre, desconto
2. **Dados FEMA e Regrid:** zona, zoneamento, acesso a estradas, utilidades
3. **Análise do Claude:** resumo, pontos positivos, pontos de atenção, veredicto
4. **Botões de ação:**
   ```
   [ Ver no Google Maps ]   [ Street View ]   [ Ver listagem original ]
   ```

**URLs dos botões (sem API key):**
- Google Maps: `https://www.google.com/maps/search/?api=1&query={endereço}`
- Street View: `https://www.google.com/maps/@?api=1&map_action=pano&viewpoint={lat},{lng}`
- Fallback (sem coordenadas): busca por endereço

### Tela 3 — Pipeline

- Botão `[ Rodar Pipeline ]`
- Log em tempo real via Server-Sent Events (SSE)
- Progresso por etapa: Raspando → Enriquecendo → Filtrando → Pontuando → Concluído
- Histórico das últimas execuções: data, duração, totais por etapa

---

## Configuração (.env)

```env
REGRID_API_KEY=opcional
ANTHROPIC_API_KEY=obrigatório para análise Claude
```

---

## Execução Local

```bash
# Backend
cd backend
pip install -r requirements.txt
python main.py
# Roda em http://localhost:8000

# Frontend
cd frontend
npm install
npm run dev
# Roda em http://localhost:5173
```
