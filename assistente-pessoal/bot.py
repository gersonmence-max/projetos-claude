"""
Ziontec Bot - v7.0
==================
Mudanças em relação à v6.0:
1. Confirmação financeira com InlineKeyboard (sem ConversationHandler por texto)
2. Fluxo de mídia com InlineKeyboard (obras como botões, sem texto livre)
3. JobQueue no lugar de threading + schedule (removido asyncio.run em thread)
4. Whitelist de usuários via allowed_users.json
5. Aba EVENTS criada automaticamente para rastreamento ML
"""

import os
import uuid
import datetime
import json
import base64
import requests
import re
import logging
from dotenv import load_dotenv
from groq import Groq
import anthropic
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, MessageHandler, CommandHandler,
    CallbackQueryHandler, filters, ContextTypes
)
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# ─── LOGGING ──────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
groq_client = Groq(api_key=GROQ_API_KEY)
anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Mapa de socios por Telegram ID - identificacao 100% confiavel
SOCIOS_IDS = {
    6042733983: "Gerson",
    # Adicionar Carlos aqui: 000000000: "Carlos",
}

# ─── CONFIG ───────────────────────────────
from core import (
    set_config, get_config, set_obras_ativas, get_obras_ativas,
    normalizar_hora, calcular_horas_trabalhadas, hora_e_ambigua,
    normalizar_valor, normalizar_socio, extrair_numero,
    calcular_data_prazo, buscar_obra_por_nome, buscar_obra_por_cliente,
    interceptar_correcao_horas, interceptar_periodo_incompleto,
    interceptar_despesa, interceptar_pagamento,
    interceptar_horas_expandido, interceptar_horas_en,
    interceptar_despesa_en, interceptar_pagamento_en,
    interceptar_undo, interceptar_consulta,
    resolver_pendencia, criar_pendencia, TIPOS_PENDENCIA,
    registrar_undo, pop_undo,
    ultimo_dia_mes, _extrair_obra_do_texto,
    validar_acao, ValidationError
)

def carregar_config():
    """Carrega config.json e atualiza core + constantes locais."""
    global VALOR_HORA
    if os.path.exists('config.json'):
        with open('config.json', encoding='utf-8') as f:
            cfg = json.load(f)
        set_config(cfg)
        VALOR_HORA = cfg.get('valor_hora', 25)
        logger.info(f"Config carregada: {cfg}")
    else:
        cfg = {"valor_hora": 25, "timezone": "America/New_York",
               "regra_8_8_igual_12h": True, "permitir_horas_sem_periodo": True,
               "confirmar_financeiro": True, "empresa": "Ziontec"}
        with open('config.json', 'w') as f:
            json.dump(cfg, f, indent=2)
        set_config(cfg)
        logger.info("config.json criado com defaults.")

def salvar_config_key(key, value):
    cfg = {}
    if os.path.exists('config.json'):
        with open('config.json') as f:
            cfg = json.load(f)
    cfg[key] = value
    with open('config.json', 'w') as f:
        json.dump(cfg, f, indent=2)
    set_config({key: value})
    if key == 'valor_hora':
        global VALOR_HORA
        VALOR_HORA = value

SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

EMPRESA = "Ziontec"
VALOR_HORA = 25
SHEET_ID = None
CHAT_IDS = []

# ─── WHITELIST ────────────────────────────

allowed_users = []

if os.path.exists('allowed_users.json'):
    with open('allowed_users.json') as f:
        allowed_users = json.load(f)
    logger.info(f"Whitelist carregada: {len(allowed_users)} usuários")
else:
    with open('allowed_users.json', 'w') as f:
        json.dump([], f)
    logger.warning("allowed_users.json não encontrado — criado vazio. Adicione os user_ids para liberar acesso.")

def usuario_autorizado(update: Update) -> bool:
    """Verifica se o usuário está na whitelist. Se lista vazia, libera todos (modo dev)."""
    if not allowed_users:
        return True
    return update.effective_user.id in allowed_users

# ─── CHECKLISTS PADRÃO ────────────────────

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

# ─── DADOS LOCAIS ─────────────────────────

obras_ativas = []
clientes = {}
lista_compras = {}
checklists = {}

for arq in ['obras.json', 'clientes.json', 'lista_compras.json', 'checklists.json']:
    if os.path.exists(arq):
        with open(arq, encoding='utf-8') as f:
            dados = json.load(f)
            if arq == 'obras.json': obras_ativas.extend(dados)
            elif arq == 'clientes.json': clientes.update(dados)
            elif arq == 'lista_compras.json': lista_compras.update(dados)
            elif arq == 'checklists.json': checklists.update(dados)

def salvar_dados():
    with open('obras.json', 'w', encoding='utf-8') as f: json.dump(obras_ativas, f, ensure_ascii=False)
    with open('clientes.json', 'w', encoding='utf-8') as f: json.dump(clientes, f, ensure_ascii=False)
    with open('lista_compras.json', 'w', encoding='utf-8') as f: json.dump(lista_compras, f, ensure_ascii=False)
    with open('checklists.json', 'w', encoding='utf-8') as f: json.dump(checklists, f, ensure_ascii=False)

# ─── UTILIDADES ───────────────────────────

def extrair_numero(texto):
    if not texto: return 0
    texto = str(texto).strip().replace('$', '').replace(',', '.')
    palavras_zero = ['n', 'nao', 'não', 'sei', 'nenhum', 'zero', 'nd', 'n/a', 'na', 'nada', 'indefinido']
    if texto.lower().strip() in palavras_zero: return 0
    if all(c.isalpha() or c.isspace() for c in texto): return 0
    try:
        numeros = re.findall(r'\d+\.?\d*', texto)
        return float(numeros[0]) if numeros else 0
    except:
        return 0


# ─── NORMALIZADORES ───────────────────────

def normalizar_hora(texto):
    """
    Converte qualquer formato de hora para HH:MM (24h).
    Retorna None se nao conseguir interpretar.
    
    8, 8h, 8:00, 8am, 8 da manha, 8hrs -> 08:00
    20, 20h, 8pm, 8 da noite -> 20:00
    meio dia -> 12:00
    """
    if not texto: return None
    t = str(texto).lower().strip()

    if 'meio dia' in t or 'meio-dia' in t: return "12:00"
    if 'meia noite' in t or 'meia-noite' in t: return "00:00"

    is_pm = any(x in t for x in ['pm', 'da noite', 'da tarde', 'noite', 'tarde', 'p.m'])
    is_am = any(x in t for x in ['am', 'da manha', 'manha', 'a.m'])

    numeros = re.findall(r'(\d{1,2})(?:[:\.](\d{2}))?', t)
    if not numeros: return None

    hora = int(numeros[0][0])
    minuto = int(numeros[0][1]) if numeros[0][1] else 0

    if is_pm and hora < 12: hora += 12
    elif is_am and hora == 12: hora = 0

    if hora < 0 or hora > 23 or minuto < 0 or minuto > 59: return None
    return f"{hora:02d}:{minuto:02d}"

def calcular_horas_trabalhadas(inicio_raw, fim_raw):
    """
    Calcula horas entre dois horarios.
    Regra: se inicio == fim (ex: "8 as 8"), assume 12h (8am ate 8pm).
    Retorna (horas_float, inicio_normalizado, fim_normalizado, ambiguo)
    ambiguo=True quando nao da pra saber se e AM ou PM.
    """
    h_ini = normalizar_hora(inicio_raw)
    h_fim = normalizar_hora(fim_raw)

    if not h_ini or not h_fim: return None, h_ini, h_fim, True

    ini_h = int(h_ini.split(':')[0])
    fim_h = int(h_fim.split(':')[0])
    ini_m = int(h_ini.split(':')[1])
    fim_m = int(h_fim.split(':')[1])

    # "das 8 as 8" = 8am ate 8pm = 12h (regra de construcao — 99% dos casos)
    if ini_h == fim_h and ini_m == fim_m:
        return 12.0, "08:00", "20:00", False

    # Turno noturno: inicio > fim (ex: 20h ate 6h) — só aceita se contexto indicar
    # Por padrao (construcao diurna) nao assumimos turno noturno

    # Fim antes do inicio -> assume que passou da meia-noite ou PM nao foi detectado
    if fim_h < ini_h:
        fim_h += 12  # tenta corrigir (ex: inicio=8h fim=4h -> fim=16h)
        if fim_h > 23: fim_h -= 12  # se passar de 23, desfaz

    total_min = (fim_h * 60 + fim_m) - (ini_h * 60 + ini_m)
    if total_min <= 0: return None, h_ini, h_fim, True

    return round(total_min / 60, 2), h_ini, f"{fim_h:02d}:{fim_m:02d}", False

def hora_e_ambigua(texto_hora, contexto_completo=None):
    """
    Retorna True se o horario precisa de confirmacao AM/PM.
    Regra: se nao tem indicador explicito E numero esta entre 1-12, e ambiguo.
    Excecao: se o contexto_completo mencionar 'manha', 'noite', 'am', 'pm'.
    """
    if not texto_hora: return True
    t = str(texto_hora).lower()
    ctx = str(contexto_completo or '').lower()

    # Indicador explicito no horario ou no contexto -> nao ambiguo
    indicadores = ['am','pm','manha','manhã','noite','tarde','a.m','p.m']
    if any(x in t for x in indicadores): return False
    # 'h' no final do numero (ex: 8h, 16h) indica formato 24h -> nao ambiguo
    if re.search(r'\d+h', t): return False
    if any(x in ctx for x in indicadores): return False

    # Numero >= 13 -> claramente 24h, nao ambiguo
    nums = re.findall(r'\d+', t)
    if not nums: return True
    n = int(nums[0])
    if n >= 13: return False
    if n == 0 or n == 12: return False  # meia-noite e meio-dia sao claros

    # 1-11 sem indicador -> ambiguo (precisa confirmar)
    return True

def normalizar_valor(texto):
    """Extrai valor numerico de qualquer formato."""
    if not texto: return 0
    t = str(texto).replace('$','').replace(',','.').strip()
    nums = re.findall(r'\d+\.?\d*', t)
    return float(nums[0]) if nums else 0

def normalizar_socio(texto, fallback='Gerson'):
    """Extrai socio do texto. Prioriza nome explicito."""
    if not texto: return fallback
    t = texto.lower()
    if 'carlos' in t: return 'Carlos'
    if 'gerson' in t: return 'Gerson'
    return fallback

def calcular_data_prazo(texto):
    hoje = datetime.datetime.now()
    t = texto.lower().strip()
    if any(p in t for p in ['nao', 'não', 'indefinido', 'sem prazo', 'nd']): return 'Indefinido'
    m = re.search(r'(\d+)\s*dia', t)
    if m: return (hoje + datetime.timedelta(days=int(m.group(1)))).strftime("%d/%m/%Y")
    m = re.search(r'(\d+)\s*semana', t)
    if m: return (hoje + datetime.timedelta(weeks=int(m.group(1)))).strftime("%d/%m/%Y")
    if 'fim do mes' in t or 'final do mes' in t:
        ultimo = (hoje.replace(day=1) + datetime.timedelta(days=32)).replace(day=1) - datetime.timedelta(days=1)
        return ultimo.strftime("%d/%m/%Y")
    meses = {'janeiro': 1, 'fevereiro': 2, 'marco': 3, 'abril': 4, 'maio': 5, 'junho': 6,
             'julho': 7, 'agosto': 8, 'setembro': 9, 'outubro': 10, 'novembro': 11, 'dezembro': 12}
    for nome, num in meses.items():
        if nome in t:
            ano = hoje.year if num >= hoje.month else hoje.year + 1
            ultimo = (datetime.datetime(ano, num, 1) + datetime.timedelta(days=32)).replace(day=1) - datetime.timedelta(days=1)
            return ultimo.strftime("%d/%m/%Y")
    m = re.search(r'(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{2,4})', t)
    if m:
        d, mo, a = m.groups()
        if len(a) == 2: a = '20' + a
        return f"{d.zfill(2)}/{mo.zfill(2)}/{a}"
    return texto

def calcular_percentual_checklist(obra):
    if obra not in checklists: return 0, 0, 0
    cl = checklists[obra]
    f1 = cl.get('fase1', {}); f2 = cl.get('fase2', {})
    tf1 = len(f1); tf2 = len(f2)
    ff1 = sum(1 for v in f1.values() if v)
    ff2 = sum(1 for v in f2.values() if v)
    total = tf1 + tf2; feitos = ff1 + ff2
    return (
        round(feitos / total * 100) if total > 0 else 0,
        round(ff1 / tf1 * 100) if tf1 > 0 else 0,
        round(ff2 / tf2 * 100) if tf2 > 0 else 0
    )

def criar_checklist_obra(obra, tipo="geral"):
    template = CHECKLIST_PADRAO.get(tipo, CHECKLIST_PADRAO["geral"])
    checklists[obra] = {
        "fase1": {item: False for item in template["fase1"]},
        "fase2": {item: False for item in template["fase2"]}
    }
    salvar_dados()

def buscar_obra_por_cliente(nome):
    nl = nome.lower()
    for c, o in clientes.items():
        if nl in c.lower() or c.lower() in nl: return o
    return None

def buscar_obra_por_nome(nome):
    if not nome: return None
    nl = nome.lower()
    for o in obras_ativas:
        if nl in o.lower() or o.lower() in nl: return o
    return None

def identificar_socio(update, texto_mensagem=None):
    """Identifica socio pelo Telegram ID (100% confiavel) ou pelo texto."""
    user_id = update.effective_user.id

    # 1. Texto menciona explicitamente outro socio -> respeita (ex: "registra 8h pro carlos")
    if texto_mensagem:
        t = texto_mensagem.lower()
        # So troca se for referencia explicita a terceiro (nao primeira pessoa)
        primeira_pessoa = any(p in t for p in [
            'para mim', 'pra mim', ' mim', 'eu trabalhei', 'eu fiz',
            'minhas horas', 'meu horario', 'eu entrei', 'eu sai',
            'eu almocei', 'eu gastei', 'eu comprei', 'eu paguei',
            'i worked', 'i spent', 'i paid', 'i got', 'my hours', 'for me',
        ])
        if not primeira_pessoa:
            if 'carlos' in t: return 'Carlos'
            if 'gerson' in t: return 'Gerson'

    # 2. ID fixo no mapa -> identificacao perfeita
    if user_id in SOCIOS_IDS:
        return SOCIOS_IDS[user_id]

    # 3. Fallback pelo nome do Telegram
    nome = update.effective_user.first_name.lower()
    if 'gerson' in nome: return 'Gerson'
    if 'carlos' in nome: return 'Carlos'
    return update.effective_user.first_name

def ultimo_dia_mes(data: datetime.datetime) -> int:
    """Retorna o último dia do mês de forma confiável para qualquer mês."""
    return (data.replace(day=1) + datetime.timedelta(days=32)).replace(day=1) - datetime.timedelta(days=1)

# ─── GOOGLE ───────────────────────────────

def get_creds():
    import os
    from google_auth_oauthlib.flow import InstalledAppFlow
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            from google.auth.transport.requests import Request
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as t:
            t.write(creds.to_json())
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return creds

def conectar_sheets():
    return build('sheets', 'v4', credentials=get_creds())

def conectar_drive():
    return build('drive', 'v3', credentials=get_creds())

def criar_aba_events_se_nao_existir():
    """Verifica e cria a aba EVENTS se não existir. Chamada durante inicialização."""
    try:
        sheets = conectar_sheets()
        planilha = sheets.spreadsheets().get(spreadsheetId=obter_ou_criar_planilha()).execute()
        abas = [s['properties']['title'] for s in planilha.get('sheets', [])]

        if 'EVENTS' not in abas:
            sheets.spreadsheets().batchUpdate(
                spreadsheetId=obter_ou_criar_planilha(),
                body={'requests': [{'addSheet': {'properties': {'title': 'EVENTS'}}}]}
            ).execute()

            headers = [['event_id', 'timestamp', 'user_id', 'user_name',
                        'message_text', 'message_type', 'intent_llm', 'intent_final',
                        'action_taken', 'action_payload', 'confirmed', 'success', 'error_message']]
            sheets.spreadsheets().values().update(
                spreadsheetId=obter_ou_criar_planilha(),
                range='EVENTS!A1:M1',
                valueInputOption='RAW',
                body={'values': headers}
            ).execute()
            logger.info("Aba EVENTS criada com sucesso.")
        else:
            logger.info("Aba EVENTS já existe.")
    except Exception as e:
        logger.error(f"Erro ao criar aba EVENTS: {e}")

def obter_ou_criar_planilha():
    global SHEET_ID
    if SHEET_ID:
        return SHEET_ID
    if os.path.exists('sheet_id.txt'):
        with open('sheet_id.txt') as f:
            SHEET_ID = f.read().strip()
        return SHEET_ID
    drive = conectar_drive()
    res = drive.files().list(
        q=f"name='{EMPRESA} - Financeiro' and mimeType='application/vnd.google-apps.spreadsheet'",
        fields="files(id)"
    ).execute()
    arquivos = res.get('files', [])
    if arquivos:
        SHEET_ID = arquivos[0]['id']
    else:
        sheets = conectar_sheets()
        planilha = {
            'properties': {'title': f'{EMPRESA} - Financeiro'},
            'sheets': [
                {'properties': {'title': 'Despesas'}},
                {'properties': {'title': 'Banco de Horas'}},
                {'properties': {'title': 'Obras'}},
                {'properties': {'title': 'Pagamentos Cliente'}},
                {'properties': {'title': 'Lista de Compras'}},
                {'properties': {'title': 'Midias'}},
            ]
        }
        res = sheets.spreadsheets().create(body=planilha).execute()
        SHEET_ID = res['spreadsheetId']
        headers = [
            ('Despesas!A1:H1', [['Data', 'Enviado por', 'Categoria', 'Descricao', 'Valor ($)', 'Desconto de', 'Obra', 'Tipo']]),
            ('Banco de Horas!A1:G1', [['Data', 'Socio', 'Horas', 'Valor ($)', 'Hora Inicio', 'Hora Fim', 'Obra']]),
            ('Obras!A1:J1', [['Nome', 'Cliente', 'Contrato ($)', 'Pago ($)', 'Saldo ($)', 'Orcamento', 'Status', 'Inicio', 'Prazo', 'Checklist %']]),
            ('Pagamentos Cliente!A1:E1', [['Data', 'Obra', 'Cliente', 'Valor ($)', 'Observacao']]),
            ('Lista de Compras!A1:F1', [['Data', 'Obra', 'Item', 'Quantidade', 'Valor Est.', 'Comprado']]),
            ('Midias!A1:E1', [['Data', 'Obra', 'Tipo', 'Link', 'Enviado por']]),
        ]
        for range_, vals in headers:
            sheets.spreadsheets().values().update(
                spreadsheetId=SHEET_ID, range=range_,
                valueInputOption='RAW', body={'values': vals}
            ).execute()
    with open('sheet_id.txt', 'w') as f:
        f.write(SHEET_ID)
    return SHEET_ID

def sheets_append(range_, values, user_data=None, undo_label=None):
    res = conectar_sheets().spreadsheets().values().append(
        spreadsheetId=obter_ou_criar_planilha(), range=range_,
        valueInputOption='RAW', insertDataOption='INSERT_ROWS',
        body={'values': values}
    ).execute()
    if user_data is not None:
        # Captura o indice da linha inserida para undo
        updated = res.get('updates', {}).get('updatedRange', '')
        row_index = None
        if updated:
            import re as _re
            m = _re.search(r'(\d+)$', updated)
            if m:
                row_index = int(m.group(1))
        aba = range_.split('!')[0]
        registrar_undo(user_data, aba, 'append', row_index=row_index, valores=values[0] if values else [])
    return res

def sheets_get(range_):
    return conectar_sheets().spreadsheets().values().get(
        spreadsheetId=obter_ou_criar_planilha(), range=range_
    ).execute().get('values', [])

def sheets_batch_get(ranges):
    res = conectar_sheets().spreadsheets().values().batchGet(
        spreadsheetId=obter_ou_criar_planilha(), ranges=ranges
    ).execute()
    return [r.get('values', []) for r in res.get('valueRanges', [])]

# ─── EVENTS (ML) ──────────────────────────

async def registrar_evento(update: Update, context: ContextTypes.DEFAULT_TYPE,
                           intent_llm=None, intent_final=None,
                           action_taken=None, success=True, error=None):
    """Registra cada interação na aba EVENTS para dataset de ML."""
    try:
        msg = update.message or (update.callback_query.message if update.callback_query else None)
        texto = msg.text if msg and msg.text else None
        tipo = 'texto' if texto else ('callback' if update.callback_query else 'midia')

        row = [
            str(uuid.uuid4()),
            datetime.datetime.now().isoformat(),
            update.effective_user.id,
            update.effective_user.first_name,
            texto,
            tipo,
            intent_llm or '',
            intent_final or '',
            action_taken or '',
            json.dumps(context.user_data.get('ultima_acao', {}), ensure_ascii=False),
            context.user_data.get('acao_confirmada', False),
            success,
            str(error) if error else ''
        ]
        sheets_append('EVENTS!A:M', [row])
    except Exception as e:
        logger.error(f"Erro ao registrar evento ML: {e}")

# ─── AÇÕES NO BANCO DE DADOS ──────────────

def acao_registrar_despesa(socio, categoria, descricao, valor, desconto, obra, tipo='Despesa Empresa', user_data=None):
    data = datetime.datetime.now().strftime("%d/%m/%Y")
    sheets_append('Despesas!A:H', [[data, socio, categoria, descricao, valor, desconto, obra, tipo]], user_data=user_data)
    return f"Despesa registrada: {categoria} - {descricao} ${valor} | Obra: {obra}"

def acao_registrar_horas(socio, horas, obra, hora_inicio='', hora_fim='', user_data=None):
    data = datetime.datetime.now().strftime("%d/%m/%Y")
    valor = round(horas * VALOR_HORA, 2)
    sheets_append('Banco de Horas!A:G', [[data, socio, horas, valor, hora_inicio, hora_fim, obra]], user_data=user_data)
    return valor

def acao_corrigir_horas(socio, total_novo, obra):
    """
    Corrige o total de horas de um socio em uma obra no mes atual.
    Nao soma - apaga os registros do mes e grava o total correto.
    Protecoes: nunca apaga linha 1 (header), match estrito de obra e socio.
    """
    if total_novo < 0: total_novo = 0
    mes = datetime.datetime.now().strftime("%m/%Y")
    svc = conectar_sheets()
    sheet_id = obter_ou_criar_planilha()
    aba_id = _get_sheet_id_by_name('Banco de Horas', svc, sheet_id)
    dados = sheets_get('Banco de Horas!A:G')

    # Match estrito: socio igual (case insensitive) + obra igual normalizada + mes
    obra_norm = obra.lower().strip()
    socio_norm = socio.lower().strip()

    linhas_deletar = []
    for i, l in enumerate(dados):
        if i == 0: continue  # NUNCA apaga o header (linha 1)
        if len(l) < 7: continue
        data_cel = l[0] if len(l) > 0 else ''
        socio_cel = l[1].lower().strip() if len(l) > 1 else ''
        obra_cel = l[6].lower().strip() if len(l) > 6 else ''

        if (mes in data_cel and
            socio_cel == socio_norm and
            (obra_norm in obra_cel or obra_cel in obra_norm)):
            linhas_deletar.append(i + 1)  # 1-indexed (i=0 e linha 1, i=1 e linha 2...)

    logger.info(f"corrigir_horas: {socio} | {obra} | deletando {len(linhas_deletar)} linhas | novo total: {total_novo}h")

    # Deleta de tras pra frente para nao deslocar indices
    for row in sorted(linhas_deletar, reverse=True):
        if row <= 1: continue  # protecao extra contra header
        try:
            svc.spreadsheets().batchUpdate(
                spreadsheetId=sheet_id,
                body={'requests': [{'deleteDimension': {
                    'range': {'sheetId': aba_id,
                              'dimension': 'ROWS',
                              'startIndex': row - 1,
                              'endIndex': row}
                }}]}
            ).execute()
        except Exception as e:
            logger.error(f"Erro ao deletar linha {row}: {e}")

    # Grava o total correto
    if total_novo > 0:
        data = datetime.datetime.now().strftime("%d/%m/%Y")
        valor = round(total_novo * VALOR_HORA, 2)
        sheets_append('Banco de Horas!A:G', [[data, socio, total_novo, valor, '', '', obra]])
        return valor
    return 0

def _get_sheet_id_by_name(nome_aba, svc, sheet_id):
    """Retorna o sheetId numerico de uma aba pelo nome."""
    meta = svc.spreadsheets().get(spreadsheetId=sheet_id).execute()
    for s in meta.get('sheets', []):
        if s['properties']['title'] == nome_aba:
            return s['properties']['sheetId']
    return 0

def acao_cadastrar_obra(nome, cliente, contrato, pago, orcamento, prazo):
    data = datetime.datetime.now().strftime("%d/%m/%Y")
    saldo = contrato - pago
    sheets_append('Obras!A:J', [[nome, cliente, contrato, pago, saldo, orcamento, 'Em andamento', data, prazo, '0%']])
    if nome not in obras_ativas: obras_ativas.append(nome)
    if cliente: clientes[cliente.lower()] = nome
    tipo = "upgrade_service" if any(p in nome.lower() for p in ['service', 'painel', 'panel', 'upgrade']) else "geral"
    criar_checklist_obra(nome, tipo)
    salvar_dados()
    return saldo

def acao_registrar_pagamento(obra, cliente, valor, user_data=None):
    data = datetime.datetime.now().strftime("%d/%m/%Y")
    sheets_append('Pagamentos Cliente!A:E', [[data, obra, cliente, valor, '']], user_data=user_data)
    obras = sheets_get('Obras!A:J')
    svc = conectar_sheets()
    for i, linha in enumerate(obras):
        if len(linha) >= 1 and linha[0].lower() == obra.lower():
            row = i + 1
            pago_atual = extrair_numero(linha[3]) if len(linha) > 3 else 0
            contrato = extrair_numero(linha[2]) if len(linha) > 2 else 0
            novo_pago = pago_atual + valor
            novo_saldo = contrato - novo_pago
            svc.spreadsheets().values().update(
                spreadsheetId=obter_ou_criar_planilha(),
                range=f'Obras!D{row}:E{row}',
                valueInputOption='RAW', body={'values': [[novo_pago, novo_saldo]]}
            ).execute()
            return novo_saldo
    return 0

def acao_ticar_checklist(obra, etapa_texto):
    if obra not in checklists: return None, None
    cl = checklists[obra]
    for fase_key in ['fase1', 'fase2']:
        for item in cl[fase_key]:
            if etapa_texto.lower() in item.lower():
                cl[fase_key][item] = True
                salvar_dados()
                pct, _, _ = calcular_percentual_checklist(obra)
                obras = sheets_get('Obras!A:J')
                svc = conectar_sheets()
                for i, linha in enumerate(obras):
                    if len(linha) >= 1 and linha[0].lower() == obra.lower():
                        svc.spreadsheets().values().update(
                            spreadsheetId=obter_ou_criar_planilha(),
                            range=f'Obras!J{i + 1}',
                            valueInputOption='RAW', body={'values': [[f'{pct}%']]}
                        ).execute()
                        break
                return item, fase_key
    return None, None

def acao_adicionar_compras(obra, itens):
    data = datetime.datetime.now().strftime("%d/%m/%Y")
    if obra not in lista_compras: lista_compras[obra] = []
    for item in itens:
        sheets_append('Lista de Compras!A:F',
                      [[data, obra, item['item'], item.get('quantidade', '1'), item.get('valor_est', 0), 'Nao']])
        lista_compras[obra].append({
            'item': item['item'], 'qtd': item.get('quantidade', '1'),
            'valor': item.get('valor_est', 0), 'comprado': False
        })
    salvar_dados()

def get_info_obra(nome):
    obras = sheets_get('Obras!A:J')
    for linha in obras[1:]:
        if len(linha) >= 1 and nome.lower() in linha[0].lower(): return linha
    return None

def get_resumo_dados():
    try:
        mes = datetime.datetime.now().strftime("%m/%Y")
        despesas, horas, obras_sheet = sheets_batch_get(['Despesas!A:H', 'Banco de Horas!A:G', 'Obras!A:J'])
        total = 0; dg = 0; dc = 0; hg = 0; hc = 0; vg = 0; vc = 0
        for l in despesas[1:]:
            if len(l) >= 5 and mes in l[0]:
                v = extrair_numero(l[4]); total += v
                d = l[5] if len(l) > 5 else ''
                if 'Gerson' in d: dg += v
                elif 'Carlos' in d: dc += v
        for l in horas[1:]:
            if len(l) >= 4 and mes in l[0]:
                h = extrair_numero(l[2]); v = extrair_numero(l[3])
                if l[1] == 'Gerson': hg += h; vg += v
                elif l[1] == 'Carlos': hc += h; vc += v
        total_saldo = 0; obras_res = []
        for l in obras_sheet[1:]:
            if len(l) >= 1 and l[0].strip():
                status = l[6] if len(l) > 6 else 'Em andamento'
                if 'Concluida' in status: continue
                contrato = extrair_numero(l[2]) if len(l) > 2 else 0
                pago = extrair_numero(l[3]) if len(l) > 3 else 0
                saldo = extrair_numero(l[4]) if len(l) > 4 else 0
                total_saldo += saldo
                obras_res.append(f"  {l[0]}: contrato ${contrato:.0f} | pago ${pago:.0f} | saldo ${saldo:.0f}")
        return {'mes': mes, 'total': total, 'dg': dg, 'dc': dc,
                'hg': hg, 'hc': hc, 'vg': vg, 'vc': vc,
                'total_saldo': total_saldo, 'obras': obras_res}
    except Exception as e:
        logger.error(f"Erro resumo: {e}")
        return None

def get_resumo_texto():
    d = get_resumo_dados()
    if not d: return "Erro ao buscar dados."
    obras_txt = "\n".join(d['obras']) if d['obras'] else "  Nenhuma obra ativa"
    return (
        f"Resumo {d['mes']} - {EMPRESA}\n\n"
        f"Despesas: ${d['total']:.2f}\n"
        f"  Desconto Gerson: ${d['dg']:.2f}\n"
        f"  Desconto Carlos: ${d['dc']:.2f}\n\n"
        f"Banco de Horas:\n"
        f"  Gerson: {d['hg']}h = ${d['vg']:.2f}\n"
        f"  Carlos: {d['hc']}h = ${d['vc']:.2f}\n\n"
        f"Saldo liquido:\n"
        f"  Gerson: ${d['vg'] - d['dg']:.2f}\n"
        f"  Carlos: ${d['vc'] - d['dc']:.2f}\n\n"
        f"A receber: ${d['total_saldo']:.2f}\n{obras_txt}"
    )

def salvar_midia_drive(caminho, nome_arquivo, obra, tipo, socio):
    """Salva mídia no Drive e registra na aba Midias. Retorna link ou None."""
    try:
        drive = conectar_drive()
        mes = datetime.datetime.now().strftime("%Y-%m")
        parent_id = None
        for parte in f"{EMPRESA}/Obras/{obra}/{mes}".split('/'):
            query = f"name='{parte}' and mimeType='application/vnd.google-apps.folder'"
            if parent_id: query += f" and '{parent_id}' in parents"
            res = drive.files().list(q=query, fields="files(id)").execute()
            if res.get('files'):
                parent_id = res['files'][0]['id']
            else:
                meta = {'name': parte, 'mimeType': 'application/vnd.google-apps.folder'}
                if parent_id: meta['parents'] = [parent_id]
                parent_id = drive.files().create(body=meta, fields='id').execute()['id']
        mime = 'image/jpeg' if tipo == 'foto' else 'video/mp4'
        arquivo = drive.files().create(
            body={'name': nome_arquivo, 'parents': [parent_id]},
            media_body=MediaFileUpload(caminho, mimetype=mime),
            fields='webViewLink'
        ).execute()
        link = arquivo.get('webViewLink', '')
        # Registrar na aba Midias
        data = datetime.datetime.now().strftime("%d/%m/%Y")
        sheets_append('Midias!A:E', [[data, obra, tipo, link, socio]])
        return link
    except Exception as e:
        logger.error(f"Erro ao salvar mídia no Drive: {e}")
        return None

# ─── PDF ───────────────────────────────────

def gerar_pdf():
    mes = datetime.datetime.now().strftime("%m/%Y")
    mes_nome = datetime.datetime.now().strftime("%B %Y")
    despesas, horas, obras_sheet = sheets_batch_get(['Despesas!A:H', 'Banco de Horas!A:G', 'Obras!A:J'])
    nome_pdf = f"Relatorio_{EMPRESA}_{mes.replace('/', '_')}.pdf"
    doc = SimpleDocTemplate(nome_pdf, pagesize=letter)
    styles = getSampleStyleSheet()
    el = []
    el.append(Paragraph(f"{EMPRESA} - {mes_nome}", styles['Title']))
    el.append(Spacer(1, 12))

    el.append(Paragraph("OBRAS", styles['Heading2']))
    tab_data = [['Nome', 'Cliente', 'Contrato', 'Pago', 'Saldo', 'Status', '%']]
    for l in obras_sheet[1:]:
        if len(l) >= 5:
            tab_data.append([l[0], l[1] if len(l) > 1 else '',
                              f"${extrair_numero(l[2]):.0f}", f"${extrair_numero(l[3]):.0f}",
                              f"${extrair_numero(l[4]):.0f}", l[6] if len(l) > 6 else '',
                              l[9] if len(l) > 9 else '0%'])
    t = Table(tab_data, colWidths=[90, 80, 60, 60, 60, 80, 45])
    t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                            ('FONTSIZE', (0, 0), (-1, -1), 8),
                            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])]))
    el.append(t); el.append(Spacer(1, 12))

    el.append(Paragraph("DESPESAS", styles['Heading2']))
    tab_data = [['Data', 'Categoria', 'Descricao', 'Valor', 'Desconto', 'Obra']]
    total = 0; dg = 0; dc = 0
    for l in despesas[1:]:
        if len(l) >= 5 and mes in l[0]:
            v = extrair_numero(l[4]); total += v
            desc = l[5] if len(l) > 5 else ''
            if 'Gerson' in desc: dg += v
            elif 'Carlos' in desc: dc += v
            tab_data.append([l[0], l[2] if len(l) > 2 else '',
                              l[3][:22] if len(l) > 3 else '', f"${v:.2f}", desc,
                              l[6] if len(l) > 6 else ''])
    t = Table(tab_data, colWidths=[58, 68, 110, 52, 72, 72])
    t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.darkred),
                            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                            ('FONTSIZE', (0, 0), (-1, -1), 8),
                            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])]))
    el.append(t)
    el.append(Paragraph(f"Total: ${total:.2f} | Gerson: ${dg:.2f} | Carlos: ${dc:.2f}", styles['Normal']))
    el.append(Spacer(1, 12))

    el.append(Paragraph("BANCO DE HORAS", styles['Heading2']))
    tab_data = [['Data', 'Socio', 'Horas', 'Valor', 'Obra']]
    hg = 0; hc = 0; vg = 0; vc = 0
    for l in horas[1:]:
        if len(l) >= 4 and mes in l[0]:
            h = extrair_numero(l[2]); v = extrair_numero(l[3])
            if l[1] == 'Gerson': hg += h; vg += v
            elif l[1] == 'Carlos': hc += h; vc += v
            tab_data.append([l[0], l[1], f"{h}h", f"${v:.2f}", l[6] if len(l) > 6 else ''])
    t = Table(tab_data, colWidths=[70, 70, 60, 70, 210])
    t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.darkgreen),
                            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                            ('FONTSIZE', (0, 0), (-1, -1), 8),
                            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])]))
    el.append(t); el.append(Spacer(1, 12))

    el.append(Paragraph("RESUMO", styles['Heading2']))
    t = Table([['Socio', 'Horas', 'Valor', 'Descontos', 'Liquido'],
               ['Gerson', f"{hg}h", f"${vg:.2f}", f"${dg:.2f}", f"${vg - dg:.2f}"],
               ['Carlos', f"{hc}h", f"${vc:.2f}", f"${dc:.2f}", f"${vc - dc:.2f}"]],
              colWidths=[80, 60, 90, 90, 100])
    t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.darkorange),
                            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                            ('FONTSIZE', (0, 0), (-1, -1), 10),
                            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold')]))
    el.append(t)
    doc.build(el)
    return nome_pdf

# ─── CALENDAR ─────────────────────────────

def criar_evento(titulo, inicio, fim, descricao=''):
    service = build('calendar', 'v3', credentials=get_creds())
    service.events().insert(calendarId='primary', body={
        'summary': titulo, 'description': descricao,
        'start': {'dateTime': inicio, 'timeZone': 'America/New_York'},
        'end': {'dateTime': fim, 'timeZone': 'America/New_York'},
        'reminders': {'useDefault': False, 'overrides': [
            {'method': 'popup', 'minutes': 60},
            {'method': 'popup', 'minutes': 10}
        ]}
    }).execute()

def listar_eventos():
    service = build('calendar', 'v3', credentials=get_creds())
    agora = datetime.datetime.now(datetime.timezone.utc).isoformat()
    eventos = service.events().list(
        calendarId='primary', timeMin=agora,
        maxResults=5, singleEvents=True, orderBy='startTime'
    ).execute().get('items', [])
    if not eventos: return "Nenhum evento."
    return "Proximos eventos:\n" + "\n".join(
        f"- {e['summary']} | {e['start'].get('dateTime', e['start'].get('date'))}"
        for e in eventos
    )

# ─── IMAGEM E ÁUDIO ───────────────────────

def analisar_imagem(caminho):
    try:
        with open(caminho, 'rb') as f:
            img_b64 = base64.b64encode(f.read()).decode('utf-8')
        payload = {
            "model": "meta-llama/llama-4-scout-17b-16e-instruct",
            "messages": [{"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
                {"type": "text", "text": (
                    'Analise esta imagem. Se compra/nota/pedido online: '
                    '{"tipo":"compra","valor":total,"categoria":"Material/Ferramenta/Alimentacao/Combustivel","descricao":"produto","e_combustivel":false}. '
                    'Se Zelle/transferencia: {"tipo":"zelle","valor":numero,"funcionario":"nome"}. '
                    'Se foto de obra: {"tipo":"obra"}. '
                    'Retorne APENAS o JSON.'
                )}
            ]}],
            "max_tokens": 300
        }
        res = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json=payload
        )
        texto = res.json()['choices'][0]['message']['content'].strip().replace('```json', '').replace('```', '').strip()
        return json.loads(texto)
    except Exception as e:
        logger.error(f"Erro ao analisar imagem: {e}")
        return None

def transcrever_audio(caminho):
    with open(caminho, 'rb') as f: audio = f.read()
    return groq_client.audio.transcriptions.create(
        file=(caminho, audio), model="whisper-large-v3", language="pt"
    ).text

# ─── CÉREBRO DA IA ────────────────────────

def construir_contexto_empresa():
    hoje = datetime.datetime.now()
    obras_str = json.dumps(obras_ativas, ensure_ascii=False) if obras_ativas else "nenhuma"
    clientes_str = json.dumps(list(clientes.keys()), ensure_ascii=False) if clientes else "nenhum"

    compras_pendentes = {}
    for obra, itens in lista_compras.items():
        pendentes = [i for i in itens if not i.get('comprado')]
        if pendentes:
            compras_pendentes[obra] = [i['item'] for i in pendentes]

    checklist_status = {}
    for obra in obras_ativas:
        pct, pct_f1, pct_f2 = calcular_percentual_checklist(obra)
        checklist_status[obra] = f"Total:{pct}% Fase1:{pct_f1}% Fase2:{pct_f2}%"

    try:
        obras_sheet = sheets_get('Obras!A:J')
        obras_detalhe = {}
        for l in obras_sheet[1:]:
            if len(l) >= 5:
                obras_detalhe[l[0]] = {
                    "cliente": l[1] if len(l) > 1 else "",
                    "contrato": extrair_numero(l[2]) if len(l) > 2 else 0,
                    "pago": extrair_numero(l[3]) if len(l) > 3 else 0,
                    "saldo": extrair_numero(l[4]) if len(l) > 4 else 0,
                    "status": l[6] if len(l) > 6 else "",
                    "prazo": l[8] if len(l) > 8 else ""
                }
    except:
        obras_detalhe = {}

    partes = [
        f"Assistente da {EMPRESA}, eletrica e construcao nos EUA.",
        f"Hoje: {hoje.strftime('%d/%m/%Y')}. Socios: Gerson e Carlos. Hora: ${VALOR_HORA}.",
        f"Obras: {obras_str}",
        f"Detalhes: {json.dumps(obras_detalhe, ensure_ascii=False)}",
        f"Clientes: {clientes_str}",
        f"Checklists: {json.dumps(checklist_status, ensure_ascii=False)}",
        f"Compras pendentes: {json.dumps(compras_pendentes, ensure_ascii=False)}",
        "",
        "REGRAS:",
        "- Responda em portugues, curto e direto. Sem apresentacoes, sem 'claro!', sem 'posso ajudar?', sem repeticoes.",
        "- Extraia tudo da mensagem e do historico. Nao pergunte o que ja foi dito.",
        "- Se faltar algo essencial, pergunte UMA coisa so, sem rodeios.",
        "- SOCIO: REGRA CRITICA — extraia o socio DIRETAMENTE do texto. Se disser Carlos, use Carlos. Se disser Gerson, use Gerson.",
        "  NUNCA troque o socio. Se o usuario disse Carlos e voce esta prestes a usar Gerson, PARE e corrija.",
        "  Se nao mencionou nenhum, use o contexto da conversa anterior. Se ainda assim duvidoso, pergunte.",
        "- REMOVER/CORRIGIR HORAS: use acao corrigir_horas com o total final. Ex: 'remova 10h do carlos que tem 30h' -> total=20.",
        "  'Carlos fez 30 horas' -> corrigir_horas socio=Carlos total=30.",
        "  Nunca some valor negativo. Sempre calcule o total correto e use corrigir_horas.",
        "- HORARIO: normalize SEMPRE para formato 24h antes de gravar.",
        "  Exemplos: 8h=08:00 | 8am=08:00 | 8 da manha=08:00 | 8pm=20:00 | 8 da noite=20:00 | 20h=20:00",
        "  Se disser das X as Y: calcule a diferenca. das 8 as 16 = 8h. das 7 as 15 = 8h.",
        "  REGRA ESPECIAL: 'das 8 as 8' sem indicar AM/PM = 8am ate 8pm = 12h. Use senso comum de construcao.",
        "  Se genuinamente ambiguo (ex: 'trabalhei ate as 8' sem mais contexto) -> pergunte: 'As 8 da manha ou da noite?'",
        "  Nunca pergunte se ja ficou claro pelo contexto.",
        "- Home Depot/Lowes = Material | restaurante = Alimentacao | posto/gas = Combustivel",
        "- Combustivel: pergunte de quem e se nao informado.",
        "- Obra nao mencionada em despesa: pergunte qual.",
        "- pagou metade = 50% do contrato.",
        "- Orcamento/pago nao mencionado = 0.",
        "",
        "ACOES — inclua JSON entre |||JSON e ||| para executar:",
        "|||JSON",
        '{"acao": "registrar_horas", "socio": "Carlos", "horas": 8, "obra": "Randolph"}',
        "|||",
        "",
        "ACOES DISPONIVEIS:",
        "- registrar_horas: socio, horas, obra, hora_inicio(opt), hora_fim(opt)",
        "- editar_horas: socio, horas(novo valor), obra  -- USE para: corrigir ontem / corrigir ultimo lancamento",
        "- editar_horas: socio, horas(novo valor), obra  -- USE para: corrigir ontem / corrigir ultimo lancamento",
        "- corrigir_horas: socio, total(numero final correto), obra  -- USE quando: remover horas / corrigir total / usuario diz 'fez X horas no mes'",
        "- cadastrar_obra: nome, cliente, contrato, pago, orcamento, prazo",
        "- registrar_pagamento: obra, cliente, valor",
        "- registrar_despesa: socio, categoria, descricao, valor, desconto(Empresa/Gerson/Carlos), obra",
        "- ticar_checklist: obra, etapa",
        "- adicionar_compras: obra, itens:[{item, quantidade, valor_est}]",
        "- criar_evento: titulo, data_inicio(ISO), data_fim(ISO)",
        "- mostrar_resumo | mostrar_obras | mostrar_checklist: obra | mostrar_compras: obra",
        "- gerar_pdf | mostrar_agenda | gerar_mensagem_cliente: obra, tipo(progresso/cobranca/conclusao)",
    ]
    return "\n".join(partes)


# ─── HELPERS DE TECLADO ───────────────────

def teclado_confirmar_acao(acao_resumo: str) -> InlineKeyboardMarkup:
    """Gera teclado inline de confirmação para ações financeiras."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Confirmar", callback_data="confirmar_acao"),
            InlineKeyboardButton("❌ Cancelar", callback_data="cancelar_acao")
        ]
    ])

def teclado_obras() -> InlineKeyboardMarkup | None:
    """Gera teclado inline com obras ativas (máximo 8). Retorna None se lista vazia."""
    if not obras_ativas:
        return None
    botoes = []
    for obra in obras_ativas[:8]:
        # Prefixo 'obra_' para identificar no callback
        botoes.append([InlineKeyboardButton(obra, callback_data=f"obra_{obra}")])
    botoes.append([InlineKeyboardButton("❌ Cancelar", callback_data="cancelar_midia")])
    return InlineKeyboardMarkup(botoes)

# ─── INTERCEPTADORES (executam antes do LLM) ──────────

def interceptar_correcao_horas(texto, socio_fallback):
    """
    Detecta por regex quando o usuario quer CORRIGIR/REMOVER horas.
    NAO intercepta: adicionar, registrar, add, lanca.
    Patterns cobertos:
      - "remova/tira/retire X horas"
      - "corrige para Y horas" / "eram Y horas" / "sao Y horas"
      - "carlos/gerson fez Y horas esse mes"
    """
    t = texto.lower().strip()
    socio = normalizar_socio(texto, socio_fallback)

    # Palavras que indicam ADICAO — se presente, nao intercepta
    palavras_adicao = ['adicione', 'adicionar', 'adiciona', 'registra', 'registre',
                       'registrar', 'lanca', 'lance', 'lancar', 'coloca', 'add ']
    if any(p in t for p in palavras_adicao):
        return None

    # Padrao: "remova/tira/retire X horas"
    m = re.search(r'(?:remov|tir[ae]|retir)[a-z]*\s+(\d+(?:\.\d+)?)\s*h', t)
    if m:
        obra = _extrair_obra_do_texto(t)
        return {"acao": "corrigir_horas", "socio": socio,
                "remover": float(m.group(1)), "obra": obra or "", "total": -1}

    # Padrao: "corrige para Y horas" / "eram Y horas" / "sao Y horas" / "foram Y horas"
    m = re.search(r'(?:corrig[a-z]*\s+para|total\s+de|fez\s+(?:um\s+)?total\s+de|eram|sao|foram|e\s+ao\s+todo)\s+(\d+(?:\.\d+)?)\s*h', t)
    if m:
        obra = _extrair_obra_do_texto(t)
        return {"acao": "corrigir_horas", "socio": socio,
                "total": float(m.group(1)), "obra": obra or ""}

    # Padrao: "carlos fez 30 horas esse mes" / "gerson fez 30h"
    m = re.search(r'(?:gerson|carlos)\s+fez\s+(\d+(?:\.\d+)?)\s*h', t)
    if m:
        obra = _extrair_obra_do_texto(t)
        return {"acao": "corrigir_horas", "socio": socio,
                "total": float(m.group(1)), "obra": obra or ""}

    return None

def _extrair_obra_do_texto(texto):
    """Tenta extrair nome de obra do texto usando obras_ativas."""
    t = texto.lower()
    melhor = None
    for obra in obras_ativas:
        if obra.lower() in t:
            melhor = obra
            break
    return melhor

def interceptar_periodo_incompleto(texto):
    """
    Detecta quando usuario menciona fim de periodo sem inicio.
    Ex: 'trabalhei ate as 8', 'sai as 17', 'cheguei as 18'
    Retorna dict com pergunta ou None.
    """
    t = texto.lower().strip()
    # Palavras que indicam fim sem inicio
    triggers = ['ate as', 'até as', 'sai as', 'saí as', 'saiu as',
                'cheguei as', 'terminou as', 'acabei as', 'parei as']
    if any(tr in t for tr in triggers):
        m = re.search(r'(\d{1,2})(?:[:\.]\d{2})?\s*h?', t)
        hora_fim = m.group(0) if m else '?'
        return {
            "tipo": "periodo_incompleto",
            "hora_fim_raw": hora_fim,
            "pergunta": f"Que horas comecastes? (saida: {hora_fim})"
        }
    return None

def executar_correcao_com_total(intercept, total_atual, socio, obra):
    """Calcula total final quando a acao era 'remover X horas'."""
    remover = intercept.get('remover', 0)
    total_novo = max(0, total_atual - remover)
    return {"acao": "corrigir_horas", "socio": socio, "total": total_novo, "obra": obra}


# ─── PROCESSADOR IA ───────────────────────

historicos = {}

async def detectar_intencao_llm(texto, obras_ativas, historico):
    """
    Claude Haiku detecta intencao — nunca executa, nunca toca em dados.
    Retorna string com a intencao.
    """
    obras_str = ", ".join(obras_ativas) if obras_ativas else "nenhuma"
    prompt_intencao = f"""Voce identifica intencoes de mensagens de um app de gestao de construcao.
Obras ativas: {obras_str}
Socios: Gerson e Carlos

Responda APENAS com UMA das intencoes abaixo (so a palavra, sem explicacao):
- registrar_horas
- registrar_despesa
- registrar_pagamento
- cadastrar_obra
- atualizar_obra
- ticar_checklist
- adicionar_compras
- criar_evento
- gerar_mensagem
- mostrar_resumo
- mostrar_horas
- mostrar_obras
- mostrar_checklist
- mostrar_compras
- mostrar_agenda
- corrigir_horas
- undo
- conversa

Mensagem: {texto}
Intencao:"""

    intencoes_validas = [
        "registrar_horas", "registrar_despesa", "registrar_pagamento",
        "cadastrar_obra", "atualizar_obra", "ticar_checklist",
        "adicionar_compras", "criar_evento", "gerar_mensagem",
        "mostrar_resumo", "mostrar_horas", "mostrar_obras",
        "mostrar_checklist", "mostrar_compras", "mostrar_agenda",
        "corrigir_horas", "undo", "conversa"
    ]

    # Claude Haiku — rapido, barato, muito melhor em PT/EN misturado
    try:
        resp = anthropic_client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=20,
            messages=[{"role": "user", "content": prompt_intencao}]
        )
        intencao = resp.content[0].text.strip().lower().replace(" ", "_")
        for iv in intencoes_validas:
            if iv in intencao:
                return iv
        return "conversa"
    except Exception as e:
        logger.error(f"Claude Haiku falhou: {e}")
        # Fallback para Groq se Claude falhar
        try:
            resp_fallback = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt_intencao}],
                max_tokens=20
            )
            intencao = resp_fallback.choices[0].message.content.strip().lower().replace(" ", "_")
            for iv in intencoes_validas:
                if iv in intencao:
                    return iv
        except Exception as e2:
            logger.error(f"Fallback Groq tambem falhou: {e2}")
        return "conversa"


async def conduzir_fluxo(intencao, texto, socio, update, context):
    """
    Codigo puro conduz o fluxo para cada intencao.
    Nunca depende do LLM para extrair dados — sempre pergunta se faltar.
    """
    obras = obras_ativas
    obras_str = ", ".join(obras) if obras else "nenhuma"

    if intencao == "registrar_horas":
        # Tenta extrair da mensagem
        intercept = interceptar_horas_expandido(texto, socio)
        if intercept and intercept.get('obra') and intercept.get('horas'):
            return await executar_acao(intercept, socio, update, context)
        # Falta dados — inicia fluxo guiado
        payload = intercept or {"acao": "registrar_horas", "socio": socio}
        if not payload.get('obra'):
            context.user_data['pendencia_ativa'] = criar_pendencia(
                'pendencia_obra', payload, f"Em qual obra? ({obras_str})")
            return f"Em qual obra? ({obras_str})"
        if not payload.get('horas'):
            context.user_data['pendencia_ativa'] = criar_pendencia(
                'pendencia_horas', payload, "Quantas horas?")
            return "Quantas horas voce trabalhou?"
        return await executar_acao(payload, socio, update, context)

    if intencao == "registrar_despesa":
        intercept = interceptar_despesa(texto, socio) or interceptar_despesa_en(texto, socio)
        if intercept and intercept.get('valor', 0) > 0:
            if not intercept.get('obra'):
                context.user_data['pendencia_ativa'] = criar_pendencia(
                    'pendencia_obra', intercept, f"Em qual obra? ({obras_str})")
                return f"Em qual obra? ({obras_str})"
            # Pede confirmacao
            context.user_data['acao_pendente'] = intercept
            context.user_data['socio_pendente'] = socio
            resumo = (f"💸 Despesa\nCategoria: {intercept.get('categoria','?')}\n"
                      f"Descricao: {intercept.get('descricao','?')}\n"
                      f"Valor: ${intercept.get('valor',0):.2f}\n"
                      f"Obra: {intercept.get('obra') or 'Geral'}")
            from telegram import InlineKeyboardMarkup, InlineKeyboardButton
            tk = InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ Confirmar", callback_data="confirmar_acao"),
                InlineKeyboardButton("❌ Cancelar", callback_data="cancelar_acao")]])
            await update.message.reply_text(f"🔍 Confirme:\n\n{resumo}", reply_markup=tk)
            return None
        # Nao conseguiu extrair — pergunta
        context.user_data['pendencia_ativa'] = criar_pendencia(
            'pendencia_despesa', {"acao": "registrar_despesa", "socio": socio},
            "Qual o valor da despesa?")
        return "Qual o valor? E em qual obra?"

    if intencao == "registrar_pagamento":
        try:
            obras_info = {}
            for l in sheets_get('Obras!A:J')[1:]:
                if len(l) >= 5:
                    obras_info[l[0].lower()] = {
                        'contrato': extrair_numero(l[2]), 'pago': extrair_numero(l[3]),
                        'saldo': extrair_numero(l[4]), 'cliente': l[1] if len(l) > 1 else ''}
        except: obras_info = {}
        intercept = interceptar_pagamento(texto, obras_info) or interceptar_pagamento_en(texto, obras_info)
        if intercept and intercept.get('valor', 0) > 0:
            if not intercept.get('obra'):
                context.user_data['pendencia_ativa'] = criar_pendencia(
                    'pendencia_obra', intercept, f"De qual obra? ({obras_str})")
                return f"De qual obra e esse pagamento? ({obras_str})"
            intercept.pop('_origem', '')
            context.user_data['acao_pendente'] = intercept
            context.user_data['socio_pendente'] = socio
            resumo = (f"💰 Pagamento\nObra: {intercept.get('obra','?')}\n"
                      f"Valor: ${intercept.get('valor',0):.2f}")
            from telegram import InlineKeyboardMarkup, InlineKeyboardButton
            tk = InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ Confirmar", callback_data="confirmar_acao"),
                InlineKeyboardButton("❌ Cancelar", callback_data="cancelar_acao")]])
            await update.message.reply_text(f"🔍 Confirme:\n\n{resumo}", reply_markup=tk)
            return None
        context.user_data['pendencia_ativa'] = criar_pendencia(
            'pendencia_pagamento', {"acao": "registrar_pagamento"},
            f"Qual o valor recebido? De qual obra? ({obras_str})")
        return f"Qual o valor recebido? De qual obra? ({obras_str})"

    if intencao == "cadastrar_obra":
        import re as _re
        # Extrai dados da mensagem inicial
        dados = {"acao": "cadastrar_obra"}
        
        # Extrai nome
        m = _re.search(r'(?:obra|job|projeto|project|nova|new)\s+(?:em\s+|in\s+|de\s+)?(\w+)', texto, _re.I)
        if m: dados['nome'] = m.group(1).capitalize()
        
        # Extrai cliente
        m = _re.search(r'cliente\s+(\w+)', texto, _re.I)
        if m: dados['cliente'] = m.group(1).capitalize()
        
        # Extrai contrato
        m = _re.search(r'(?:contrato|valor|contract)\s+\$?([\d,.]+)', texto, _re.I)
        if m: dados['contrato'] = float(m.group(1).replace(',', ''))
        
        # Extrai prazo
        m = _re.search(r'prazo\s+(.+?)(?:\s+contrato|$)', texto, _re.I)
        if m: dados['prazo'] = m.group(1).strip()
        
        # Se tem tudo necessario, cadastra direto
        if dados.get('nome') and dados.get('cliente') and dados.get('contrato'):
            dados.setdefault('pago', 0)
            dados.setdefault('orcamento', 0)
            dados.setdefault('prazo', 'Indefinido')
            return await executar_acao(dados, socio, update, context)
        
        # Falta nome — pergunta primeiro
        if not dados.get('nome'):
            context.user_data['pendencia_ativa'] = criar_pendencia(
                'pendencia_cadastro_obra', dados, "Qual o nome da obra/job?")
            return "Qual o nome da obra/job?"
        
        # Tem nome, falta cliente
        if not dados.get('cliente'):
            context.user_data['pendencia_ativa'] = criar_pendencia(
                'pendencia_cadastro_cliente', dados, f"Obra: {dados['nome']}\nQual o nome do cliente?")
            return f"Cadastrando obra \"{dados['nome']}\"\nQual o nome do cliente?"
        
        # Tem nome e cliente, falta contrato
        if not dados.get('contrato'):
            context.user_data['pendencia_ativa'] = criar_pendencia(
                'pendencia_cadastro_contrato', dados, f"Qual o valor do contrato para {dados['nome']}?")
            return f"Qual o valor do contrato para {dados['nome']}?"

    if intencao == "corrigir_horas":
        intercept = interceptar_correcao_horas(texto, socio)
        if intercept:
            if not intercept.get('obra'):
                context.user_data['pendencia_ativa'] = criar_pendencia(
                    'pendencia_correcao', intercept, f"Em qual obra? ({obras_str})")
                return f"Em qual obra? ({obras_str})"
            return await executar_acao(intercept, socio, update, context)
        context.user_data['pendencia_ativa'] = criar_pendencia(
            'pendencia_correcao', {"acao": "corrigir_horas", "socio": socio},
            "Qual o total correto de horas?")
        return "Qual o total correto de horas? Em qual obra?"

    if intencao == "undo":
        entrada = pop_undo(context.user_data)
        if not entrada: return "Nada para desfazer."
        await cmd_undo(update, context)
        return None

    if intencao == "mostrar_resumo":
        return get_resumo_texto()

    if intencao == "mostrar_horas":
        await cmd_horas(update, context)
        return None

    if intencao == "mostrar_obras":
        await cmd_obras(update, context)
        return None

    if intencao == "mostrar_agenda":
        await cmd_agenda(update, context)
        return None

    if intencao == "ticar_checklist":
        obra = _extrair_obra_do_texto(texto.lower())
        if not obra:
            context.user_data['pendencia_ativa'] = criar_pendencia(
                'pendencia_obra', {"acao": "ticar_checklist"},
                f"Em qual obra? ({obras_str})")
            return f"Em qual obra? ({obras_str})"
        return await executar_acao({"acao": "ticar_checklist", "obra": obra, "etapa": texto}, socio, update, context)

    if intencao == "mostrar_checklist":
        obra = _extrair_obra_do_texto(texto.lower())
        if not obra:
            context.user_data['pendencia_ativa'] = criar_pendencia(
                'pendencia_obra', {"acao": "mostrar_checklist"},
                f"Em qual obra? ({obras_str})")
            return f"Em qual obra? ({obras_str})"
        return await executar_acao({"acao": "mostrar_checklist", "obra": obra}, socio, update, context)

    if intencao == "adicionar_compras":
        obra = _extrair_obra_do_texto(texto.lower())
        if not obra:
            context.user_data['pendencia_ativa'] = criar_pendencia(
                'pendencia_obra', {"acao": "adicionar_compras", "texto_original": texto},
                f"Em qual obra? ({obras_str})")
            return f"Em qual obra? ({obras_str})"
        return await executar_acao({"acao": "adicionar_compras", "obra": obra, "texto": texto}, socio, update, context)

    if intencao == "criar_evento":
        return await executar_acao({"acao": "criar_evento", "texto": texto}, socio, update, context)

    if intencao == "gerar_mensagem":
        obra = _extrair_obra_do_texto(texto.lower())
        tipo = "progresso"
        if any(p in texto.lower() for p in ['cobr', 'pagar', 'pagamento', 'invoice']): tipo = "cobranca"
        if any(p in texto.lower() for p in ['conclu', 'finaliz', 'done', 'finish']): tipo = "conclusao"
        return await executar_acao({"acao": "gerar_mensagem_cliente", "obra": obra or "", "tipo": tipo}, socio, update, context)

    # conversa ou intencao desconhecida
    return "Nao entendi. Pode ser mais especifico? Ex: \'trabalhei 8h na Randolph\', \'gastei $50 no home depot\', \'recebi $1000 da Quincy\'"


async def processar_com_ia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler principal. Fluxo:
    1. Resolve pendencia ativa se houver
    2. Roda interceptadores de codigo (rapido, sem LLM)
    3. LLM detecta APENAS intencao
    4. Codigo executa o fluxo da intencao
    """
    texto = update.message.text.strip()
    socio = identificar_socio(update, texto)

    # ── Maquina de pendencias de cadastro de obra ──
    if context.user_data.get('pendencia_ativa'):
        pend = context.user_data['pendencia_ativa']
        tipo_pend = pend.get('tipo', '')
        
        if tipo_pend in ('pendencia_cadastro_obra', 'pendencia_cadastro_cliente', 'pendencia_cadastro_contrato'):
            payload = dict(pend.get('payload', {}))
            
            if tipo_pend == 'pendencia_cadastro_obra':
                # Resposta e o nome da obra
                payload['nome'] = texto.strip().capitalize()
                context.user_data['pendencia_ativa'] = criar_pendencia(
                    'pendencia_cadastro_cliente', payload, f"Qual o nome do cliente?")
                await update.message.reply_text(f"Obra: {payload['nome']}\nQual o nome do cliente?")
                return
            
            if tipo_pend == 'pendencia_cadastro_cliente':
                # Resposta e o nome do cliente
                payload['cliente'] = texto.strip().capitalize()
                context.user_data['pendencia_ativa'] = criar_pendencia(
                    'pendencia_cadastro_contrato', payload, f"Qual o valor do contrato?")
                await update.message.reply_text(f"Cliente: {payload['cliente']}\nQual o valor do contrato?")
                return
            
            if tipo_pend == 'pendencia_cadastro_contrato':
                # Resposta e o valor do contrato
                import re as _re
                nums = _re.findall(r'[\d,.]+', texto)
                if nums:
                    payload['contrato'] = float(nums[0].replace(',', ''))
                    payload.setdefault('pago', 0)
                    payload.setdefault('orcamento', 0)
                    payload.setdefault('prazo', 'Indefinido')
                    context.user_data.pop('pendencia_ativa', None)
                    resultado = await executar_acao(payload, socio, update, context)
                    if resultado: await update.message.reply_text(resultado)
                else:
                    await update.message.reply_text("Qual o valor do contrato? (ex: 15000, $12500)")
                return

    # ── Maquina de pendencias ──
    if context.user_data.get('pendencia_ativa'):
        payload_resolvido, followup = resolver_pendencia(context.user_data, texto)
        if followup:
            await update.message.reply_text(followup)
            return
        if payload_resolvido:
            resultado = await executar_acao(payload_resolvido, socio, update, context)
            if resultado: await update.message.reply_text(resultado)
            return

    context.user_data['ultimo_texto'] = texto

    # ── Interceptadores de codigo (sem LLM) ──

    # Undo
    if interceptar_undo(texto):
        await cmd_undo(update, context)
        return

    # Consultas rapidas
    consulta = interceptar_consulta(texto)
    if consulta:
        acao_q = consulta.get('acao')
        if acao_q == 'mostrar_resumo':
            await update.message.reply_text(get_resumo_texto()); return
        if acao_q == 'mostrar_horas':
            await cmd_horas(update, context); return
        if acao_q == 'mostrar_obras':
            await cmd_obras(update, context); return

    # Horas PT
    intercept_horas = interceptar_horas_expandido(texto, socio)
    if intercept_horas:
        if intercept_horas.get('acao') == 'registrar_horas_ambos':
            horas_ab = intercept_horas.get('horas', 8)
            obra_ab = intercept_horas.get('obra', '')
            if not obra_ab:
                context.user_data['pendencia_ativa'] = criar_pendencia(
                    'pendencia_obra', intercept_horas,
                    "Em qual obra? (" + (", ".join(obras_ativas) or "nenhuma") + ")")
                await update.message.reply_text("Em qual obra?"); return
            await executar_acao({"acao":"registrar_horas","socio":"Gerson","horas":horas_ab,"obra":obra_ab}, "Gerson", update, context)
            await executar_acao({"acao":"registrar_horas","socio":"Carlos","horas":horas_ab,"obra":obra_ab}, "Carlos", update, context)
            await update.message.reply_text(f"✅ {horas_ab}h | Gerson e Carlos | {obra_ab}"); return
        if not intercept_horas.get('obra'):
            context.user_data['pendencia_ativa'] = criar_pendencia(
                'pendencia_obra', intercept_horas,
                "Em qual obra? (" + (", ".join(obras_ativas) or "nenhuma") + ")")
            await update.message.reply_text("Em qual obra? (" + (", ".join(obras_ativas) or "nenhuma") + ")"); return
        r = await executar_acao(intercept_horas, socio, update, context)
        if r: await update.message.reply_text(r)
        return

    # Horas EN
    intercept_h_en = interceptar_horas_en(texto, socio)
    if intercept_h_en:
        if not intercept_h_en.get('obra'):
            context.user_data['pendencia_ativa'] = criar_pendencia(
                'pendencia_obra', intercept_h_en,
                "Em qual obra? (" + (", ".join(obras_ativas) or "nenhuma") + ")")
            await update.message.reply_text("Em qual obra?"); return
        r = await executar_acao(intercept_h_en, socio, update, context)
        if r: await update.message.reply_text(r)
        return

    # Periodo incompleto
    intercept_p = interceptar_periodo_incompleto(texto)
    if intercept_p:
        payload_p = {"acao": "registrar_horas", "socio": socio,
                     "hora_fim_raw": intercept_p.get("hora_fim_raw", ""),
                     "hora_inicio_raw": intercept_p.get("hora_inicio_raw", "")}
        context.user_data['pendencia_ativa'] = criar_pendencia(
            'pendencia_horario', payload_p, intercept_p.get("pergunta", "Que horas?"))
        context.user_data['pendencia_ativa']['subtipo'] = 'sem_inicio' if intercept_p.get('hora_fim_raw') else 'sem_fim'
        await update.message.reply_text(intercept_p.get("pergunta", "Que horas?")); return

    # Correcao horas
    intercept_cor = interceptar_correcao_horas(texto, socio)
    if intercept_cor:
        if not intercept_cor.get('obra'):
            context.user_data['pendencia_ativa'] = criar_pendencia(
                'pendencia_correcao', intercept_cor,
                "Em qual obra? (" + (", ".join(obras_ativas) or "nenhuma") + ")")
            await update.message.reply_text("Em qual obra?"); return
        r = await executar_acao(intercept_cor, socio, update, context)
        if r: await update.message.reply_text(r)
        return

    # Despesa PT
    intercept_desp = interceptar_despesa(texto, socio)
    if intercept_desp and intercept_desp.get('valor', 0) > 0:
        if not intercept_desp.get('obra'):
            context.user_data['pendencia_ativa'] = criar_pendencia(
                'pendencia_obra', intercept_desp,
                "Em qual obra? (" + (", ".join(obras_ativas) or "nenhuma") + ")")
            await update.message.reply_text("Em qual obra?"); return
        context.user_data['acao_pendente'] = intercept_desp
        context.user_data['socio_pendente'] = socio
        resumo = (f"💸 Despesa\nCategoria: {intercept_desp.get('categoria','?')}\n"
                  f"Valor: ${intercept_desp.get('valor',0):.2f}\nObra: {intercept_desp.get('obra','?')}")
        from telegram import InlineKeyboardMarkup, InlineKeyboardButton
        tk = InlineKeyboardMarkup([[InlineKeyboardButton("✅ Confirmar", callback_data="confirmar_acao"),
                                    InlineKeyboardButton("❌ Cancelar", callback_data="cancelar_acao")]])
        await update.message.reply_text(f"🔍 Confirme:\n\n{resumo}", reply_markup=tk); return

    # Despesa EN
    intercept_d_en = interceptar_despesa_en(texto, socio)
    if intercept_d_en and intercept_d_en.get('valor', 0) > 0:
        if not intercept_d_en.get('obra'):
            context.user_data['pendencia_ativa'] = criar_pendencia(
                'pendencia_obra', intercept_d_en,
                "Em qual obra? (" + (", ".join(obras_ativas) or "nenhuma") + ")")
            await update.message.reply_text("Em qual obra?"); return
        context.user_data['acao_pendente'] = intercept_d_en
        context.user_data['socio_pendente'] = socio
        resumo2 = (f"💸 Despesa\nCategoria: {intercept_d_en.get('categoria','?')}\n"
                   f"Valor: ${intercept_d_en.get('valor',0):.2f}\nObra: {intercept_d_en.get('obra','?')}")
        from telegram import InlineKeyboardMarkup, InlineKeyboardButton
        tk2 = InlineKeyboardMarkup([[InlineKeyboardButton("✅ Confirmar", callback_data="confirmar_acao"),
                                     InlineKeyboardButton("❌ Cancelar", callback_data="cancelar_acao")]])
        await update.message.reply_text(f"🔍 Confirme:\n\n{resumo2}", reply_markup=tk2); return

    # Pagamento PT/EN
    try:
        obras_info_pag = {}
        for l in sheets_get('Obras!A:J')[1:]:
            if len(l) >= 5:
                obras_info_pag[l[0].lower()] = {
                    'contrato': extrair_numero(l[2]), 'pago': extrair_numero(l[3]),
                    'saldo': extrair_numero(l[4]), 'cliente': l[1] if len(l) > 1 else ''}
    except: obras_info_pag = {}

    t_low = texto.lower()
    intercept_pag = None
    if any(p in t_low for p in ['zelle', 'venmo', 'recebi', 'pagou', 'transferiu',
                                  'depositou', 'mandou', 'enviou', 'check de', 'cash de',
                                  'wire', 'got paid', 'received', 'client paid']):
        intercept_pag = interceptar_pagamento(texto, obras_info_pag) or interceptar_pagamento_en(texto, obras_info_pag)

    if intercept_pag and intercept_pag.get('valor', 0) > 0:
        if not intercept_pag.get('obra'):
            context.user_data['pendencia_ativa'] = criar_pendencia(
                'pendencia_obra', intercept_pag,
                "De qual obra? (" + (", ".join(obras_ativas) or "nenhuma") + ")")
            await update.message.reply_text("De qual obra e esse pagamento?"); return
        intercept_pag.pop('_origem', '')
        context.user_data['acao_pendente'] = intercept_pag
        context.user_data['socio_pendente'] = socio
        resumo3 = (f"💰 Pagamento\nObra: {intercept_pag.get('obra','?')}\n"
                   f"Valor: ${intercept_pag.get('valor',0):.2f}")
        from telegram import InlineKeyboardMarkup, InlineKeyboardButton
        tk3 = InlineKeyboardMarkup([[InlineKeyboardButton("✅ Confirmar", callback_data="confirmar_acao"),
                                     InlineKeyboardButton("❌ Cancelar", callback_data="cancelar_acao")]])
        await update.message.reply_text(f"🔍 Confirme:\n\n{resumo3}", reply_markup=tk3); return

    # ── LLM: detecta APENAS intencao ──
    try:
        intencao = await detectar_intencao_llm(texto, obras_ativas, [])
        logger.info(f"LLM intencao: {intencao}")
        resultado = await conduzir_fluxo(intencao, texto, socio, update, context)
        if resultado:
            await update.message.reply_text(resultado)
    except Exception as e:
        logger.error(f"Erro processar_com_ia: {e}")
        await update.message.reply_text("Nao entendi. Tente: 'trabalhei 8h na Randolph', 'gastei $50 no home depot', 'recebi $1000 da Quincy'")


async def processar_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler central para todos os callbacks de botões inline."""
    query = update.callback_query
    await query.answer()
    data = query.data

    # ── Confirmação financeira ──
    if data == "confirmar_acao":
        acao_pendente = context.user_data.get('acao_pendente')
        socio = context.user_data.get('socio_pendente', 'Desconhecido')

        if not acao_pendente:
            await query.edit_message_text("⚠️ Ação expirada. Tente novamente.")
            return

        try:
            resultado = await executar_acao(acao_pendente, socio, update, context)
            context.user_data['acao_confirmada'] = True
            context.user_data.pop('aguardando_confirmacao', None)
            await query.edit_message_text(f"✅ Confirmado!\n\n{resultado or 'Ação executada.'}")
            await registrar_evento(update, context,
                                   intent_final=acao_pendente.get('acao'),
                                   action_taken=acao_pendente.get('acao'),
                                   success=True)
        except Exception as e:
            logger.error(f"Erro ao executar ação confirmada: {e}")
            await query.edit_message_text(f"❌ Erro ao executar: {str(e)}")
            await registrar_evento(update, context, success=False, error=e)
        finally:
            context.user_data.pop('acao_pendente', None)
            context.user_data.pop('socio_pendente', None)

    elif data == "cancelar_acao":
        acao_pendente = context.user_data.pop('acao_pendente', {})
        context.user_data.pop('socio_pendente', None)
        context.user_data.pop('aguardando_confirmacao', None)
        context.user_data['acao_confirmada'] = False
        await query.edit_message_text("❌ Ação cancelada.")
        await registrar_evento(update, context,
                               intent_final=acao_pendente.get('acao', 'desconhecido'),
                               action_taken='cancelado',
                               success=False,
                               error='Cancelado pelo usuário')

    # ── Seleção de obra para mídia ──
    elif data.startswith("obra_"):
        nome_obra = data[5:]  # Remove prefixo 'obra_'
        midia = context.user_data.get('midia_pendente')

        if not midia:
            await query.edit_message_text("⚠️ Sessão expirada. Envie a mídia novamente.")
            return

        await query.edit_message_text(f"⏳ Salvando no Drive... obra: {nome_obra}")

        link = salvar_midia_drive(
            midia['caminho'],
            os.path.basename(midia['caminho']),
            nome_obra,
            midia.get('tipo', 'foto'),
            midia.get('socio', '')
        )

        # Limpar arquivo temporário independente de sucesso
        if os.path.exists(midia['caminho']):
            os.remove(midia['caminho'])
        context.user_data.pop('midia_pendente', None)

        if link:
            await query.edit_message_text(f"✅ Salvo em {nome_obra}!\n🔗 {link}")
            await registrar_evento(update, context,
                                   intent_final='salvar_midia',
                                   action_taken=f"salvar_{midia.get('tipo', 'foto')}",
                                   success=True)
        else:
            await query.edit_message_text("❌ Erro ao salvar no Drive. Verifique os logs.")
            await registrar_evento(update, context,
                                   intent_final='salvar_midia',
                                   action_taken='erro_upload',
                                   success=False,
                                   error='Falha no upload para o Drive')

    elif data == "cancelar_midia":
        midia = context.user_data.pop('midia_pendente', None)
        if midia and os.path.exists(midia.get('caminho', '')):
            os.remove(midia['caminho'])
        await query.edit_message_text("❌ Envio cancelado.")

# ─── EXECUTAR AÇÃO ────────────────────────

async def executar_acao(d, socio, update, context):
    acao = d.get('acao')

    # ── Validacao central — roda antes de qualquer gravacao ──
    texto_original = context.user_data.get('ultimo_texto', '')
    try:
        validar_acao(d, texto_original)
    except ValidationError as ve:
        # Falta dado essencial — pergunta e nao grava
        # Cria pendencia generica para resolver depois
        tipo = TIPOS_PENDENCIA.get('obra') if 'obra' in ve.pergunta.lower() else TIPOS_PENDENCIA.get('valor', 'pendencia_valor')
        context.user_data['pendencia_ativa'] = criar_pendencia(tipo, d, ve.pergunta)
        msg = update.message or (update.callback_query.message if update.callback_query else None)
        if msg:
            await msg.reply_text(ve.pergunta)
        return None
    except ValueError as ve:
        # Conflito critico (ex: socio errado) — loga e rejeita
        logger.error(f"Validacao falhou: {ve}")
        msg = update.message or (update.callback_query.message if update.callback_query else None)
        if msg:
            await msg.reply_text(f"⚠️ {str(ve)}")
        return None

    if acao == 'corrigir_horas':
        # Correcao explicita: "carlos fez 30 horas", "remova X horas", "corrija para Y horas"
        socio_acao = normalizar_socio(d.get('socio', ''), socio)
        total = float(d.get('total', 0))
        obra = d.get('obra', '')
        if not obra:
            # Obra obrigatoria para nao corrigir a errada
            context.user_data['corrigir_pendente'] = d
            obras_txt = ", ".join(obras_ativas) if obras_ativas else "nenhuma"
            return f"Em qual obra? ({obras_txt})"
        obra_real = buscar_obra_por_nome(obra) or obra
        if total < 0: total = 0
        valor = acao_corrigir_horas(socio_acao, total, obra_real)
        return f"✅ Horas corrigidas | {socio_acao} | {obra_real} | Total: {total}h = ${valor:.2f}"

    if acao == 'registrar_horas':
        obra = d.get('obra') or 'Geral'
        obra_real = buscar_obra_por_nome(obra) or obra
        inicio_raw = d.get('hora_inicio', '')
        fim_raw = d.get('hora_fim', '')
        horas_raw = d.get('horas', 0)

        # REGRA: so aceita periodo se o usuario forneceu inicio E fim
        # Nunca usa periodo "preenchido" pelo LLM (08:00-18:00 inventado)
        tem_periodo_real = bool(inicio_raw and fim_raw and
            inicio_raw not in ['08:00','08h','8:00'] or  # nao e default inventado
            (inicio_raw and fim_raw and d.get('periodo_confirmado')))  # ou foi confirmado

        if inicio_raw and fim_raw:
            horas_calc, h_ini, h_fim, ambiguo = calcular_horas_trabalhadas(inicio_raw, fim_raw)
            if ambiguo or horas_calc is None:
                context.user_data['horas_pendente'] = d
                return "Das " + str(inicio_raw) + " as " + str(fim_raw) + " — e da manha ou da noite?"
            horas = horas_calc
            inicio_fmt = h_ini
            fim_fmt = h_fim
        else:
            # Sem periodo: usa so as horas informadas, sem inventar horario
            horas = float(horas_raw) if horas_raw else 0
            inicio_fmt = ''
            fim_fmt = ''

        if not horas:
            context.user_data['horas_pendente'] = d
            return "Quantas horas?"

        # Validacao: socio nao pode trocar silenciosamente
        socio_acao = normalizar_socio(d.get('socio', ''), socio)

        valor = acao_registrar_horas(socio_acao, horas, obra_real, inicio_fmt, fim_fmt, user_data=context.user_data)
        return f"✅ {horas}h | {socio_acao} | {obra_real} | ${valor:.2f}" + (f" ({inicio_fmt}-{fim_fmt})" if inicio_fmt and fim_fmt else "")

    if acao == 'cadastrar_obra':
        nome = d.get('nome', '')
        cliente = d.get('cliente', '')
        contrato = float(d.get('contrato', 0))
        pago = float(d.get('pago', 0))
        orcamento = float(d.get('orcamento', 0))
        prazo = calcular_data_prazo(d.get('prazo', 'Indefinido'))
        saldo = acao_cadastrar_obra(nome, cliente, contrato, pago, orcamento, prazo)
        pct, _, _ = calcular_percentual_checklist(nome)
        barra = "▓" * (pct // 10) + "░" * (10 - pct // 10)
        return (
            f"✅ Obra cadastrada!\n\n"
            f"🏗 {nome} | Cliente: {cliente}\n"
            f"Contrato: ${contrato:.2f} | Pago: ${pago:.2f}\n"
            f"Saldo: ${saldo:.2f} | Prazo: {prazo}\n"
            f"Checklist: [{barra}] 0%"
        )

    if acao == 'registrar_pagamento':
        obra = d.get('obra', '')
        obra_real = buscar_obra_por_nome(obra) or obra
        cliente = d.get('cliente', '')
        valor = float(d.get('valor', 0))
        info = get_info_obra(obra_real)
        if not cliente and info and len(info) > 1: cliente = info[1]
        novo_saldo = acao_registrar_pagamento(obra_real, cliente, valor, user_data=context.user_data)
        return f"✅ Pagamento registrado!\nObra: {obra_real} | Valor: ${valor:.2f} | Novo saldo: ${novo_saldo:.2f}"

    if acao == 'registrar_despesa':
        valor = float(d.get('valor', 0))
        categoria = d.get('categoria', 'Material')
        descricao = d.get('descricao', '')
        desconto = d.get('desconto', 'Empresa')
        obra = d.get('obra', 'Geral')
        obra_real = buscar_obra_por_nome(obra) or obra
        msg = acao_registrar_despesa(socio, categoria, descricao, valor, desconto, obra_real, user_data=context.user_data)
        return f"✅ {msg}"

    if acao == 'ticar_checklist':
        obra = d.get('obra', '')
        obra_real = buscar_obra_por_nome(obra) or obra
        etapa = d.get('etapa', '')
        item, fase = acao_ticar_checklist(obra_real, etapa)
        if item:
            pct, pct_f1, pct_f2 = calcular_percentual_checklist(obra_real)
            barra = "▓" * (pct // 10) + "░" * (10 - pct // 10)
            msg = f"✅ '{item}' concluido!\n[{barra}] {pct}% | F1:{pct_f1}% F2:{pct_f2}%"
            if fase == 'fase1' and pct_f1 == 100:
                msg += "\n\n🎉 Fase 1 concluida! Partiu acabamento!"
            if pct == 100:
                msg += "\n\n🏆 OBRA 100% CONCLUIDA!"
            return msg
        return f"Etapa '{etapa}' nao encontrada. Use 'checklist {obra_real}' para ver as etapas."

    if acao == 'adicionar_compras':
        obra = d.get('obra', '')
        obra_real = buscar_obra_por_nome(obra) or obra
        itens = d.get('itens', [])
        acao_adicionar_compras(obra_real, itens)
        lista = "\n".join([f"  + {i.get('quantidade', '1')}x {i['item']}" for i in itens])
        return f"✅ Lista de compras - {obra_real}:\n{lista}"

    if acao == 'editar_horas':
        socio_acao = normalizar_socio(d.get('socio', ''), socio)
        obra = d.get('obra', '')
        obra_real = buscar_obra_por_nome(obra) or obra
        horas_novas = float(d.get('horas', 0))
        if not horas_novas:
            return "Quantas horas e o valor correto?"
        valor, erro = editar_ultimo_lancamento_horas(socio_acao, obra_real, horas_novas, context.user_data)
        if erro:
            return f"⚠️ {erro}"
        return f"✅ Ultimo lancamento editado | {socio_acao} | {obra_real} | {horas_novas}h = ${valor:.2f}"

    if acao == 'criar_evento':
        criar_evento(d.get('titulo', 'Evento'), d.get('data_inicio'), d.get('data_fim'), d.get('descricao', ''))
        return f"✅ Evento criado: {d.get('titulo')} | {str(d.get('data_inicio', ''))[:10]}"

    if acao == 'mostrar_resumo':
        return get_resumo_texto()

    if acao == 'mostrar_obras':
        obras_sheet = sheets_get('Obras!A:J')
        if len(obras_sheet) <= 1: return "Nenhuma obra cadastrada."
        msg = "Obras:\n\n"
        for l in obras_sheet[1:]:
            if len(l) < 1: continue
            pct, pct_f1, pct_f2 = calcular_percentual_checklist(l[0])
            barra = "▓" * (pct // 10) + "░" * (10 - pct // 10)
            msg += (
                f"🏗 {l[0]} | {l[1] if len(l) > 1 else 'N/A'}\n"
                f"  Contrato: ${extrair_numero(l[2]) if len(l) > 2 else 0:.2f} | "
                f"Saldo: ${extrair_numero(l[4]) if len(l) > 4 else 0:.2f}\n"
                f"  [{barra}] {pct}% | Prazo: {l[8] if len(l) > 8 else 'N/A'}\n\n"
            )
        return msg

    if acao == 'mostrar_checklist':
        obra = d.get('obra', '')
        obra_real = buscar_obra_por_nome(obra) or obra
        if obra_real not in checklists:
            tipo = "upgrade_service" if any(p in obra_real.lower() for p in ['service', 'painel', 'panel', 'upgrade']) else "geral"
            criar_checklist_obra(obra_real, tipo)
        cl = checklists.get(obra_real, {})
        pct, pct_f1, pct_f2 = calcular_percentual_checklist(obra_real)
        barra = "▓" * (pct // 10) + "░" * (10 - pct // 10)
        msg = f"Checklist: {obra_real}\n[{barra}] {pct}%\n\n"
        msg += f"FASE 1 - Instalacao ({pct_f1}%)\n"
        for item, feito in cl.get('fase1', {}).items():
            msg += f"{'✅' if feito else '⬜'} {item}\n"
        msg += f"\nFASE 2 - Acabamento ({pct_f2}%)\n"
        for item, feito in cl.get('fase2', {}).items():
            msg += f"{'✅' if feito else '⬜'} {item}\n"
        return msg

    if acao == 'mostrar_compras':
        obra = d.get('obra', '')
        obra_real = buscar_obra_por_nome(obra) or obra
        itens = lista_compras.get(obra_real, [])
        if not itens: return f"Lista vazia para {obra_real}."
        pendentes = [i for i in itens if not i.get('comprado')]
        comprados = [i for i in itens if i.get('comprado')]
        msg = f"Lista - {obra_real}:\n"
        if pendentes:
            msg += "\nPendentes:\n" + "\n".join([f"  ⬜ {i.get('qtd', '1')}x {i['item']}" for i in pendentes])
        if comprados:
            msg += "\nComprados:\n" + "\n".join([f"  ✅ {i.get('qtd', '1')}x {i['item']}" for i in comprados])
        return msg

    if acao == 'gerar_pdf':
        nome_pdf = gerar_pdf()
        msg = update.message or (update.callback_query.message if update.callback_query else None)
        if msg:
            with open(nome_pdf, 'rb') as f:
                await msg.reply_document(f, filename=nome_pdf)
        os.remove(nome_pdf)
        return None

    if acao == 'mostrar_agenda':
        return listar_eventos()

    if acao == 'gerar_mensagem_cliente':
        obra = d.get('obra', '')
        obra_real = buscar_obra_por_nome(obra) or obra
        tipo = d.get('tipo', 'progresso')
        info = get_info_obra(obra_real)
        pct, pct_f1, pct_f2 = calcular_percentual_checklist(obra_real)
        cliente = info[1] if info and len(info) > 1 else 'cliente'
        saldo = extrair_numero(info[4]) if info and len(info) > 4 else 0
        if tipo == 'progresso':
            prompt = f"Crie mensagem profissional em ingles para {cliente} sobre progresso da obra {obra_real}. Fase 1: {pct_f1}%, Fase 2: {pct_f2}%, Total: {pct}%. Breve e positivo."
        elif tipo == 'cobranca':
            prompt = f"Crie mensagem educada em ingles cobrando {cliente} o saldo de ${saldo:.2f} da obra {obra_real}. Direto e cordial."
        else:
            prompt = f"Crie mensagem em ingles informando {cliente} que obra {obra_real} foi concluida. Agradeca pela confianca."
        msg = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}]
        ).choices[0].message.content
        return f"Mensagem para {cliente}:\n\n{msg}"

    return None

# ─── HANDLERS TELEGRAM ────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not usuario_autorizado(update): return
    chat_id = update.effective_chat.id
    if chat_id not in CHAT_IDS: CHAT_IDS.append(chat_id)
    historicos[chat_id] = []
    await update.message.reply_text(
        f"Ola! Sou o assistente da {EMPRESA}.\n\n"
        f"Fale comigo naturalmente:\n"
        f"'quero adicionar uma obra em Milton, cliente Jorge'\n"
        f"'trabalhei 8h hoje na Randolph'\n"
        f"'Jorge pagou $3500 hoje'\n"
        f"'gastei $45 no Home Depot pra Randolph'\n"
        f"'preciso de 2 breakers 20amp pra Randolph'\n"
        f"'checklist da Randolph'\n"
        f"'conclui a instalacao do painel'\n\n"
        f"Ou mande foto, audio, video!\n\n"
        f"Comandos rapidos: /resumo /obras /pdf /agenda /horas"
    )

async def cmd_resumo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not usuario_autorizado(update): return
    await update.message.reply_text("Buscando dados...")
    await update.message.reply_text(get_resumo_texto())

async def cmd_obras(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not usuario_autorizado(update): return
    try:
        dados = sheets_get('Obras!A:J')
        if len(dados) <= 1:
            await update.message.reply_text("Nenhuma obra cadastrada.")
            return
        txt = "🏗 Obras ativas:\n\n"
        for l in dados[1:]:
            if not l or not l[0].strip(): continue
            status = l[6] if len(l) > 6 else 'Em andamento'
            if 'Concluida' in status: continue
            nome = l[0]
            cliente = l[1] if len(l) > 1 else ''
            contrato = extrair_numero(l[2]) if len(l) > 2 else 0
            pago = extrair_numero(l[3]) if len(l) > 3 else 0
            saldo = extrair_numero(l[4]) if len(l) > 4 else 0
            prazo = l[8] if len(l) > 8 else 'Indefinido'
            pct = l[9] if len(l) > 9 else '0%'
            txt += (f"📌 {nome}\n"
                    f"   Cliente: {cliente}\n"
                    f"   Contrato: ${contrato:.0f} | Pago: ${pago:.0f} | Saldo: ${saldo:.0f}\n"
                    f"   Prazo: {prazo} | Checklist: {pct}\n\n")
        await update.message.reply_text(txt or "Nenhuma obra ativa.")
    except Exception as e:
        logger.error(f"Erro cmd_obras: {e}")
        await update.message.reply_text(f"Erro ao buscar obras: {e}")

async def cmd_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not usuario_autorizado(update): return
    await update.message.reply_text("Gerando PDF...")
    try:
        nome_pdf = gerar_pdf()
        with open(nome_pdf, 'rb') as f:
            await update.message.reply_document(f, filename=nome_pdf)
        os.remove(nome_pdf)
    except Exception as e:
        logger.error(f"Erro ao gerar PDF: {e}")
        await update.message.reply_text(f"Erro: {str(e)}")

async def cmd_agenda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not usuario_autorizado(update): return
    await update.message.reply_text(listar_eventos())

async def cmd_corrigir_carlos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove todas as horas do Carlos neste mes (para corrigir lancamentos errados)."""
    if not usuario_autorizado(update): return
    mes = datetime.datetime.now().strftime("%m/%Y")
    try:
        dados = sheets_get('Banco de Horas!A:G')
        svc = conectar_sheets()
        sheet_id = obter_ou_criar_planilha()
        # Encontra linhas do Carlos neste mes (de tras pra frente)
        linhas_apagar = []
        for i, l in enumerate(dados):
            if i == 0: continue
            if len(l) >= 2 and l[1] == 'Carlos' and mes in (l[0] if l else ''):
                linhas_apagar.append(i + 1)
        if not linhas_apagar:
            await update.message.reply_text("Nenhuma hora do Carlos encontrada neste mes.")
            return
        # Apaga de tras pra frente
        for row in sorted(linhas_apagar, reverse=True):
            svc.spreadsheets().batchUpdate(
                spreadsheetId=sheet_id,
                body={'requests': [{'deleteDimension': {
                    'range': {'sheetId': 0, 'dimension': 'ROWS',
                              'startIndex': row - 1, 'endIndex': row}
                }}]}
            ).execute()
        await update.message.reply_text(f"✅ Removidas {len(linhas_apagar)} linha(s) do Carlos neste mes.")
    except Exception as e:
        logger.error(f"Erro corrigir_carlos: {e}")
        await update.message.reply_text(f"Erro: {e}")

async def cmd_undo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not usuario_autorizado(update): return
    entrada = pop_undo(context.user_data)
    if not entrada:
        await update.message.reply_text("Nada para desfazer.")
        return
    aba = entrada.get('aba')
    tipo = entrada.get('tipo')
    row = entrada.get('row_index')
    valores = entrada.get('valores', [])
    try:
        if tipo == 'append' and row:
            svc = conectar_sheets()
            sheet_id = obter_ou_criar_planilha()
            from core import _get_sheet_id_by_name
            aba_id = _get_sheet_id_by_name(aba, svc, sheet_id)
            svc.spreadsheets().batchUpdate(
                spreadsheetId=sheet_id,
                body={'requests': [{'deleteDimension': {
                    'range': {'sheetId': aba_id, 'dimension': 'ROWS',
                              'startIndex': row - 1, 'endIndex': row}
                }}]}
            ).execute()
            desc = valores[2] if len(valores) > 2 else str(valores)
            await update.message.reply_text(f"↩️ Desfeito: {aba} linha {row} ({desc})")
        elif tipo == 'update' and row:
            estado = entrada.get('estado_antes', [])
            if estado:
                svc = conectar_sheets()
                sheet_id = obter_ou_criar_planilha()
                svc.spreadsheets().values().update(
                    spreadsheetId=sheet_id,
                    range=f'{aba}!A{row}:{chr(64+len(estado))}{row}',
                    valueInputOption='RAW',
                    body={'values': [estado]}
                ).execute()
                await update.message.reply_text(f"↩️ Desfeito: {aba} linha {row} restaurada.")
            else:
                await update.message.reply_text("⚠️ Sem estado anterior salvo para restaurar.")
        else:
            await update.message.reply_text("⚠️ Este tipo de acao nao pode ser desfeita automaticamente.")
    except Exception as e:
        logger.error(f"Erro no undo: {e}")
        await update.message.reply_text(f"Erro ao desfazer: {str(e)}")

async def cmd_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not usuario_autorizado(update): return
    if os.path.exists('config.json'):
        with open('config.json') as f:
            cfg = json.load(f)
    else:
        cfg = {}
    txt = "⚙️ Config atual:\n\n"
    for k, v in cfg.items():
        txt += f"  {k}: {v}\n"
    txt += "\nPara alterar: /set_valor_hora 30"
    await update.message.reply_text(txt)

async def cmd_set_valor_hora(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not usuario_autorizado(update): return
    args = context.args
    if not args:
        await update.message.reply_text("Uso: /set_valor_hora 30")
        return
    try:
        novo_valor = float(args[0])
        if novo_valor <= 0:
            await update.message.reply_text("Valor deve ser maior que zero.")
            return
        salvar_config_key('valor_hora', novo_valor)
        await update.message.reply_text(f"✅ Valor hora atualizado: ${novo_valor:.2f}\nNovos lancamentos usam esse valor.")
    except ValueError:
        await update.message.reply_text("Valor invalido. Exemplo: /set_valor_hora 30")

async def cmd_horas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not usuario_autorizado(update): return
    try:
        mes = datetime.datetime.now().strftime("%m/%Y")
        dados = sheets_get('Banco de Horas!A:G')
        hg = hc = vg = vc = 0
        for l in dados[1:]:
            if len(l) >= 4 and mes in (l[0] if l else ''):
                h = extrair_numero(l[2]); v = extrair_numero(l[3])
                if len(l) > 1 and l[1] == 'Gerson': hg += h; vg += v
                elif len(l) > 1 and l[1] == 'Carlos': hc += h; vc += v
        txt = (f"⏱ Banco de Horas {mes}\n\n"
               f"Gerson: {hg}h = ${vg:.2f}\n"
               f"Carlos: {hc}h = ${vc:.2f}\n"
               f"Total: {hg+hc}h = ${vg+vc:.2f}")
        await update.message.reply_text(txt)
    except Exception as e:
        logger.error(f"Erro cmd_horas: {e}")
        await update.message.reply_text(f"Erro: {e}")
async def receber_texto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not usuario_autorizado(update): return
    chat_id = update.effective_chat.id
    if chat_id not in CHAT_IDS: CHAT_IDS.append(chat_id)
    if chat_id not in historicos: historicos[chat_id] = []
    await processar_com_ia(update, context)

async def receber_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not usuario_autorizado(update): return
    await update.message.reply_text("Transcrevendo...")
    audio = update.message.voice or update.message.audio
    arquivo = await audio.get_file()
    caminho = f"temp_audio_{update.message.message_id}.ogg"
    await arquivo.download_to_drive(caminho)
    try:
        texto = transcrever_audio(caminho)
        if os.path.exists(caminho): os.remove(caminho)
        await update.message.reply_text(f'Entendi: "{texto}"')
        chat_id = update.effective_chat.id
        if chat_id not in historicos: historicos[chat_id] = []
        context.user_data["ultimo_texto"] = texto
        await processar_com_ia(update, context)
    except Exception as e:
        logger.error(f"Erro transcrição: {e}")
        if os.path.exists(caminho): os.remove(caminho)
        await update.message.reply_text(f"Erro: {str(e)}")

async def receber_foto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not usuario_autorizado(update): return
    socio = identificar_socio(update)
    await update.message.reply_text("Analisando imagem...")
    foto = update.message.photo[-1]
    arquivo = await foto.get_file()
    caminho = f"temp_{update.message.message_id}.jpg"
    await arquivo.download_to_drive(caminho)

    dados = analisar_imagem(caminho)

    if dados and dados.get('tipo') == 'obra':
        # Foto de obra → perguntar qual obra com botões
        teclado = teclado_obras()
        if teclado:
            context.user_data['midia_pendente'] = {'caminho': caminho, 'socio': socio, 'tipo': 'foto'}
            await update.message.reply_text(
                "📸 Foto de obra identificada.\nQual obra pertence?",
                reply_markup=teclado
            )
        else:
            if os.path.exists(caminho): os.remove(caminho)
            await update.message.reply_text("Nenhuma obra cadastrada. Use /obras para adicionar uma.")
        return

    if dados and dados.get('tipo') == 'zelle':
        if os.path.exists(caminho): os.remove(caminho)
        chat_id = update.effective_chat.id
        if chat_id not in historicos: historicos[chat_id] = []
        context.user_data['ultimo_texto'] = f"Recebi comprovante Zelle de ${dados.get('valor', 0)} para {dados.get('funcionario', 'funcionario')}. Devo registrar como despesa."
        await processar_com_ia(update, context)
        return

    if dados and dados.get('tipo') == 'compra':
        if os.path.exists(caminho): os.remove(caminho)
        chat_id = update.effective_chat.id
        if chat_id not in historicos: historicos[chat_id] = []
        msg = (f"Recebi foto de compra: {dados.get('descricao', 'produto')}, "
               f"categoria {dados.get('categoria', 'Material')}, "
               f"valor ${dados.get('valor', 0)}. "
               f"{'E combustivel.' if dados.get('e_combustivel') else ''} "
               f"Devo registrar como despesa.")
        context.user_data['ultimo_texto'] = msg
        await processar_com_ia(update, context)
        return

    # Não identificado → perguntar obra com botões
    teclado = teclado_obras()
    if teclado:
        context.user_data['midia_pendente'] = {'caminho': caminho, 'socio': socio, 'tipo': 'foto'}
        await update.message.reply_text(
            "🤔 Não consegui identificar automaticamente.\nQual obra pertence essa foto?",
            reply_markup=teclado
        )
    else:
        if os.path.exists(caminho): os.remove(caminho)
        await update.message.reply_text("Não consegui identificar e não há obras cadastradas.")

async def receber_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not usuario_autorizado(update): return
    socio = identificar_socio(update)
    await update.message.reply_text("Recebendo video...")
    arquivo = await update.message.video.get_file()
    caminho = f"temp_video_{update.message.message_id}.mp4"
    await arquivo.download_to_drive(caminho)

    teclado = teclado_obras()
    if teclado:
        context.user_data['midia_pendente'] = {'caminho': caminho, 'socio': socio, 'tipo': 'video'}
        await update.message.reply_text(
            "🎥 Video recebido.\nQual obra pertence?",
            reply_markup=teclado
        )
    else:
        if os.path.exists(caminho): os.remove(caminho)
        await update.message.reply_text("Nenhuma obra cadastrada. Use /obras para adicionar uma.")

# ─── JOBS (JobQueue) ──────────────────────

async def job_alertas(context: ContextTypes.DEFAULT_TYPE):
    """Executa às 8:00 — verifica saldos e prazos."""
    try:
        hoje = datetime.datetime.now()
        obras_sheet = sheets_get('Obras!A:J')
        alertas = []

        for l in obras_sheet[1:]:
            if len(l) < 5: continue
            nome = l[0]
            saldo = extrair_numero(l[4]) if len(l) > 4 else 0
            prazo_str = l[8] if len(l) > 8 else ''
            status = l[6] if len(l) > 6 else ''
            if 'Concluida' in status: continue

            if saldo > 500:
                alertas.append(f"💰 {nome}: saldo a receber ${saldo:.2f}")

            if prazo_str and prazo_str != 'Indefinido':
                try:
                    partes = prazo_str.split('/')
                    if len(partes) == 3:
                        prazo_dt = datetime.datetime(int(partes[2]), int(partes[1]), int(partes[0]))
                        dias = (prazo_dt - hoje).days
                        if 0 < dias <= 7:
                            pct, _, _ = calcular_percentual_checklist(nome)
                            alertas.append(f"⚠️ {nome}: prazo em {dias} dias! ({pct}% feito)")
                        elif dias < 0:
                            alertas.append(f"🔴 {nome}: PRAZO VENCIDO ha {abs(dias)} dias!")
                except Exception as e:
                    logger.warning(f"Erro ao parsear prazo de {nome}: {e}")

        if alertas and CHAT_IDS:
            msg = "🔔 Alertas:\n\n" + "\n".join(alertas)
            for cid in CHAT_IDS:
                try:
                    await context.bot.send_message(chat_id=cid, text=msg)
                except Exception as e:
                    logger.error(f"Erro enviando alerta para {cid}: {e}")

    except Exception as e:
        logger.error(f"Erro no job de alertas: {e}")

async def job_relatorio_mensal(context: ContextTypes.DEFAULT_TYPE):
    """
    Executa às 8:30 diariamente.
    Só envia o relatório se hoje for o último dia do mês.
    Não usa `days=` fixo — funciona corretamente em meses de 28/29/30/31 dias.
    """
    hoje = datetime.datetime.now()
    ultimo = ultimo_dia_mes(hoje)

    if hoje.day != ultimo.day:
        return  # Não é último dia do mês, sai silenciosamente

    if not CHAT_IDS:
        return

    try:
        nome_pdf = gerar_pdf()
        resumo = get_resumo_texto()
        for cid in CHAT_IDS:
            try:
                await context.bot.send_message(chat_id=cid, text=f"📊 Relatorio mensal!\n\n{resumo}")
                with open(nome_pdf, 'rb') as f:
                    await context.bot.send_document(chat_id=cid, document=f)
            except Exception as e:
                logger.error(f"Erro enviando relatório para {cid}: {e}")
        os.remove(nome_pdf)
    except Exception as e:
        logger.error(f"Erro ao gerar relatório mensal: {e}")

# ─── MAIN ─────────────────────────────────

def editar_ultimo_lancamento_horas(socio, obra, horas_novas, user_data=None):
    """
    Busca o lancamento mais recente do socio+obra no mes e atualiza horas/valor.
    Registra estado anterior no undo_stack.
    """
    mes = datetime.datetime.now().strftime("%m/%Y")
    svc = conectar_sheets()
    sheet_id = obter_ou_criar_planilha()
    dados = sheets_get('Banco de Horas!A:G')

    obra_norm = obra.lower().strip()
    socio_norm = socio.lower().strip()

    # Encontra a linha mais recente do mes para socio+obra
    ultima_linha = None
    for i, l in enumerate(dados):
        if i == 0: continue
        if (len(l) >= 7 and mes in l[0] and
            l[1].lower().strip() == socio_norm and
            obra_norm in l[6].lower().strip()):
            ultima_linha = i + 1  # 1-indexed

    if not ultima_linha:
        return None, f"Nenhum lancamento encontrado para {socio} em {obra} este mes."

    # Salva estado anterior no undo
    linha_atual = dados[ultima_linha - 1]
    if user_data is not None:
        registrar_undo(user_data, 'Banco de Horas', 'update',
                       row_index=ultima_linha,
                       estado_antes=linha_atual[:])

    # Atualiza horas e valor
    valor_novo = round(horas_novas * VALOR_HORA, 2)
    svc.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range=f'Banco de Horas!C{ultima_linha}:D{ultima_linha}',
        valueInputOption='RAW',
        body={'values': [[horas_novas, valor_novo]]}
    ).execute()

    return valor_novo, None

def inicializar_abas_planilha():
    """Cria todas as abas necessárias se não existirem."""
    try:
        svc = conectar_sheets()
        sheet_id = obter_ou_criar_planilha()
        meta = svc.spreadsheets().get(spreadsheetId=sheet_id).execute()
        abas_existentes = [s['properties']['title'] for s in meta.get('sheets', [])]
        
        abas_necessarias = {
            'Despesas': ['Data', 'Enviado por', 'Categoria', 'Descricao', 'Valor ($)', 'Desconto de', 'Obra', 'Tipo'],
            'Banco de Horas': ['Data', 'Socio', 'Horas', 'Valor ($)', 'Hora Inicio', 'Hora Fim', 'Obra'],
            'Obras': ['Nome', 'Cliente', 'Contrato ($)', 'Pago ($)', 'Saldo ($)', 'Orcamento', 'Status', 'Inicio', 'Prazo', 'Checklist %'],
            'Pagamentos Cliente': ['Data', 'Obra', 'Cliente', 'Valor ($)', 'Observacao'],
            'Lista de Compras': ['Data', 'Obra', 'Item', 'Quantidade', 'Valor Est.', 'Comprado'],
            'Midias': ['Data', 'Obra', 'Tipo', 'Link', 'Enviado por'],
        }
        
        requests_body = []
        for aba in abas_necessarias:
            if aba not in abas_existentes:
                requests_body.append({'addSheet': {'properties': {'title': aba}}})
        
        if requests_body:
            svc.spreadsheets().batchUpdate(
                spreadsheetId=sheet_id,
                body={'requests': requests_body}
            ).execute()
            # Adiciona headers
            for aba, headers in abas_necessarias.items():
                if aba not in abas_existentes:
                    col = chr(64 + len(headers))
                    svc.spreadsheets().values().update(
                        spreadsheetId=sheet_id,
                        range=f'{aba}!A1:{col}1',
                        valueInputOption='RAW',
                        body={'values': [headers]}
                    ).execute()
            logger.info(f"Abas criadas: {[r['addSheet']['properties']['title'] for r in requests_body]}")
        else:
            logger.info("Todas as abas já existem.")
    except Exception as e:
        logger.error(f"Erro ao inicializar abas: {e}")

def sincronizar_obras_da_planilha():
    """Sincroniza obras da planilha — fonte de verdade e o Sheets."""
    global obras_ativas
    try:
        dados = sheets_get('Obras!A:G')
        # Obras ativas = apenas as que nao estao Concluidas
        nomes_sheet = []
        for l in dados[1:]:
            if l and l[0].strip():
                status = l[6] if len(l) > 6 else 'Em andamento'
                if 'Concluida' not in status:
                    nomes_sheet.append(l[0].strip())
        # Planilha e a fonte de verdade
        obras_ativas = nomes_sheet
        from core import set_obras_ativas
        set_obras_ativas(obras_ativas)
        with open('obras.json', 'w', encoding='utf-8') as f:
            json.dump(obras_ativas, f, ensure_ascii=False)
        logger.info(f"Obras sincronizadas: {obras_ativas}")
    except Exception as e:
        # Fallback para obras.json
        logger.warning(f"Sync obras falhou, usando json: {e}")
        if os.path.exists('obras.json'):
            with open('obras.json') as f:
                obras_ativas = json.load(f)
        from core import set_obras_ativas
        set_obras_ativas(obras_ativas)

def main():
    logger.info("🚀 Iniciando Ziontec Bot v7.0...")

    carregar_config()
    obter_ou_criar_planilha()
    criar_aba_events_se_nao_existir()
    inicializar_abas_planilha()
    sincronizar_obras_da_planilha()
    logger.info(f"📊 Planilha ID: {SHEET_ID}")

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Comandos
    app.add_handler(CommandHandler('start', cmd_start))
    app.add_handler(CommandHandler('resumo', cmd_resumo))
    app.add_handler(CommandHandler('obras', cmd_obras))
    app.add_handler(CommandHandler('pdf', cmd_pdf))
    app.add_handler(CommandHandler('agenda', cmd_agenda))
    app.add_handler(CommandHandler('horas', cmd_horas))
    app.add_handler(CommandHandler('undo', cmd_undo))
    app.add_handler(CommandHandler('corrigir_carlos', cmd_corrigir_carlos))
    app.add_handler(CommandHandler('config', cmd_config))
    app.add_handler(CommandHandler('set_valor_hora', cmd_set_valor_hora))

    # Callback (confirmações financeiras + seleção de obras)
    app.add_handler(CallbackQueryHandler(processar_callback))

    # Mídia e texto
    app.add_handler(MessageHandler(filters.PHOTO, receber_foto))
    app.add_handler(MessageHandler(filters.VIDEO, receber_video))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, receber_audio))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receber_texto))

    # Jobs — substitui threading + schedule
    app.job_queue.run_daily(job_alertas, time=datetime.time(8, 0, 0))
    app.job_queue.run_daily(job_relatorio_mensal, time=datetime.time(8, 30, 0))

    logger.info("✅ Bot pronto!")
    app.run_polling()

if __name__ == '__main__':
    main()