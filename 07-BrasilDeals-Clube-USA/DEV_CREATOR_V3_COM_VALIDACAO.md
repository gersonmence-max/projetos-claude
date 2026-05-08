# 🔐 DEV CREATOR v3: SISTEMA COM VALIDAÇÃO E REVISÃO

**EXECUÇÃO COM MÚLTIPLAS CAMADAS DE CONFERÊNCIA ANTES DE FINALIZAR**

---

## ARQUITETURA DE VALIDAÇÃO

```
┌─────────────────────────────────────────────────────┐
│  ETAPA 1: ANÁLISE E PLANEJAMENTO                   │
│  - Ler especificação completa                       │
│  - Criar diagrama de arquitetura                    │
│  - Listar TODOS os arquivos + tamanho esperado      │
└─────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────┐
│  ETAPA 2: GERAÇÃO DE CÓDIGO                         │
│  - Criar cada arquivo um por um                     │
│  - NÃO deixar nenhum vazio                          │
│  - Validar sintaxe imediatamente                    │
└─────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────┐
│  ETAPA 3: CHECKPOINT 1 - VERIFICAÇÃO BÁSICA        │
│  ✓ Arquivo existe?                                 │
│  ✓ Arquivo não está vazio? (> 100 bytes)           │
│  ✓ Sintaxe Python correta?                         │
│  ✓ Imports resolvem?                               │
└─────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────┐
│  ETAPA 4: CHECKPOINT 2 - VALIDAÇÃO DE CONTEÚDO    │
│  ✓ Arquivo tem as funções esperadas?               │
│  ✓ Funções têm docstrings?                         │
│  ✓ Variáveis críticas existem?                     │
│  ✓ Tratamento de erros implementado?               │
└─────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────┐
│  ETAPA 5: CHECKPOINT 3 - INTEGRAÇÃO                │
│  ✓ Imports entre módulos funcionam?                │
│  ✓ Não há dependências circulares?                 │
│  ✓ Config está acessível de todos?                 │
│  ✓ Database functions estão presentes?             │
└─────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────┐
│  ETAPA 6: AGENTE DE REVISÃO (Claude)               │
│  - Ler CADA arquivo e revisar qualidade            │
│  - Verificar:                                      │
│    * Código segue padrões Python                   │
│    * Sem simulações/mocks                          │
│    * Tratamento de erros robusto                   │
│    * Documentação clara                            │
│    * Performance acceptable                        │
│  - CORRIGIR problemas encontrados                  │
│  - REVALIDAR após correções                        │
└─────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────┐
│  ETAPA 7: TESTE END-TO-END                         │
│  - Executar setup.sh (criar venv, instalar deps)   │
│  - Executar python main.py (teste de sintaxe)      │
│  - Executar pytest (testes unitários)              │
│  - Verificar logs são criados                      │
│  - Confirmar DB schema criado                      │
└─────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────┐
│  ETAPA 8: RELATÓRIO FINAL DETALHADO                │
│  - Listar TODOS os 16 arquivos + status            │
│  - Documentar o que foi criado vs esperado          │
│  - Listar qualquer aviso ou problema               │
│  - Gerar checklist de próximas ações                │
│  - Relatório em JSON para auditoria                │
└─────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────┐
│  ✅ SISTEMA PRONTO PARA PRODUÇÃO                   │
│  - Todos os arquivos validados                     │
│  - Código revisado por agente                      │
│  - Testes passando                                 │
│  - Documentação completa                           │
└─────────────────────────────────────────────────────┘
```

---

## ETAPA 1: ANÁLISE E PLANEJAMENTO

**O agente deve:**

```
1. Ler PROJETO.txt (especificação completa)
2. Listar TODOS os 16 arquivos esperados com:
   - Nome
   - Propósito
   - Tamanho esperado (KB)
   - Funções críticas esperadas
   
3. Exemplo de output:

   ARQUIVO 1: requirements.txt
   - Propósito: Dependências Python
   - Tamanho esperado: 0.5-1 KB
   - Conteúdo crítico: python-telegram-bot, twilio, sqlalchemy, psycopg2, apscheduler
   
   ARQUIVO 2: models.py
   - Propósito: SQLAlchemy ORM models
   - Tamanho esperado: 2-3 KB
   - Funções críticas: Deal, PostLog, Commission, DailyStats classes
   
   ARQUIVO 3: database.py
   - Propósito: Conexão PostgreSQL e operações DB
   - Tamanho esperado: 3-4 KB
   - Funções críticas: init_db(), save_deal(), log_post(), get_daily_stats()
   
   ... (continue para todos os 16)
```

---

## ETAPA 2: GERAÇÃO DE CÓDIGO

**O agente deve:**

```
1. Criar CADA arquivo completo (não deixar vazio)
2. Para CADA arquivo:
   a) Gerar código completo
   b) Validar sintaxe Python
   c) Verificar que NÃO está vazio
   d) Confirmar que foi escrito
   
3. Se arquivo ficar vazio ou incompleto:
   - PARAR
   - Relatar qual arquivo e por quê
   - REGENERAR esse arquivo
   - Validar novamente
   
4. Output esperado:
   ✅ requirements.txt (285 bytes) - VÁLIDO
   ✅ models.py (2847 bytes) - VÁLIDO
   ✅ database.py (3452 bytes) - VÁLIDO
   ✅ scraper.py (5234 bytes) - VÁLIDO
   ... etc
```

---

## ETAPA 3: CHECKPOINT 1 - VERIFICAÇÃO BÁSICA

**O agente deve:**

```python
for each_file in all_16_files:
    # 1. Arquivo existe?
    assert os.path.exists(file_path)
    
    # 2. Arquivo NÃO está vazio?
    file_size = os.path.getsize(file_path)
    assert file_size > 100, f"{file} é muito pequeno ({file_size} bytes)"
    
    # 3. Sintaxe Python correta?
    try:
        compile(open(file_path).read(), file_path, 'exec')
        print(f"✅ {file} - Sintaxe OK")
    except SyntaxError as e:
        print(f"❌ {file} - Erro de sintaxe: {e}")
        REGENERATE(file)
    
    # 4. Imports resolvem?
    try:
        with open(file_path) as f:
            ast.parse(f.read())
        print(f"✅ {file} - Imports OK")
    except Exception as e:
        print(f"⚠️  {file} - Aviso: {e}")
```

---

## ETAPA 4: CHECKPOINT 2 - VALIDAÇÃO DE CONTEÚDO

**O agente deve fazer CODE REVIEW:**

```python
# Para CADA arquivo, validar:

requirements.txt:
  ✓ Contém: python-telegram-bot, twilio, sqlalchemy, psycopg2, apscheduler
  ✓ Versões especificadas (não apenas "requests")
  ✓ Sem dependências desnecessárias

models.py:
  ✓ SQLAlchemy Base importado
  ✓ Classes: Deal, PostLog, Commission, DailyStats
  ✓ Cada classe tem __tablename__
  ✓ Cada coluna tem type (Column, String, Integer, etc)
  ✓ Relacionamentos definidos (ForeignKey)
  ✓ Cada função tem docstring

database.py:
  ✓ Function init_db() - cria tabelas
  ✓ Function save_deal() - salva sem duplicatas
  ✓ Function log_post() - registra posts
  ✓ Function get_daily_stats() - retorna dict
  ✓ Error handling com try/except
  ✓ Logging em cada operação crítica

messenger.py:
  ✓ NENHUMA função simulada (0 mocks)
  ✓ async def send_telegram_message() - usa telegram.Bot REAL
  ✓ def send_whatsapp_message() - usa twilio.Client REAL
  ✓ Ambos têm error handling
  ✓ Ambos retornam boolean ou ID

scraper.py:
  ✓ Function fetch_slickdeals_rss() - fetcha RSS REAL
  ✓ Function parse_rss_item() - parseia XML REAL
  ✓ Function extract_asin_from_link() - regex REAL
  ✓ NENHUMA função mock (get_amazon_product_details removida)
  ✓ Retorna lista de dicts com deal completo

scheduler.py:
  ✓ APScheduler importado
  ✓ Job configurado para 4x/dia (6, 10, 14, 18)
  ✓ Função run_scraper_cycle() implementada
  ✓ Tratamento de exceções
  ✓ Logging

config.py:
  ✓ Load from .env usando os.getenv()
  ✓ Variáveis críticas com defaults
  ✓ NENHUMA hardcoded credential

.env.example:
  ✓ Todas as variáveis esperadas
  ✓ Comentários explicando cada uma
  ✓ Valores exemplo corretos

main.py:
  ✓ Function main() assíncrona
  ✓ Fluxo: init_db → scrape → filter → post → log
  ✓ Error handling em cada etapa
  ✓ Logging detalhado

tests/test_integration.py:
  ✓ Testes para cada função crítica
  ✓ Usando pytest
  ✓ Cobrindo casos de sucesso E erro

setup.sh:
  ✓ Criar venv
  ✓ Instalar requirements
  ✓ Copiar .env.example → .env
  ✓ Init DB
  ✓ Chmod +x para scripts

brasildeals.service:
  ✓ Systemd service correto
  ✓ After=network.target
  ✓ ExecStart aponta para scheduler.py
  ✓ Restart=always

README.md:
  ✓ Setup instructions
  ✓ Quick start
  ✓ Architecture diagram
  ✓ Troubleshooting
```

---

## ETAPA 5: CHECKPOINT 3 - INTEGRAÇÃO

**O agente deve testar imports:**

```python
# Verificar que tudo se integra:

1. from config import config
   ✓ Todos os valores estão presentes

2. from models import Deal, PostLog, Commission
   ✓ Classes importam sem erro

3. from database import init_db, save_deal, log_post
   ✓ Funções importam sem erro
   
4. from scraper import get_deals_from_source_updated
   ✓ Função importa sem erro
   
5. from messenger import send_telegram_message_real, send_whatsapp_message_real
   ✓ Funções importam sem erro
   
6. from scheduler import run_scraper_cycle, start_scheduler
   ✓ Funções importam sem erro

7. Verificar dependências circulares:
   ✓ config.py não importa nada de outros módulos
   ✓ models.py importa só sqlalchemy
   ✓ database.py importa models + config
   ✓ scraper.py importa config (ok)
   ✓ messenger.py importa config + database (ok)
   ✓ scheduler.py importa tudo (ok)
   ✓ main.py importa tudo (ok)

8. Verificar que DATABASE_URL está em config:
   ✓ os.getenv("DATABASE_URL")
   
9. Verificar que TELEGRAM_BOT_TOKEN está em config:
   ✓ os.getenv("TELEGRAM_BOT_TOKEN")
   
10. Verificar que .env.example tem TODOS os necessários:
    ✓ TELEGRAM_BOT_TOKEN
    ✓ TELEGRAM_CHANNEL_ID
    ✓ TWILIO_ACCOUNT_SID
    ✓ TWILIO_AUTH_TOKEN
    ✓ AMAZON_PARTNER_TAG
    ✓ DATABASE_URL
```

---

## ETAPA 6: AGENTE DE REVISÃO (CLAUDE)

**O agente CLAUDE deve:**

```
1. Ler CADA arquivo completo (não só primeiras linhas)

2. Para CADA arquivo, fazer CODE REVIEW verificando:
   
   SEGURANÇA:
   - Nenhuma credencial hardcoded
   - Inputs são validados
   - SQL injection prevenido (usando ORM)
   - Error messages não expõem informações sensíveis
   
   QUALIDADE:
   - Código segue PEP 8
   - Funções têm propósito claro
   - Variáveis têm nomes descritivos
   - Não há código duplicado
   - Complexidade ciclomática aceitável
   
   FUNCIONALIDADE:
   - Sem mocks/simulações
   - APIs reais sendo usadas
   - Tratamento de erro robusto
   - Logging apropriado
   - Performance aceitável
   
   DOCUMENTAÇÃO:
   - Docstrings em todas funções
   - Comentários em código complexo
   - README completo
   - Setup instructions claros
   
3. Se encontrar problemas:
   - Listar exatamente o que está errado
   - Sugerir correção específica
   - REESCREVER o arquivo
   - REVALIDAR após correção

4. Output exemplo:
   
   ✅ requirements.txt - REVIEW OK
   
   ❌ models.py - 2 PROBLEMAS:
      - Falta docstring na classe Deal
      - Falta unique constraint em title
      AÇÃO: Reescrever com docstrings e constraints
      [reescreve]
      ✅ models.py - REVIEW OK (após correção)
   
   ⚠️  database.py - 1 AVISO:
      - log_post() não trata exceção se deal_id inválido
      AÇÃO: Adicionar try/except
      [modifica]
      ✅ database.py - REVIEW OK (após correção)
```

---

## ETAPA 7: TESTE END-TO-END

**O agente deve:**

```bash
# 1. Criar venv virtual
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. Instalar dependências
pip install -r requirements.txt
✓ Verificar que instala sem erro

# 3. Testar imports
python -c "from models import Deal; from database import init_db; from scraper import get_deals_from_source_updated"
✓ Nenhum import error

# 4. Testar sintaxe de todos arquivos
python -m py_compile models.py database.py scraper.py messenger.py scheduler.py main.py
✓ Todos compilam sem erro

# 5. Executar testes
pytest tests/ -v
✓ Testes passam (ou listam quais falharam)

# 6. Simular criação de DB
python -c "from database import init_db; init_db()"
✓ Database criado (sqlite:///brasildeals.db)

# 7. Verificar estrutura de pasta
ls -la
✓ Verificar que logs/ foi criado
✓ Verificar que tests/ existe
```

---

## ETAPA 8: RELATÓRIO FINAL DETALHADO

**O agente deve gerar relatório.json:**

```json
{
  "project": "BrasilDeals",
  "execution_date": "2026-05-07T22:30:00Z",
  "status": "✅ READY FOR PRODUCTION",
  "validation_status": "PASSED ALL CHECKPOINTS",
  
  "files_generated": {
    "requirements.txt": {
      "status": "✅ OK",
      "size_bytes": 285,
      "syntax_check": "✅ PASS",
      "content_check": "✅ PASS",
      "review_check": "✅ PASS",
      "critical_content": ["python-telegram-bot", "twilio", "sqlalchemy", "psycopg2"]
    },
    "models.py": {
      "status": "✅ OK",
      "size_bytes": 2847,
      "syntax_check": "✅ PASS",
      "content_check": "✅ PASS",
      "review_check": "✅ PASS",
      "classes": ["Deal", "PostLog", "Commission", "DailyStats"]
    },
    "database.py": {
      "status": "✅ OK",
      "size_bytes": 3452,
      "syntax_check": "✅ PASS",
      "content_check": "✅ PASS",
      "review_check": "✅ PASS",
      "functions": ["init_db", "save_deal", "log_post", "get_daily_stats"]
    },
    ... (continue para todos 16)
  },
  
  "checkpoint_results": {
    "checkpoint_1_basic": "✅ PASS - Todos arquivos existem e não estão vazios",
    "checkpoint_2_content": "✅ PASS - Conteúdo validado em todos arquivos",
    "checkpoint_3_integration": "✅ PASS - Imports resolvem, sem circular dependencies",
    "checkpoint_4_review": "✅ PASS - Code review completou, 3 problemas corrigidos",
    "checkpoint_5_e2e": "✅ PASS - Todos testes passam, DB criado"
  },
  
  "issues_found_and_fixed": [
    {
      "file": "models.py",
      "issue": "Faltava docstring em Deal class",
      "severity": "LOW",
      "status": "FIXED"
    },
    {
      "file": "database.py",
      "issue": "log_post() não tratava exceção em deal_id inválido",
      "severity": "MEDIUM",
      "status": "FIXED"
    },
    {
      "file": "messenger.py",
      "issue": "send_telegram_message retornava None ao invés de False",
      "severity": "MEDIUM",
      "status": "FIXED"
    }
  ],
  
  "test_results": {
    "syntax_tests": "✅ 16/16 PASS",
    "import_tests": "✅ 10/10 PASS",
    "integration_tests": "✅ 8/8 PASS",
    "e2e_tests": "✅ 5/5 PASS"
  },
  
  "summary": {
    "total_files": 16,
    "files_valid": 16,
    "files_with_issues": 0,
    "total_lines_of_code": 2847,
    "test_coverage": "85%",
    "ready_for_production": true
  },
  
  "next_steps": [
    "1. Preencher .env com credenciais reais",
    "2. Executar: bash setup.sh",
    "3. Teste local: python main.py",
    "4. Deploy em VPS: systemctl start brasildeals"
  ]
}
```

---

## CHECKLIST FINAL (Antes de liberar)

```
VALIDAÇÃO OBRIGATÓRIA:

Arquivos:
[ ] Todos 16 arquivos existem?
[ ] Nenhum arquivo vazio? (todos > 100 bytes)
[ ] Sintaxe Python válida em todos?
[ ] Nenhuma dependência circular?

Código:
[ ] Nenhuma simulação/mock encontrada?
[ ] Apis reais sendo usadas (Telegram, WhatsApp, etc)?
[ ] Error handling em funções críticas?
[ ] Logging apropriado?
[ ] Docstrings em todas funções?

Integração:
[ ] Imports funcionam entre módulos?
[ ] Config acessível de todos módulos?
[ ] Database functions presentes?
[ ] Scheduler configurado?

Testes:
[ ] Testes unitários passam?
[ ] E2E funciona?
[ ] Database criado com sucesso?
[ ] Logs são gerados?

Documentação:
[ ] README completo?
[ ] Setup.sh funciona?
[ ] .env.example tem tudo?
[ ] Comments claros no código?

ENTÃO E SOMENTE ENTÃO:
✅ LIBERAR PARA PRODUÇÃO
```

---

## RESULTADO ESPERADO

```
======================================================================
✅ DEV CREATOR v3 - EXECUÇÃO COMPLETA COM VALIDAÇÃO
======================================================================

Passos Executados:
  [1/8] ✅ Análise e Planejamento
  [2/8] ✅ Geração de Código (16/16 arquivos)
  [3/8] ✅ Checkpoint 1 - Verificação Básica
  [4/8] ✅ Checkpoint 2 - Validação de Conteúdo
  [5/8] ✅ Checkpoint 3 - Integração
  [6/8] ✅ Agente de Revisão (Claude) - 3 problemas encontrados e CORRIGIDOS
  [7/8] ✅ Teste End-to-End
  [8/8] ✅ Relatório Final Detalhado

Resultado:
  - 16/16 arquivos válidos
  - 0 problemas pendentes
  - 100% pronto para produção
  
Relatório: reports/validation_report.json
======================================================================
```

---

## VANTAGENS DESTE SISTEMA:

✅ **Nenhum arquivo vazio** - Todos validados antes de entregar  
✅ **Agente revisa tudo** - Code review automático  
✅ **Problemas corrigidos** - Encontra e conserta antes de finalizar  
✅ **Testes passam** - E2E validado  
✅ **Relatório detalhado** - Rastreabilidade completa  
✅ **Pronto para produção** - Sem surpresas depois  

---

**FIM DA ESPECIFICAÇÃO. AGENTE, EXECUTE DEV CREATOR v3 COM VALIDAÇÃO COMPLETA!**
