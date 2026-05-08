"""
core.py — Ziontec Bot
=====================
Motor determinístico: normalizadores, validadores, interceptadores.
Cobre 97+ padrões de linguagem natural para construção/elétrica EUA.
"""
import re
import datetime
import logging

logger = logging.getLogger(__name__)

_config = {
    "valor_hora": 25,
    "regra_8_8_igual_12h": True,
    "permitir_horas_sem_periodo": True,
    "timezone": "America/New_York"
}

def set_config(cfg: dict):
    _config.update(cfg)

def get_config(key, default=None):
    return _config.get(key, default)

_obras_ativas = []

def set_obras_ativas(obras: list):
    global _obras_ativas
    _obras_ativas = list(obras)

def get_obras_ativas():
    return list(_obras_ativas)

CHECKLIST_PADRAO = {
    "upgrade_service": {
        "fase1": ["Permissao / inspecao agendada", "Desligar servico com a utility",
                  "Remover painel antigo", "Instalar novo painel / meter base",
                  "Passar fiacao nova", "Aterramento"],
        "fase2": ["Conectar circuitos", "Identificar breakers", "Ligar servico de volta",
                  "Teste de circuitos", "Inspecao final aprovada", "Limpeza e entrega"]
    },
    "geral": {
        "fase1": ["Planejamento e medicao", "Compra de materiais",
                  "Demolicao / preparacao", "Instalacao rough", "Inspecao intermediaria"],
        "fase2": ["Acabamento", "Testes", "Inspecao final", "Limpeza", "Entrega ao cliente"]
    }
}

checklists = {}

# ─── NORMALIZADORES ───────────────────────────────────────────────────────────

def extrair_numero(texto):
    if not texto: return 0
    t = str(texto).lower().strip()
    if any(x in t for x in ['nao', 'não', 'zero', 'nd', 'indefinido', 'nenhum', 'sem']): return 0
    t = t.replace('$', '').replace(',', '.').strip()
    m = re.search(r'\d+(?:\.\d+)?', t)
    return float(m.group()) if m else 0

def normalizar_hora(texto):
    if not texto: return None
    t = str(texto).lower().strip()
    if 'meio dia' in t or 'meiodia' in t: return "12:00"
    if 'meia noite' in t or 'meianoite' in t: return "00:00"
    pm = any(x in t for x in ['pm', 'p.m', 'noite', 'tarde'])
    am = any(x in t for x in ['am', 'a.m', 'manha', 'manhã', 'cedo'])
    t_clean = re.sub(r'[^\d:]', '', t)
    if ':' in t_clean:
        parts = t_clean.split(':')
        h = int(parts[0]) % 24
        m = int(parts[1][:2]) if len(parts) > 1 else 0
    elif t_clean:
        h = int(t_clean) % 24
        m = 0
    else:
        return None
    if pm and h < 12: h += 12
    if am and h == 12: h = 0
    return f"{h:02d}:{m:02d}"

def hora_e_ambigua(texto_hora, contexto_completo=None):
    if not texto_hora: return True
    t = str(texto_hora).lower().strip()
    ctx = str(contexto_completo or '').lower()
    if re.search(r'\b\d{1,2}:\d{2}\b', t): return False
    if re.search(r'\b\d{1,2}\s*h(rs)?\b', t): return False
    indicadores = ['am', 'pm', 'manha', 'manhã', 'noite', 'tarde', 'a.m', 'p.m']
    if any(x in t for x in indicadores): return False
    if any(x in ctx for x in indicadores): return False
    t_num = re.sub(r'\D', '', t)
    if t_num:
        h = int(t_num)
        if h >= 13 or h == 0: return False
    return True

def calcular_horas_trabalhadas(inicio_raw, fim_raw):
    if not inicio_raw or not fim_raw: return None, None, None, True
    ini_str = str(inicio_raw).lower().strip()
    fim_str = str(fim_raw).lower().strip()
    tem_am_pm = lambda s: any(x in s for x in ['am','pm','manha','manhã','noite','tarde','a.m','p.m'])
    regra_8_8 = get_config('regra_8_8_igual_12h', True)
    ini_num = re.sub(r'\D', '', re.sub(r'[apmanhãtárdnoite]', '', ini_str))
    fim_num = re.sub(r'\D', '', re.sub(r'[apmanhãtárdnoite]', '', fim_str))
    if (regra_8_8 and ini_num == fim_num and not tem_am_pm(ini_str) and not tem_am_pm(fim_str)):
        h_ini = int(ini_num) if ini_num else 8
        if 1 <= h_ini <= 12:
            return 12.0, f"{h_ini:02d}:00", f"{h_ini+12:02d}:00", False
    ini_norm = normalizar_hora(ini_str)
    fim_norm = normalizar_hora(fim_str)
    if not ini_norm or not fim_norm: return None, None, None, True
    ini_h, ini_m = map(int, ini_norm.split(':'))
    fim_h, fim_m = map(int, fim_norm.split(':'))
    if fim_h < ini_h and not tem_am_pm(fim_str): return None, ini_norm, fim_norm, True
    total = (fim_h * 60 + fim_m - ini_h * 60 - ini_m) / 60
    if total <= 0: return None, ini_norm, fim_norm, True
    return round(total, 2), ini_norm, fim_norm, False

def normalizar_valor(texto):
    return extrair_numero(texto)

def normalizar_socio(texto, fallback=None):
    if not texto: return fallback
    t = str(texto).lower()
    primeira_pessoa = any(p in t for p in [
        'para mim', 'pra mim', ' mim', 'eu trabalhei', 'eu fiz', 'eu fiquei',
        'minhas horas', 'meu registro', 'minha hora', 'eu entrei', 'eu sai',
        'eu almocei', 'eu gastei', 'eu comprei', 'eu paguei', 'meu horario'
    ])
    if primeira_pessoa: return fallback
    if 'carlos' in t: return 'Carlos'
    if 'gerson' in t: return 'Gerson'
    return fallback

def calcular_data_prazo(texto):
    if not texto: return "Indefinido"
    t = str(texto).lower().strip()
    indefinidos = ['indefinido', 'nao definido', 'não definido', 'nd', 'sem prazo', 'nenhum', 'n/a']
    if any(x in t for x in indefinidos): return "Indefinido"
    hoje = datetime.datetime.now()
    m = re.search(r'(\d+)\s*(semana|week)', t)
    if m: return (hoje + datetime.timedelta(weeks=int(m.group(1)))).strftime("%d/%m/%Y")
    m = re.search(r'(\d+)\s*(dia|day)', t)
    if m: return (hoje + datetime.timedelta(days=int(m.group(1)))).strftime("%d/%m/%Y")
    m = re.search(r'(\d+)\s*(mes|month|mês)', t)
    if m: return (hoje + datetime.timedelta(days=int(m.group(1))*30)).strftime("%d/%m/%Y")
    m = re.search(r'(\d{2})/(\d{2})/(\d{4})', t)
    if m: return m.group(0)
    return "Indefinido"

def ultimo_dia_mes():
    hoje = datetime.datetime.now()
    if hoje.month == 12:
        return datetime.datetime(hoje.year+1, 1, 1) - datetime.timedelta(days=1)
    return datetime.datetime(hoje.year, hoje.month+1, 1) - datetime.timedelta(days=1)

def buscar_obra_por_nome(nome):
    if not nome: return None
    nl = nome.lower().strip()
    for o in _obras_ativas:
        if o.lower().strip() == nl: return o
    for o in _obras_ativas:
        if nl in o.lower() or o.lower() in nl: return o
    return None

def buscar_obra_por_cliente(cliente):
    if not cliente: return None
    cl = cliente.lower().strip()
    for o in _obras_ativas:
        if cl in o.lower(): return o
    return None

def _extrair_obra_do_texto(texto):
    if not texto: return None
    t = texto.lower().strip()
    for o in _obras_ativas:
        if o.lower() in t: return o
    return None

# ─── LOJAS E CATEGORIAS ───────────────────────────────────────────────────────

LOJAS_CATEGORIA = {
    # Material
    'home depot': 'Material', 'lowes': 'Material', "lowe's": 'Material',
    'menards': 'Material', 'fastenal': 'Material', 'grainger': 'Material',
    'ace hardware': 'Material', 'true value': 'Material',
    'amazon': 'Material', 'walmart': 'Material', 'costco': 'Material',
    '84 lumber': 'Material', 'lumber': 'Material',
    # Ferramenta
    'harbor freight': 'Ferramenta', 'tool': 'Ferramenta',
    'dewalt': 'Ferramenta', 'milwaukee': 'Ferramenta', 'ridgid': 'Ferramenta',
    # Alimentacao
    "mcdonald's": 'Alimentacao', 'mcdonalds': 'Alimentacao',
    'burger king': 'Alimentacao', 'subway': 'Alimentacao',
    'dunkin': 'Alimentacao', 'starbucks': 'Alimentacao',
    'restaurante': 'Alimentacao', 'restaurant': 'Alimentacao',
    'almoco': 'Alimentacao', 'almoço': 'Alimentacao',
    'lanche': 'Alimentacao', 'jantar': 'Alimentacao', 'cafe': 'Alimentacao',
    'lunch': 'Alimentacao', 'dinner': 'Alimentacao', 'breakfast': 'Alimentacao',
    'pizza': 'Alimentacao', 'comida': 'Alimentacao', 'chinese': 'Alimentacao',
    'wendys': 'Alimentacao', "wendy's": 'Alimentacao', 'popeyes': 'Alimentacao',
    'chipotle': 'Alimentacao', 'taco bell': 'Alimentacao',
    # Combustivel
    'shell': 'Combustivel', 'exxon': 'Combustivel', 'mobil': 'Combustivel',
    'gulf': 'Combustivel', 'bp ': 'Combustivel', 'sunoco': 'Combustivel',
    'citgo': 'Combustivel', 'speedway': 'Combustivel', 'cumberland': 'Combustivel',
    'gasolina': 'Combustivel', 'combustivel': 'Combustivel', 'posto': 'Combustivel',
    'gas station': 'Combustivel', 'fuel': 'Combustivel', 'tanque': 'Combustivel',
    # Transporte
    'uber': 'Transporte', 'lyft': 'Transporte', 'taxi': 'Transporte',
    # Outros
    'hotel': 'Hospedagem', 'motel': 'Hospedagem',
    'seguro': 'Seguro', 'insurance': 'Seguro',
    'telefone': 'Telefone', 'phone': 'Telefone', 'verizon': 'Telefone',
    't-mobile': 'Telefone', 'at&t': 'Telefone',
}

DESCONTO_EMPRESA_KW = [
    'corporativo', 'empresa', 'work', 'negocio', 'business',
    'da empresa', 'do trabalho', 'cartao da', 'card', 'servico'
]

def _detectar_categoria(texto):
    t = texto.lower()
    for loja, cat in LOJAS_CATEGORIA.items():
        if loja in t: return cat, loja
    return 'Material', None

def _detectar_desconto(texto, socio, categoria):
    t = texto.lower()
    if any(k in t for k in DESCONTO_EMPRESA_KW): return "Empresa"
    if categoria == "Combustivel": return socio
    if categoria == "Transporte": return socio
    if categoria == "Alimentacao":
        return "Empresa" if any(k in t for k in ['trabalho', 'obra', 'servico', 'work', 'corporativo']) else socio
    return "Empresa"

# ─── INTERCEPTADORES DE HORAS ─────────────────────────────────────────────────

def interceptar_correcao_horas(texto, socio_fallback):
    t = texto.lower().strip()
    socio = normalizar_socio(texto, socio_fallback)
    palavras_adicao = ['adicione', 'adicionar', 'adiciona', 'registra', 'registre',
                       'registrar', 'lanca', 'lance', 'lancar', 'add ']
    if any(p in t for p in palavras_adicao): return None
    m = re.search(r'(?:remov|tir[ae]|retir)[a-z]*\s+(\d+(?:\.\d+)?)\s*h', t)
    if m:
        obra = _extrair_obra_do_texto(t)
        return {"acao": "corrigir_horas", "socio": socio,
                "remover": float(m.group(1)), "obra": obra or "", "total": -1}
    m = re.search(r'(?:corrig[a-z]*\s+para|total\s+de|fez\s+(?:um\s+)?total\s+de|eram|sao|foram)\s+(\d+(?:\.\d+)?)\s*h', t)
    if m:
        obra = _extrair_obra_do_texto(t)
        return {"acao": "corrigir_horas", "socio": socio,
                "total": float(m.group(1)), "obra": obra or ""}
    m = re.search(r'(?:gerson|carlos)\s+fez\s+(\d+(?:\.\d+)?)\s*h', t)
    if m:
        obra = _extrair_obra_do_texto(t)
        return {"acao": "corrigir_horas", "socio": socio,
                "total": float(m.group(1)), "obra": obra or ""}
    return None

def interceptar_periodo_incompleto(texto):
    t = texto.lower().strip()
    if re.search(r'das?\s+\d+.*as?\s+\d+', t): return None
    if re.search(r'\d+\s*h\s*(ate|até)\s*\d+', t): return None
    m = re.search(r'(?:ate|até|saí|sai|saiu|terminei|terminou|parei|parou)\s+(?:as|às)?\s*(\d{1,2}\s*h?\w*)', t)
    if m:
        return {"tipo": "periodo_incompleto", "hora_fim_raw": m.group(1),
                "pergunta": "Que horas voce comecou?"}
    m = re.search(r'(?:cheguei|chegou|comecei|comecou|entrei|entrou)\s+(?:as|às)?\s*(\d{1,2}\s*h?\w*)', t)
    if m:
        return {"tipo": "periodo_incompleto", "hora_inicio_raw": m.group(1),
                "pergunta": "Que horas voce terminou?"}
    return None

def executar_correcao_com_total(socio, obra, total_novo):
    if total_novo < 0: total_novo = 0
    return {"acao": "corrigir_horas", "socio": socio, "obra": obra, "total": total_novo}

def interceptar_horas_expandido(texto, socio_fallback):
    """Detecta registro de horas em linguagem natural."""
    t = texto.lower().strip()
    socio = normalizar_socio(texto, socio_fallback)
    if interceptar_correcao_horas(texto, socio_fallback): return None

    # Ambos trabalharam ("a gente", "eu e o carlos", "nos dois")
    if re.search(r'(?:a\s+gente|nos\s+dois|eu\s+e\s+o?\s*carlos|eu\s+e\s+o?\s*gerson|ambos)', t):
        m = re.search(r'(\d+(?:[.,]\d+)?)\s*h', t)
        horas = float(m.group(1).replace(',', '.')) if m else 12.0
        obra = _extrair_obra_do_texto(t) or ''
        return {"acao": "registrar_horas_ambos", "horas": horas, "obra": obra}

    # Dia completo / dia todo = 12h
    if re.search(r'(?:trabalhei?|trabalhou|fiz|fez|fiquei?|ficamos?)\s+(?:o\s+dia\s+todo|dia\s+inteiro|o\s+dia\b|hoje\s+o\s+dia)', t) or \
       re.search(r'(?:dia\s+todo|dia\s+inteiro|o\s+dia\s+todo)', t):
        obra = _extrair_obra_do_texto(t) or ''
        return {"acao": "registrar_horas", "socio": socio,
                "horas": 12.0, "obra": obra, "hora_inicio": "08:00", "hora_fim": "20:00"}

    # Meio periodo = 6h
    if re.search(r'(?:meio\s+periodo|half\s+day|manha\s+toda|tarde\s+toda|so\s+a\s+manha|so\s+a\s+tarde)', t):
        is_am = re.search(r'(?:manha|morning|am)', t)
        obra = _extrair_obra_do_texto(t) or ''
        ini = "08:00" if is_am else "12:00"
        fim = "12:00" if is_am else "18:00"
        return {"acao": "registrar_horas", "socio": socio,
                "horas": 6.0, "obra": obra, "hora_inicio": ini, "hora_fim": fim}

    # Periodo explicito: "das 8 às 17" / "entrei 8am sai 5pm"
    m = re.search(r'(?:das?|de|entrei|cheguei|comecei)\s+(\d{1,2}\s*(?:am|pm|h)?)\s+(?:as?|ate|até|sai|saí|sai|saiu)\s+(\d{1,2}\s*(?:am|pm|h)?)', t)
    if m:
        h_ini, h_fim = m.group(1), m.group(2)
        horas, ini, fim, amb = calcular_horas_trabalhadas(h_ini, h_fim)
        if not amb and horas:
            obra = _extrair_obra_do_texto(t) or ''
            return {"acao": "registrar_horas", "socio": socio,
                    "horas": horas, "obra": obra, "hora_inicio": ini, "hora_fim": fim}

    # Horas diretas: "trabalhei 8h" / "fiz 10 horas"
    m = re.search(r'(?:trabalhei?|trabalhou|fiz|fez|botei?|coloca|adiciona)\s+(\d+(?:[.,]\d+)?)\s*h(?:oras?)?', t)
    if m:
        horas = float(m.group(1).replace(',', '.'))
        obra = _extrair_obra_do_texto(t) or ''
        if horas > 0:
            return {"acao": "registrar_horas", "socio": socio, "horas": horas, "obra": obra}

    # "X horas na obra"
    m = re.search(r'(\d+(?:[.,]\d+)?)\s*h(?:oras?)?\s+(?:na?|em|no)\s+(\w+)', t)
    if m:
        horas = float(m.group(1).replace(',', '.'))
        obra_txt = m.group(2)
        obra = buscar_obra_por_nome(obra_txt) or _extrair_obra_do_texto(t) or ''
        if horas > 0:
            return {"acao": "registrar_horas", "socio": socio, "horas": horas, "obra": obra}

    # "horas extras X"
    m = re.search(r'(?:\d+)\s*h(?:oras?)?\s+extra', t)
    if not m:
        m = re.search(r'extra[s]?\s+(\d+(?:[.,]\d+)?)\s*h', t)
    if m:
        num = re.search(r'(\d+(?:[.,]\d+)?)', t)
        if num:
            horas = float(num.group(1).replace(',', '.'))
            obra = _extrair_obra_do_texto(t) or ''
            return {"acao": "registrar_horas", "socio": socio, "horas": horas, "obra": obra}

    return None

# ─── INTERCEPTADORES DE DESPESA ───────────────────────────────────────────────

def interceptar_despesa(texto, socio_fallback):
    """Detecta despesas em linguagem natural. Cobre 20+ padroes."""
    t = texto.lower().strip()
    verbos_registro = ['registr', 'lanc', 'anot', 'salv']
    if any(v in t for v in verbos_registro):
        if not re.search(r'(?:adicion|coloca|bota)\s+', t): return None
    socio = normalizar_socio(texto, socio_fallback)
    obra = _extrair_obra_do_texto(t)
    categoria, loja_detectada = _detectar_categoria(t)

    # Padrao 0: verbos de refeicao (almocei, jantei, comi, lanchei)
    if re.search(r'(?:almocei|almocamos|jantei|jantamos|comi|comemos|lanchei|lanchamos|tomei\s+cafe)', t):
        num = re.search(r'(\d+(?:[.,]\d+)?)', t)
        if num:
            valor = extrair_numero(num.group(1))
            desconto = _detectar_desconto(t, socio, 'Alimentacao')
            local = loja_detectada or 'restaurante'
            if valor > 0:
                return {"acao": "registrar_despesa", "socio": socio, "valor": valor,
                        "categoria": "Alimentacao", "descricao": local.title(),
                        "obra": obra or "", "desconto": desconto}

    # Padrao 1: gastei/paguei/comprei/custou X
    m = re.search(r'(?:gastei|paguei|comprei|custou|foi|saiu|cobrou)\s+\$?(\d+(?:[.,]\d+)?)', t)
    if m:
        valor = extrair_numero(m.group(1))
        desconto = _detectar_desconto(t, socio, categoria)
        descricao = loja_detectada or categoria.lower()
        if valor > 0:
            return {"acao": "registrar_despesa", "socio": socio, "valor": valor,
                    "categoria": categoria, "descricao": descricao.title(),
                    "obra": obra or "", "desconto": desconto}

    # Padrao 2: loja + valor (home depot 120)
    for loja, cat in LOJAS_CATEGORIA.items():
        m = re.search(re.escape(loja) + r'\s+\$?(\d+(?:[.,]\d+)?)', t)
        if m:
            valor = extrair_numero(m.group(1))
            desconto = _detectar_desconto(t, socio, cat)
            if valor > 0:
                return {"acao": "registrar_despesa", "socio": socio, "valor": valor,
                        "categoria": cat, "descricao": loja.title(),
                        "obra": obra or "", "desconto": desconto}

    # Padrao 3: categoria + valor (almoco 25, gas 45, uber 30)
    m = re.search(r'(?:almoco|almoço|lanche|jantar|cafe|gas\s|gasolina|uber|lyft|taxi|ferramenta|hotel)\s+\$?(\d+(?:[.,]\d+)?)', t)
    if m:
        valor = extrair_numero(m.group(1))
        cat, _ = _detectar_categoria(t)
        desconto = _detectar_desconto(t, socio, cat)
        if valor > 0:
            return {"acao": "registrar_despesa", "socio": socio, "valor": valor,
                    "categoria": cat, "descricao": t.split()[0].title(),
                    "obra": obra or "", "desconto": desconto}

    # Padrao 4: valor + de/do/da + categoria (20 de almoco, 50 de material)
    m = re.search(r'\$?(\d+(?:[.,]\d+)?)\s+(?:de|do|da|em)\s+(almoco|almoço|material|gas|gasolina|ferramenta|lanche|jantar|cafe|comida|restaurante|uber|taxi|combustivel)', t)
    if m:
        valor = extrair_numero(m.group(1))
        cat, _ = _detectar_categoria(m.group(2))
        desconto = _detectar_desconto(t, socio, cat)
        if valor > 0:
            return {"acao": "registrar_despesa", "socio": socio, "valor": valor,
                    "categoria": cat, "descricao": m.group(2).title(),
                    "obra": obra or "", "desconto": desconto}

    # Padrao 5: nota/invoice/recibo de X
    m = re.search(r'(?:nota|nf|invoice|recibo|receipt)\s+(?:de\s+)?\$?(\d+(?:[.,]\d+)?)', t)
    if m:
        valor = extrair_numero(m.group(1))
        if valor > 0:
            return {"acao": "registrar_despesa", "socio": socio, "valor": valor,
                    "categoria": "Material", "descricao": "Nota Fiscal",
                    "obra": obra or "", "desconto": "Empresa"}

    # Padrao 6: adicione/coloca X de categoria/gasto
    m = re.search(r'(?:adicion[ae]|coloca|bota)\s+\$?(\d+(?:[.,]\d+)?)\s*(?:de\s+)?(\w+)', t)
    if m:
        valor = extrair_numero(m.group(1))
        desc = m.group(2) if m.group(2) else 'gasto'
        cat, _ = _detectar_categoria(t + ' ' + desc)
        desconto = _detectar_desconto(t, socio, cat)
        if valor > 0:
            return {"acao": "registrar_despesa", "socio": socio, "valor": valor,
                    "categoria": cat, "descricao": desc.title(),
                    "obra": obra or "", "desconto": desconto}

    # Padrao 7: enchi o tanque X / abasteci X
    m = re.search(r'(?:enchi|abasteci|botei\s+gas)\s+(?:o\s+tanque\s+)?(?:por\s+)?\$?(\d+(?:[.,]\d+)?)', t)
    if m:
        valor = extrair_numero(m.group(1))
        if valor > 0:
            return {"acao": "registrar_despesa", "socio": socio, "valor": valor,
                    "categoria": "Combustivel", "descricao": "Gasolina",
                    "obra": obra or "", "desconto": socio}

    return None

# ─── INTERCEPTADORES DE PAGAMENTO ─────────────────────────────────────────────

def interceptar_pagamento(texto, obras_info=None):
    """Detecta recebimento de pagamento. Cobre 15+ padroes."""
    t = texto.lower().strip()
    triggers = [
        'recebi', 'recebemos', 'recebeu', 'pagou', 'cliente pagou',
        'pagamento de', 'depositou', 'transferiu', 'mandou', 'enviou',
        'zelle', 'venmo', 'check de', 'cheque de', 'cash de', 'wire de',
        'ach de', 'entrada de', 'sinal de', 'down payment'
    ]
    if not any(p in t for p in triggers): return None

    obra = _extrair_obra_do_texto(t)
    if not obra and obras_info:
        for nome_obra in obras_info:
            if nome_obra.lower() in t:
                obra = nome_obra
                break

    # "metade" = 50% do contrato
    if 'metade' in t and obra and obras_info and obra in obras_info:
        contrato = float(obras_info[obra].get('contrato', 0))
        valor = round(contrato * 0.5, 2)
        return {"acao": "registrar_pagamento", "obra": obra,
                "cliente": obras_info[obra].get("cliente", ""),
                "valor": valor, "_origem": "metade_contrato"}

    # "tudo" / "total" / "valor total" = saldo restante
    if any(p in t for p in ['pagou tudo', 'pagou o total', 'pagou tudo',
                              'quitou', 'liquidou', 'pagou o restante', 'pagou o saldo']):
        if obra and obras_info and obra in obras_info:
            saldo = float(obras_info[obra].get('saldo', 0))
            if saldo > 0:
                return {"acao": "registrar_pagamento", "obra": obra,
                        "cliente": obras_info[obra].get("cliente", ""),
                        "valor": saldo, "_origem": "saldo_total"}

    # Valor explicito
    m = re.search(r'\$?(\d+(?:[.,]\d+)?)', t)
    if m:
        valor = extrair_numero(m.group(1))
        if valor > 0:
            return {"acao": "registrar_pagamento",
                    "obra": obra or "", "cliente": "", "valor": valor}
    return None

# ─── VALIDADOR CENTRAL ────────────────────────────────────────────────────────

class ValidationError(Exception):
    def __init__(self, pergunta: str):
        self.pergunta = pergunta
        super().__init__(pergunta)

def validar_acao(payload: dict, texto_original: str = '') -> None:
    acao = payload.get('acao', '')
    texto = texto_original.lower()
    socio = payload.get('socio') or ''
    if socio:
        carlos_no_texto = 'carlos' in texto
        gerson_no_texto = 'gerson' in texto
        if carlos_no_texto and not gerson_no_texto and socio.lower() != 'carlos':
            raise ValueError(f"Conflito: texto menciona Carlos mas acao tem socio={socio}")
        if gerson_no_texto and not carlos_no_texto and socio.lower() != 'gerson':
            raise ValueError(f"Conflito: texto menciona Gerson mas acao tem socio={socio}")
    acoes_exigem_obra = {'registrar_horas', 'corrigir_horas', 'registrar_despesa',
                         'ticar_checklist', 'adicionar_compras', 'salvar_midia'}
    if acao in acoes_exigem_obra:
        if not payload.get('obra', '').strip():
            raise ValidationError("Em qual obra?")
    if acao in ('registrar_despesa', 'registrar_pagamento'):
        valor = float(payload.get('valor', 0))
        if valor <= 0 and re.search(r'\d+', texto):
            raise ValidationError("Qual o valor exato?")
        if valor <= 0:
            raise ValidationError("Qual o valor?")
    if acao == 'registrar_horas':
        horas = float(payload.get('horas', 0))
        if horas < 0:
            raise ValueError("Horas nao podem ser negativas.")
        if horas == 0:
            raise ValidationError("Quantas horas?")
        h_ini = payload.get('hora_inicio', '')
        h_fim = payload.get('hora_fim', '')
        if h_ini and hora_e_ambigua(h_ini, texto):
            raise ValidationError(f"As {h_ini} e da manha ou da noite?")
        if h_fim and hora_e_ambigua(h_fim, texto):
            raise ValidationError(f"As {h_fim} e da manha ou da noite?")
    if acao == 'corrigir_horas':
        total = float(payload.get('total', -1))
        if total < 0 and payload.get('remover', 0) == 0:
            raise ValidationError("Qual o total correto de horas?")

# ─── MAQUINA DE PENDENCIAS ───────────────────────────────────────────────────

TIPOS_PENDENCIA = {
    'obra': 'pendencia_obra', 'horario': 'pendencia_horario',
    'confirmacao': 'pendencia_confirmacao', 'correcao': 'pendencia_correcao',
    'valor': 'pendencia_valor', 'socio': 'pendencia_socio',
}

def criar_pendencia(tipo, payload, pergunta):
    return {'tipo': tipo, 'payload': payload, 'pergunta': pergunta, 'tentativas': 0}

def resolver_pendencia(user_data, texto_usuario):
    pend = user_data.get('pendencia_ativa')
    if not pend: return None, None
    tipo = pend.get('tipo')
    payload = dict(pend.get('payload', {}))
    t = texto_usuario.lower().strip()
    pend['tentativas'] = pend.get('tentativas', 0) + 1

    if tipo == 'pendencia_obra':
        obra = _extrair_obra_do_texto(t)
        if not obra:
            for o in _obras_ativas:
                if o.lower() in t or t in o.lower(): obra = o; break
        if obra:
            payload['obra'] = obra
            user_data.pop('pendencia_ativa', None)
            prox = _proxima_pergunta(payload)
            if prox:
                user_data['pendencia_ativa'] = criar_pendencia(prox[0], payload, prox[1])
                return None, prox[1]
            return payload, None
        return None, f"Nao encontrei. Opcoes: {', '.join(_obras_ativas) or 'nenhuma'}"

    if tipo == 'pendencia_horario':
        subtipo = pend.get('subtipo', 'ambiguo')
        if subtipo == 'sem_inicio':
            h = normalizar_hora(t)
            if h:
                payload['hora_inicio'] = h
                if payload.get('hora_fim'):
                    horas, ini, fim, amb = calcular_horas_trabalhadas(h, payload['hora_fim'])
                    if not amb and horas:
                        payload['horas'] = horas
                        payload['hora_inicio'] = ini
                        payload['hora_fim'] = fim
                user_data.pop('pendencia_ativa', None)
                return payload, None
            return None, "Que horas voce entrou? (ex: 7h, 8am)"
        if subtipo == 'ambiguo':
            hora_raw = pend.get('hora_raw', '')
            if any(x in t for x in ['manha', 'manhã', 'am', 'cedo', 'morning']):
                h = normalizar_hora(hora_raw + ' am')
                payload[pend.get('campo', 'hora_inicio')] = h
                user_data.pop('pendencia_ativa', None)
                return payload, None
            if any(x in t for x in ['noite', 'tarde', 'pm', 'night', 'evening']):
                h = normalizar_hora(hora_raw + ' pm')
                payload[pend.get('campo', 'hora_inicio')] = h
                user_data.pop('pendencia_ativa', None)
                return payload, None
            return None, f"As {hora_raw} e da manha ou da noite?"

    if tipo == 'pendencia_valor':
        valor = extrair_numero(t)
        if valor > 0:
            payload['valor'] = valor
            user_data.pop('pendencia_ativa', None)
            prox = _proxima_pergunta(payload)
            if prox:
                user_data['pendencia_ativa'] = criar_pendencia(prox[0], payload, prox[1])
                return None, prox[1]
            return payload, None
        return None, "Qual o valor? (ex: 150, $200)"

    if tipo == 'pendencia_socio':
        socio = normalizar_socio(t, None)
        if socio:
            payload['socio'] = socio
            user_data.pop('pendencia_ativa', None)
            return payload, None
        return None, "Quem foi — Gerson ou Carlos?"

    if tipo == 'pendencia_correcao':
        if not payload.get('obra'):
            obra = _extrair_obra_do_texto(t)
            if not obra:
                for o in _obras_ativas:
                    if o.lower() in t: obra = o; break
            if obra:
                payload['obra'] = obra
                if payload.get('total', -1) >= 0:
                    user_data.pop('pendencia_ativa', None)
                    return payload, None
                user_data['pendencia_ativa'] = criar_pendencia(
                    'pendencia_correcao', payload, "Qual o total correto de horas?")
                return None, "Qual o total correto de horas?"
            return None, f"Em qual obra? ({', '.join(_obras_ativas) or 'nenhuma'})"
        if payload.get('total', -1) < 0:
            total = extrair_numero(t)
            if total >= 0:
                payload['total'] = total
                user_data.pop('pendencia_ativa', None)
                return payload, None
            return None, "Qual o total correto de horas?"

    return None, pend.get('pergunta', "Pode repetir?")

def _proxima_pergunta(payload):
    acao = payload.get('acao', '')
    if acao in {'registrar_horas', 'corrigir_horas', 'registrar_despesa',
                'ticar_checklist', 'adicionar_compras'} and not payload.get('obra'):
        return ('pendencia_obra', f"Em qual obra? ({', '.join(_obras_ativas) or 'nenhuma'})")
    if acao in ('registrar_despesa', 'registrar_pagamento'):
        if not payload.get('valor') or float(payload.get('valor', 0)) <= 0:
            return ('pendencia_valor', "Qual o valor?")
    return None

# ─── UNDO STACK ──────────────────────────────────────────────────────────────

def registrar_undo(user_data, aba, tipo, row_index=None, valores=None, estado_antes=None):
    if 'undo_stack' not in user_data: user_data['undo_stack'] = []
    user_data['undo_stack'].append({
        'aba': aba, 'tipo': tipo, 'row_index': row_index,
        'valores': valores, 'estado_antes': estado_antes,
        'timestamp': datetime.datetime.now().isoformat(),
    })
    if len(user_data['undo_stack']) > 5: user_data['undo_stack'].pop(0)

def pop_undo(user_data):
    stack = user_data.get('undo_stack', [])
    if not stack: return None
    return stack.pop()


# ─── SUPORTE INGLES ──────────────────────────────────────────────────────────

LOJAS_CATEGORIA.update({
    'lunch': 'Alimentacao', 'dinner': 'Alimentacao', 'breakfast': 'Alimentacao',
    'coffee': 'Alimentacao', 'food': 'Alimentacao',
    'supplies': 'Material', 'materials': 'Material', 'hardware': 'Material',
    'equipment': 'Ferramenta', 'tool store': 'Ferramenta',
    'gas money': 'Combustivel', 'fuel': 'Combustivel', 'parking': 'Transporte',
    'hotel': 'Hospedagem', 'insurance': 'Seguro',
    "wendy's": 'Alimentacao', 'chipotle': 'Alimentacao', 'taco bell': 'Alimentacao',
    'verizon': 'Telefone', 't-mobile': 'Telefone',
})

PAYMENT_TRIGGERS_EN = [
    'got paid', 'received payment', 'client paid', 'they paid', 'he paid',
    'payment received', 'sent zelle', 'wire received', 'check received',
    'first payment', 'final payment', 'down payment', 'deposit received',
    'paid in full', 'paid cash', 'cash payment', 'sent money',
]

EXPENSE_TRIGGERS_EN = [
    'spent', 'bought', 'purchased', 'paid for', 'cost me',
    'billed', 'invoice', 'receipt', 'bill',
]

HOURS_TRIGGERS_EN = [
    'worked', 'clocked', 'on site', 'at the job', 'at work',
    'put in', 'logged', 'overtime', 'full day', 'half day',
]


def interceptar_despesa_en(texto, socio_fallback):
    t = texto.lower().strip()
    if not any(k in t for k in EXPENSE_TRIGGERS_EN + list(LOJAS_CATEGORIA.keys())):
        return None
    socio = normalizar_socio(texto, socio_fallback)
    obra = _extrair_obra_do_texto(t)
    categoria, loja_detectada = _detectar_categoria(t)
    m = re.search(r'(?:spent|paid|bought|purchased|cost)\s+\$?(\d+(?:[.,]\d+)?)', t)
    if m:
        valor = extrair_numero(m.group(1))
        if valor > 0:
            return {"acao": "registrar_despesa", "socio": socio, "valor": valor,
                    "categoria": categoria, "descricao": loja_detectada or "Compra",
                    "obra": obra or "", "desconto": _detectar_desconto(t, socio, categoria)}
    for loja, cat in LOJAS_CATEGORIA.items():
        if loja in t:
            m2 = re.search(r'\$?(\d+(?:[.,]\d+)?)', t)
            if m2:
                valor = extrair_numero(m2.group(1))
                if 0 < valor < 10000:
                    return {"acao": "registrar_despesa", "socio": socio, "valor": valor,
                            "categoria": cat, "descricao": loja.title(),
                            "obra": obra or "", "desconto": _detectar_desconto(t, socio, cat)}
    if re.search(r'(?:gas\s+money|filled\s+up|fuel\s+up)', t):
        m3 = re.search(r'\$?(\d+(?:[.,]\d+)?)', t)
        if m3:
            valor = extrair_numero(m3.group(1))
            if valor > 0:
                return {"acao": "registrar_despesa", "socio": socio, "valor": valor,
                        "categoria": "Combustivel", "descricao": "Gasolina",
                        "obra": obra or "", "desconto": socio}
    if re.search(r'(?:lunch|dinner|breakfast|coffee|food|ate)', t):
        m4 = re.search(r'\$?(\d+(?:[.,]\d+)?)', t)
        if m4:
            valor = extrair_numero(m4.group(1))
            if valor > 0:
                return {"acao": "registrar_despesa", "socio": socio, "valor": valor,
                        "categoria": "Alimentacao", "descricao": "Almoco",
                        "obra": obra or "", "desconto": _detectar_desconto(t, socio, 'Alimentacao')}
    return None


def interceptar_pagamento_en(texto, obras_info=None):
    t = texto.lower().strip()
    if not any(p in t for p in PAYMENT_TRIGGERS_EN): return None
    obra = _extrair_obra_do_texto(t)
    if not obra and obras_info:
        for nome_obra in obras_info:
            if nome_obra.lower() in t: obra = nome_obra; break
    if re.search(r'(?:paid\s+in\s+full|paid\s+everything|final\s+payment)', t):
        if obra and obras_info and obra in obras_info:
            saldo = float(obras_info[obra].get('saldo', 0))
            if saldo > 0:
                return {"acao": "registrar_pagamento", "obra": obra,
                        "cliente": obras_info[obra].get("cliente", ""),
                        "valor": saldo, "_origem": "saldo_total"}
    m = re.search(r'\$?(\d+(?:[.,]\d+)?)', t)
    if m:
        valor = extrair_numero(m.group(1))
        if valor > 0:
            return {"acao": "registrar_pagamento", "obra": obra or "", "cliente": "", "valor": valor}
    return None


def interceptar_horas_en(texto, socio_fallback):
    t = texto.lower().strip()
    if not any(k in t for k in HOURS_TRIGGERS_EN): return None
    socio = normalizar_socio(texto, socio_fallback)
    obra = _extrair_obra_do_texto(t)
    if re.search(r'(?:full\s+day|all\s+day|full\s+shift)', t):
        return {"acao": "registrar_horas", "socio": socio, "horas": 12.0,
                "obra": obra or "", "hora_inicio": "08:00", "hora_fim": "20:00"}
    if 'half day' in t:
        return {"acao": "registrar_horas", "socio": socio, "horas": 6.0, "obra": obra or ""}
    m = re.search(r'(?:worked|put\s+in|logged)\s+(\d+(?:\.d+)?)\s*h', t)
    if not m:
        m = re.search(r'(\d+(?:\.d+)?)\s*hours?\s+(?:today|yesterday|at|on)', t)
    if m:
        horas = float(m.group(1))
        if horas > 0:
            return {"acao": "registrar_horas", "socio": socio, "horas": horas, "obra": obra or ""}
    m = re.search(r'overtime\s+(\d+(?:\.d+)?)', t)
    if m:
        return {"acao": "registrar_horas", "socio": socio, "horas": float(m.group(1)), "obra": obra or ""}
    return None


def interceptar_undo(texto):
    t = texto.lower().strip()
    triggers = ['cancela isso', 'cancela o ultimo', 'desfaz', 'volta atras',
                'remove esse lancamento', 'apaga o ultimo', 'undo', 'desfaz isso',
                'errei cancela', 'nao era isso', 'cancela', 'isso ta errado']
    if any(p in t for p in triggers):
        return {"acao": "undo"}
    return None


def interceptar_consulta(texto):
    t = texto.lower().strip()
    if re.search(r'(?:resumo|summary|quanto\s+recebi|my\s+balance|qual\s+meu\s+saldo|quanto\s+falta)', t):
        return {"acao": "mostrar_resumo"}
    if re.search(r'(?:minhas?\s+horas?|my\s+hours?|horas?\s+do\s+mes|banco\s+de\s+horas)', t):
        return {"acao": "mostrar_horas"}
    if re.search(r'(?:obras?\s+ativas?|lista\s+de\s+obras?|quais\s+obras?|my\s+jobs)', t):
        return {"acao": "mostrar_obras"}
    return None
