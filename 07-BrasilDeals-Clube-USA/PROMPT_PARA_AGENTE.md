# 🚀 BRASILDEALS: PROMPT PARA EXECUÇÃO POR AGENTE

**ESTE PROMPT DEVE SER EXECUTADO POR UM AGENTE/CLAUDE COM ACESSO A ESCREVER CÓDIGO**

---

## CONTEXTO COMPLETO

**Projeto:** BrasilDeals (Clube USA)  
**Status Atual:** Prova de conceito com código simulado  
**Objetivo:** Transformar em sistema 100% funcional, pronto para produção  
**Localização:** `C:\Users\g-fil\Documents\Projetos Claude\projetos-organizados\07-BrasilDeals-Clube-USA\`

**Documentação de referência:**
- `PROJETO.txt` - Especificação completa do modelo de negócio
- `README.md` - Stack técnica atual
- Arquivos Python existentes - Código atual (parcialmente simulado)

---

## O QUE ESTÁ FEITO (NÃO MEXER)

```
✅ scraper.py: função fetch_slickdeals_rss() FUNCIONA (fetcha RSS real)
✅ scraper.py: função parse_rss_item() FUNCIONA (parseia XML real)
✅ deal_processor.py: lógica de filtro por desconto FUNCIONA
✅ main.py: estrutura básica existe
```

---

## O QUE PRECISA SER REESCRITO/CRIADO

### 1. REESCREVER: `scraper.py` (40% mudança)

**Manter o que funciona:**
- `fetch_slickdeals_rss()` - continua como está
- `parse_rss_item()` - continua como está

**Remover completamente:**
- `get_amazon_product_details()` - INTEIRA (é 100% mock)

**Adicionar novo:**
```python
def extract_asin_from_link(product_link: str) -> Optional[str]:
    """Extrai ASIN real do link, ou retorna None"""
    # Procura padrão: /dp/ASIN
    # Retorna ASIN string de 10 caracteres, ou None

def get_real_amazon_details(asin: str, partner_tag: str) -> Dict:
    """
    Integração REAL com Amazon PA-API (não mock)
    
    Requer:
    - boto3 library (AWS SDK)
    - Credenciais AWS: access_key, secret_key
    
    Retorna:
    {
        "image_url": "https://...",
        "price": "$XX.XX",
        "affiliate_link": "https://amazon.com/dp/ASIN/?tag=partner_tag"
    }
    
    NOTA: Se sem credenciais, retornar link affiliate com ASIN extraído
    """

def get_deals_from_source_complete(rss_url, partner_tag) -> List[Dict]:
    """
    Reescrever função existente:
    - Scrapar RSS (KEEP EXISTING)
    - Parse items (KEEP EXISTING)
    - Para cada deal:
      * Extrair ASIN do link
      * Tentar buscar detalhes Amazon PA-API (ou skip se sem credenciais)
      * Gerar affiliate link com partner_tag
      * Salvar no DB (novo - vê db.py)
      * Retornar deal completo
    """
```

---

### 2. REESCREVER COMPLETO: `messenger.py` (100% rewrite)

**Remover TUDO:**
- `send_telegram_message()` - completamente mock, remover
- `send_whatsapp_message()` - completamente mock, remover
- `notify_channels()` - remover

**Criar novo com código REAL:**

```python
import telegram
from telegram.constants import ParseMode
import asyncio
from twilio.rest import Client

# ========== TELEGRAM (REAL) ==========

async def send_telegram_message_real(bot_token: str, channel_id: str, message: str) -> bool:
    """
    Envia mensagem REAL para canal Telegram
    
    Args:
        bot_token: token do bot (ex: "123456:ABCDefgh...")
        channel_id: ID do canal (ex: "-100123456789" ou "@brasildeals_club")
        message: HTML formatted message
    
    Returns:
        True if success, False if error
    """
    try:
        async with telegram.Bot(token=bot_token) as bot:
            await bot.send_message(
                chat_id=channel_id,
                text=message,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=False
            )
        return True
    except Exception as e:
        print(f"Erro ao enviar Telegram: {e}")
        return False

async def send_telegram_group_message_real(bot_token: str, group_id: str, message: str) -> bool:
    """Similar a canal, mas para grupo privado"""

# ========== WHATSAPP (TWILIO) ==========

def send_whatsapp_message_real(
    account_sid: str,
    auth_token: str,
    from_whatsapp_number: str,
    to_whatsapp_number: str,
    message: str
) -> str:
    """
    Envia mensagem REAL para WhatsApp usando Twilio
    
    Args:
        account_sid: Twilio Account SID
        auth_token: Twilio Auth Token
        from_whatsapp_number: Seu número Twilio (ex: "+14155552671")
        to_whatsapp_number: Número destino (ex: "+5511999999999")
        message: Texto da mensagem
    
    Returns:
        Message SID if success, empty string if error
    """
    try:
        client = Client(account_sid, auth_token)
        
        message_obj = client.messages.create(
            from_=f"whatsapp:{from_whatsapp_number}",
            body=message,
            to=f"whatsapp:{to_whatsapp_number}"
        )
        return message_obj.sid
    except Exception as e:
        print(f"Erro ao enviar WhatsApp: {e}")
        return ""

# ========== NOTIFY (ORCHESTRATOR) ==========

async def notify_all_channels(
    deal_dict: Dict,
    telegram_config: Dict,
    whatsapp_config: Dict,
    db_session
) -> Dict:
    """
    Notifica TODAS as plataformas com um deal
    
    telegram_config: {
        "bot_token": "xxx",
        "channel_id": "-100xxx",
        "group_id": "-100xxx"
    }
    
    whatsapp_config: {
        "account_sid": "xxx",
        "auth_token": "xxx",
        "from_number": "+14155552671",
        "to_numbers": ["+5511999999999", "+5511988888888"]
    }
    
    Retorna:
    {
        "telegram_channel": True/False,
        "telegram_group": True/False,
        "whatsapp": [True, False, True, ...],  # Um por destinatário
        "errors": ["erro 1", "erro 2"]
    }
    """
    results = {
        "telegram_channel": False,
        "telegram_group": False,
        "whatsapp_results": [],
        "errors": []
    }
    
    # Formatar mensagem
    msg = format_deal_message(deal_dict)
    
    # Enviar Telegram Channel
    try:
        success = await send_telegram_message_real(
            telegram_config["bot_token"],
            telegram_config["channel_id"],
            msg
        )
        results["telegram_channel"] = success
    except Exception as e:
        results["errors"].append(f"Telegram channel: {e}")
    
    # Enviar Telegram Group
    try:
        success = await send_telegram_message_real(
            telegram_config["bot_token"],
            telegram_config["group_id"],
            msg
        )
        results["telegram_group"] = success
    except Exception as e:
        results["errors"].append(f"Telegram group: {e}")
    
    # Enviar WhatsApp (múltiplos números)
    for to_number in whatsapp_config["to_numbers"]:
        try:
            sid = send_whatsapp_message_real(
                whatsapp_config["account_sid"],
                whatsapp_config["auth_token"],
                whatsapp_config["from_number"],
                to_number,
                msg
            )
            results["whatsapp_results"].append(bool(sid))
        except Exception as e:
            results["whatsapp_results"].append(False)
            results["errors"].append(f"WhatsApp {to_number}: {e}")
    
    # Logar no DB
    if db_session:
        # Usar db.log_post() para registrar tudo
        pass
    
    return results
```

---

### 3. CRIAR NOVO: `models.py` (100% novo arquivo)

```python
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Deal(Base):
    """Modelo para deals scraped"""
    __tablename__ = "deals"
    
    id = Column(Integer, primary_key=True)
    title = Column(String(500), nullable=False)
    description = Column(Text)
    original_link = Column(String(1000))
    affiliate_link = Column(String(1000))
    discount_percentage = Column(Integer)
    category = Column(String(100))
    source = Column(String(50))  # "slickdeals", "amazon", etc
    asin = Column(String(20))
    amazon_price = Column(String(50))
    amazon_image_url = Column(String(1000))
    posted_at = Column(DateTime, default=datetime.utcnow, unique=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Constraints para evitar duplicatas
    __table_args__ = (
        # Unique constraint: se mesmo título e source no mesmo dia
    )

class PostLog(Base):
    """Log de quando deals foram postados"""
    __tablename__ = "post_logs"
    
    id = Column(Integer, primary_key=True)
    deal_id = Column(Integer, ForeignKey("deals.id"))
    channel = Column(String(50))  # "telegram", "whatsapp"
    status = Column(String(20))  # "success", "failed"
    message = Column(String(500))
    timestamp = Column(DateTime, default=datetime.utcnow)

class Commission(Base):
    """Log de comissões Amazon"""
    __tablename__ = "commissions"
    
    id = Column(Integer, primary_key=True)
    deal_id = Column(Integer, ForeignKey("deals.id"))
    amazon_order_id = Column(String(100), unique=True)
    amount = Column(Float)
    date_tracked = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

class DailyStats(Base):
    """Stats diários"""
    __tablename__ = "daily_stats"
    
    id = Column(Integer, primary_key=True)
    date = Column(DateTime, unique=True)
    deals_scraped = Column(Integer)
    deals_posted_telegram = Column(Integer)
    deals_posted_whatsapp = Column(Integer)
    total_revenue = Column(Float)
```

---

### 4. CRIAR NOVO: `database.py` (100% novo arquivo)

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from models import Base, Deal, PostLog, Commission, DailyStats
from datetime import datetime
import os

# Inicializar engine e session factory
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///brasildeals.db")
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)

def init_db():
    """Criar todas as tabelas"""
    Base.metadata.create_all(bind=engine)
    print("✅ Database initialized")

def get_db_session() -> Session:
    """Retorna uma sessão de DB"""
    return SessionLocal()

def save_deal(session: Session, deal_dict: dict) -> Deal:
    """
    Salva deal no DB
    
    Previne duplicatas com base em: title + source + data
    """
    # Check se deal similar já existe
    existing = session.query(Deal).filter(
        Deal.title == deal_dict["title"],
        Deal.source == deal_dict.get("source", "unknown")
    ).first()
    
    if existing:
        return existing
    
    deal = Deal(
        title=deal_dict["title"],
        description=deal_dict.get("description"),
        original_link=deal_dict.get("original_link"),
        affiliate_link=deal_dict.get("affiliate_link"),
        discount_percentage=deal_dict.get("discount_percentage"),
        category=deal_dict.get("category"),
        source=deal_dict.get("source"),
        asin=deal_dict.get("asin"),
        amazon_price=deal_dict.get("amazon_price"),
        amazon_image_url=deal_dict.get("amazon_image_url")
    )
    
    session.add(deal)
    session.commit()
    
    return deal

def log_post(session: Session, deal_id: int, channel: str, status: str, message: str = ""):
    """Loga que deal foi postado"""
    log = PostLog(
        deal_id=deal_id,
        channel=channel,
        status=status,
        message=message
    )
    session.add(log)
    session.commit()

def save_commission(session: Session, deal_id: int, order_id: str, amount: float):
    """Salva comissão"""
    comm = Commission(
        deal_id=deal_id,
        amazon_order_id=order_id,
        amount=amount,
        date_tracked=datetime.utcnow()
    )
    session.add(comm)
    session.commit()

def get_daily_stats(session: Session, date: datetime) -> dict:
    """Retorna stats do dia"""
    day_start = date.replace(hour=0, minute=0, second=0)
    day_end = date.replace(hour=23, minute=59, second=59)
    
    deals_scraped = session.query(Deal).filter(
        Deal.created_at >= day_start,
        Deal.created_at <= day_end
    ).count()
    
    telegram_posts = session.query(PostLog).filter(
        PostLog.channel == "telegram",
        PostLog.timestamp >= day_start,
        PostLog.timestamp <= day_end
    ).count()
    
    whatsapp_posts = session.query(PostLog).filter(
        PostLog.channel == "whatsapp",
        PostLog.timestamp >= day_start,
        PostLog.timestamp <= day_end
    ).count()
    
    total_revenue = session.query(Commission).filter(
        Commission.created_at >= day_start,
        Commission.created_at <= day_end
    ).with_entities(sum(Commission.amount)).scalar() or 0
    
    return {
        "date": date.isoformat(),
        "deals_scraped": deals_scraped,
        "deals_posted_telegram": telegram_posts,
        "deals_posted_whatsapp": whatsapp_posts,
        "total_revenue": float(total_revenue)
    }
```

---

### 5. CRIAR NOVO: `scheduler.py` (100% novo arquivo)

```python
import asyncio
import os
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from pytz import timezone

from config import config
from scraper import get_deals_from_source_complete
from deal_processor import filter_deals, format_deal_message
from messenger import notify_all_channels
from database import get_db_session, save_deal, log_post, init_db
from logging_setup import get_logger

logger = get_logger(__name__)

def create_scheduler():
    """Cria e configura scheduler"""
    
    scheduler = BackgroundScheduler(timezone=timezone('America/New_York'))
    
    # Adicionar job para rodar 4x/dia
    scheduler.add_job(
        run_scraper_cycle,
        'cron',
        hour='6,10,14,18',
        minute=0,
        id='brasildeals_scraper'
    )
    
    return scheduler

async def run_scraper_cycle():
    """
    Executa um ciclo completo:
    1. Scrape deals do RSS
    2. Filter por critérios
    3. Post no Telegram e WhatsApp
    4. Log no DB
    """
    
    logger.info("🚀 Starting BrasilDeals scraper cycle")
    
    try:
        # Init DB
        init_db()
        session = get_db_session()
        
        # 1. SCRAPE
        logger.info("📥 Scraping deals from Slickdeals RSS...")
        raw_deals = get_deals_from_source_complete(
            config.SLICKDEALS_RSS_URL,
            config.AMAZON_PARTNER_TAG
        )
        
        if not raw_deals:
            logger.warning("❌ No deals scraped")
            return
        
        logger.info(f"✅ Scraped {len(raw_deals)} deals")
        
        # 2. FILTER
        logger.info(f"🔍 Filtering deals (>{config.MIN_DISCOUNT_PERCENTAGE}% off)...")
        filtered_deals = filter_deals(
            raw_deals,
            config.MIN_DISCOUNT_PERCENTAGE,
            config.RELEVANT_CATEGORIES
        )
        
        logger.info(f"✨ Filtered to {len(filtered_deals)} relevant deals")
        
        # 3. POST
        telegram_config = {
            "bot_token": config.TELEGRAM_BOT_TOKEN,
            "channel_id": config.TELEGRAM_CHANNEL_ID,
            "group_id": config.TELEGRAM_GROUP_ID
        }
        
        whatsapp_config = {
            "account_sid": config.TWILIO_ACCOUNT_SID,
            "auth_token": config.TWILIO_AUTH_TOKEN,
            "from_number": config.TWILIO_WHATSAPP_NUMBER,
            "to_numbers": [config.WHATSAPP_TEST_NUMBER]  # Começa com 1, depois expande
        }
        
        for i, deal in enumerate(filtered_deals):
            logger.info(f"📤 Processing deal {i+1}/{len(filtered_deals)}: {deal['title']}")
            
            # Salvar deal no DB
            db_deal = save_deal(session, deal)
            logger.info(f"   ✅ Saved to DB (ID: {db_deal.id})")
            
            # Notificar canais
            results = await notify_all_channels(
                deal,
                telegram_config,
                whatsapp_config,
                session
            )
            
            # Logar resultados
            if results["telegram_channel"]:
                log_post(session, db_deal.id, "telegram_channel", "success")
                logger.info("   ✅ Posted to Telegram Channel")
            else:
                log_post(session, db_deal.id, "telegram_channel", "failed")
                logger.warning("   ❌ Failed to post to Telegram")
            
            if results["whatsapp_results"]:
                log_post(session, db_deal.id, "whatsapp", "success")
                logger.info("   ✅ Posted to WhatsApp")
            else:
                log_post(session, db_deal.id, "whatsapp", "failed")
                logger.warning("   ❌ Failed to post to WhatsApp")
        
        session.close()
        logger.info("✅ BrasilDeals scraper cycle completed")
        
    except Exception as e:
        logger.error(f"❌ Error during scraper cycle: {e}")

def start_scheduler():
    """Inicia scheduler em background"""
    scheduler = create_scheduler()
    scheduler.start()
    logger.info("🕐 BrasilDeals Scheduler started")
    return scheduler

if __name__ == '__main__':
    logger.info("Starting BrasilDeals Scheduler...")
    scheduler = start_scheduler()
    
    try:
        asyncio.run(asyncio.Event().wait())
    except KeyboardInterrupt:
        logger.info("Shutting down scheduler...")
        scheduler.shutdown()
```

---

### 6. CRIAR NOVO: `logging_setup.py` (100% novo arquivo)

```python
import logging
import os
from pythonjsonlogger import jsonlogger
from datetime import datetime

def get_logger(name):
    """Configure logger com JSON format"""
    
    # Criar pasta logs se não existe
    os.makedirs('logs', exist_ok=True)
    
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # JSON File Handler
    log_file = f"logs/brasildeals_{datetime.now().strftime('%Y-%m-%d')}.json"
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)
    
    json_formatter = jsonlogger.JsonFormatter()
    file_handler.setFormatter(json_formatter)
    logger.addHandler(file_handler)
    
    # Console Handler (human readable)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    return logger
```

---

### 7. ATUALIZAR: `requirements.txt`

```
requests==2.31.0
beautifulsoup4==4.12.2
lxml==4.9.3
python-dotenv==1.0.0
python-telegram-bot==20.3
twilio==8.10.0
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
apscheduler==3.10.4
python-json-logger==2.0.7
gunicorn==21.2.0
boto3==1.28.0  # Para Amazon PA-API (opcional)
```

---

### 8. REESCREVER: `main.py`

```python
import asyncio
import os
from config import config
from scraper import get_deals_from_source_complete
from deal_processor import filter_deals, format_deal_message
from messenger import notify_all_channels
from database import init_db, get_db_session, save_deal, log_post
from logging_setup import get_logger

logger = get_logger(__name__)

async def main():
    """Executa um ciclo completo de scraping e posting"""
    
    logger.info("🚀 Starting BrasilDeals")
    
    # Init DB
    init_db()
    session = get_db_session()
    
    # Scrape
    logger.info("📥 Scraping deals...")
    raw_deals = get_deals_from_source_complete(
        config.SLICKDEALS_RSS_URL,
        config.AMAZON_PARTNER_TAG
    )
    
    if not raw_deals:
        logger.warning("❌ No deals scraped")
        return
    
    logger.info(f"✅ Scraped {len(raw_deals)} deals")
    
    # Filter
    filtered_deals = filter_deals(
        raw_deals,
        config.MIN_DISCOUNT_PERCENTAGE,
        config.RELEVANT_CATEGORIES
    )
    
    logger.info(f"✨ Filtered to {len(filtered_deals)} deals")
    
    # Post to channels
    telegram_config = {
        "bot_token": config.TELEGRAM_BOT_TOKEN,
        "channel_id": config.TELEGRAM_CHANNEL_ID,
        "group_id": config.TELEGRAM_GROUP_ID
    }
    
    whatsapp_config = {
        "account_sid": config.TWILIO_ACCOUNT_SID,
        "auth_token": config.TWILIO_AUTH_TOKEN,
        "from_number": config.TWILIO_WHATSAPP_NUMBER,
        "to_numbers": [config.WHATSAPP_TEST_NUMBER]
    }
    
    for deal in filtered_deals:
        db_deal = save_deal(session, deal)
        results = await notify_all_channels(deal, telegram_config, whatsapp_config, session)
        logger.info(f"Posted deal {db_deal.id}: {results}")
    
    session.close()
    logger.info("✅ Done")

if __name__ == "__main__":
    asyncio.run(main())
```

---

### 9. CRIAR NOVO: `.env.example` (atualizado com credenciais REAIS)

```
# TELEGRAM - Obter em https://t.me/BotFather
TELEGRAM_BOT_TOKEN="seu_token_aqui"
TELEGRAM_CHANNEL_ID="@brasildeals_club"  # Seu canal público
TELEGRAM_GROUP_ID="-100xxxx"  # Seu grupo privado

# WHATSAPP TWILIO - Obter em https://twilio.com
TWILIO_ACCOUNT_SID="ACxxxx"
TWILIO_AUTH_TOKEN="xxxxx"
TWILIO_WHATSAPP_NUMBER="+14155552671"  # Número sandbox Twilio
WHATSAPP_TEST_NUMBER="+5511999999999"  # Seu número para testes

# AMAZON ASSOCIATES - Obter em https://affiliate-program.amazon.com
AMAZON_PARTNER_TAG="gersonmence-20"
AMAZON_PA_API_ACCESS_KEY="xxx"  # Opcional
AMAZON_PA_API_SECRET_KEY="xxx"  # Opcional

# DATABASE - PostgreSQL (Supabase, Heroku, ou local)
DATABASE_URL="postgresql://user:password@localhost/brasildeals"

# CONFIG
MIN_DISCOUNT_PERCENTAGE=50
RELEVANT_CATEGORIES="electronics,home,fashion,kitchen,health,beauty,toys,tools"
SLICKDEALS_RSS_URL="https://slickdeals.net/rss/deals.xml"

# LOGGING
LOG_LEVEL="INFO"
```

---

### 10. CRIAR NOVO: `tests/test_integration.py`

```python
import pytest
import asyncio
from unittest.mock import patch, MagicMock

from scraper import get_deals_from_source_complete, extract_asin_from_link
from messenger import send_telegram_message_real, send_whatsapp_message_real
from database import init_db, save_deal, get_db_session
from deal_processor import filter_deals

class TestScraper:
    def test_extract_asin(self):
        """Test ASIN extraction"""
        link = "https://amazon.com/dp/B0ABC123XYZ/"
        asin = extract_asin_from_link(link)
        assert asin == "B0ABC123XYZ"
    
    @pytest.mark.asyncio
    async def test_scraper_returns_deals(self):
        """Test que scraper retorna deals reais"""
        deals = get_deals_from_source_complete(
            "https://slickdeals.net/rss/deals.xml",
            "test-tag"
        )
        assert len(deals) > 0
        assert all("title" in d for d in deals)

class TestMessenger:
    @pytest.mark.asyncio
    async def test_telegram_config_exists(self):
        """Test que credenciais Telegram estão configuradas"""
        from config import config
        assert config.TELEGRAM_BOT_TOKEN
        assert config.TELEGRAM_CHANNEL_ID
    
    @pytest.mark.asyncio
    async def test_whatsapp_config_exists(self):
        """Test que credenciais WhatsApp estão configuradas"""
        from config import config
        assert config.TWILIO_ACCOUNT_SID
        assert config.TWILIO_AUTH_TOKEN

class TestDatabase:
    def test_database_init(self):
        """Test que DB pode ser inicializado"""
        init_db()
        session = get_db_session()
        assert session is not None
        session.close()
    
    def test_save_deal(self):
        """Test que deal pode ser salvo no DB"""
        init_db()
        session = get_db_session()
        
        deal_dict = {
            "title": "Test Deal 50% off",
            "description": "Test description",
            "discount_percentage": 50,
            "category": "Electronics",
            "source": "slickdeals"
        }
        
        deal = save_deal(session, deal_dict)
        assert deal.id is not None
        session.close()

class TestFilter:
    def test_filter_deals(self):
        """Test que filtro funciona"""
        deals = [
            {"title": "Item 30% off", "discount_percentage": 30, "category": "Electronics"},
            {"title": "Item 60% off", "discount_percentage": 60, "category": "Electronics"},
            {"title": "Item 80% off", "discount_percentage": 80, "category": "Home"},
        ]
        
        filtered = filter_deals(deals, 50, ["Electronics", "Home"])
        
        assert len(filtered) == 2
        assert all(d["discount_percentage"] >= 50 for d in filtered)
```

---

### 11. CRIAR NOVO: `setup.sh` (Script de setup)

```bash
#!/bin/bash

echo "🚀 Setting up BrasilDeals..."

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env from example
if [ ! -f .env ]; then
    cp .env.example .env
    echo "⚠️  Created .env - YOU NEED TO FILL IN CREDENTIALS"
fi

# Create logs directory
mkdir -p logs

# Initialize database
python -c "from database import init_db; init_db()"

echo "✅ Setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Edit .env and fill in your credentials:"
echo "   - TELEGRAM_BOT_TOKEN (from BotFather)"
echo "   - TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN (from Twilio)"
echo "   - AMAZON_PARTNER_TAG (from Amazon Associates)"
echo "   - DATABASE_URL (PostgreSQL connection)"
echo ""
echo "2. Run tests:"
echo "   pytest tests/"
echo ""
echo "3. Run scraper once:"
echo "   python main.py"
echo ""
echo "4. Start scheduler (background):"
echo "   python scheduler.py"
```

---

### 12. CRIAR NOVO: `brasildeals.service` (systemd service file)

```ini
[Unit]
Description=BrasilDeals Scraper Service
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=brasildeals
WorkingDirectory=/home/brasildeals/brasildeals
Environment="PATH=/home/brasildeals/brasildeals/venv/bin"
ExecStart=/home/brasildeals/brasildeals/venv/bin/python scheduler.py
Restart=always
RestartSec=30
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

---

### 13. ATUALIZAR: `README.md`

```markdown
# BrasilDeals - Deal Scraper for Brazilians in USA

## Status
✅ **100% FUNCTIONAL** - No simulations, all real integrations

## Features
- ✅ Real Slickdeals RSS scraper (4x/day)
- ✅ Real Telegram posting (channel + group)
- ✅ Real WhatsApp posting (Twilio)
- ✅ Real Amazon affiliate links
- ✅ PostgreSQL database persistence
- ✅ Automatic scheduling (6AM, 10AM, 2PM, 6PM EST)
- ✅ JSON logging
- ✅ Deal filtering (50%+ discount)
- ✅ Category detection

## Prerequisites
- Python 3.9+
- PostgreSQL (local or cloud: Supabase, Heroku)
- Telegram account + BotFather
- Twilio account (free tier works)
- Amazon Associates account

## Quick Start

1. Clone and setup:
```bash
git clone <repo>
cd brasildeals
bash setup.sh
```

2. Configure credentials in `.env`:
```
TELEGRAM_BOT_TOKEN=...
TWILIO_ACCOUNT_SID=...
AMAZON_PARTNER_TAG=...
DATABASE_URL=...
```

3. Run tests:
```bash
pytest tests/
```

4. Run once:
```bash
python main.py
```

5. Run scheduled (background):
```bash
python scheduler.py
```

6. Or deploy with systemd:
```bash
sudo cp brasildeals.service /etc/systemd/system/
sudo systemctl enable brasildeals
sudo systemctl start brasildeals
```

## Architecture

```
scraper.py         → Fetches deals from RSS + Amazon PA-API
  ↓
filter_deals()     → Filters by discount % and category
  ↓
format_message()   → Creates HTML-formatted message
  ↓
messenger.py       → Posts to Telegram + WhatsApp (REAL)
  ↓
database.py        → Saves to PostgreSQL
  ↓
logging.py         → Logs everything as JSON
```

## Monitoring

```bash
# View logs
journalctl -u brasildeals -f

# Check database stats
python -c "from database import get_daily_stats; print(get_daily_stats(...))"
```

## Revenue Tracking

First commission appears in Amazon Associates dashboard after 24-48 hours.

Check at: https://affiliate-program.amazon.com/home/earnings

---

Created: May 2026  
Status: Production Ready ✅
```

---

## CHECKLIST FINAL DE EXECUÇÃO

**O agente DEVE executar nestes passos:**

- [ ] Ler PROJETO.txt completo
- [ ] Ler arquivo README.md existente
- [ ] Ler código Python existente (identificar o que é real vs mock)
- [ ] Criar/Reescrever cada arquivo conforme especificado acima
- [ ] Atualizar requirements.txt
- [ ] Criar .env.example com TODAS as variáveis
- [ ] Criar setup.sh
- [ ] Criar tests/test_integration.py
- [ ] Criar brasildeals.service
- [ ] Atualizar README.md
- [ ] Garantir que NÃO há nenhuma simulação no código
- [ ] Garantir que todos os arquivos Python usam imports reais (not mock)
- [ ] Verificar que código está pronto para produção

---

## RESULTADO ESPERADO

Após execução deste prompt, o projeto estará:

✅ **100% Funcional**
- Scraper real conectado a Slickdeals RSS
- Telegram Bot real enviando mensagens
- WhatsApp Twilio real enviando mensagens
- Amazon Associates links com affiliate tags
- PostgreSQL Database salvando deals
- APScheduler rodando 4x/dia
- Systemd service pronto para produção
- JSON logging para audit trail
- Sem nenhuma simulação ou mock

✅ **Pronto para Deploy**
- Código está refatorado e lindo
- Testes estão escritos
- Documentação está completa
- Setup script funciona
- Credenciais são variáveis de ambiente

✅ **Gerando Receita**
- Links de afiliação Amazon com partner tag
- Comissões aparecem em Amazon Associates após 24-48h
- Sistema rastreia deals postados

---

## OBSERVAÇÕES IMPORTANTES

1. **Não há mocks** - Todo código é REAL
2. **Credenciais como variáveis** - Usuário preenche .env depois
3. **Tested & Documented** - Código tem testes e documentação
4. **Production Ready** - Pronto para deploy em VPS 24/7
5. **Zero Simulações** - Diferente do código original

---

**Fim do prompt. Agente, execute!**
