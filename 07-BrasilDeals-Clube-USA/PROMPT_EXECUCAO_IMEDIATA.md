# BRASILDEALS: EXECUÇÃO IMEDIATA E COMPLETA

## OBJETIVO FINAL
Entregar o projeto BrasilDeals 100% funcional, pronto para produção, SEM simulações. O sistema deve estar completamente operacional após esta execução.

---

## O QUE EXECUTAR (SEM QUEBRAR EM FASES)

### 1. ANÁLISE E DIAGNÓSTICO
- [ ] Ler completamente: PROJETO.txt (modelo de negócio)
- [ ] Revisar código existente: scraper.py, deal_processor.py, messenger.py, main.py
- [ ] Identificar EXATAMENTE o que é simulado vs funcional
- [ ] Criar lista de APIs a integrar (Telegram, WhatsApp, Amazon PA-API, PostgreSQL)

### 2. SETUP COMPLETO DE CREDENCIAIS
**Você precisa fazer estas coisas MANUALMENTE (Claude não consegue fazer):**
- [ ] Criar bot Telegram no BotFather (@BotFather)
  - Salvar: TELEGRAM_BOT_TOKEN
  - Criar canal: @brasildeals_club
  - Salvar: TELEGRAM_CHANNEL_ID
  
- [ ] Setup WhatsApp (escolha uma opção):
  - **Option A - Twilio (mais fácil):** https://twilio.com
    - Criar conta, confirmar email
    - Ir para Console > Phone Numbers > Manage Numbers
    - Setup WhatsApp Sandbox
    - Salvar: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_NUMBER
  
  - **Option B - Meta WhatsApp Business:** https://business.facebook.com
    - Criar conta Meta Business
    - Setup WhatsApp Business API
    - Salvar: WHATSAPP_ACCESS_TOKEN, WHATSAPP_BUSINESS_ACCOUNT_ID
  
- [ ] Amazon Associates: https://affiliate-program.amazon.com
  - Registrar e wait 24h para aprovação
  - Salvar: AMAZON_PARTNER_TAG (ex: gersonmence-20)
  
- [ ] Banco de dados (escolha uma):
  - **Option A - Supabase (recomendado):** https://supabase.com
    - Criar projeto PostgreSQL gratuito
    - Salvar: DATABASE_URL
  
  - **Option B - Heroku Postgres:**
    - Criar account, create app
    - Add Postgres add-on
    - Salvar: DATABASE_URL
  
  - **Option C - Local PostgreSQL:**
    - Instalar PostgreSQL
    - Criar DB: brasildeals
    - Salvar: postgresql://user:pass@localhost/brasildeals

**Arquivo .env completo esperado:**
```
# TELEGRAM
TELEGRAM_BOT_TOKEN="seu_token_do_botfather"
TELEGRAM_CHANNEL_ID="-100XXXXX"  # ou @seu_channel
TELEGRAM_GROUP_ID="-100XXXXX"

# WHATSAPP (Twilio)
TWILIO_ACCOUNT_SID="ACxxxxxx"
TWILIO_AUTH_TOKEN="xxxxxx"
TWILIO_WHATSAPP_NUMBER="+14155552671"
WHATSAPP_TEST_NUMBER="+5511999999999"  # Seu número para testes

# AMAZON
AMAZON_PARTNER_TAG="gersonmence-20"

# DATABASE
DATABASE_URL="postgresql://user:password@host:5432/brasildeals"

# LOGGING
LOG_LEVEL="INFO"
```

---

### 3. IMPLEMENTAÇÃO COMPLETA DO CÓDIGO

**Execute estas tarefas em ordem:**

#### 3.1 - Atualizar requirements.txt
```
Adicionar:
python-telegram-bot==20.3
twilio==8.10.0  # ou facebook-business==18.0.0
psycopg2-binary==2.9.9
sqlalchemy==2.0.23
apscheduler==3.10.4
python-dotenv==1.0.0
requests==2.31.0
beautifulsoup4==4.12.2
lxml==4.9.3
gunicorn==21.2.0
python-json-logger==2.0.7
```

#### 3.2 - Criar models.py (ORM SQLAlchemy)
```python
Implementar:
- Deal model (id, title, description, link, affiliate_link, discount_percentage, category, source, posted_at, posted_channel)
- Channel model (id, name, telegram_channel_id, telegram_group_id, whatsapp_numbers, active)
- PostLog model (id, deal_id, channel, status, timestamp, error_message)
- Commission model (id, deal_id, amazon_order_id, amount, date_tracked)

Criar session factory com connection pooling
```

#### 3.3 - Reescrever scraper.py
```python
MANTER:
- fetch_slickdeals_rss() função real (já funciona)
- parse_rss_item() função real (já funciona)
- category detection (já funciona)

ADICIONAR:
- Função para extrair ASIN real do link Amazon (não mock)
- Integração REAL Amazon PA-API (signed requests)
- Salvar automaticamente deals no DB
- Detectar e evitar duplicatas
- Logar cada deal scraped
```

#### 3.4 - Reescrever deal_processor.py
```python
MANTER:
- filter_deals() função (filtragem por desconto > 50%)
- format_deal_message() função (formatação)

MODIFICAR:
- format_deal_message deve incluir:
  * Affiliate link com AMAZON_PARTNER_TAG
  * Emoji por categoria
  * Timestamp
  * Link de clique para rastreamento (se possível)
```

#### 3.5 - REESCREVER COMPLETO messenger.py
```python
REMOVER TODA SIMULAÇÃO.

Implementar REAL com python-telegram-bot:

async def send_telegram_message(channel_id, message):
    """Envia MENSAGEM REAL para canal Telegram"""
    async with telegram.Bot(token=TELEGRAM_BOT_TOKEN) as bot:
        await bot.send_message(
            chat_id=channel_id,
            text=message,
            parse_mode=telegram.constants.ParseMode.HTML,
            disable_web_page_preview=False
        )
        return True

Implementar REAL com Twilio (ou Meta):

def send_whatsapp_message(phone_number, message):
    """Envia MENSAGEM REAL para WhatsApp"""
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    
    response = client.messages.create(
        from_=TWILIO_WHATSAPP_NUMBER,
        body=message,
        to=f"whatsapp:{phone_number}"
    )
    return response.sid

def notify_channels(deal, channel_config):
    """Notifica Telegram E WhatsApp com mensagem real"""
    # Enviar para Telegram
    # Enviar para WhatsApp
    # Logar status de cada envio
    # Registrar no DB
```

#### 3.6 - Criar scheduler.py
```python
Implementar:

from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler(timezone='America/New_York')

# Rodar 4x/dia: 6AM, 10AM, 2PM, 6PM
scheduler.add_job(
    run_scraper_cycle,
    'cron',
    hour='6,10,14,18',
    minute=0
)

async def run_scraper_cycle():
    """Executa ciclo completo: scrape → filter → post → log"""
    try:
        deals = scrape_slickdeals()
        filtered = filter_deals(deals)
        for deal in filtered:
            # Salvar no DB
            # Postar no Telegram
            # Postar no WhatsApp
            # Logar sucesso
    except Exception as e:
        # Logar erro
        # Enviar alert

if __name__ == '__main__':
    scheduler.start()
    try:
        asyncio.run(asyncio.Event().wait())
    except KeyboardInterrupt:
        scheduler.shutdown()
```

#### 3.7 - Criar dashboard.py
```python
Funções:

def get_daily_stats(date):
    """Retorna stats do dia"""
    return {
        "date": date,
        "deals_scraped": count,
        "deals_posted": count,
        "channels": {"telegram": count, "whatsapp": count},
        "categories": {...},
        "errors": [...]
    }

def get_revenue_stats():
    """Retorna $ ganho"""
    return {
        "today": $,
        "this_week": $,
        "this_month": $,
        "total": $
    }

def print_dashboard():
    """Imprime dashboard no terminal"""
    # Mostrar stats formatadas
```

#### 3.8 - Criar database.py
```python
Funções:

def init_db():
    """Criar todas as tabelas no DB"""
    Base.metadata.create_all(engine)

def save_deal(deal_dict):
    """Salvar deal no DB, retornar ID"""
    # Check duplicata
    # Insert
    # Return ID

def log_post(deal_id, channel, status):
    """Logar que deal foi postado"""

def save_commission(order_id, amount):
    """Logar comissão ganha"""
```

#### 3.9 - Atualizar main.py
```python
Integrar tudo:

async def main():
    # Init DB
    await init_db()
    
    # Scrape
    raw_deals = await scrape_slickdeals_rss()
    
    # Filter
    filtered = filter_deals(raw_deals, MIN_DISCOUNT=50)
    
    # For each deal:
    for deal in filtered:
        # Save to DB
        deal_id = await save_deal(deal)
        
        # Format message
        msg = format_deal_message(deal)
        
        # Post to Telegram
        try:
            await send_telegram_message(TELEGRAM_CHANNEL_ID, msg)
            await log_post(deal_id, 'telegram', 'success')
        except Exception as e:
            await log_post(deal_id, 'telegram', f'error: {e}')
        
        # Post to WhatsApp
        try:
            await send_whatsapp_message(WHATSAPP_NUMBER, msg)
            await log_post(deal_id, 'whatsapp', 'success')
        except Exception as e:
            await log_post(deal_id, 'whatsapp', f'error: {e}')

if __name__ == '__main__':
    asyncio.run(main())
```

#### 3.10 - Criar logging.py
```python
Implementar:

import logging
from pythonjsonlogger import jsonlogger

def setup_logging():
    """Configure JSON logging para arquivo e console"""
    # Salvar em: logs/brasildeals.log
    # Formato: JSON (machine readable)
    # Level: INFO
    # Rotation: daily
```

#### 3.11 - Criar tests/test_integration.py
```python
Testes:

async def test_telegram_connection():
    """Confirma que consegue enviar para Telegram"""
    msg = send_telegram_message(CHANNEL_ID, "Test")
    assert msg is not None

async def test_whatsapp_connection():
    """Confirma que consegue enviar para WhatsApp"""
    msg = send_whatsapp_message(PHONE, "Test")
    assert msg is not None

async def test_database_connection():
    """Confirma que DB está acessível"""
    session = get_db_session()
    assert session is not None

async def test_scraper():
    """Executa scraper e confirma que retorna deals"""
    deals = await scrape_slickdeals_rss()
    assert len(deals) > 0

async def test_end_to_end():
    """Full cycle: scrape → filter → post → log"""
    # Executa tudo
    # Confirma que deals foram postados
    # Confirma que foram salvos no DB
```

---

### 4. SETUP E TESTES

#### 4.1 - Criar arquivo de setup local
```bash
# setup.sh (ou setup.bat no Windows)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Criar .env
cp .env.example .env
# [User needs to fill in credentials]

# Inicializar DB
python -c "from database import init_db; init_db()"

# Executar testes
python -m pytest tests/test_integration.py -v
```

#### 4.2 - Testar cada função
```
[ ] Confirmar Telegram Bot envia mensagem real
[ ] Confirmar WhatsApp envia mensagem real
[ ] Confirmar Scraper fetcha deals reais
[ ] Confirmar Filtro funciona (> 50% off)
[ ] Confirmar DB salva deals
[ ] Confirmar Dashboard mostra stats
[ ] Executar Full cycle: scrape → post → log
```

---

### 5. DEPLOYMENT EM PRODUÇÃO

#### 5.1 - Criar systemd service
```ini
# /etc/systemd/system/brasildeals.service
[Unit]
Description=BrasilDeals Scraper Service
After=network.target postgresql.service

[Service]
Type=simple
User=brasildeals
WorkingDirectory=/home/brasildeals/brasildeals-app
Environment="PATH=/home/brasildeals/brasildeals-app/venv/bin"
ExecStart=/home/brasildeals/brasildeals-app/venv/bin/python scheduler.py
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
```

#### 5.2 - Setup em VPS (Digital Ocean / Heroku / Hetzner)
```bash
# VPS Commands:
ssh user@your_vps.com

# Install dependencies
sudo apt-get update
sudo apt-get install python3.9 python3-pip postgresql

# Clone/upload code
git clone <your-repo> /home/brasildeals
cd /home/brasildeals

# Setup virtual env
python3.9 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Setup .env (copy from local, paste secrets)
nano .env

# Init DB
python -c "from database import init_db; init_db()"

# Install systemd service
sudo cp brasildeals.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable brasildeals
sudo systemctl start brasildeals

# Verify running
sudo systemctl status brasildeals
sudo journalctl -u brasildeals -f  # View logs
```

---

### 6. VALIDAÇÃO FINAL

```
CHECKLIST DE VALIDAÇÃO (Executar na ordem):

[ ] .env está preenchido com todas as credenciais
[ ] DB está criado e conectável
[ ] Scraper roda e retorna deals reais
[ ] Filter funciona (50%+ discount)
[ ] Mensagem formatada está correta
[ ] Telegram Bot consegue enviar mensagem REAL
[ ] WhatsApp consegue enviar mensagem REAL
[ ] DB salva deals corretamente
[ ] Não cria duplicatas
[ ] Dashboard mostra stats corretos
[ ] Logs são gerados em JSON
[ ] Scheduler está rodando 4x/dia
[ ] Service systemd está ativo e restartando se cair
[ ] Deploy em VPS está funcionando
[ ] Recebeu primeiro clique em link affiliate
[ ] Dashboard mostra primeira comissão

SUCESSO: Todos os itens acima ✓
```

---

## DEPENDÊNCIAS CRÍTICAS

```
python-telegram-bot==20.3  # Telegram Real
twilio==8.10.0  # WhatsApp Real
sqlalchemy==2.0.23  # ORM Database
psycopg2==2.9.9  # PostgreSQL connector
apscheduler==3.10.4  # Scheduler
```

---

## ESTRUTURA FINAL DE ARQUIVOS

```
07-BrasilDeals-Clube-USA/
├── .env (PREENCHIDO COM CREDENCIAIS)
├── .env.example
├── requirements.txt (ATUALIZADO)
├── main.py (REESCRITO - não simulado)
├── scheduler.py (NOVO - roda 4x/dia)
├── config.py (EXISTENTE)
├── scraper.py (REESCRITO - real)
├── deal_processor.py (MODIFICADO)
├── messenger.py (REESCRITO - 100% real)
├── database.py (NOVO - SQLAlchemy models)
├── models.py (NOVO - Deal, Channel, PostLog, Commission)
├── dashboard.py (NOVO - stats)
├── logging.py (NOVO - JSON logging)
├── tests/
│   └── test_integration.py (NOVO)
├── logs/ (NOVO - arquivo de logs)
├── reports/
│   └── daily_YYYY-MM-DD.json (Gerado automaticamente)
├── brasildeals.service (NOVO - systemd)
├── setup.sh (NOVO - script de setup)
├── README.md (ATUALIZADO com instrções reais)
├── DEPLOYMENT.md (NOVO - deploy guide)
└── PROJETO.txt (ATUALIZADO - status FUNCIONAL)
```

---

## DEFINIÇÃO DE SUCESSO

Projeto está COMPLETO quando:

```
✅ EXECUÇÃO AUTOMÁTICA:
   - Roda sozinho 4x/dia
   - Não precisa de intervenção manual
   
✅ FUNCIONALIDADE 100% REAL:
   - Telegram: Mensagens reais aparecem no @brasildeals_club
   - WhatsApp: Mensagens reais chegam nos números
   - Amazon: Links com affiliate tag funcionam
   - Database: Deals salvos e rastreáveis
   
✅ MONETIZAÇÃO ATIVA:
   - Primeiro clique rastreado em link affiliate
   - Primeira comissão recebida (pode levar 24-48h)
   - Dashboard mostrando $
   
✅ PRODUÇÃO:
   - Rodando 24/7 em VPS
   - Service systemd auto-restartando se cair
   - Logs JSON sendo gerados diariamente
   - Nenhuma simulação, zero mocks
   
✅ DOCUMENTAÇÃO:
   - README com instruções reais
   - DEPLOYMENT.md com passo a passo
   - Logs rastreáveis
   - PROJETO.txt marcado como FUNCIONAL
```

---

## NOTA CRÍTICA

**Claude não consegue fazer:**
- Criar conta Telegram/WhatsApp/Amazon (requer confirmação email)
- Executar código que precisa de credenciais reais (segurança)
- Fazer deploy efetivamente sem permissão SSH

**Você precisa fazer:**
1. Criar as contas e gerar credenciais
2. Preencher .env
3. Rodar os testes localmente
4. Fazer deploy em VPS

**Claude vai fazer:**
- Escrever TODO o código
- Estruturar tudo
- Explicar como usar
- Validar que funciona com testes unitários

---

## PRÓXIMAS AÇÕES

Após isso estar 100% funcional:

```
FASE 2 DO MODELO DE NEGÓCIO:
[ ] Coletar dados por 1 semana
[ ] Medir: CTR, conversão, comissão
[ ] Se resultados bons:
    [ ] Recrutar 100-500 usuários beta
    [ ] Testar tier VIP $4.99/mês
    [ ] Integrar Maria Madah
    [ ] Sistema de remessas
```

---

**Status:** Pronto para execução imediata e completa  
**Tempo esperado:** Execução contínua até conclusão (sem parar por "semanas")  
**Objetivo final:** Sistema 100% funcional, gerando receita real, rodando em produção 24/7
