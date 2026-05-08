# ============================================================
#  categories.py — Categorias, lojas e classificacao automatica
# ============================================================

# ============================================================
#  CATEGORIAS DISPONIVEIS PARA O ASSINANTE
# ============================================================

CATEGORIES = {
    "beauty": {
        "label_pt": "Maquiagem e Beleza",
        "label_es": "Maquillaje y Belleza",
        "icon":     "lipstick",
        "stores":   ["sephora","ulta","mac","elf","morphe","nyx","fenty","clinique"],
        "keywords": ["makeup","foundation","lipstick","mascara","skincare","serum",
                     "moisturizer","concealer","eyeshadow","blush","sephora","ulta",
                     "beauty","cosmetics","parfum","fragrance","perfume"],
        "commission_avg": 6.0,
    },
    "fashion": {
        "label_pt": "Moda e Roupas",
        "label_es": "Moda y Ropa",
        "icon":     "dress",
        "stores":   ["nordstrom","macys","hm","zara","forever21","fashionnova","gap","express"],
        "keywords": ["dress","blouse","shirt","pants","jeans","jacket","coat","sweater",
                     "clothing","apparel","fashion","nordstrom","macys","zara"],
        "commission_avg": 7.0,
    },
    "shoes": {
        "label_pt": "Tenis e Calcados",
        "label_es": "Tenis y Calzado",
        "icon":     "sneaker",
        "stores":   ["nike","adidas","footlocker","dsw","stevemadden","zappos","reebok","puma"],
        "keywords": ["sneakers","shoes","boots","sandals","heels","nike","adidas",
                     "footlocker","running shoes","athletic shoes","dsw","zappos"],
        "commission_avg": 8.0,
    },
    "fragrance": {
        "label_pt": "Perfume e Fragrancas",
        "label_es": "Perfumes y Fragancias",
        "icon":     "sparkles",
        "stores":   ["fragrancenet","fragrancex","perfumania","scentbird"],
        "keywords": ["perfume","cologne","fragrance","eau de parfum","eau de toilette",
                     "scent","spray","deodorant","body spray"],
        "commission_avg": 9.0,
    },
    "electronics": {
        "label_pt": "Eletronicos",
        "label_es": "Electrónicos",
        "icon":     "device",
        "stores":   ["amazon","bestbuy","ebay","walmart","newegg","bhphotovideo"],
        "keywords": ["phone","laptop","tablet","headphones","speaker","tv","monitor",
                     "keyboard","mouse","charger","cable","smartwatch","earbuds","iphone",
                     "samsung","apple","sony","lg","dell","hp","asus"],
        "commission_avg": 2.5,
    },
    "home": {
        "label_pt": "Casa e Cozinha",
        "label_es": "Hogar y Cocina",
        "icon":     "home",
        "stores":   ["wayfair","overstock","amazon","target","ikea","crateandbarrel"],
        "keywords": ["kitchen","cookware","blender","coffee maker","air fryer","instant pot",
                     "vacuum","bedding","pillow","curtain","furniture","lamp","rug","decor",
                     "storage","organizer","cleaning"],
        "commission_avg": 5.0,
    },
    "baby": {
        "label_pt": "Bebe e Kids",
        "label_es": "Bebé y Niños",
        "icon":     "baby",
        "stores":   ["amazon","target","walmart","carters","gerber","babylist"],
        "keywords": ["baby","diapers","wipes","formula","stroller","crib","monitor",
                     "toys","children","kids","toddler","infant","newborn","carter"],
        "commission_avg": 4.5,
    },
    "fitness": {
        "label_pt": "Fitness e Saude",
        "label_es": "Fitness y Salud",
        "icon":     "fitness",
        "stores":   ["gnc","vitamix","amazon","dickssporting","underarmour","lululemon"],
        "keywords": ["protein","supplement","vitamin","workout","gym","yoga","fitness",
                     "dumbbell","resistance band","treadmill","whey","preworkout","creatine",
                     "sports","athletic","exercise"],
        "commission_avg": 5.0,
    },
    "pets": {
        "label_pt": "Pets",
        "label_es": "Mascotas",
        "icon":     "paw",
        "stores":   ["chewy","petsmart","petco","amazon"],
        "keywords": ["dog","cat","pet","puppy","kitten","food","treats","leash","collar",
                     "litter","grooming","aquarium","bird","fish"],
        "commission_avg": 4.0,
    },
    "tools": {
        "label_pt": "Ferramentas",
        "label_es": "Herramientas",
        "icon":     "tool",
        "stores":   ["homedepot","lowes","amazon","ebay","acme"],
        "keywords": ["drill","saw","wrench","screwdriver","toolset","power tool","dewalt",
                     "milwaukee","makita","stanley","craftsman","hardware","garden","lawn"],
        "commission_avg": 4.0,
    },
    "automotive": {
        "label_pt": "Automotivo",
        "label_es": "Automotriz",
        "icon":     "car",
        "stores":   ["autozone","amazon","ebay","advance auto","oreilly"],
        "keywords": ["car","auto","vehicle","tire","brake","oil","battery","wiper",
                     "seat cover","dashboard","gps","car charger","floor mat"],
        "commission_avg": 4.5,
    },
    "travel": {
        "label_pt": "Viagem",
        "label_es": "Viajes",
        "icon":     "plane",
        "stores":   ["expedia","booking","hotels","kayak","airbnb"],
        "keywords": ["hotel","flight","vacation","trip","travel","luggage","suitcase",
                     "booking","resort","cruise","airline","airbnb"],
        "commission_avg": 5.0,
    },
}

# Ordem de exibicao no painel
CATEGORY_ORDER = [
    "electronics","home","baby","beauty","fashion",
    "shoes","fragrance","fitness","pets","tools","automotive","travel"
]


# ============================================================
#  CLASSIFICADOR AUTOMATICO DE CATEGORIA
# ============================================================

def classify_deal(title: str, source: str = "") -> str:
    """
    Classifica automaticamente um deal em uma categoria
    baseado no titulo e na fonte.
    Retorna o slug da categoria (ex: 'beauty', 'shoes').
    """
    text = (title + " " + source).lower()

    # Score por categoria baseado em keywords encontradas
    scores = {}
    for slug, cat in CATEGORIES.items():
        score = 0
        for kw in cat["keywords"]:
            if kw in text:
                score += 1
        # Bonus se a loja bate
        for store in cat["stores"]:
            if store in text:
                score += 3
        if score > 0:
            scores[slug] = score

    if not scores:
        return "electronics"  # default

    # Retorna categoria com maior score
    return max(scores, key=scores.get)


def get_category_label(slug: str, lang: str = "pt") -> str:
    """Retorna label da categoria no idioma especificado."""
    cat = CATEGORIES.get(slug, {})
    if lang == "es":
        return cat.get("label_es", slug)
    return cat.get("label_pt", slug)


def get_commission_for_category(slug: str) -> float:
    """Retorna comissao media da categoria."""
    return CATEGORIES.get(slug, {}).get("commission_avg", 4.0)


# ============================================================
#  FUSOS HORARIOS
# ============================================================

TIMEZONES = {
    # Eastern (UTC-5 / UTC-4 DST)
    "eastern": {
        "label":    "Eastern Time",
        "abbr":     "ET",
        "utc_offset": -5,
        "states": [
            "massachusetts","connecticut","new york","new jersey","pennsylvania",
            "florida","georgia","virginia","north carolina","south carolina",
            "maryland","delaware","maine","vermont","new hampshire","rhode island",
            "ohio","michigan","indiana","kentucky","west virginia",
        ],
        "send_hours": [9, 13, 20],   # horarios locais de envio
    },
    # Central (UTC-6 / UTC-5 DST)
    "central": {
        "label":    "Central Time",
        "abbr":     "CT",
        "utc_offset": -6,
        "states": [
            "illinois","texas","minnesota","wisconsin","iowa","missouri",
            "tennessee","alabama","mississippi","louisiana","arkansas",
            "oklahoma","kansas","nebraska","south dakota","north dakota",
        ],
        "send_hours": [9, 13, 20],
    },
    # Mountain (UTC-7 / UTC-6 DST)
    "mountain": {
        "label":    "Mountain Time",
        "abbr":     "MT",
        "utc_offset": -7,
        "states": [
            "colorado","utah","new mexico","montana","idaho","wyoming",
            "arizona",  # Arizona nao tem DST
        ],
        "send_hours": [9, 13, 20],
    },
    # Pacific (UTC-8 / UTC-7 DST)
    "pacific": {
        "label":    "Pacific Time",
        "abbr":     "PT",
        "utc_offset": -8,
        "states": [
            "california","washington","oregon","nevada",
        ],
        "send_hours": [9, 13, 20],
    },
    # Alaska (UTC-9)
    "alaska": {
        "label":    "Alaska Time",
        "abbr":     "AKT",
        "utc_offset": -9,
        "states": ["alaska"],
        "send_hours": [9, 13, 20],
    },
    # Hawaii (UTC-10)
    "hawaii": {
        "label":    "Hawaii Time",
        "abbr":     "HST",
        "utc_offset": -10,
        "states": ["hawaii"],
        "send_hours": [9, 13, 20],
    },
}

# Lookup rapido estado -> fuso
_STATE_TO_TZ = {}
for tz_key, tz_data in TIMEZONES.items():
    for state in tz_data["states"]:
        _STATE_TO_TZ[state.lower()] = tz_key


def get_timezone(state: str) -> str:
    """Retorna slug do fuso horario para um estado."""
    return _STATE_TO_TZ.get(state.lower().strip(), "eastern")


def get_send_times_utc(state: str) -> list[int]:
    """
    Retorna os horarios de envio em UTC para um estado.
    Ex: California (PT, UTC-8) envia as 9h local = 17h UTC
    """
    tz_key  = get_timezone(state)
    tz_data = TIMEZONES[tz_key]
    offset  = tz_data["utc_offset"]
    return [(h - offset) % 24 for h in tz_data["send_hours"]]


def local_to_utc(hour_local: int, state: str) -> int:
    """Converte hora local para UTC baseado no estado."""
    tz_key = get_timezone(state)
    offset = TIMEZONES[tz_key]["utc_offset"]
    return (hour_local - offset) % 24


def utc_to_local(hour_utc: int, state: str) -> int:
    """Converte hora UTC para local baseado no estado."""
    tz_key = get_timezone(state)
    offset = TIMEZONES[tz_key]["utc_offset"]
    return (hour_utc + offset) % 24


# ============================================================
#  REGRAS FREE vs VIP
# ============================================================

PLAN_RULES = {
    "free": {
        "deals_per_slot":   1,    # 1 deal por horario (3/dia)
        "max_categories":   1,    # apenas 1 categoria
        "advance_hours":    0,    # sem antecipacao
        "raffle_prize":     50,   # $50 sorteio semanal
        "raffle_frequency": "weekly",
    },
    "vip": {
        "deals_per_slot":   3,    # 3 deals por horario (9/dia)
        "max_categories":   5,    # ate 5 categorias
        "advance_hours":    2,    # 2h antes dos free
        "raffle_prize":     150,  # $150 sorteio mensal
        "raffle_frequency": "monthly",
    },
}


def get_plan_rules(plan: str) -> dict:
    return PLAN_RULES.get(plan, PLAN_RULES["free"])
