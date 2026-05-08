# PROMPT DE EXECUÇÃO: BRASILDEALS 100% FUNCIONAL

## OBJETIVO
Transformar o projeto BrasilDeals de uma Prova de Conceito simulada em um **sistema 100% funcional e pronto para gerar receita** respeitando completamente o modelo de negócio especificado.

---

## CONTEXTO DO PROJETO

**Nome:** BrasilDeals (Clube USA)  
**Mercado-Alvo:** Brasileiros/Latinos nos EUA (200k+ pessoas)  
**Modelo:** Comunidade de deals + monetização multi-canal  
**Localização dos arquivos:** `C:\Users\g-fil\Documents\Projetos Claude\projetos-organizados\07-BrasilDeals-Clube-USA\`

**Documento de referência completo:** Ler `PROJETO.txt` nesta pasta

---

## FASE 1: DIAGNÓSTICO (Ler e Analisar)

Antes de implementar, faça um diagnóstico completo:

1. Leia todo o arquivo `PROJETO.txt` (especificação completa do negócio)
2. Revise o arquivo `README.md` (stack técnica atual)
3. Analise os arquivos Python:
   - `scraper.py` - identifique o que é real vs simulado
   - `deal_processor.py` - lógica de filtragem
   - `messenger.py` - foco aqui (está 100% simulado)
   - `main.py` - orquestrador
4. Liste especificamente:
   - O que está funcional
   - O que é simulado
   - O que precisa ser implementado

---

## FASE 2: IMPLEMENTAÇÃO (4 SEMANAS)

### SEMANA 1: Integração Real de Canais

**Objetivo:** Fazer o sistema enviar mensagens REAIS para Telegram e WhatsApp

#### 2.1 - Telegram Bot (3 dias)
```
□ Criar bot no BotFather (@BotFather no Telegram)
  - Salvar token do bot
  - Criar canal público: @brasildeals_club
  - Criar grupo privado: BrasilDeals Members
  
□ Instalar SDK oficial:
  pip install python-telegram-bot
  
□ Reescrever messenger.py:
  - Remover função simulada send_telegram_message()
  - Implementar integração REAL com telegram.ext.Application
  - Testar envio de mensagem formatada ao canal
  - Testar envio em grupo privado
  - Logar todas as mensagens enviadas (timestamp, deal ID)
  
□ Adicionar ao .env:
  TELEGRAM_BOT_TOKEN="seu_token_aqui"
  TELEGRAM_CHANNEL_ID="@brasildeals_club"  # Ou ID numérico -100xxxxx
  TELEGRAM_GROUP_ID="seu_group_id"
  
□ Validação: Enviar 5 deals teste e confirmar aparecem no Telegram
```

#### 2.2 - WhatsApp Business API (3 dias)
```
□ Opção A - Twilio (mais fácil para MVP):
  - Criar conta Twilio (twilio.com)
  - Configurar WhatsApp Sandbox
  - Obter credenciais: ACCOUNT_SID, AUTH_TOKEN, TWILIO_WHATSAPP_NUMBER
  - pip install twilio
  
□ Opção B - Meta Official API (mais escalável):
  - Registrar em Meta Business (meta.com/business)
  - Configurar WhatsApp Business API
  - Obter token de acesso
  - Documentação: developers.facebook.com/docs/whatsapp
  
□ Reescrever messenger.py para WhatsApp:
  - Remover simulação send_whatsapp_message()
  - Implementar envio REAL usando Twilio ou Meta SDK
  - Testar envio de mensagem formatada
  - Logar entregas (timestamp, status, telefone)
  
□ Adicionar ao .env:
  # Twilio
  TWILIO_ACCOUNT_SID="xxxx"
  TWILIO_AUTH_TOKEN="xxxx"
  TWILIO_WHATSAPP_NUMBER="+14155552671"  # Sandbox ou seu número
  WHATSAPP_RECIPIENTS="+551199999999,+551188888888"  # Múltiplos
  
  # OU Meta Official
  WHATSAPP_BUSINESS_ACCOUNT_ID="xxxx"
  WHATSAPP_ACCESS_TOKEN="xxxx"
  WHATSAPP_PHONE_NUMBER_ID="xxxx"
  
□ Validação: Enviar 5 deals teste para WhatsApp e confirmar chegam
```

#### 2.3 - Amazon Associates Afiliação (2 dias)
```
□ Registrar em Amazon Associates:
  - https://affiliate-program.amazon.com
  - Preencher dados (conta bancária para pagamento)
  - Obter Associate ID/Partner Tag
  
□ Implementar link de afiliação REAL em deal_processor.py:
  - Atualmente está usando link original do Slickdeals
  - Mudar para: https://amazon.com/dp/ASIN/?tag=YOUR_PARTNER_TAG
  - Validar que cada link tem o tag correto
  - Testar que links rastreiam corretamente na Amazon Associates
  
□ Integração opcional - Amazon PA-API (mais complexo):
  - Se quiser dados reais de preço/imagem
  - Requer credenciais: Access Key, Secret Key, Partner Tag
  - Implementar signed requests usando amazon-product-advertising-api
  - NOTA: Pode deixar para Fase 2 se não souber fazer
  
□ Adicionar ao .env:
  AMAZON_PARTNER_TAG="seu_tag"
  AMAZON_PA_API_ACCESS_KEY="xxxx"  # Opcional
  AMAZON_PA_API_SECRET_KEY="xxxx"  # Opcional
  
□ Validação: Confirmar que links em deals têm affiliate tag
```

---

### SEMANA 2: Banco de Dados e Persistência

**Objetivo:** Deixar de usar apenas memória, armazenar deals e rastrear performance

#### 2.4 - PostgreSQL Setup (2 dias)
```
□ Instalar PostgreSQL localmente ou usar Heroku Postgres:
  - Option A (Local): postgresql.org
  - Option B (Cloud): heroku.com (free tier, 10k rows)
  - Option C (Cloud): supabase.com (5MB free, bom)
  
□ Criar schema do banco:
  
  CREATE TABLE deals (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    original_link VARCHAR(500),
    affiliate_link VARCHAR(500),
    discount_percentage INT,
    category VARCHAR(100),
    source VARCHAR(50),  -- "slickdeals", "amazon", etc
    posted_at TIMESTAMP DEFAULT NOW(),
    posted_channel VARCHAR(50),  -- "telegram", "whatsapp"
    UNIQUE(title, posted_at)  -- Evitar duplicatas
  );
  
  CREATE TABLE impressions (
    id SERIAL PRIMARY KEY,
    deal_id INT REFERENCES deals(id),
    channel VARCHAR(50),  -- "telegram", "whatsapp"
    user_count INT,  -- Estimado por reações/forwards
    clicked_at TIMESTAMP
  );
  
  CREATE TABLE sales (
    id SERIAL PRIMARY KEY,
    deal_id INT REFERENCES deals(id),
    amazon_order_id VARCHAR(100),
    commission_amount DECIMAL(10,2),
    tracked_at TIMESTAMP,
    UNIQUE(amazon_order_id)
  );
  
□ Instalar driver Python:
  pip install psycopg2-binary sqlalchemy
  
□ Criar models.py usando SQLAlchemy ORM:
  - Deal, Impression, Sale models
  - Session management
  
□ Integrar com scraper.py:
  - Em vez de retornar lista em memória
  - Armazenar cada deal no DB
  - Checar duplicatas antes de inserir
  - Logar: qual deal foi salvo, timestamp, source
  
□ Adicionar ao .env:
  DATABASE_URL="postgresql://user:password@localhost/brasildeals"
  # OU para Heroku/Supabase:
  DATABASE_URL="postgresql://user:password@host.com:5432/brasildeals"
  
□ Validação: Executar scraper, confirmar deals aparecem no DB
```

#### 2.5 - Dashboard de Tracking (2 dias)
```
□ Criar dashboard.py (simples, sem frontend):
  - Função que faz queries ao DB
  - Mostra stats em terminal:
    * Total de deals scraped
    * Deals por categoria
    * Deals por canal (Telegram vs WhatsApp)
    * Timestamp do último deal
    
□ Criar relatório.py:
  - Gera relatório JSON diário
  - Salva em: reports/daily_YYYY-MM-DD.json
  - Inclui:
    * Deals do dia (count, categories)
    * Canais utilizados
    * Erros/falhas
    * Próxima execução
    
□ Output esperado:
  {
    "date": "2026-05-07",
    "deals_scraped": 15,
    "deals_filtered": 8,
    "posted_telegram": 8,
    "posted_whatsapp": 8,
    "categories": {
      "electronics": 4,
      "fashion": 2,
      "home": 2
    },
    "errors": []
  }
  
□ Validação: Executar, confirmar relatório é gerado
```

---

### SEMANA 3: Agendamento Automático e Infraestrutura

**Objetivo:** Parar de executar manualmente, fazer rodar automaticamente 4x/dia

#### 2.6 - Agendador (2 dias)
```
□ Opção A - Python APScheduler (simples):
  pip install apscheduler
  
  Implementar em scheduler.py:
  ```python
  from apscheduler.schedulers.background import BackgroundScheduler
  
  scheduler = BackgroundScheduler()
  scheduler.add_job(
      run_deal_scraper_once,
      'cron',
      hour='6,10,14,18',  # 6AM, 10AM, 2PM, 6PM
      timezone='America/New_York'
  )
  scheduler.start()
  ```
  
□ Opção B - Celery (mais robusto):
  pip install celery redis
  - Requer Redis
  - Melhor para produção
  - Mais complexo
  
□ RECOMENDAÇÃO: APScheduler para MVP, depois migra para Celery
  
□ Testar:
  - Executar scheduler.py
  - Esperar próxima execução agendada
  - Confirmar que scraped, filtrou, e postou automaticamente
```

#### 2.7 - Deploy em VPS (2 dias)
```
□ Escolher VPS:
  - Opção A: Heroku (fácil, $5-7/mês)
  - Opção B: Digital Ocean (melhor, $5/mês)
  - Opção C: Hetzner (barato, €3/mês)
  
□ Setup no VPS:
  1. SSH into servidor
  2. apt-get install python3.9 python3-pip postgresql
  3. Clone o repo (ou upload files)
  4. pip install -r requirements.txt
  5. Configure .env com credenciais
  6. Criar systemd service:
  
  # /etc/systemd/system/brasildeals.service
  [Unit]
  Description=BrasilDeals Scraper
  After=network.target
  
  [Service]
  Type=simple
  User=ubuntu
  WorkingDirectory=/home/ubuntu/brasildeals
  ExecStart=/usr/bin/python3 scheduler.py
  Restart=always
  
  [Install]
  WantedBy=multi-user.target
  
  7. sudo systemctl enable brasildeals
  8. sudo systemctl start brasildeals
  9. Confirmar que está rodando: sudo systemctl status brasildeals
  
□ Monitoramento:
  - Logs: journalctl -u brasildeals -f
  - Alertas se falhar por 2 execuções seguidas
  
□ Validação: VPS rodando, scrapers executando 4x/dia sozinhos
```

---

### SEMANA 4: Monetização FASE 1 + Testes

**Objetivo:** Começar a ganhar dinheiro real com Amazon Associates

#### 2.8 - Sistema de Monitoramento de Vendas (1 dia)
```
□ Integrar com Amazon Associates API:
  - Rastrear clicks → conversões → comissão
  - Amazon fornece relatório via web ou API
  - Implementar scraper de relatório da Amazon
  - OU usar affiliate link tracking manual
  
□ Implementar tracking simples:
  - URL tracking parameters: ?ref=brasildeals_deal_ID
  - Monitorar manualmente no painel Amazon Associates
  - Log todas as comissões em DB
  
□ Dashboard de receita:
  - Mostrar: $ ganho hoje, semana, mês
  - Estimar: $ por deal, $ por visitante
  
□ Validação: Postar deals, esperar cliques, ver $ no Amazon Associates
```

#### 2.9 - Testes e Otimização (2 dias)
```
□ Teste E2E:
  1. Executar main.py manualmente
  2. Verificar deals aparecem no Telegram ✓
  3. Verificar deals aparecem no WhatsApp ✓
  4. Verificar links tem affiliate tag ✓
  5. Verificar dados salvos no DB ✓
  6. Verificar relatório gerado ✓
  
□ Teste de carga:
  - Scrapar 100+ deals simultâneos
  - Enviar para 500+ contatos
  - Medir tempo de execução
  - Otimizar gargalos
  
□ Teste de confiabilidade:
  - Simular falha de rede (Telegram down)
  - Simular DB offline
  - Confirmar que sistema não quebra, continua na próxima vez
  - Implementar retry logic com exponential backoff
  
□ Otimizações:
  - Batch requests ao Telegram/WhatsApp (enviar 10 deals em 1 mensagem)
  - Cachet para não re-postar mesmo deal 2x
  - Priorizar deals com desconto > 60%
```

#### 2.10 - Documentação Final (1 dia)
```
□ Atualizar README.md com:
  - Como setup local (dev)
  - Como deploy em VPS (prod)
  - Variáveis de ambiente necessárias
  - Como acessar dashboard
  - Como interpretar relatórios
  - Troubleshooting
  
□ Criar DEPLOYMENT.md com:
  - Passo a passo deploy em Digital Ocean
  - Health checks
  - Backup strategy do DB
  - Escalonamento (quando > 5k membros)
  
□ Atualizar PROJETO.txt:
  - Marcar como "FUNCIONAL - FASE 1 COMPLETADA"
  - Documentar o que foi implementado
  - Descrever próximas fases
```

---

## FASE 3: VALIDAÇÃO COM USUÁRIOS REAIS (1 SEMANA)

**Objetivo:** Confirmar que o sistema funciona, e colher dados reais de desempenho

```
□ Recrutar 50-100 usuários beta:
  - Reddit: r/BrazilianExpats, r/Brazil
  - WhatsApp groups de brasileiros
  - Amigos/família
  
□ Postar deals durante 1 semana:
  - 5 deals/dia via Telegram
  - 5 deals/dia via WhatsApp
  
□ Coletar métricas:
  - Quantos clicaram no link? (simples: pedir feedback)
  - Quantos compraram? (rastrear no Amazon Associates)
  - Qual desconto atrai mais cliques?
  - Qual categoria vende mais?
  - Telegram ou WhatsApp funciona melhor?
  
□ Decisão:
  - Se > 5% conversão → continua e escala para Fase 2
  - Se < 5% conversão → iterar, mudar copy dos deals, etc
```

---

## FASE 4: FASE 2 DO MODELO DE NEGÓCIO (Depois)

SOMENTE depois que Fase 1 funcionar e gerar receita:

```
□ VIP Tier $4.99/mês:
  - Stripe integration
  - Grupo WhatsApp privado para VIPs
  - Early access a deals (15min antes)
  
□ Maria Madah Integration:
  - Post semanal da marca
  - Link de afiliação com margem 65%
  
□ Sistema de Remessas:
  - Parceria Wise/Remitly
  - Bot para converter USD → BRL
  - Ganho: $5-10 por transação
```

---

## REQUISITOS TÉCNICOS

### Dependências Novas (adicionar a requirements.txt):
```
python-telegram-bot>=20.0
twilio>=8.0  # OU facebook-business para Meta WhatsApp
psycopg2-binary>=2.9
sqlalchemy>=2.0
apscheduler>=3.10
python-dotenv>=0.20
gunicorn>=20.0  # Para deploy
```

### Variáveis de Ambiente Necessárias (.env):
```
# Telegram
TELEGRAM_BOT_TOKEN=xxx
TELEGRAM_CHANNEL_ID=xxx
TELEGRAM_GROUP_ID=xxx

# WhatsApp (Twilio)
TWILIO_ACCOUNT_SID=xxx
TWILIO_AUTH_TOKEN=xxx
TWILIO_WHATSAPP_NUMBER=xxx
WHATSAPP_RECIPIENTS=xxx

# Amazon
AMAZON_PARTNER_TAG=xxx

# Database
DATABASE_URL=postgresql://...

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/brasildeals.log
```

---

## ENTREGAS ESPERADAS

Ao final de 4 semanas:

```
✅ Código 100% funcional (zero simulação)
✅ Scraper rodando automaticamente 4x/dia
✅ Mensagens REAIS no Telegram
✅ Mensagens REAIS no WhatsApp
✅ Deals armazenados no DB
✅ Links com affiliate tag funcionando
✅ Dashboard mostrando stats
✅ Relatórios diários gerados
✅ Rodando em VPS 24/7
✅ Primeira receita de comissões Amazon
✅ Documentação completa
✅ Pronto para Fase 2 (VIP Tier)
```

---

## NOTAS IMPORTANTES

1. **Não simulem nada** - Cada integração deve ser REAL
2. **Testes são críticos** - Depois de cada integração, testar com dados reais
3. **Banco de dados é essencial** - Sem DB, não conseguem escalar
4. **Documentem tudo** - Relatórios diários devem ser lidos
5. **Respeitem o modelo de negócio** - Não mudem fases, sigam na ordem
6. **Meçam resultados** - CTR, conversão, comissão — tudo importa
7. **Deploy cedo** - Não esperar 4 semanas, fazer deploy na semana 2

---

## SUCESSO = ?

Quando vocês conseguirem:

```
1. Postar 20+ deals/dia automaticamente ✓
2. Receber clicks REAIS de 100+ usuários ✓
3. Ganhar primeira comissão da Amazon ✓
4. Ter 500+ membros engajados ✓
5. Relatórios mostrando ROI positivo ✓
```

Aí sim, BrasilDeals é um negócio de verdade.

---

**Data:** 07 de Maio de 2026  
**Criado por:** Claude  
**Para:** Gerson Mence  
**Referência:** Projeto 07-BrasilDeals-Clube-USA
