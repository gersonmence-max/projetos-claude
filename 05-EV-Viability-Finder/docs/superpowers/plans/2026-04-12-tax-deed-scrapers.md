# Tax Deed Scrapers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Substituir o scraper do Zillow por dois scrapers de tax deed sales — COSL (Arkansas) e GovEase (Alabama) — adicionando campos `parcel_id` e `sale_date` ao banco, e atualizando o frontend para mostrar data do leilão e fonte correta.

**Architecture:** Dois novos scrapers produzem dicionários no mesmo schema do pipeline atual. O pipeline substitui a chamada `scrape_all_states()` por `scrape_cosl() + scrape_govease()`. O resto do pipeline (FEMA, filtros, scorer, IA) não muda.

**Tech Stack:** Python/httpx/BeautifulSoup (backend), React/TypeScript (frontend), SQLite/SQLAlchemy (DB)

---

## Arquivos

| Arquivo | Ação |
|---|---|
| `backend/models.py` | Modificar — adicionar `parcel_id`, `sale_date` |
| `backend/scrapers/cosl.py` | Criar — scraper COSL Arkansas |
| `backend/scrapers/govease.py` | Criar — scraper GovEase Alabama |
| `backend/scrapers/zillow.py` | Não tocar — só não chamar mais |
| `backend/routes/pipeline.py` | Modificar — trocar scraper |
| `backend/routes/properties.py` | Modificar — incluir novos campos na resposta |
| `backend/tests/test_cosl.py` | Criar — testes do parser COSL |
| `backend/tests/test_govease.py` | Criar — testes do parser GovEase |
| `frontend/src/types.ts` | Modificar — adicionar `parcel_id`, `sale_date` |
| `frontend/src/components/PropertyTable.tsx` | Modificar — colunas Sale Date e Fonte |
| `frontend/src/pages/PropertyDetail.tsx` | Modificar — campos novos + link correto |
| `backend/terrenos.db` | Apagar — necessário para nova schema |

---

## Task 1: Adicionar campos ao modelo do banco

**Files:**
- Modify: `backend/models.py`

- [ ] **Step 1: Adicionar os dois campos novos ao modelo Property**

Abrir `backend/models.py` e adicionar após a linha do `listing_url`:

```python
    parcel_id = Column(String, nullable=True)          # ID da parcela no condado
    sale_date = Column(String, nullable=True)           # "YYYY-MM-DD" — data do leilão
```

O arquivo completo fica assim:

```python
# backend/models.py
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text
from sqlalchemy.sql import func
from database import Base


class Property(Base):
    __tablename__ = "properties"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String, nullable=False)
    state = Column(String, nullable=False)
    county = Column(String)
    address = Column(String)
    lat = Column(Float)
    lng = Column(Float)
    price = Column(Float)
    acres = Column(Float)
    price_per_acre = Column(Float)
    avg_price_per_acre = Column(Float)
    discount_pct = Column(Float)
    fema_zone = Column(String)
    has_road_access = Column(Boolean)
    utilities_available = Column(Boolean)
    zoning = Column(String)
    score = Column(Float)
    ai_analysis = Column(Text)
    listing_url = Column(String, unique=True, index=True)
    parcel_id = Column(String, nullable=True)
    sale_date = Column(String, nullable=True)
    scraped_at = Column(DateTime, nullable=False, server_default=func.now())
    passed_filters = Column(Boolean, default=False)


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id = Column(Integer, primary_key=True, index=True)
    started_at = Column(DateTime, server_default=func.now())
    finished_at = Column(DateTime, nullable=True)
    status = Column(String, default="rodando")
    scraped = Column(Integer, default=0)
    enriched = Column(Integer, default=0)
    filtered = Column(Integer, default=0)
    scored = Column(Integer, default=0)
    error_msg = Column(Text, nullable=True)
```

- [ ] **Step 2: Apagar o banco antigo**

SQLite não aplica `ALTER TABLE` automaticamente via `create_all`. O banco precisa ser recriado do zero:

```bash
cd backend
del terrenos.db
```

(No Linux/Mac: `rm terrenos.db`)

- [ ] **Step 3: Verificar que o banco é recriado corretamente**

```bash
cd backend
python -c "from database import Base, engine; from models import Property, PipelineRun; Base.metadata.create_all(bind=engine); print('OK')"
```

Expected: `OK` sem erros. O arquivo `terrenos.db` reaparece.

- [ ] **Step 4: Commit**

```bash
git add backend/models.py
git commit -m "feat: add parcel_id and sale_date to Property model"
```

---

## Task 2: Criar scraper COSL (Arkansas)

**Files:**
- Create: `backend/scrapers/cosl.py`
- Create: `backend/tests/test_cosl.py`

### API real do COSL

- Base URL: `https://auction.cosl.org`
- Endpoint de leilões ativos: `GET /auctions/ongoing-auctions_grid_read`
- Parâmetros: `page=1`, `pageSize=100`
- Resposta JSON:
```json
{
  "Data": [
    {
      "Owner": "JOHN DOE",
      "CoSLCountyName": "SALINE",
      "CoSLParcelNumber": "931-92009-000",
      "Acreage": 5.2,
      "CoSLPropertyId": 12345,
      "StartingBid": 4250.00,
      "End": "2026-05-15T20:00:00Z",
      "Section": "03",
      "Township": "07S",
      "Range": "09W"
    }
  ],
  "Total": 487
}
```

- [ ] **Step 1: Escrever o teste do parser**

Criar `backend/tests/test_cosl.py`:

```python
# backend/tests/test_cosl.py
import pytest
from scrapers.cosl import _parse_cosl_item


def _make_item(**kwargs):
    base = {
        "CoSLParcelNumber": "931-00001-000",
        "CoSLCountyName": "SALINE",
        "CoSLPropertyId": 99,
        "Acreage": 5.2,
        "StartingBid": 4250.00,
        "End": "2026-05-15T20:00:00Z",
        "Section": "03",
        "Township": "07S",
        "Range": "09W",
        "Owner": "JOHN DOE",
    }
    base.update(kwargs)
    return base


def test_parse_basic_fields():
    result = _parse_cosl_item(_make_item())
    assert result["source"] == "cosl"
    assert result["state"] == "AR"
    assert result["county"] == "Saline"
    assert result["price"] == 4250.00
    assert result["acres"] == 5.2
    assert result["parcel_id"] == "931-00001-000"
    assert result["sale_date"] == "2026-05-15"
    assert result["listing_url"] == "https://auction.cosl.org/auctions?id=99"


def test_parse_address_from_legal_description():
    result = _parse_cosl_item(_make_item())
    assert "03-07S-09W" in result["address"]
    assert "Saline" in result["address"]


def test_parse_missing_acreage_returns_none():
    result = _parse_cosl_item(_make_item(Acreage=None))
    assert result["acres"] is None


def test_parse_missing_bid_returns_none():
    result = _parse_cosl_item(_make_item(StartingBid=None))
    assert result["price"] is None


def test_parse_end_date_formats():
    result = _parse_cosl_item(_make_item(End="2026-12-31T23:59:00Z"))
    assert result["sale_date"] == "2026-12-31"


def test_parse_missing_end_date():
    result = _parse_cosl_item(_make_item(End=None))
    assert result["sale_date"] is None
```

- [ ] **Step 2: Rodar o teste para confirmar que falha**

```bash
cd backend
pytest tests/test_cosl.py -v
```

Expected: `ImportError: cannot import name '_parse_cosl_item' from 'scrapers.cosl'`

- [ ] **Step 3: Implementar o scraper COSL**

Criar `backend/scrapers/cosl.py`:

```python
# backend/scrapers/cosl.py
import asyncio
from typing import Any, Dict, List, Optional

import httpx

_BASE_URL = "https://auction.cosl.org"
_ENDPOINT = "/auctions/ongoing-auctions_grid_read"
_PAGE_SIZE = 100


def _parse_cosl_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """Converte um item da API COSL para o schema do pipeline."""
    county_raw = item.get("CoSLCountyName") or ""
    county = county_raw.title()  # "SALINE" → "Saline"

    section = item.get("Section") or ""
    township = item.get("Township") or ""
    range_ = item.get("Range") or ""
    address = f"Sec {section}-{township}-{range_}, {county} County, AR".strip(", ")

    prop_id = item.get("CoSLPropertyId")
    listing_url = f"{_BASE_URL}/auctions?id={prop_id}" if prop_id else _BASE_URL

    end_raw = item.get("End")
    sale_date = None
    if end_raw:
        # "2026-05-15T20:00:00Z" → "2026-05-15"
        sale_date = end_raw[:10]

    acreage = item.get("Acreage")
    starting_bid = item.get("StartingBid")

    return {
        "source": "cosl",
        "state": "AR",
        "county": county,
        "address": address,
        "lat": None,
        "lng": None,
        "price": float(starting_bid) if starting_bid is not None else None,
        "acres": float(acreage) if acreage is not None else None,
        "parcel_id": item.get("CoSLParcelNumber"),
        "sale_date": sale_date,
        "listing_url": listing_url,
    }


async def scrape_cosl() -> List[Dict[str, Any]]:
    """Raspa todos os leilões ativos do COSL Arkansas."""
    results: List[Dict[str, Any]] = []
    page = 1

    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        while True:
            params = {"page": page, "pageSize": _PAGE_SIZE}
            try:
                resp = await client.get(_BASE_URL + _ENDPOINT, params=params)
                if resp.status_code != 200:
                    print(f"COSL página {page}: status {resp.status_code}")
                    break

                data = resp.json()
                items = data.get("Data") or []
                total = data.get("Total") or 0

                if not items:
                    break

                for item in items:
                    parsed = _parse_cosl_item(item)
                    if parsed["listing_url"]:
                        results.append(parsed)

                print(f"COSL página {page}: {len(items)} imóveis (total: {total})")

                if len(results) >= total or len(items) < _PAGE_SIZE:
                    break

                page += 1
                await asyncio.sleep(2.0)

            except Exception as e:
                print(f"Erro COSL página {page}: {e}")
                break

    print(f"COSL total: {len(results)} imóveis")
    return results
```

- [ ] **Step 4: Rodar os testes**

```bash
cd backend
pytest tests/test_cosl.py -v
```

Expected: todos os 6 testes PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/scrapers/cosl.py backend/tests/test_cosl.py
git commit -m "feat: add COSL Arkansas tax deed scraper"
```

---

## Task 3: Criar scraper GovEase (Alabama)

**Files:**
- Create: `backend/scrapers/govease.py`
- Create: `backend/tests/test_govease.py`

### API real do GovEase

- Base URL: `https://liveauctions.govease.com`
- Endpoint: `GET /OpenAuction/RefreshBidDownAuctions`
- Parâmetros: `countyId`, `stateAbbr=al`, `pageNumber`, `pageSize`
- Resposta JSON:
```json
{
  "Result": true,
  "Grid": "<table>...<tbody><tr><td>...</td></tr></tbody></table>"
}
```

Colunas do HTML na ordem: Watch, Unique#, Parcel#, Owner Name, Face Value, Parcel Address, Auction Name, Auction Type, Bidding, My Bid

**Alabama counties on GovEase (parcial — o scraper descobre mais dinamicamente):**
```python
_AL_COUNTIES = [
    {"id": 1252, "slug": "alcolbert", "name": "Colbert"},
    {"id": 1309, "slug": "alhale",    "name": "Hale"},
]
```

- [ ] **Step 1: Escrever o teste do parser HTML**

Criar `backend/tests/test_govease.py`:

```python
# backend/tests/test_govease.py
import pytest
from scrapers.govease import _parse_grid_html, _parse_face_value


_SAMPLE_GRID = """
<table>
  <thead>
    <tr>
      <th>Watch</th><th>Unique #</th><th>Parcel #</th><th>Owner Name</th>
      <th>Face Value</th><th>Parcel Address</th><th>Auction Name</th>
      <th>Auction Type</th><th>Bidding</th><th>My Bid</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td></td>
      <td>AU-001</td>
      <td>12-34-56-789</td>
      <td>JANE DOE</td>
      <td>$3,450.00</td>
      <td>123 Main St, Colbert, AL</td>
      <td>2026 Colbert County Tax Lien Auction</td>
      <td>Tax Lien</td>
      <td>Open</td>
      <td></td>
    </tr>
    <tr>
      <td></td>
      <td>AU-002</td>
      <td>98-76-54-321</td>
      <td>BOB SMITH</td>
      <td>$1,200.50</td>
      <td>456 Oak Ave, Colbert, AL</td>
      <td>2026 Colbert County Tax Lien Auction</td>
      <td>Tax Deed</td>
      <td>Open</td>
      <td></td>
    </tr>
  </tbody>
</table>
"""


def test_parse_grid_returns_two_rows():
    results = _parse_grid_html(_SAMPLE_GRID, county_id=1252, county_name="Colbert")
    assert len(results) == 2


def test_parse_first_row_fields():
    results = _parse_grid_html(_SAMPLE_GRID, county_id=1252, county_name="Colbert")
    r = results[0]
    assert r["source"] == "govease"
    assert r["state"] == "AL"
    assert r["county"] == "Colbert"
    assert r["parcel_id"] == "12-34-56-789"
    assert r["address"] == "123 Main St, Colbert, AL"
    assert r["price"] == 3450.00
    assert r["listing_url"] == "https://liveauctions.govease.com/al/alcolbert/1252/browsebiddown"


def test_parse_face_value():
    assert _parse_face_value("$3,450.00") == 3450.00
    assert _parse_face_value("$1,200.50") == 1200.50
    assert _parse_face_value("") is None
    assert _parse_face_value("N/A") is None


def test_parse_empty_grid_returns_empty_list():
    results = _parse_grid_html("<table><tbody></tbody></table>", county_id=1252, county_name="Colbert")
    assert results == []


def test_parse_malformed_row_skipped():
    bad_html = "<table><tbody><tr><td>only one cell</td></tr></tbody></table>"
    results = _parse_grid_html(bad_html, county_id=1252, county_name="Colbert")
    assert results == []
```

- [ ] **Step 2: Rodar o teste para confirmar que falha**

```bash
cd backend
pytest tests/test_govease.py -v
```

Expected: `ImportError: cannot import name '_parse_grid_html'`

- [ ] **Step 3: Implementar o scraper GovEase**

Criar `backend/scrapers/govease.py`:

```python
# backend/scrapers/govease.py
import asyncio
import re
from typing import Any, Dict, List, Optional

import httpx
from bs4 import BeautifulSoup

_BASE_URL = "https://liveauctions.govease.com"
_REFRESH_ENDPOINT = "/OpenAuction/RefreshBidDownAuctions"
_PAGE_SIZE = 50

# Condados do Alabama confirmados no GovEase.
# O scraper também tenta descobrir mais dinamicamente na função _discover_counties().
_AL_COUNTIES_FALLBACK = [
    {"id": 1252, "slug": "alcolbert", "name": "Colbert"},
    {"id": 1309, "slug": "alhale",    "name": "Hale"},
]


def _parse_face_value(text: str) -> Optional[float]:
    """Converte '$3,450.00' → 3450.0. Retorna None se não parsear."""
    cleaned = re.sub(r"[^\d.]", "", text.strip())
    try:
        return float(cleaned) if cleaned else None
    except ValueError:
        return None


def _parse_grid_html(
    html: str, county_id: int, county_name: str
) -> List[Dict[str, Any]]:
    """Extrai propriedades do HTML da resposta GovEase."""
    results = []
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.select("tbody tr")

    county_slug = "al" + county_name.lower().replace(" ", "")
    listing_url = f"{_BASE_URL}/al/{county_slug}/{county_id}/browsebiddown"

    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 9:
            continue
        try:
            parcel_id = cells[2].get_text(strip=True)
            address = cells[5].get_text(strip=True)
            face_value_text = cells[4].get_text(strip=True)
            price = _parse_face_value(face_value_text)

            if not parcel_id:
                continue

            results.append({
                "source": "govease",
                "state": "AL",
                "county": county_name,
                "address": address,
                "lat": None,
                "lng": None,
                "price": price,
                "acres": None,
                "parcel_id": parcel_id,
                "sale_date": None,
                "listing_url": listing_url,
            })
        except Exception:
            continue

    return results


async def _discover_counties(client: httpx.AsyncClient) -> List[Dict[str, Any]]:
    """Tenta descobrir condados do Alabama na página principal do GovEase."""
    try:
        resp = await client.get(f"{_BASE_URL}/al/")
        if resp.status_code != 200:
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        counties = []

        # Links no padrão /al/{slug}/{id}/browsebiddown
        pattern = re.compile(r"/al/([^/]+)/(\d+)/browsebiddown")
        seen_ids = set()

        for a_tag in soup.find_all("a", href=pattern):
            href = a_tag.get("href", "")
            match = pattern.search(href)
            if match:
                slug = match.group(1)
                county_id = int(match.group(2))
                if county_id not in seen_ids:
                    seen_ids.add(county_id)
                    # Deriva o nome do slug: "alcolbert" → "Colbert"
                    name = slug[2:].title()  # remove prefixo "al"
                    counties.append({"id": county_id, "slug": slug, "name": name})

        return counties
    except Exception as e:
        print(f"GovEase: erro ao descobrir condados: {e}")
        return []


async def _scrape_county(
    client: httpx.AsyncClient, county: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Raspa todos os leilões de um condado Alabama."""
    results = []
    page = 1

    while True:
        params = {
            "countyId": county["id"],
            "stateAbbr": "al",
            "pageNumber": page,
            "pageSize": _PAGE_SIZE,
            "orderBy": "",
            "orderDesc": "false",
        }
        try:
            resp = await client.get(_BASE_URL + _REFRESH_ENDPOINT, params=params)
            if resp.status_code != 200:
                print(f"GovEase {county['name']}: status {resp.status_code}")
                break

            data = resp.json()
            if not data.get("Result"):
                break

            grid_html = data.get("Grid") or ""
            page_results = _parse_grid_html(
                grid_html, county_id=county["id"], county_name=county["name"]
            )

            if not page_results:
                break

            results.extend(page_results)
            print(f"GovEase {county['name']} página {page}: {len(page_results)} imóveis")

            if len(page_results) < _PAGE_SIZE:
                break

            page += 1
            await asyncio.sleep(2.0)

        except Exception as e:
            print(f"Erro GovEase {county['name']} página {page}: {e}")
            break

    return results


async def scrape_govease() -> List[Dict[str, Any]]:
    """Raspa todos os leilões ativos do GovEase para Alabama."""
    results = []

    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        # Tenta descobrir condados dinamicamente; usa fallback se falhar
        counties = await _discover_counties(client)
        if not counties:
            print("GovEase: usando lista de condados hardcoded")
            counties = _AL_COUNTIES_FALLBACK

        print(f"GovEase: {len(counties)} condados encontrados")

        for county in counties:
            county_results = await _scrape_county(client, county)
            results.extend(county_results)
            await asyncio.sleep(2.0)

    print(f"GovEase total: {len(results)} imóveis")
    return results
```

- [ ] **Step 4: Rodar os testes**

```bash
cd backend
pytest tests/test_govease.py -v
```

Expected: todos os 5 testes PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/scrapers/govease.py backend/tests/test_govease.py
git commit -m "feat: add GovEase Alabama tax deed scraper"
```

---

## Task 4: Atualizar o pipeline

**Files:**
- Modify: `backend/routes/pipeline.py`

- [ ] **Step 1: Substituir o import do scraper**

Em `backend/routes/pipeline.py`, linha 17, substituir:

```python
from scrapers.zillow import scrape_all_states
```

por:

```python
from scrapers.cosl import scrape_cosl
from scrapers.govease import scrape_govease
```

- [ ] **Step 2: Substituir a chamada ao scraper no `_pipeline_task`**

Encontrar o bloco `# ── 1. Scraping` e substituir:

```python
        # ── 1. Scraping ──────────────────────────────────────────────────
        all_listings = await scrape_all_states()
        run.scraped = len(all_listings)
        db.commit()
```

por:

```python
        # ── 1. Scraping ──────────────────────────────────────────────────
        cosl_listings = await scrape_cosl()
        govease_listings = await scrape_govease()
        all_listings = cosl_listings + govease_listings
        run.scraped = len(all_listings)
        db.commit()
```

- [ ] **Step 3: Ajustar o cálculo de discount_pct**

O cálculo de `discount_pct` atual usa `avg_price_per_acre` do Regrid. O COSL não tem `assessed_value` diretamente — mantemos o cálculo existente baseado em `avg_price_per_acre` do county_gis (que não muda). Nenhuma alteração necessária nesse bloco.

- [ ] **Step 4: Verificar que o pipeline importa sem erros**

```bash
cd backend
python -c "from routes.pipeline import router; print('OK')"
```

Expected: `OK` (com aviso Pydantic que é normal).

- [ ] **Step 5: Commit**

```bash
git add backend/routes/pipeline.py
git commit -m "feat: wire COSL + GovEase scrapers into pipeline"
```

---

## Task 5: Atualizar a resposta da API de propriedades

**Files:**
- Modify: `backend/routes/properties.py`

- [ ] **Step 1: Adicionar `parcel_id` e `sale_date` ao `_prop_to_dict`**

Em `backend/routes/properties.py`, na função `_prop_to_dict`, adicionar dois campos após `"listing_url"`:

```python
        "listing_url": p.listing_url,
        "parcel_id": p.parcel_id,
        "sale_date": p.sale_date,
```

O bloco completo do return fica:

```python
    return {
        "id": p.id,
        "source": p.source,
        "state": p.state,
        "county": p.county,
        "address": p.address,
        "lat": p.lat,
        "lng": p.lng,
        "price": p.price,
        "acres": p.acres,
        "price_per_acre": p.price_per_acre,
        "avg_price_per_acre": p.avg_price_per_acre,
        "discount_pct": p.discount_pct,
        "fema_zone": p.fema_zone,
        "has_road_access": p.has_road_access,
        "utilities_available": p.utilities_available,
        "zoning": p.zoning,
        "score": p.score,
        "ai_analysis": ai_analysis,
        "listing_url": p.listing_url,
        "parcel_id": p.parcel_id,
        "sale_date": p.sale_date,
        "scraped_at": p.scraped_at.isoformat() if p.scraped_at else None,
        "passed_filters": p.passed_filters,
    }
```

- [ ] **Step 2: Verificar que a API sobe sem erros**

```bash
cd backend
python -c "from routes.properties import router; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/routes/properties.py
git commit -m "feat: expose parcel_id and sale_date in properties API"
```

---

## Task 6: Atualizar o frontend

**Files:**
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/components/PropertyTable.tsx`
- Modify: `frontend/src/pages/PropertyDetail.tsx`

### 6a — Tipos TypeScript

- [ ] **Step 1: Adicionar campos à interface Property em `frontend/src/types.ts`**

Adicionar após `"listing_url: string;"`:

```typescript
  parcel_id: string | null;
  sale_date: string | null;
```

O bloco `Property` completo fica:

```typescript
export interface Property {
  id: number;
  source: string;
  state: string;
  county: string;
  address: string;
  lat: number | null;
  lng: number | null;
  price: number | null;
  acres: number | null;
  price_per_acre: number | null;
  avg_price_per_acre: number | null;
  discount_pct: number | null;
  fema_zone: string | null;
  has_road_access: boolean | null;
  utilities_available: boolean | null;
  zoning: string | null;
  score: number | null;
  ai_analysis: AiAnalysis | null;
  listing_url: string;
  parcel_id: string | null;
  sale_date: string | null;
  scraped_at: string | null;
  passed_filters: boolean;
}
```

### 6b — Tabela

- [ ] **Step 2: Adicionar função `formatSaleDate` em `frontend/src/lib/utils.ts`**

Adicionar ao final do arquivo:

```typescript
export function formatSaleDate(value: string | null | undefined): string {
  if (!value) return "—";
  const [year, month, day] = value.split("-");
  return `${day}/${month}/${year}`;
}
```

- [ ] **Step 3: Adicionar colunas "Fonte" e "Leilão" em `PropertyTable.tsx`**

Em `frontend/src/components/PropertyTable.tsx`:

1. Adicionar import de `formatSaleDate`:
```typescript
import { formatCurrency, formatAcres, formatDiscount, formatSaleDate } from "../lib/utils";
```

2. Adicionar duas colunas após a coluna `"fema_zone"` (antes do `veredicto`):

```typescript
  {
    accessorKey: "source",
    header: "Fonte",
    size: 90,
    cell: ({ getValue }) => {
      const src = getValue() as string;
      return (
        <span
          className="text-xs font-mono font-semibold px-2 py-0.5 rounded"
          style={{
            backgroundColor: src === "cosl" ? "rgba(34,197,94,0.1)" : "rgba(108,99,255,0.1)",
            color: src === "cosl" ? "#22c55e" : "#6c63ff",
          }}
        >
          {src.toUpperCase()}
        </span>
      );
    },
  },
  {
    accessorKey: "sale_date",
    header: "Leilão",
    size: 110,
    cell: ({ getValue }) => (
      <span className="font-mono text-xs" style={{ color: "#64748b" }}>
        {formatSaleDate(getValue() as string | null)}
      </span>
    ),
  },
```

### 6c — Detalhe

- [ ] **Step 4: Atualizar `PropertyDetail.tsx`**

Em `frontend/src/pages/PropertyDetail.tsx`:

1. Adicionar import de `formatSaleDate`:
```typescript
import {
  formatCurrency,
  formatAcres,
  formatDiscount,
  formatSaleDate,
  buildGoogleMapsUrl,
  buildStreetViewUrl,
} from "../lib/utils";
```

2. Adicionar import de `Calendar` no bloco lucide-react:
```typescript
import {
  ArrowLeft, MapPin, Maximize2, DollarSign, TrendingDown,
  Shield, Zap, ExternalLink, Map, Eye, CheckCircle2,
  AlertCircle, Navigation, Calendar,
} from "lucide-react";
```

3. No card "Dados Básicos", adicionar linha de `sale_date` e `parcel_id` após a linha de "Fonte":

```tsx
          <DataRow icon={MapPin} label="Fonte" value={property.source.toUpperCase()} />
          {property.sale_date && (
            <DataRow
              icon={Calendar}
              label="Data do leilão"
              value={
                <span style={{ color: "#f59e0b" }}>
                  {formatSaleDate(property.sale_date)}
                </span>
              }
            />
          )}
          {property.parcel_id && (
            <DataRow
              icon={MapPin}
              label="ID da parcela"
              value={
                <span className="font-mono text-xs">{property.parcel_id}</span>
              }
            />
          )}
```

4. Alterar o label do botão de link para refletir a fonte:

Encontrar:
```tsx
          {property.listing_url && (
            <ActionButton
              href={property.listing_url}
              icon={ExternalLink}
              label="Ver listagem original"
              primary
            />
          )}
```

Substituir por:
```tsx
          {property.listing_url && (
            <ActionButton
              href={property.listing_url}
              icon={ExternalLink}
              label={
                property.source === "cosl"
                  ? "Ver no COSL"
                  : property.source === "govease"
                  ? "Ver no GovEase"
                  : "Ver listagem original"
              }
              primary
            />
          )}
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/types.ts frontend/src/lib/utils.ts frontend/src/components/PropertyTable.tsx frontend/src/pages/PropertyDetail.tsx
git commit -m "feat: add sale_date, parcel_id and source badge to frontend"
```

---

## Task 7: Build e teste final

**Files:**
- Build: `frontend/dist/`

- [ ] **Step 1: Rodar todos os testes do backend**

```bash
cd backend
pytest tests/ -v
```

Expected: todos os testes passam (incluindo os 10 de filtros + 5 de scorer + 6 de cosl + 5 de govease).

- [ ] **Step 2: Compilar o frontend**

```bash
cd frontend
npm run build
```

Expected: `✓ built in Xs` sem erros TypeScript.

- [ ] **Step 3: Iniciar o servidor**

```bash
cd backend
python -m uvicorn main:app --port 8000
```

- [ ] **Step 4: Verificar o servidor responde**

```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/properties/
```

Expected:
```
{"status":"ok"}
[]
```

- [ ] **Step 5: Abrir http://localhost:8000 e verificar o Dashboard**

- Dashboard carrega sem erros
- Tabela mostra colunas "Fonte" e "Leilão"
- Rodar o pipeline e verificar que busca dados COSL + GovEase

- [ ] **Step 6: Commit final**

```bash
git add frontend/dist
git commit -m "build: rebuild frontend with tax deed scraper changes"
```
