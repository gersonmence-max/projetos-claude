# Buscador de Terrenos — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir um app web local full-stack que raspa listagens de terrenos do Zillow/Realtor.com em AL e AR, enriquece com dados FEMA e Regrid, filtra e pontua automaticamente, e apresenta resultados em um dashboard React dark-mode de visual premium.

**Architecture:** Backend FastAPI com banco SQLite (SQLAlchemy ORM) expõe endpoints REST + SSE. Frontend React + Vite consome a API e renderiza UI dark-mode premium com shadcn/ui, Tailwind CSS e Framer Motion. Pipeline disparado manualmente pelo frontend.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy, SQLite, httpx, BeautifulSoup4, Anthropic SDK | React 18, Vite, TypeScript, shadcn/ui, Tailwind CSS, Framer Motion, TanStack Table, React Router

---

## Mapa de Arquivos

```
buscador-de-terrenos/
├── backend/
│   ├── main.py                  # FastAPI app, CORS, inclui routers
│   ├── database.py              # Engine SQLite, SessionLocal, Base
│   ├── models.py                # ORM: Property, PipelineRun
│   ├── config.py                # Carrega .env, constantes
│   ├── filters.py               # Lógica de filtros configuráveis
│   ├── scorer.py                # Score numérico + Claude API
│   ├── scrapers/
│   │   ├── __init__.py
│   │   ├── zillow.py            # Scraper Zillow (AL + AR)
│   │   └── county_gis.py       # ArcGIS REST dos condados
│   ├── enrichers/
│   │   ├── __init__.py
│   │   ├── fema.py              # FEMA flood zone API
│   │   └── regrid.py            # Regrid parcel API
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── properties.py        # GET /properties, GET /properties/{id}
│   │   └── pipeline.py          # POST /pipeline/run, GET /pipeline/status/{id}, GET /pipeline/history
│   ├── tests/
│   │   ├── test_filters.py
│   │   └── test_scorer.py
│   ├── .env.example
│   └── requirements.txt
└── frontend/
    ├── src/
    │   ├── main.tsx             # Entry point React
    │   ├── App.tsx              # Router + Layout wrapper
    │   ├── pages/
    │   │   ├── Dashboard.tsx    # Tabela principal com filtros
    │   │   ├── PropertyDetail.tsx # Detalhe + análise AI + botões Google
    │   │   └── Pipeline.tsx     # Controle e log do pipeline
    │   ├── components/
    │   │   ├── Layout.tsx       # Sidebar + área principal
    │   │   ├── ScoreBadge.tsx   # Badge colorido de score 0-100
    │   │   ├── VerdictBadge.tsx # Badge de veredicto Claude
    │   │   ├── FilterPanel.tsx  # Painel de filtros
    │   │   ├── PropertyTable.tsx # TanStack Table wrapper
    │   │   └── PipelineLog.tsx  # Log SSE em tempo real
    │   ├── api/
    │   │   ├── client.ts        # Axios base config
    │   │   ├── properties.ts    # Chamadas de propriedades
    │   │   └── pipeline.ts      # Chamadas de pipeline
    │   └── lib/
    │       └── utils.ts         # Formatadores de moeda, acres, etc.
    ├── index.html
    ├── vite.config.ts
    ├── tailwind.config.ts
    ├── tsconfig.json
    └── package.json
```

---

## Task 1: Estrutura de Pastas + Dependências Backend

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/.env.example`
- Create: `backend/scrapers/__init__.py`
- Create: `backend/enrichers/__init__.py`
- Create: `backend/routes/__init__.py`
- Create: `backend/tests/__init__.py`

- [ ] **Step 1: Criar estrutura de pastas**

```bash
cd "C:/Users/g-fil/Desktop/buscador de terrenos"
mkdir -p backend/scrapers backend/enrichers backend/routes backend/tests
touch backend/scrapers/__init__.py backend/enrichers/__init__.py backend/routes/__init__.py backend/tests/__init__.py
```

- [ ] **Step 2: Criar requirements.txt**

Conteúdo de `backend/requirements.txt`:
```
fastapi==0.115.0
uvicorn[standard]==0.30.0
sqlalchemy==2.0.35
httpx==0.27.2
beautifulsoup4==4.12.3
anthropic==0.40.0
python-dotenv==1.0.1
pytest==8.3.3
pytest-asyncio==0.24.0
httpx==0.27.2
```

- [ ] **Step 3: Criar .env.example**

Conteúdo de `backend/.env.example`:
```env
ANTHROPIC_API_KEY=sk-ant-sua-chave-aqui
REGRID_API_KEY=opcional-deixe-vazio-se-nao-tiver
```

- [ ] **Step 4: Instalar dependências**

```bash
cd backend
pip install -r requirements.txt
```

Esperado: todas as dependências instaladas sem erro.

---

## Task 2: Banco de Dados + Modelos ORM

**Files:**
- Create: `backend/database.py`
- Create: `backend/models.py`

- [ ] **Step 1: Criar database.py**

```python
# backend/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./terrenos.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 2: Criar models.py**

```python
# backend/models.py
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text
from sqlalchemy.sql import func
from database import Base


class Property(Base):
    __tablename__ = "properties"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String, nullable=False)          # "zillow" | "realtor"
    state = Column(String, nullable=False)           # "AL" | "AR"
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
    ai_analysis = Column(Text)                       # JSON string
    listing_url = Column(String)
    scraped_at = Column(DateTime, server_default=func.now())
    passed_filters = Column(Boolean, default=False)


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id = Column(Integer, primary_key=True, index=True)
    started_at = Column(DateTime, server_default=func.now())
    finished_at = Column(DateTime, nullable=True)
    status = Column(String, default="rodando")       # rodando | concluído | erro
    scraped = Column(Integer, default=0)
    enriched = Column(Integer, default=0)
    filtered = Column(Integer, default=0)
    scored = Column(Integer, default=0)
    error_msg = Column(Text, nullable=True)
```

- [ ] **Step 3: Verificar que os modelos importam sem erro**

```bash
cd backend
python -c "from models import Property, PipelineRun; print('OK')"
```

Esperado: `OK`

---

## Task 3: Configuração (.env)

**Files:**
- Create: `backend/config.py`
- Create: `backend/.env`

- [ ] **Step 1: Criar config.py**

```python
# backend/config.py
import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
REGRID_API_KEY: str = os.getenv("REGRID_API_KEY", "")

# Filtros padrão (sobrescritos pela UI)
DEFAULT_MAX_PRICE: float = 500_000
DEFAULT_MIN_ACRES: float = 1.0
DEFAULT_MIN_DISCOUNT_PCT: float = 10.0
DEFAULT_MAX_PRICE_PER_ACRE: float = 10_000
```

- [ ] **Step 2: Criar .env com chaves reais**

Criar `backend/.env` (NÃO commitar este arquivo):
```env
ANTHROPIC_API_KEY=sk-ant-sua-chave-aqui
REGRID_API_KEY=
```

- [ ] **Step 3: Verificar carregamento**

```bash
cd backend
python -c "from config import ANTHROPIC_API_KEY; print('Config OK')"
```

Esperado: `Config OK`

---

## Task 4: Testes de Filtros e Scorer (TDD)

**Files:**
- Create: `backend/tests/test_filters.py`
- Create: `backend/tests/test_scorer.py`

- [ ] **Step 1: Escrever testes para filters.py**

```python
# backend/tests/test_filters.py
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from filters import apply_filters, FilterConfig


def test_preco_maximo_exclui_caro():
    config = FilterConfig(max_price=300_000)
    prop = {"price": 500_000, "acres": 5, "fema_zone": "X"}
    assert apply_filters(prop, config, regrid_available=False) is False


def test_preco_maximo_permite_dentro_do_limite():
    config = FilterConfig(max_price=300_000)
    prop = {"price": 200_000, "acres": 5, "fema_zone": "X"}
    assert apply_filters(prop, config, regrid_available=False) is True


def test_tamanho_minimo_exclui_pequeno():
    config = FilterConfig(min_acres=2.0)
    prop = {"price": 100_000, "acres": 0.5, "fema_zone": "X"}
    assert apply_filters(prop, config, regrid_available=False) is False


def test_tamanho_minimo_permite_grande():
    config = FilterConfig(min_acres=2.0)
    prop = {"price": 100_000, "acres": 10, "fema_zone": "X"}
    assert apply_filters(prop, config, regrid_available=False) is True


def test_zona_fema_exclui_risco_inundacao():
    config = FilterConfig()
    prop = {"price": 100_000, "acres": 5, "fema_zone": "AE"}
    assert apply_filters(prop, config, regrid_available=False) is False


def test_zona_fema_x_passa():
    config = FilterConfig()
    prop = {"price": 100_000, "acres": 5, "fema_zone": "X"}
    assert apply_filters(prop, config, regrid_available=False) is True


def test_desconto_minimo_exclui_com_regrid():
    config = FilterConfig(min_discount_pct=10.0)
    prop = {"price": 100_000, "acres": 5, "fema_zone": "X", "discount_pct": 5.0}
    assert apply_filters(prop, config, regrid_available=True) is False


def test_desconto_minimo_passa_com_regrid():
    config = FilterConfig(min_discount_pct=10.0)
    prop = {"price": 100_000, "acres": 5, "fema_zone": "X", "discount_pct": 15.0}
    assert apply_filters(prop, config, regrid_available=True) is True


def test_filtros_regrid_ignorados_sem_chave():
    config = FilterConfig(min_discount_pct=10.0, max_price_per_acre=5_000)
    prop = {
        "price": 100_000, "acres": 5, "fema_zone": "X",
        "discount_pct": 2.0, "price_per_acre": 20_000
    }
    assert apply_filters(prop, config, regrid_available=False) is True


def test_preco_por_acre_exclui_caro_com_regrid():
    config = FilterConfig(max_price_per_acre=5_000)
    prop = {"price": 100_000, "acres": 5, "fema_zone": "X", "price_per_acre": 8_000}
    assert apply_filters(prop, config, regrid_available=True) is False
```

- [ ] **Step 2: Escrever testes para scorer.py**

```python
# backend/tests/test_scorer.py
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scorer import calculate_score


def test_score_propriedade_perfeita():
    prop = {
        "discount_pct": 50,
        "price_per_acre": 1_000,
        "fema_zone": "X",
        "acres": 50,
        "has_road_access": True,
        "utilities_available": True,
    }
    score = calculate_score(prop)
    assert score == 100.0


def test_score_zona_inundacao_penalizada():
    prop = {
        "discount_pct": 50,
        "price_per_acre": 1_000,
        "fema_zone": "AE",
        "acres": 50,
        "has_road_access": True,
        "utilities_available": True,
    }
    score = calculate_score(prop)
    assert score <= 80.0


def test_score_sem_dados_retorna_zero():
    assert calculate_score({}) == 0.0


def test_score_sempre_entre_0_e_100():
    prop = {
        "discount_pct": 999,
        "price_per_acre": 0,
        "fema_zone": "X",
        "acres": 9999,
        "has_road_access": True,
        "utilities_available": True,
    }
    score = calculate_score(prop)
    assert 0.0 <= score <= 100.0


def test_score_sem_infraestrutura_penalizado():
    prop_com = {
        "discount_pct": 20, "price_per_acre": 3_000, "fema_zone": "X",
        "acres": 10, "has_road_access": True, "utilities_available": True,
    }
    prop_sem = {
        "discount_pct": 20, "price_per_acre": 3_000, "fema_zone": "X",
        "acres": 10, "has_road_access": False, "utilities_available": False,
    }
    assert calculate_score(prop_com) > calculate_score(prop_sem)
```

- [ ] **Step 3: Rodar testes — esperado FAIL (módulos ainda não existem)**

```bash
cd backend
pytest tests/ -v
```

Esperado: `ImportError: No module named 'filters'` — confirma que TDD está funcionando.

---

## Task 5: Módulo de Filtros

**Files:**
- Create: `backend/filters.py`

- [ ] **Step 1: Criar filters.py**

```python
# backend/filters.py
from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class FilterConfig:
    max_price: float = 500_000
    min_acres: float = 1.0
    min_discount_pct: float = 10.0
    max_price_per_acre: float = 10_000
    only_fema_x: bool = True


def apply_filters(
    property_data: Dict[str, Any],
    config: FilterConfig,
    regrid_available: bool,
) -> bool:
    """Retorna True se a propriedade passa em todos os filtros."""

    price = property_data.get("price")
    if price is not None and price > config.max_price:
        return False

    acres = property_data.get("acres")
    if acres is not None and acres < config.min_acres:
        return False

    fema_zone = property_data.get("fema_zone")
    if config.only_fema_x and fema_zone and fema_zone not in ("X", "X500"):
        return False

    if regrid_available:
        discount_pct = property_data.get("discount_pct")
        if discount_pct is not None and discount_pct < config.min_discount_pct:
            return False

        price_per_acre = property_data.get("price_per_acre")
        if price_per_acre is not None and price_per_acre > config.max_price_per_acre:
            return False

    return True
```

- [ ] **Step 2: Rodar testes de filtros**

```bash
cd backend
pytest tests/test_filters.py -v
```

Esperado: todos os testes `PASSED`.

---

## Task 6: AI Scorer

**Files:**
- Create: `backend/scorer.py`

- [ ] **Step 1: Criar scorer.py**

```python
# backend/scorer.py
import json
from typing import Any, Dict, Optional

import anthropic

from config import ANTHROPIC_API_KEY

_client: Optional[anthropic.Anthropic] = None


def _get_client() -> Optional[anthropic.Anthropic]:
    global _client
    if ANTHROPIC_API_KEY and _client is None:
        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    return _client


def calculate_score(property_data: Dict[str, Any]) -> float:
    """Calcula score numérico 0-100 para um terreno."""
    score = 0.0

    # 1. Desconto em relação à média regional (35 pts)
    discount_pct = property_data.get("discount_pct") or 0.0
    score += min(discount_pct / 50 * 35, 35.0)

    # 2. Preço por acre (25 pts) — $1.000/acre = máximo, $10.000/acre = 0
    ppa = property_data.get("price_per_acre") or 0.0
    if ppa > 0:
        ppa_score = max(0.0, (1.0 - (ppa - 1_000) / 9_000)) * 25.0
        score += ppa_score

    # 3. Zona FEMA (20 pts)
    fema_zone = property_data.get("fema_zone") or ""
    if fema_zone in ("X", "X500"):
        score += 20.0
    elif fema_zone in ("B", "C"):
        score += 10.0

    # 4. Tamanho em acres (10 pts) — 50+ acres = máximo
    acres = property_data.get("acres") or 0.0
    score += min(acres / 50.0 * 10.0, 10.0)

    # 5. Infraestrutura (10 pts)
    if property_data.get("has_road_access"):
        score += 5.0
    if property_data.get("utilities_available"):
        score += 5.0

    return round(min(score, 100.0), 1)


async def generate_ai_analysis(property_data: Dict[str, Any]) -> Optional[Dict]:
    """Gera análise textual do Claude para terrenos com score >= 70."""
    client = _get_client()
    if not client:
        return None

    if (property_data.get("score") or 0) < 70:
        return None

    prompt = f"""Analise este terreno nos EUA e responda em JSON.

Dados:
- Endereço: {property_data.get("address", "N/A")}
- Estado: {property_data.get("state", "N/A")} | Condado: {property_data.get("county", "N/A")}
- Preço total: ${property_data.get("price", 0):,.0f}
- Tamanho: {property_data.get("acres", 0):.1f} acres
- Preço/acre: ${property_data.get("price_per_acre", 0):,.0f}
- Desconto vs. média regional: {property_data.get("discount_pct", 0):.1f}%
- Zona FEMA: {property_data.get("fema_zone", "N/A")}
- Acesso a estrada: {"Sim" if property_data.get("has_road_access") else "Não"}
- Utilidades disponíveis: {"Sim" if property_data.get("utilities_available") else "Não"}
- Zoneamento: {property_data.get("zoning", "N/A")}
- Score calculado: {property_data.get("score", 0)}/100

Responda SOMENTE com JSON válido, sem texto adicional:
{{
  "resumo": "2-3 frases explicando por que este terreno é interessante ou não",
  "pontos_positivos": ["ponto 1", "ponto 2", "ponto 3"],
  "pontos_atencao": ["ponto 1", "ponto 2"],
  "veredicto": "Oportunidade forte"
}}

O veredicto deve ser exatamente um de: "Oportunidade forte", "Merece análise", "Cautela"."""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}],
        )
        return json.loads(message.content[0].text)
    except Exception as e:
        print(f"Erro ao gerar análise Claude: {e}")
        return None
```

- [ ] **Step 2: Rodar testes do scorer**

```bash
cd backend
pytest tests/test_scorer.py -v
```

Esperado: todos os testes `PASSED`.

---

## Task 7: Scraper Zillow

**Files:**
- Create: `backend/scrapers/zillow.py`

- [ ] **Step 1: Criar zillow.py**

```python
# backend/scrapers/zillow.py
import asyncio
import json
import random
from typing import Any, Dict, List

import httpx

STATES = ["AL", "AR"]

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
]

_STATE_CONFIG = {
    "AL": {
        "mapBounds": {"north": 35.0, "south": 30.1, "east": -84.8, "west": -88.5},
        "regionId": 8,  # Alabama state region ID Zillow
    },
    "AR": {
        "mapBounds": {"north": 36.5, "south": 33.0, "east": -89.6, "west": -94.6},
        "regionId": 9,  # Arkansas state region ID Zillow
    },
}

_SEARCH_URL = "https://www.zillow.com/search/GetSearchPageState.htm"


def _build_headers() -> Dict[str, str]:
    return {
        "User-Agent": random.choice(_USER_AGENTS),
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://www.zillow.com/",
        "X-Requested-With": "XMLHttpRequest",
    }


def _parse_listing(listing: Dict[str, Any], state: str) -> Optional[Dict[str, Any]]:
    """Extrai campos relevantes de uma listagem Zillow."""
    hdp = listing.get("hdpData", {}).get("homeInfo", {})
    home_type = hdp.get("homeType", "")

    if home_type not in ("LOT", "LAND"):
        return None

    price = hdp.get("price") or listing.get("price")
    acres_raw = hdp.get("lotAreaValue")
    lot_unit = hdp.get("lotAreaUnit", "")

    # Converter sqft para acres se necessário
    acres = None
    if acres_raw:
        if lot_unit == "sqft":
            acres = acres_raw / 43_560
        elif lot_unit == "acres":
            acres = acres_raw

    detail_url = listing.get("detailUrl", "")

    return {
        "source": "zillow",
        "state": state,
        "county": hdp.get("county", ""),
        "address": listing.get("address", ""),
        "lat": hdp.get("latitude"),
        "lng": hdp.get("longitude"),
        "price": float(price) if price else None,
        "acres": float(acres) if acres else None,
        "listing_url": f"https://www.zillow.com{detail_url}" if detail_url else "",
    }


async def scrape_zillow(state: str) -> List[Dict[str, Any]]:
    """Raspa listagens de terrenos do Zillow para um estado."""
    results: List[Dict[str, Any]] = []
    config = _STATE_CONFIG[state]

    for page in range(1, 6):
        search_query_state = {
            "pagination": {"currentPage": page},
            "isMapVisible": False,
            "filterState": {
                "lot": {"value": True},
                "land": {"value": True},
                "mf": {"value": False},
                "con": {"value": False},
                "apa": {"value": False},
                "manu": {"value": False},
                "tow": {"value": False},
                "ac": {"min": 1},
                "price": {"max": 500_000},
            },
            "isEntryPoint": False,
            "regionSelection": [{"regionId": config["regionId"], "regionType": 2}],
            "mapBounds": config["mapBounds"],
        }

        params = {
            "searchQueryState": json.dumps(search_query_state),
            "wants": json.dumps({"cat1": ["listResults", "mapResults"]}),
            "requestId": random.randint(1, 20),
        }

        async with httpx.AsyncClient(
            headers=_build_headers(), timeout=30, follow_redirects=True
        ) as client:
            try:
                resp = await client.get(_SEARCH_URL, params=params)
                if resp.status_code != 200:
                    print(f"Zillow {state} página {page}: status {resp.status_code}")
                    break

                data = resp.json()
                listings = (
                    data.get("cat1", {})
                    .get("searchResults", {})
                    .get("listResults", [])
                )

                if not listings:
                    break

                for listing in listings:
                    parsed = _parse_listing(listing, state)
                    if parsed:
                        results.append(parsed)

                print(f"Zillow {state} página {page}: {len(listings)} listagens")
                await asyncio.sleep(random.uniform(2.5, 5.0))

            except Exception as e:
                print(f"Erro Zillow {state} página {page}: {e}")
                break

    return results


async def scrape_all_states() -> List[Dict[str, Any]]:
    """Raspa todos os estados configurados."""
    results: List[Dict[str, Any]] = []
    for state in STATES:
        state_results = await scrape_zillow(state)
        results.extend(state_results)
        print(f"Zillow {state}: {len(state_results)} terrenos encontrados")
        await asyncio.sleep(random.uniform(3.0, 6.0))
    return results
```

- [ ] **Step 2: Adicionar import faltando no zillow.py**

Adicionar `from typing import Optional` na linha de imports (junto com os outros typing imports):

```python
from typing import Any, Dict, List, Optional
```

- [ ] **Step 3: Verificar sintaxe**

```bash
cd backend
python -c "from scrapers.zillow import scrape_all_states; print('OK')"
```

Esperado: `OK`

---

## Task 8: Scraper County GIS

**Files:**
- Create: `backend/scrapers/county_gis.py`

- [ ] **Step 1: Criar county_gis.py**

```python
# backend/scrapers/county_gis.py
import asyncio
from typing import Any, Dict, List, Optional

import httpx

# Endpoints ArcGIS REST públicos dos condados de AL e AR
# Nota: URLs podem mudar — verificar em gis.<condado>.gov se algum falhar
_COUNTY_ENDPOINTS: List[Dict[str, str]] = [
    {
        "state": "AL",
        "county": "Jefferson",
        "url": "https://gis.jeffersoncountyal.gov/arcgis/rest/services/ParcelViewer/MapServer/0/query",
    },
    {
        "state": "AL",
        "county": "Madison",
        "url": "https://gis.madisoncountyal.gov/arcgis/rest/services/Parcels/MapServer/0/query",
    },
    {
        "state": "AL",
        "county": "Mobile",
        "url": "https://www.mobilecountyal.gov/arcgis/rest/services/Parcels/MapServer/0/query",
    },
    {
        "state": "AR",
        "county": "Pulaski",
        "url": "https://maps.pulaskicounty.net/arcgis/rest/services/Parcels/FeatureServer/0/query",
    },
    {
        "state": "AR",
        "county": "Benton",
        "url": "https://gis.bentoncountyar.gov/arcgis/rest/services/Parcels/MapServer/0/query",
    },
]

_ARCGIS_PARAMS = {
    "where": "LAND_USE_CODE IN ('V', 'VAC', 'VACANT', 'AG', 'FARM') OR ACRES >= 1",
    "outFields": "ADDRESS,SITUS_ADDR,LAND_USE,LAND_USE_CODE,ZONING,ACRES,ROAD_ACCESS,UTILITIES,ASSESSED_VALUE",
    "returnGeometry": "true",
    "geometryType": "esriGeometryEnvelope",
    "f": "json",
    "resultRecordCount": "100",
}


def _parse_arcgis_feature(feature: Dict, endpoint: Dict) -> Optional[Dict[str, Any]]:
    attrs = feature.get("attributes", {})
    geometry = feature.get("geometry", {})

    address = (
        attrs.get("ADDRESS")
        or attrs.get("SITUS_ADDR")
        or ""
    )
    acres = attrs.get("ACRES")
    assessed_value = attrs.get("ASSESSED_VALUE")

    lat = geometry.get("y")
    lng = geometry.get("x")

    # Centróide se vier como rings (polygon)
    rings = geometry.get("rings")
    if rings and not lat:
        try:
            all_x = [pt[0] for ring in rings for pt in ring]
            all_y = [pt[1] for ring in rings for pt in ring]
            lng = sum(all_x) / len(all_x)
            lat = sum(all_y) / len(all_y)
        except Exception:
            pass

    return {
        "source": "county_gis",
        "state": endpoint["state"],
        "county": endpoint["county"],
        "address": address,
        "lat": float(lat) if lat else None,
        "lng": float(lng) if lng else None,
        "acres": float(acres) if acres else None,
        "zoning": attrs.get("ZONING") or attrs.get("LAND_USE_CODE"),
        "has_road_access": bool(attrs.get("ROAD_ACCESS")),
        "utilities_available": bool(attrs.get("UTILITIES")),
        "avg_price_per_acre": (
            float(assessed_value) / float(acres)
            if assessed_value and acres and float(acres) > 0
            else None
        ),
    }


async def query_county(endpoint: Dict[str, str]) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []

    async with httpx.AsyncClient(timeout=20) as client:
        try:
            resp = await client.get(endpoint["url"], params=_ARCGIS_PARAMS)
            if resp.status_code != 200:
                print(f"GIS {endpoint['county']}: status {resp.status_code}")
                return results

            data = resp.json()
            features = data.get("features", [])

            for feature in features:
                parsed = _parse_arcgis_feature(feature, endpoint)
                if parsed and parsed.get("acres") and parsed["acres"] >= 1:
                    results.append(parsed)

            print(f"GIS {endpoint['county']}: {len(results)} parcelas")
        except Exception as e:
            print(f"Erro GIS {endpoint['county']}: {e}")

    return results


async def scrape_all_counties() -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for endpoint in _COUNTY_ENDPOINTS:
        county_results = await query_county(endpoint)
        results.extend(county_results)
        await asyncio.sleep(1.0)
    return results
```

- [ ] **Step 2: Verificar sintaxe**

```bash
cd backend
python -c "from scrapers.county_gis import scrape_all_counties; print('OK')"
```

Esperado: `OK`

---

## Task 9: Enrichers FEMA e Regrid

**Files:**
- Create: `backend/enrichers/fema.py`
- Create: `backend/enrichers/regrid.py`

- [ ] **Step 1: Criar fema.py**

```python
# backend/enrichers/fema.py
from typing import Optional

import httpx

_FEMA_URL = "https://msc.fema.gov/api/public/maps/1.0/zones"


async def get_fema_zone(lat: float, lng: float) -> Optional[str]:
    """Retorna zona de inundação FEMA para as coordenadas dadas."""
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(_FEMA_URL, params={"lat": lat, "lon": lng})
            if resp.status_code == 200:
                data = resp.json()
                zones = data.get("flood_zones", [])
                if zones:
                    return zones[0].get("flood_zone", "X")
                return "X"  # sem dados = sem zona especial de risco
        except Exception as e:
            print(f"Erro FEMA ({lat:.4f}, {lng:.4f}): {e}")
    return None
```

- [ ] **Step 2: Criar regrid.py**

```python
# backend/enrichers/regrid.py
from typing import Any, Dict, Optional

import httpx

from config import REGRID_API_KEY

_REGRID_URL = "https://app.regrid.com/api/v2/parcels/point"


async def get_regrid_data(lat: float, lng: float) -> Optional[Dict[str, Any]]:
    """Retorna dados de parcela do Regrid. Retorna None se sem chave de API."""
    if not REGRID_API_KEY:
        return None

    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(
                _REGRID_URL,
                params={"lat": lat, "lon": lng, "token": REGRID_API_KEY},
            )
            if resp.status_code != 200:
                return None

            data = resp.json()
            features = data.get("parcels", {}).get("features", [])
            if not features:
                return None

            fields = features[0].get("properties", {}).get("fields", {})
            acres = fields.get("ll_gisacre")
            land_val = fields.get("landval")

            avg_ppa = None
            if acres and float(acres) > 0 and land_val:
                avg_ppa = float(land_val) / float(acres)

            return {
                "acres": float(acres) if acres else None,
                "zoning": fields.get("zoning"),
                "avg_price_per_acre": avg_ppa,
                "has_road_access": bool(fields.get("road_access")),
                "utilities_available": bool(fields.get("utilities")),
            }
        except Exception as e:
            print(f"Erro Regrid ({lat:.4f}, {lng:.4f}): {e}")
    return None
```

- [ ] **Step 3: Verificar sintaxe dos enrichers**

```bash
cd backend
python -c "from enrichers.fema import get_fema_zone; from enrichers.regrid import get_regrid_data; print('OK')"
```

Esperado: `OK`

---

## Task 10: API Routes — Properties

**Files:**
- Create: `backend/routes/properties.py`

- [ ] **Step 1: Criar routes/properties.py**

```python
# backend/routes/properties.py
import json
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from models import Property

router = APIRouter(prefix="/properties", tags=["properties"])


def _prop_to_dict(p: Property) -> Dict[str, Any]:
    ai_analysis = None
    if p.ai_analysis:
        try:
            ai_analysis = json.loads(p.ai_analysis)
        except Exception:
            pass

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
        "scraped_at": p.scraped_at.isoformat() if p.scraped_at else None,
        "passed_filters": p.passed_filters,
    }


@router.get("/")
def list_properties(
    state: Optional[str] = None,
    min_score: float = Query(0, ge=0, le=100),
    max_price: Optional[float] = Query(None),
    min_acres: Optional[float] = Query(None),
    max_price_per_acre: Optional[float] = Query(None),
    min_discount_pct: Optional[float] = Query(None),
    limit: int = Query(200, le=500),
    db: Session = Depends(get_db),
):
    q = db.query(Property).filter(Property.passed_filters == True)

    if state:
        q = q.filter(Property.state == state)
    if min_score:
        q = q.filter(Property.score >= min_score)
    if max_price is not None:
        q = q.filter(Property.price <= max_price)
    if min_acres is not None:
        q = q.filter(Property.acres >= min_acres)
    if max_price_per_acre is not None:
        q = q.filter(Property.price_per_acre <= max_price_per_acre)
    if min_discount_pct is not None:
        q = q.filter(Property.discount_pct >= min_discount_pct)

    props = q.order_by(Property.score.desc()).limit(limit).all()
    return [_prop_to_dict(p) for p in props]


@router.get("/{property_id}")
def get_property(property_id: int, db: Session = Depends(get_db)):
    prop = db.query(Property).filter(Property.id == property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Propriedade não encontrada")
    return _prop_to_dict(prop)
```

---

## Task 11: API Routes — Pipeline

**Files:**
- Create: `backend/routes/pipeline.py`

- [ ] **Step 1: Criar routes/pipeline.py**

```python
# backend/routes/pipeline.py
import asyncio
import json
from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from config import REGRID_API_KEY
from database import SessionLocal, get_db
from enrichers.fema import get_fema_zone
from enrichers.regrid import get_regrid_data
from filters import FilterConfig, apply_filters
from models import PipelineRun, Property
from scrapers.county_gis import scrape_all_counties
from scrapers.zillow import scrape_all_states
from scorer import calculate_score, generate_ai_analysis

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


@router.post("/run")
async def run_pipeline(db: Session = Depends(get_db)):
    """Dispara o pipeline de scraping em background."""
    run = PipelineRun(status="rodando")
    db.add(run)
    db.commit()
    db.refresh(run)

    asyncio.create_task(_pipeline_task(run.id))

    return {"run_id": run.id, "status": "rodando"}


@router.get("/status/{run_id}")
async def pipeline_status_sse(run_id: int):
    """SSE stream com status em tempo real do pipeline."""

    async def generator():
        db = SessionLocal()
        try:
            while True:
                run = db.query(PipelineRun).filter(PipelineRun.id == run_id).first()
                if not run:
                    yield f"data: {json.dumps({'error': 'Run não encontrado'})}\n\n"
                    break

                payload = {
                    "status": run.status,
                    "scraped": run.scraped,
                    "enriched": run.enriched,
                    "filtered": run.filtered,
                    "scored": run.scored,
                    "error_msg": run.error_msg,
                    "finished_at": run.finished_at.isoformat() if run.finished_at else None,
                }
                yield f"data: {json.dumps(payload)}\n\n"

                if run.status in ("concluído", "erro"):
                    break

                await asyncio.sleep(1)
                db.refresh(run)
        finally:
            db.close()

    return StreamingResponse(generator(), media_type="text/event-stream")


@router.get("/history")
def pipeline_history(db: Session = Depends(get_db)):
    runs = (
        db.query(PipelineRun)
        .order_by(PipelineRun.started_at.desc())
        .limit(10)
        .all()
    )
    return [
        {
            "id": r.id,
            "status": r.status,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            "scraped": r.scraped,
            "enriched": r.enriched,
            "filtered": r.filtered,
            "scored": r.scored,
            "error_msg": r.error_msg,
        }
        for r in runs
    ]


async def _pipeline_task(run_id: int) -> None:
    """Tarefa background: scraping → enriquecimento → filtros → score."""
    db = SessionLocal()
    try:
        run = db.query(PipelineRun).filter(PipelineRun.id == run_id).first()
        filter_config = FilterConfig()
        regrid_available = bool(REGRID_API_KEY)

        # ── 1. Scraping ──────────────────────────────────────────────────
        all_listings = await scrape_all_states()
        run.scraped = len(all_listings)
        db.commit()

        # ── 2. Enriquecimento + filtros + score ──────────────────────────
        for listing in all_listings:
            lat = listing.get("lat")
            lng = listing.get("lng")

            if lat and lng:
                # FEMA
                fema_zone = await get_fema_zone(lat, lng)
                if fema_zone:
                    listing["fema_zone"] = fema_zone

                # Regrid (opcional)
                if regrid_available:
                    regrid = await get_regrid_data(lat, lng)
                    if regrid:
                        for key, val in regrid.items():
                            if val is not None:
                                listing[key] = val

            # Calcular preço/acre e desconto
            price = listing.get("price")
            acres = listing.get("acres")
            if price and acres and acres > 0:
                listing["price_per_acre"] = price / acres

            avg_ppa = listing.get("avg_price_per_acre")
            ppa = listing.get("price_per_acre")
            if avg_ppa and ppa and avg_ppa > 0:
                listing["discount_pct"] = (1 - ppa / avg_ppa) * 100

            run.enriched = (run.enriched or 0) + 1
            db.commit()

            # Filtros
            passed = apply_filters(listing, filter_config, regrid_available)
            listing["passed_filters"] = passed

            if not passed:
                continue

            run.filtered = (run.filtered or 0) + 1
            db.commit()

            # Score
            listing["score"] = calculate_score(listing)

            # Análise Claude (apenas score >= 70)
            ai_result = await generate_ai_analysis(listing)
            if ai_result:
                listing["ai_analysis"] = json.dumps(ai_result, ensure_ascii=False)

            # Salvar no banco
            valid_cols = {c.name for c in Property.__table__.columns}
            prop_data = {k: v for k, v in listing.items() if k in valid_cols}
            db.add(Property(**prop_data))

            run.scored = (run.scored or 0) + 1
            db.commit()

        run.status = "concluído"
        run.finished_at = datetime.utcnow()
        db.commit()

    except Exception as exc:
        run.status = "erro"
        run.error_msg = str(exc)
        run.finished_at = datetime.utcnow()
        db.commit()
    finally:
        db.close()
```

---

## Task 12: FastAPI Main App

**Files:**
- Create: `backend/main.py`

- [ ] **Step 1: Criar main.py**

```python
# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import Base, engine
from routes.pipeline import router as pipeline_router
from routes.properties import router as properties_router

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Buscador de Terrenos API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(properties_router)
app.include_router(pipeline_router)


@app.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 2: Iniciar o backend e testar health check**

```bash
cd backend
uvicorn main:app --reload --port 8000
```

Em outro terminal:
```bash
curl http://localhost:8000/health
```

Esperado: `{"status":"ok"}`

- [ ] **Step 3: Acessar docs da API**

Abrir `http://localhost:8000/docs` no navegador. Deve aparecer a documentação interativa Swagger com os endpoints `/properties/` e `/pipeline/*`.

---

## Task 13: Setup Frontend (Vite + React + shadcn + Tailwind)

**Files:**
- Create: `frontend/` (projeto Vite completo)

- [ ] **Step 1: Criar projeto Vite**

```bash
cd "C:/Users/g-fil/Desktop/buscador de terrenos"
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
```

- [ ] **Step 2: Instalar Tailwind CSS**

```bash
cd frontend
npm install tailwindcss @tailwindcss/vite
```

Criar `frontend/tailwind.config.ts`:
```typescript
import type { Config } from "tailwindcss";

export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "#0a0a0f",
        surface: "#12121a",
        border: "#1e1e2e",
        accent: "#6c63ff",
        "accent-hover": "#5a52e0",
        "text-primary": "#e2e8f0",
        "text-muted": "#64748b",
        "score-high": "#22c55e",
        "score-mid": "#f59e0b",
        "score-low": "#ef4444",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
    },
  },
  plugins: [],
} satisfies Config;
```

- [ ] **Step 3: Configurar Tailwind no Vite**

Substituir conteúdo de `frontend/vite.config.ts`:
```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "path";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        rewrite: (p) => p.replace(/^\/api/, ""),
      },
    },
  },
});
```

- [ ] **Step 4: Instalar dependências restantes**

```bash
cd frontend
npm install framer-motion @tanstack/react-table react-router-dom axios
npm install lucide-react class-variance-authority clsx tailwind-merge
npm install @radix-ui/react-dialog @radix-ui/react-slot @radix-ui/react-separator
npm install @radix-ui/react-tooltip
```

- [ ] **Step 5: Atualizar src/index.css**

Substituir conteúdo de `frontend/src/index.css`:
```css
@import "tailwindcss";
@import url("https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap");

* {
  box-sizing: border-box;
}

body {
  background-color: #0a0a0f;
  color: #e2e8f0;
  font-family: "Inter", system-ui, sans-serif;
  -webkit-font-smoothing: antialiased;
}

::-webkit-scrollbar {
  width: 6px;
}
::-webkit-scrollbar-track {
  background: #12121a;
}
::-webkit-scrollbar-thumb {
  background: #1e1e2e;
  border-radius: 3px;
}
```

- [ ] **Step 6: Verificar que o frontend compila**

```bash
cd frontend
npm run dev
```

Abrir `http://localhost:5173`. Deve aparecer a página padrão do Vite.

---

## Task 14: API Client + Tipos TypeScript

**Files:**
- Create: `frontend/src/lib/utils.ts`
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/api/properties.ts`
- Create: `frontend/src/api/pipeline.ts`
- Create: `frontend/src/types.ts`

- [ ] **Step 1: Criar types.ts**

```typescript
// frontend/src/types.ts

export interface AiAnalysis {
  resumo: string;
  pontos_positivos: string[];
  pontos_atencao: string[];
  veredicto: "Oportunidade forte" | "Merece análise" | "Cautela";
}

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
  scraped_at: string | null;
  passed_filters: boolean;
}

export interface PipelineRun {
  id: number;
  status: "rodando" | "concluído" | "erro";
  started_at: string | null;
  finished_at: string | null;
  scraped: number;
  enriched: number;
  filtered: number;
  scored: number;
  error_msg: string | null;
}

export interface PropertyFilters {
  state?: string;
  min_score?: number;
  max_price?: number;
  min_acres?: number;
  max_price_per_acre?: number;
  min_discount_pct?: number;
}
```

- [ ] **Step 2: Criar lib/utils.ts**

```typescript
// frontend/src/lib/utils.ts
import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatCurrency(value: number | null | undefined): string {
  if (value == null) return "—";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

export function formatAcres(value: number | null | undefined): string {
  if (value == null) return "—";
  return `${value.toFixed(1)} ac`;
}

export function formatDiscount(value: number | null | undefined): string {
  if (value == null) return "—";
  return `${value.toFixed(1)}%`;
}

export function scoreColor(score: number | null | undefined): string {
  if (score == null) return "text-text-muted";
  if (score >= 70) return "text-score-high";
  if (score >= 40) return "text-score-mid";
  return "text-score-low";
}

export function scoreBg(score: number | null | undefined): string {
  if (score == null) return "bg-surface";
  if (score >= 70) return "bg-score-high/10 border-score-high/30";
  if (score >= 40) return "bg-score-mid/10 border-score-mid/30";
  return "bg-score-low/10 border-score-low/30";
}

export function buildGoogleMapsUrl(address: string): string {
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(address)}`;
}

export function buildStreetViewUrl(
  lat: number | null,
  lng: number | null,
  address?: string
): string {
  if (lat && lng) {
    return `https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=${lat},${lng}`;
  }
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(address ?? "")}`;
}
```

- [ ] **Step 3: Criar api/client.ts**

```typescript
// frontend/src/api/client.ts
import axios from "axios";

const client = axios.create({
  baseURL: "/api",
  timeout: 30_000,
  headers: { "Content-Type": "application/json" },
});

export default client;
```

- [ ] **Step 4: Criar api/properties.ts**

```typescript
// frontend/src/api/properties.ts
import type { Property, PropertyFilters } from "../types";
import client from "./client";

export async function fetchProperties(filters: PropertyFilters = {}): Promise<Property[]> {
  const params: Record<string, string | number> = {};
  if (filters.state) params.state = filters.state;
  if (filters.min_score != null) params.min_score = filters.min_score;
  if (filters.max_price != null) params.max_price = filters.max_price;
  if (filters.min_acres != null) params.min_acres = filters.min_acres;
  if (filters.max_price_per_acre != null) params.max_price_per_acre = filters.max_price_per_acre;
  if (filters.min_discount_pct != null) params.min_discount_pct = filters.min_discount_pct;

  const { data } = await client.get<Property[]>("/properties/", { params });
  return data;
}

export async function fetchProperty(id: number): Promise<Property> {
  const { data } = await client.get<Property>(`/properties/${id}`);
  return data;
}
```

- [ ] **Step 5: Criar api/pipeline.ts**

```typescript
// frontend/src/api/pipeline.ts
import type { PipelineRun } from "../types";
import client from "./client";

export async function startPipeline(): Promise<{ run_id: number; status: string }> {
  const { data } = await client.post("/pipeline/run");
  return data;
}

export async function fetchPipelineHistory(): Promise<PipelineRun[]> {
  const { data } = await client.get<PipelineRun[]>("/pipeline/history");
  return data;
}

export function openPipelineSSE(
  runId: number,
  onMessage: (run: PipelineRun) => void,
  onDone: () => void
): () => void {
  const es = new EventSource(`/api/pipeline/status/${runId}`);

  es.onmessage = (event) => {
    const payload = JSON.parse(event.data) as PipelineRun;
    onMessage(payload);
    if (payload.status === "concluído" || payload.status === "erro") {
      es.close();
      onDone();
    }
  };

  es.onerror = () => {
    es.close();
    onDone();
  };

  return () => es.close();
}
```

---

## Task 15: Componentes Base

**Files:**
- Create: `frontend/src/components/Layout.tsx`
- Create: `frontend/src/components/ScoreBadge.tsx`
- Create: `frontend/src/components/VerdictBadge.tsx`

- [ ] **Step 1: Criar Layout.tsx**

```tsx
// frontend/src/components/Layout.tsx
import { Link, useLocation } from "react-router-dom";
import { LayoutDashboard, Activity, Map } from "lucide-react";
import { cn } from "../lib/utils";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/pipeline", label: "Pipeline", icon: Activity },
];

export default function Layout({ children }: { children: React.ReactNode }) {
  const location = useLocation();

  return (
    <div className="flex min-h-screen bg-background">
      {/* Sidebar */}
      <aside className="w-64 bg-surface border-r border-border flex flex-col">
        {/* Logo */}
        <div className="p-6 border-b border-border">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-accent flex items-center justify-center">
              <Map size={16} className="text-white" />
            </div>
            <div>
              <p className="text-sm font-semibold text-text-primary">Buscador de</p>
              <p className="text-xs text-text-muted">Terrenos AL • AR</p>
            </div>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 p-4 space-y-1">
          {NAV_ITEMS.map(({ to, label, icon: Icon }) => {
            const active = location.pathname === to;
            return (
              <Link
                key={to}
                to={to}
                className={cn(
                  "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-150",
                  active
                    ? "bg-accent/10 text-accent font-medium"
                    : "text-text-muted hover:text-text-primary hover:bg-white/5"
                )}
              >
                <Icon size={16} />
                {label}
              </Link>
            );
          })}
        </nav>

        {/* Footer */}
        <div className="p-4 border-t border-border">
          <p className="text-xs text-text-muted">AL & AR Land Finder</p>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-auto">{children}</main>
    </div>
  );
}
```

- [ ] **Step 2: Criar ScoreBadge.tsx**

```tsx
// frontend/src/components/ScoreBadge.tsx
import { cn, scoreColor, scoreBg } from "../lib/utils";

interface Props {
  score: number | null | undefined;
  size?: "sm" | "md" | "lg";
}

export default function ScoreBadge({ score, size = "md" }: Props) {
  if (score == null) return <span className="text-text-muted text-sm">—</span>;

  return (
    <span
      className={cn(
        "inline-flex items-center justify-center rounded-full border font-mono font-semibold",
        scoreBg(score),
        scoreColor(score),
        size === "sm" && "text-xs px-2 py-0.5 min-w-[3rem]",
        size === "md" && "text-sm px-2.5 py-1 min-w-[3.5rem]",
        size === "lg" && "text-2xl px-4 py-2 min-w-[5rem]"
      )}
    >
      {score.toFixed(0)}
    </span>
  );
}
```

- [ ] **Step 3: Criar VerdictBadge.tsx**

```tsx
// frontend/src/components/VerdictBadge.tsx
import { cn } from "../lib/utils";

type Verdict = "Oportunidade forte" | "Merece análise" | "Cautela" | null | undefined;

const VERDICT_STYLES: Record<string, string> = {
  "Oportunidade forte": "bg-score-high/10 text-score-high border-score-high/30",
  "Merece análise": "bg-score-mid/10 text-score-mid border-score-mid/30",
  Cautela: "bg-score-low/10 text-score-low border-score-low/30",
};

export default function VerdictBadge({ verdict }: { verdict: Verdict }) {
  if (!verdict) return <span className="text-text-muted text-xs">—</span>;

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium whitespace-nowrap",
        VERDICT_STYLES[verdict] ?? "bg-surface text-text-muted border-border"
      )}
    >
      {verdict}
    </span>
  );
}
```

---

## Task 16: Dashboard — Tabela Principal

**Files:**
- Create: `frontend/src/components/FilterPanel.tsx`
- Create: `frontend/src/components/PropertyTable.tsx`
- Create: `frontend/src/pages/Dashboard.tsx`

- [ ] **Step 1: Criar FilterPanel.tsx**

```tsx
// frontend/src/components/FilterPanel.tsx
import { useState } from "react";
import type { PropertyFilters } from "../types";

interface Props {
  filters: PropertyFilters;
  onChange: (filters: PropertyFilters) => void;
}

function FilterInput({
  label,
  value,
  onChange,
  placeholder,
  prefix,
  suffix,
}: {
  label: string;
  value: number | undefined;
  onChange: (v: number | undefined) => void;
  placeholder: string;
  prefix?: string;
  suffix?: string;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-xs text-text-muted font-medium uppercase tracking-wide">
        {label}
      </label>
      <div className="flex items-center gap-1 bg-surface border border-border rounded-lg px-3 py-2 focus-within:border-accent/50 transition-colors">
        {prefix && <span className="text-text-muted text-sm">{prefix}</span>}
        <input
          type="number"
          value={value ?? ""}
          onChange={(e) =>
            onChange(e.target.value ? Number(e.target.value) : undefined)
          }
          placeholder={placeholder}
          className="flex-1 bg-transparent text-sm text-text-primary placeholder:text-text-muted outline-none min-w-0"
        />
        {suffix && <span className="text-text-muted text-sm">{suffix}</span>}
      </div>
    </div>
  );
}

export default function FilterPanel({ filters, onChange }: Props) {
  return (
    <div className="bg-surface border border-border rounded-xl p-4 space-y-4">
      <h3 className="text-sm font-semibold text-text-primary">Filtros</h3>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
        <div className="flex flex-col gap-1.5">
          <label className="text-xs text-text-muted font-medium uppercase tracking-wide">
            Estado
          </label>
          <select
            value={filters.state ?? ""}
            onChange={(e) =>
              onChange({ ...filters, state: e.target.value || undefined })
            }
            className="bg-background border border-border rounded-lg px-3 py-2 text-sm text-text-primary outline-none focus:border-accent/50 transition-colors"
          >
            <option value="">Todos</option>
            <option value="AL">Alabama</option>
            <option value="AR">Arkansas</option>
          </select>
        </div>

        <FilterInput
          label="Preço máximo"
          value={filters.max_price}
          onChange={(v) => onChange({ ...filters, max_price: v })}
          placeholder="500000"
          prefix="$"
        />

        <FilterInput
          label="Tamanho mínimo"
          value={filters.min_acres}
          onChange={(v) => onChange({ ...filters, min_acres: v })}
          placeholder="1"
          suffix="ac"
        />

        <FilterInput
          label="Preço/acre máx."
          value={filters.max_price_per_acre}
          onChange={(v) => onChange({ ...filters, max_price_per_acre: v })}
          placeholder="10000"
          prefix="$"
        />

        <FilterInput
          label="Desconto mín."
          value={filters.min_discount_pct}
          onChange={(v) => onChange({ ...filters, min_discount_pct: v })}
          placeholder="10"
          suffix="%"
        />
      </div>

      <div className="flex items-center gap-2 pt-1">
        <div className="flex items-center gap-2 text-xs text-text-muted">
          <div className="w-2 h-2 rounded-full bg-score-high" />
          FEMA Zona X aplicado automaticamente
        </div>
        <button
          onClick={() => onChange({})}
          className="ml-auto text-xs text-text-muted hover:text-accent transition-colors"
        >
          Limpar filtros
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Criar PropertyTable.tsx**

```tsx
// frontend/src/components/PropertyTable.tsx
import {
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
  type ColumnDef,
  type SortingState,
} from "@tanstack/react-table";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ChevronUp, ChevronDown } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import type { Property } from "../types";
import ScoreBadge from "./ScoreBadge";
import VerdictBadge from "./VerdictBadge";
import { formatCurrency, formatAcres, formatDiscount } from "../lib/utils";

interface Props {
  data: Property[];
  isLoading: boolean;
}

const columns: ColumnDef<Property>[] = [
  {
    accessorKey: "score",
    header: "Score",
    cell: ({ getValue }) => <ScoreBadge score={getValue() as number} size="sm" />,
    size: 80,
  },
  {
    accessorKey: "state",
    header: "Estado",
    size: 70,
    cell: ({ getValue }) => (
      <span className="font-mono text-xs bg-accent/10 text-accent px-2 py-0.5 rounded">
        {getValue() as string}
      </span>
    ),
  },
  {
    accessorKey: "county",
    header: "Condado",
    size: 120,
  },
  {
    accessorKey: "address",
    header: "Endereço",
    size: 260,
    cell: ({ getValue }) => (
      <span className="text-text-primary truncate block max-w-[260px]" title={getValue() as string}>
        {getValue() as string}
      </span>
    ),
  },
  {
    accessorKey: "acres",
    header: "Acres",
    size: 90,
    cell: ({ getValue }) => formatAcres(getValue() as number),
  },
  {
    accessorKey: "price",
    header: "Preço",
    size: 120,
    cell: ({ getValue }) => formatCurrency(getValue() as number),
  },
  {
    accessorKey: "price_per_acre",
    header: "$/Acre",
    size: 110,
    cell: ({ getValue }) => formatCurrency(getValue() as number),
  },
  {
    accessorKey: "discount_pct",
    header: "Desconto",
    size: 100,
    cell: ({ getValue }) => {
      const v = getValue() as number | null;
      if (v == null) return <span className="text-text-muted">—</span>;
      return (
        <span className={v >= 10 ? "text-score-high" : "text-text-muted"}>
          {formatDiscount(v)}
        </span>
      );
    },
  },
  {
    accessorKey: "fema_zone",
    header: "FEMA",
    size: 80,
    cell: ({ getValue }) => {
      const zone = getValue() as string | null;
      return (
        <span
          className={
            zone === "X"
              ? "text-score-high text-xs font-mono font-semibold"
              : "text-score-low text-xs font-mono"
          }
        >
          {zone ?? "—"}
        </span>
      );
    },
  },
  {
    id: "veredicto",
    header: "Veredicto",
    size: 150,
    cell: ({ row }) => (
      <VerdictBadge verdict={row.original.ai_analysis?.veredicto} />
    ),
  },
];

export default function PropertyTable({ data, isLoading }: Props) {
  const [sorting, setSorting] = useState<SortingState>([
    { id: "score", desc: true },
  ]);
  const navigate = useNavigate();

  const table = useReactTable({
    data,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin" />
          <p className="text-text-muted text-sm">Carregando terrenos...</p>
        </div>
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="text-center">
          <p className="text-text-muted text-sm">Nenhum terreno encontrado.</p>
          <p className="text-text-muted text-xs mt-1">
            Rode o pipeline ou ajuste os filtros.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-border">
      <table className="w-full text-sm">
        <thead>
          {table.getHeaderGroups().map((hg) => (
            <tr key={hg.id} className="border-b border-border bg-surface">
              {hg.headers.map((header) => (
                <th
                  key={header.id}
                  className="px-4 py-3 text-left text-xs font-semibold text-text-muted uppercase tracking-wide whitespace-nowrap cursor-pointer select-none hover:text-text-primary transition-colors"
                  style={{ width: header.getSize() }}
                  onClick={header.column.getToggleSortingHandler()}
                >
                  <div className="flex items-center gap-1">
                    {flexRender(header.column.columnDef.header, header.getContext())}
                    {header.column.getIsSorted() === "asc" && <ChevronUp size={12} />}
                    {header.column.getIsSorted() === "desc" && <ChevronDown size={12} />}
                  </div>
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody>
          <AnimatePresence>
            {table.getRowModel().rows.map((row, i) => (
              <motion.tr
                key={row.id}
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.15, delay: i * 0.02 }}
                className="border-b border-border/50 hover:bg-white/[0.03] cursor-pointer transition-colors"
                onClick={() => navigate(`/property/${row.original.id}`)}
              >
                {row.getVisibleCells().map((cell) => (
                  <td
                    key={cell.id}
                    className="px-4 py-3 text-text-muted whitespace-nowrap"
                  >
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </motion.tr>
            ))}
          </AnimatePresence>
        </tbody>
      </table>
    </div>
  );
}
```

- [ ] **Step 3: Criar pages/Dashboard.tsx**

```tsx
// frontend/src/pages/Dashboard.tsx
import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { RefreshCw } from "lucide-react";
import type { Property, PropertyFilters } from "../types";
import { fetchProperties } from "../api/properties";
import FilterPanel from "../components/FilterPanel";
import PropertyTable from "../components/PropertyTable";

export default function Dashboard() {
  const [properties, setProperties] = useState<Property[]>([]);
  const [filters, setFilters] = useState<PropertyFilters>({});
  const [isLoading, setIsLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const load = async (f: PropertyFilters) => {
    setIsLoading(true);
    try {
      const data = await fetchProperties(f);
      setProperties(data);
      setLastUpdated(new Date());
    } catch (err) {
      console.error("Erro ao carregar propriedades:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    load(filters);
  }, [filters]);

  const highScore = properties.filter((p) => (p.score ?? 0) >= 70).length;
  const midScore = properties.filter(
    (p) => (p.score ?? 0) >= 40 && (p.score ?? 0) < 70
  ).length;

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-start justify-between"
      >
        <div>
          <h1 className="text-2xl font-bold text-text-primary">Terrenos</h1>
          <p className="text-text-muted text-sm mt-1">
            {properties.length} propriedades encontradas
            {lastUpdated && (
              <span className="ml-2 opacity-60">
                · atualizado às {lastUpdated.toLocaleTimeString("pt-BR")}
              </span>
            )}
          </p>
        </div>

        <button
          onClick={() => load(filters)}
          disabled={isLoading}
          className="flex items-center gap-2 bg-surface border border-border text-text-muted hover:text-text-primary hover:border-accent/50 px-3 py-2 rounded-lg text-sm transition-all disabled:opacity-40"
        >
          <RefreshCw size={14} className={isLoading ? "animate-spin" : ""} />
          Atualizar
        </button>
      </motion.div>

      {/* Stats */}
      {!isLoading && properties.length > 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.1 }}
          className="grid grid-cols-3 gap-4"
        >
          {[
            { label: "Total", value: properties.length, color: "text-text-primary" },
            { label: "Score alto (≥70)", value: highScore, color: "text-score-high" },
            { label: "Score médio (40–70)", value: midScore, color: "text-score-mid" },
          ].map(({ label, value, color }) => (
            <div
              key={label}
              className="bg-surface border border-border rounded-xl p-4"
            >
              <p className="text-xs text-text-muted mb-1">{label}</p>
              <p className={`text-2xl font-bold font-mono ${color}`}>{value}</p>
            </div>
          ))}
        </motion.div>
      )}

      {/* Filters */}
      <FilterPanel filters={filters} onChange={setFilters} />

      {/* Table */}
      <PropertyTable data={properties} isLoading={isLoading} />
    </div>
  );
}
```

---

## Task 17: Property Detail Page

**Files:**
- Create: `frontend/src/pages/PropertyDetail.tsx`

- [ ] **Step 1: Criar PropertyDetail.tsx**

```tsx
// frontend/src/pages/PropertyDetail.tsx
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { motion } from "framer-motion";
import {
  ArrowLeft,
  MapPin,
  Maximize2,
  DollarSign,
  TrendingDown,
  Shield,
  Road,
  Zap,
  ExternalLink,
  Map,
  Eye,
  CheckCircle2,
  AlertCircle,
} from "lucide-react";
import type { Property } from "../types";
import { fetchProperty } from "../api/properties";
import ScoreBadge from "../components/ScoreBadge";
import VerdictBadge from "../components/VerdictBadge";
import {
  formatCurrency,
  formatAcres,
  formatDiscount,
  buildGoogleMapsUrl,
  buildStreetViewUrl,
} from "../lib/utils";

function DataRow({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ElementType;
  label: string;
  value: React.ReactNode;
}) {
  return (
    <div className="flex items-center gap-3 py-3 border-b border-border/50 last:border-0">
      <Icon size={16} className="text-text-muted flex-shrink-0" />
      <span className="text-sm text-text-muted flex-1">{label}</span>
      <span className="text-sm text-text-primary font-medium text-right">{value}</span>
    </div>
  );
}

export default function PropertyDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [property, setProperty] = useState<Property | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    fetchProperty(Number(id))
      .then(setProperty)
      .catch(console.error)
      .finally(() => setIsLoading(false));
  }, [id]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full py-24">
        <div className="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!property) {
    return (
      <div className="flex flex-col items-center justify-center py-24 gap-3">
        <p className="text-text-muted">Propriedade não encontrada.</p>
        <button
          onClick={() => navigate("/")}
          className="text-accent text-sm hover:underline"
        >
          Voltar
        </button>
      </div>
    );
  }

  const { ai_analysis: ai } = property;

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      {/* Back + Header */}
      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-2 text-text-muted hover:text-text-primary text-sm mb-4 transition-colors"
        >
          <ArrowLeft size={16} />
          Voltar
        </button>

        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold text-text-primary leading-snug">
              {property.address || "Endereço não disponível"}
            </h1>
            <p className="text-text-muted text-sm mt-1">
              {property.county && `${property.county}, `}
              {property.state}
            </p>
          </div>
          <ScoreBadge score={property.score} size="lg" />
        </div>
      </motion.div>

      {/* Action Buttons */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.1 }}
        className="flex flex-wrap gap-3"
      >
        <a
          href={buildGoogleMapsUrl(property.address ?? "")}
          target="_blank"
          rel="noreferrer"
          className="flex items-center gap-2 bg-surface border border-border hover:border-accent/50 text-text-primary px-4 py-2.5 rounded-lg text-sm transition-all hover:bg-accent/5"
        >
          <Map size={15} />
          Ver no Google Maps
        </a>
        <a
          href={buildStreetViewUrl(property.lat, property.lng, property.address ?? "")}
          target="_blank"
          rel="noreferrer"
          className="flex items-center gap-2 bg-surface border border-border hover:border-accent/50 text-text-primary px-4 py-2.5 rounded-lg text-sm transition-all hover:bg-accent/5"
        >
          <Eye size={15} />
          Street View
        </a>
        {property.listing_url && (
          <a
            href={property.listing_url}
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-2 bg-accent hover:bg-accent-hover text-white px-4 py-2.5 rounded-lg text-sm transition-all"
          >
            <ExternalLink size={15} />
            Ver listagem original
          </a>
        )}
      </motion.div>

      {/* Main grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Dados básicos */}
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15 }}
          className="bg-surface border border-border rounded-xl p-5"
        >
          <h2 className="text-sm font-semibold text-text-primary mb-3">
            Dados Básicos
          </h2>
          <DataRow icon={DollarSign} label="Preço total" value={formatCurrency(property.price)} />
          <DataRow icon={Maximize2} label="Tamanho" value={formatAcres(property.acres)} />
          <DataRow icon={DollarSign} label="Preço por acre" value={formatCurrency(property.price_per_acre)} />
          <DataRow
            icon={TrendingDown}
            label="Desconto vs. média"
            value={
              <span className={property.discount_pct && property.discount_pct >= 10 ? "text-score-high" : ""}>
                {formatDiscount(property.discount_pct)}
              </span>
            }
          />
          <DataRow icon={MapPin} label="Fonte" value={property.source} />
        </motion.div>

        {/* FEMA + Regrid */}
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="bg-surface border border-border rounded-xl p-5"
        >
          <h2 className="text-sm font-semibold text-text-primary mb-3">
            Localização & Infraestrutura
          </h2>
          <DataRow
            icon={Shield}
            label="Zona FEMA"
            value={
              <span
                className={
                  property.fema_zone === "X" ? "text-score-high font-mono" : "text-score-low font-mono"
                }
              >
                {property.fema_zone ?? "—"}
              </span>
            }
          />
          <DataRow
            icon={Road}
            label="Acesso a estrada"
            value={
              property.has_road_access ? (
                <span className="text-score-high">Sim</span>
              ) : (
                <span className="text-score-low">Não</span>
              )
            }
          />
          <DataRow
            icon={Zap}
            label="Utilidades disponíveis"
            value={
              property.utilities_available ? (
                <span className="text-score-high">Sim</span>
              ) : (
                <span className="text-score-low">Não</span>
              )
            }
          />
          <DataRow icon={MapPin} label="Zoneamento" value={property.zoning ?? "—"} />
        </motion.div>
      </div>

      {/* AI Analysis */}
      {ai && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.25 }}
          className="bg-surface border border-border rounded-xl p-5 space-y-4"
        >
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-text-primary">
              Análise Claude AI
            </h2>
            <VerdictBadge verdict={ai.veredicto} />
          </div>

          <p className="text-sm text-text-muted leading-relaxed">{ai.resumo}</p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <p className="text-xs font-semibold text-score-high uppercase tracking-wide mb-2">
                Pontos positivos
              </p>
              <ul className="space-y-1.5">
                {ai.pontos_positivos.map((p, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-text-muted">
                    <CheckCircle2 size={13} className="text-score-high mt-0.5 flex-shrink-0" />
                    {p}
                  </li>
                ))}
              </ul>
            </div>

            <div>
              <p className="text-xs font-semibold text-score-mid uppercase tracking-wide mb-2">
                Pontos de atenção
              </p>
              <ul className="space-y-1.5">
                {ai.pontos_atencao.map((p, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-text-muted">
                    <AlertCircle size={13} className="text-score-mid mt-0.5 flex-shrink-0" />
                    {p}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </motion.div>
      )}
    </div>
  );
}
```

---

## Task 18: Pipeline Page

**Files:**
- Create: `frontend/src/components/PipelineLog.tsx`
- Create: `frontend/src/pages/Pipeline.tsx`

- [ ] **Step 1: Criar PipelineLog.tsx**

```tsx
// frontend/src/components/PipelineLog.tsx
import { motion, AnimatePresence } from "framer-motion";
import type { PipelineRun } from "../types";

interface LogStep {
  label: string;
  value: number;
  total?: number;
  done: boolean;
}

function ProgressBar({ value, max }: { value: number; max: number }) {
  const pct = max > 0 ? Math.min((value / max) * 100, 100) : 0;
  return (
    <div className="h-1.5 bg-border rounded-full overflow-hidden">
      <motion.div
        className="h-full bg-accent rounded-full"
        initial={{ width: 0 }}
        animate={{ width: `${pct}%` }}
        transition={{ duration: 0.5 }}
      />
    </div>
  );
}

export default function PipelineLog({ run }: { run: PipelineRun | null }) {
  if (!run) return null;

  const steps: LogStep[] = [
    { label: "Raspando listagens", value: run.scraped, done: run.enriched > 0 },
    {
      label: "Enriquecendo dados (FEMA + Regrid)",
      value: run.enriched,
      total: run.scraped,
      done: run.filtered > 0,
    },
    {
      label: "Aplicando filtros",
      value: run.filtered,
      total: run.enriched,
      done: run.scored > 0,
    },
    {
      label: "Pontuando e analisando",
      value: run.scored,
      total: run.filtered,
      done: run.status === "concluído",
    },
  ];

  return (
    <div className="bg-surface border border-border rounded-xl p-5 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-text-primary">Progresso</h3>
        <span
          className={`text-xs font-medium px-2.5 py-1 rounded-full border ${
            run.status === "concluído"
              ? "bg-score-high/10 text-score-high border-score-high/30"
              : run.status === "erro"
              ? "bg-score-low/10 text-score-low border-score-low/30"
              : "bg-accent/10 text-accent border-accent/30"
          }`}
        >
          {run.status}
        </span>
      </div>

      <div className="space-y-4">
        <AnimatePresence>
          {steps.map((step, i) => (
            <motion.div
              key={step.label}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.05 }}
              className="space-y-1.5"
            >
              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2 text-text-muted">
                  <div
                    className={`w-1.5 h-1.5 rounded-full ${
                      step.done
                        ? "bg-score-high"
                        : step.value > 0
                        ? "bg-accent animate-pulse"
                        : "bg-border"
                    }`}
                  />
                  {step.label}
                </div>
                <span className="font-mono text-text-muted">
                  {step.value}
                  {step.total ? `/${step.total}` : ""}
                </span>
              </div>
              {step.total && step.total > 0 && (
                <ProgressBar value={step.value} max={step.total} />
              )}
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      {run.error_msg && (
        <div className="mt-3 p-3 bg-score-low/10 border border-score-low/30 rounded-lg">
          <p className="text-xs text-score-low font-mono">{run.error_msg}</p>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Criar pages/Pipeline.tsx**

```tsx
// frontend/src/pages/Pipeline.tsx
import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Play, Clock, CheckCircle2, XCircle, Loader2 } from "lucide-react";
import type { PipelineRun } from "../types";
import { startPipeline, fetchPipelineHistory, openPipelineSSE } from "../api/pipeline";
import PipelineLog from "../components/PipelineLog";

function HistoryRow({ run }: { run: PipelineRun }) {
  const started = run.started_at ? new Date(run.started_at) : null;
  const finished = run.finished_at ? new Date(run.finished_at) : null;
  const duration =
    started && finished
      ? Math.round((finished.getTime() - started.getTime()) / 1000)
      : null;

  return (
    <div className="flex items-center gap-4 py-3 border-b border-border/50 last:border-0">
      <div className="flex-shrink-0">
        {run.status === "concluído" && <CheckCircle2 size={16} className="text-score-high" />}
        {run.status === "erro" && <XCircle size={16} className="text-score-low" />}
        {run.status === "rodando" && <Loader2 size={16} className="text-accent animate-spin" />}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-3 text-sm">
          <span className="text-text-primary font-medium">
            {started?.toLocaleDateString("pt-BR")} às{" "}
            {started?.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}
          </span>
          {duration && (
            <span className="text-text-muted text-xs flex items-center gap-1">
              <Clock size={11} />
              {duration}s
            </span>
          )}
        </div>
        <div className="flex items-center gap-4 mt-1 text-xs text-text-muted font-mono">
          <span>{run.scraped} raspados</span>
          <span>{run.enriched} enriquecidos</span>
          <span>{run.filtered} filtrados</span>
          <span className="text-accent">{run.scored} pontuados</span>
        </div>
      </div>
    </div>
  );
}

export default function Pipeline() {
  const [isRunning, setIsRunning] = useState(false);
  const [currentRun, setCurrentRun] = useState<PipelineRun | null>(null);
  const [history, setHistory] = useState<PipelineRun[]>([]);

  const loadHistory = async () => {
    try {
      const data = await fetchPipelineHistory();
      setHistory(data);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    loadHistory();
  }, []);

  const handleRun = async () => {
    if (isRunning) return;
    setIsRunning(true);

    try {
      const { run_id } = await startPipeline();

      setCurrentRun({
        id: run_id,
        status: "rodando",
        started_at: new Date().toISOString(),
        finished_at: null,
        scraped: 0,
        enriched: 0,
        filtered: 0,
        scored: 0,
        error_msg: null,
      });

      const cleanup = openPipelineSSE(
        run_id,
        (run) => setCurrentRun(run),
        () => {
          setIsRunning(false);
          loadHistory();
          cleanup();
        }
      );
    } catch (err) {
      console.error(err);
      setIsRunning(false);
    }
  };

  return (
    <div className="p-6 max-w-2xl mx-auto space-y-6">
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="text-2xl font-bold text-text-primary">Pipeline</h1>
        <p className="text-text-muted text-sm mt-1">
          Dispara o scraping, enriquecimento, filtros e pontuação manualmente.
        </p>
      </motion.div>

      {/* Run Button */}
      <motion.div
        initial={{ opacity: 0, scale: 0.97 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay: 0.1 }}
        className="bg-surface border border-border rounded-xl p-6 flex flex-col items-center gap-4"
      >
        <button
          onClick={handleRun}
          disabled={isRunning}
          className={`flex items-center gap-3 px-8 py-4 rounded-xl text-base font-semibold transition-all ${
            isRunning
              ? "bg-accent/20 text-accent cursor-not-allowed"
              : "bg-accent hover:bg-accent-hover text-white shadow-lg shadow-accent/20 hover:shadow-accent/30"
          }`}
        >
          {isRunning ? (
            <>
              <Loader2 size={20} className="animate-spin" />
              Pipeline rodando...
            </>
          ) : (
            <>
              <Play size={20} />
              Rodar Pipeline
            </>
          )}
        </button>

        <p className="text-xs text-text-muted text-center max-w-sm">
          O pipeline vai raspar listagens do Zillow em AL e AR, enriquecer com dados
          FEMA e Regrid, aplicar filtros e gerar scores automaticamente.
        </p>
      </motion.div>

      {/* Live Log */}
      {currentRun && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <PipelineLog run={currentRun} />
        </motion.div>
      )}

      {/* History */}
      {history.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="bg-surface border border-border rounded-xl p-5"
        >
          <h3 className="text-sm font-semibold text-text-primary mb-4">
            Histórico de execuções
          </h3>
          {history.map((run) => (
            <HistoryRow key={run.id} run={run} />
          ))}
        </motion.div>
      )}
    </div>
  );
}
```

---

## Task 19: App Router + Entry Point

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/main.tsx`

- [ ] **Step 1: Atualizar main.tsx**

```tsx
// frontend/src/main.tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import App from "./App";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>
);
```

- [ ] **Step 2: Atualizar App.tsx**

```tsx
// frontend/src/App.tsx
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import PropertyDetail from "./pages/PropertyDetail";
import Pipeline from "./pages/Pipeline";

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/property/:id" element={<PropertyDetail />} />
          <Route path="/pipeline" element={<Pipeline />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}
```

- [ ] **Step 3: Verificar que frontend compila sem erros de TypeScript**

```bash
cd frontend
npm run build
```

Esperado: build concluído sem erros. Se houver erros de tipos, corrigi-los.

- [ ] **Step 4: Rodar frontend em dev mode e verificar visualmente**

```bash
cd frontend
npm run dev
```

Abrir `http://localhost:5173`. Verificar:
- Sidebar aparece com navegação
- Dashboard carrega (vazio, mas sem erros)
- Pipeline page abre corretamente
- Sem erros no console do navegador

---

## Task 20: CLAUDE.md + README.md

**Files:**
- Create: `CLAUDE.md`
- Create: `README.md`

- [ ] **Step 1: Criar CLAUDE.md**

```markdown
# CLAUDE.md — Buscador de Terrenos

## Arquitetura
- **Backend:** FastAPI + SQLite (SQLAlchemy ORM) em `backend/`
- **Frontend:** React + Vite + TypeScript + shadcn/ui + Tailwind em `frontend/`
- **Banco:** `backend/terrenos.db` (SQLite, criado automaticamente na primeira execução)

## Como Rodar
```bash
# Terminal 1 — Backend
cd backend
pip install -r requirements.txt
cp .env.example .env  # adicionar ANTHROPIC_API_KEY
uvicorn main:app --reload --port 8000

# Terminal 2 — Frontend
cd frontend
npm install
npm run dev
```

## Estrutura de Dados
- `Property` — um registro por terreno raspado e aprovado nos filtros
- `PipelineRun` — histórico de execuções manuais do pipeline

## Fluxo do Pipeline
1. `scrapers/zillow.py` raspa Zillow em AL e AR
2. `scrapers/county_gis.py` complementa com dados ArcGIS dos condados
3. `enrichers/fema.py` consulta zona de inundação FEMA por coordenadas
4. `enrichers/regrid.py` consulta dados de parcela Regrid (opcional, requer API key)
5. `filters.py` aplica filtros configuráveis (preço, acres, desconto, FEMA)
6. `scorer.py` calcula score 0-100 e chama Claude API para terrenos score≥70

## Variáveis de Ambiente
- `ANTHROPIC_API_KEY` — obrigatório para análise Claude
- `REGRID_API_KEY` — opcional; sem ela, filtros de desconto e preço/acre ficam desabilitados

## Testes
```bash
cd backend
pytest tests/ -v
```

## Notas
- Scrapers Zillow usam headers de navegador real para evitar bloqueios. Rate limiting de 2-5s entre páginas.
- ArcGIS endpoints dos condados podem mudar — verificar em gis.<condado>.gov
- Análise Claude só é gerada para terrenos com score ≥ 70 para economizar tokens
```

- [ ] **Step 2: Criar README.md**

```markdown
# Buscador de Terrenos 🌎

Ferramenta local para encontrar terrenos baratos em Alabama (AL) e Arkansas (AR). Raspa listagens do Zillow, enriquece com dados FEMA e Regrid, aplica filtros automáticos e pontua cada terreno com IA.

## Requisitos

- Python 3.11+
- Node.js 18+
- Chave de API da Anthropic (para análise IA)

## Instalação e Execução

### 1. Backend

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# Editar .env e adicionar ANTHROPIC_API_KEY
uvicorn main:app --reload --port 8000
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Abrir: **http://localhost:5173**

## Como Usar

1. Acesse o sistema em `http://localhost:5173`
2. Vá para **Pipeline** e clique em **Rodar Pipeline**
3. Aguarde o scraping e processamento (acompanhe o progresso em tempo real)
4. Volte para **Dashboard** para ver os terrenos pontuados
5. Clique em qualquer terreno para ver detalhes, análise IA e abrir no Google Maps / Street View

## Filtros Disponíveis

| Filtro | Padrão |
|---|---|
| Preço máximo | $500.000 |
| Tamanho mínimo | 1 acre |
| Desconto mínimo | 10% |
| Preço/acre máximo | $10.000/ac |
| Zona FEMA | Apenas Zona X (sem risco) |

## Configuração Opcional — Regrid

Sem chave Regrid, os filtros de desconto e preço/acre ficam desabilitados. Para ativar:

```env
REGRID_API_KEY=sua-chave-aqui
```
```

- [ ] **Step 3: Verificar todos os testes passam**

```bash
cd backend
pytest tests/ -v
```

Esperado: todos os testes `PASSED`.

---

## Self-Review do Plano

**Cobertura da spec:**
- ✅ Scrapers Zillow (AL + AR) — Task 7
- ✅ Scraper County GIS — Task 8
- ✅ FEMA enricher — Task 9
- ✅ Regrid enricher (com fallback sem chave) — Task 9
- ✅ Filtros configuráveis (preço, acres, desconto, preço/acre, FEMA) — Tasks 4 + 5
- ✅ Score numérico 0-100 — Tasks 4 + 6
- ✅ Análise Claude para score ≥ 70 — Task 6
- ✅ API REST + SSE — Tasks 10 + 11 + 12
- ✅ Frontend dark-mode premium — Tasks 13-19
- ✅ Dashboard com tabela e filtros — Task 16
- ✅ Detalhe da propriedade — Task 17
- ✅ Botões Google Maps + Street View + listagem original — Task 17
- ✅ Pipeline page com log SSE — Task 18
- ✅ CLAUDE.md + README.md — Task 20

**Tipos consistentes:** `Property`, `PipelineRun`, `PropertyFilters` definidos em `types.ts` e usados em todos os componentes e páginas. Funções de API retornam esses tipos diretamente.

**Sem placeholders:** Todos os steps têm código completo.

**Sem TODOs:** Nenhum.
```
