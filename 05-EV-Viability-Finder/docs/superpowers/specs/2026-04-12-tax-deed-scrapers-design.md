# Tax Deed Scrapers — Design Spec

> **For agentic workers:** Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Substituir o scraper do Zillow por dois scrapers de tax deed sales — COSL (Arkansas) e GovEase (Alabama) — mantendo todo o resto do pipeline intacto.

**Data:** 2026-04-12

---

## Contexto

O sistema atual raspa listagens de mercado aberto do Zillow. O objetivo é mudar para listas de **tax deed sales**: imóveis vendidos pelo condado por impostos atrasados, com lances mínimos muito abaixo do valor de mercado.

Fontes escolhidas:
- **COSL** (Commissioner of State Lands) — repositório centralizado do Arkansas em `cosl.org`
- **GovEase** — plataforma centralizada usada por dezenas de condados do Alabama em `govease.com`

Escopo: apenas **leilões agendados** (com data e lance mínimo definidos), não todos os inadimplentes.

---

## Arquitetura

```
scrapers/cosl.py      (AR) ──┐
                              ├──→ pipeline.py → FEMA enricher → filtros → scorer → DB → frontend
scrapers/govease.py   (AL) ──┘
        ↑
scrapers/county_gis.py  (continua: fornece avg_price_per_acre de referência de mercado)
scrapers/zillow.py      (desativado: código mantido mas não chamado)
```

O pipeline chama os dois novos scrapers em sequência. O enriquecimento FEMA, os filtros e o scorer não mudam — apenas recebem os dados no mesmo formato de dicionário que já usam.

---

## Campos extraídos pelos novos scrapers

Ambos os scrapers produzem dicionários com estes campos (mesmo schema do pipeline atual):

| Campo | Tipo | Descrição |
|---|---|---|
| `source` | str | `"cosl"` ou `"govease"` |
| `state` | str | `"AR"` ou `"AL"` |
| `county` | str | Nome do condado |
| `address` | str | Endereço do imóvel |
| `lat` | float\|None | Latitude (se disponível) |
| `lng` | float\|None | Longitude (se disponível) |
| `price` | float | Lance mínimo do leilão (impostos devidos) |
| `acres` | float\|None | Tamanho em acres |
| `parcel_id` | str\|None | ID da parcela no condado |
| `sale_date` | str\|None | Data do leilão (`"YYYY-MM-DD"`) |
| `listing_url` | str | Link direto na plataforma |
| `assessed_value` | float\|None | Valor avaliado pelo condado (base para calcular desconto) |

O `discount_pct` é calculado no pipeline como:
```python
if assessed_value and price and assessed_value > 0:
    listing["discount_pct"] = (1 - price / assessed_value) * 100
```

---

## Scraper 1 — COSL Arkansas (`backend/scrapers/cosl.py`)

**Fonte:** `https://cosl.org/map-sales` e API interna do COSL

O COSL disponibiliza imóveis certificados para venda (redemption period expirado). A página lista os condados com vendas ativas. Para cada condado:

1. Fetch da lista de propriedades via endpoint COSL (JSON ou HTML)
2. Parse: parcel_id, county, address, acres, assessed_value, min_bid, sale_date
3. Rate limiting: 2–3s entre requisições
4. Retorna lista de dicionários no schema acima

**Campos mapeados:**
- `price` ← `min_bid` (lance mínimo = impostos devidos)
- `assessed_value` ← valor avaliado pelo condado (para calcular desconto)
- `listing_url` ← URL da parcela no portal COSL

---

## Scraper 2 — GovEase Alabama (`backend/scrapers/govease.py`)

**Fonte:** `https://www.govease.com/` — listagens de leilões ativos por condado em AL

1. Fetch da lista de leilões ativos para o estado AL
2. Filtra por tipo "tax deed" / "tax sale"
3. Parse por propriedade: parcel_id, county, address, acres, min_bid, sale_date
4. Rate limiting: 2–3s entre páginas
5. Retorna lista de dicionários no schema acima

**Observação:** GovEase nem sempre expõe o `assessed_value`. Quando ausente, `discount_pct` fica `None` e o filtro de desconto é ignorado (mesmo comportamento atual sem Regrid).

---

## Mudanças no banco de dados (`backend/models.py`)

Dois campos novos na tabela `properties`:

```python
parcel_id  = Column(String, nullable=True)   # ID da parcela no condado
sale_date  = Column(String, nullable=True)   # "2025-06-15"
```

A migration é automática via `Base.metadata.create_all()` — SQLite adiciona colunas novas sem recriar a tabela (via `ALTER TABLE` implícito do SQLAlchemy se configurado, ou recriação manual do DB).

**Atenção:** o banco existente (`terrenos.db`) precisará ser apagado na primeira execução após a mudança, pois SQLAlchemy com SQLite não aplica ALTER TABLE automaticamente via `create_all`. Documentar isso no README.

---

## Mudanças no pipeline (`backend/routes/pipeline.py`)

Substituição da chamada ao scraper:

```python
# ANTES
from scrapers.zillow import scrape_all_states
all_listings = await scrape_all_states()

# DEPOIS
from scrapers.cosl import scrape_cosl
from scrapers.govease import scrape_govease
cosl_listings = await scrape_cosl()
govease_listings = await scrape_govease()
all_listings = cosl_listings + govease_listings
```

O cálculo de `discount_pct` no pipeline passa a usar `assessed_value` (vindo do scraper) em vez de `avg_price_per_acre` do Regrid:

```python
# Desconto via assessed_value (tax deed)
assessed = listing.get("assessed_value")
price = listing.get("price")
if assessed and price and assessed > 0:
    listing["discount_pct"] = (1 - price / assessed) * 100
```

O `county_gis.py` continua sendo chamado para buscar `avg_price_per_acre` de referência de mercado por região.

---

## Mudanças no frontend

### Tabela (`PropertyTable.tsx`)
- Coluna "Leilão" adicionada, mostrando `sale_date` formatada (`DD/MM/YYYY`)
- Coluna "Fonte" mostra badge `COSL` ou `GovEase`

### Detalhe (`PropertyDetail.tsx`)
- Seção de dados básicos inclui: Data do leilão, ID da parcela, Fonte
- Link "Ver no COSL" / "Ver no GovEase" substitui o link "Ver listagem"

---

## Arquivos criados/modificados

| Arquivo | Ação |
|---|---|
| `backend/scrapers/cosl.py` | Criar |
| `backend/scrapers/govease.py` | Criar |
| `backend/scrapers/zillow.py` | Manter (não deletar, não chamar) |
| `backend/models.py` | Modificar: adicionar `parcel_id`, `sale_date` |
| `backend/routes/pipeline.py` | Modificar: trocar scraper, ajustar cálculo discount_pct |
| `frontend/src/components/PropertyTable.tsx` | Modificar: colunas Sale Date e Fonte |
| `frontend/src/pages/PropertyDetail.tsx` | Modificar: campos novos + link correto |
| `frontend/src/types.ts` | Modificar: adicionar `parcel_id`, `sale_date` na interface Property |
| `README.md` | Modificar: instrução para apagar terrenos.db na migração |

---

## O que NÃO muda

- `backend/filters.py` — sem alteração
- `backend/scorer.py` — sem alteração
- `backend/enrichers/fema.py` — sem alteração
- `backend/enrichers/regrid.py` — sem alteração
- `backend/config.py` — sem alteração
- `backend/database.py` — sem alteração
- `frontend/src/pages/Pipeline.tsx` — sem alteração
- `frontend/src/pages/Dashboard.tsx` — sem alteração
- `frontend/src/components/FilterPanel.tsx` — sem alteração
- `frontend/src/components/PipelineLog.tsx` — sem alteração
