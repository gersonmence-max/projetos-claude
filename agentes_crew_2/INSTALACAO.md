# INSTALACAO - agentes_crew_2
## EV Viability Backend v2.1

---

## ESTRUTURA DA PASTA

```
agentes_crew_2/
├── app.py                          ← arquivo principal (RODAR ESTE)
├── scoring_engine.py               ← motor de scoring
├── requirements.txt                ← dependencias
├── .env                            ← API keys (JA PREENCHIDO)
├── .gitignore
├── Procfile                        ← deploy Heroku/Railway
│
├── correcoes/
│   ├── __init__.py
│   ├── correcao_1_penalidade_dinamica.py
│   ├── correcao_2_confidence_ranking.py
│   ├── correcao_3_timeout_global.py
│   └── correcao_4_feature_flags.py
│
├── services/
│   ├── __init__.py
│   ├── http.py                     ← fetch_json robusto
│   └── geocode.py                  ← geocoding com fallback
│
├── config/
│   ├── __init__.py
│   └── feature_flags.json          ← ligar/desligar funcionalidades
│
└── templates/
    └── index.html                  ← frontend
```

---

## PASSO 1 — ABRIR O TERMINAL

Abra o **Prompt de Comando** (cmd) ou **PowerShell** dentro da pasta `agentes_crew_2`:

```
Clique com botao direito na pasta > "Abrir no Terminal"
```

Ou navegue manualmente:
```cmd
cd C:\caminho\para\agentes_crew_2
```

---

## PASSO 2 — CRIAR AMBIENTE VIRTUAL

```cmd
python -m venv venv
```

Ativar:
```cmd
venv\Scripts\activate
```

Voce deve ver `(venv)` no inicio da linha do terminal.

---

## PASSO 3 — INSTALAR DEPENDENCIAS

```cmd
pip install -r requirements.txt
```

Aguarde o download de todos os pacotes.

---

## PASSO 4 — RODAR O APP

```cmd
python app.py
```

Voce deve ver:
```
============================================================
  EV VIABILITY BACKEND - agentes_crew_2 v2.1
  4 Correcoes Criticas Ativas
  Debug: True
  Cidades: 331
  Acesse: http://localhost:5000
============================================================
```

---

## PASSO 5 — TESTAR

Abra o navegador e acesse:

```
http://localhost:5000
```

Para testar a API diretamente:
```
http://localhost:5000/health
http://localhost:5000/cidades
http://localhost:5000/api/buscar/Boston
http://localhost:5000/api/buscar/Cambridge?modo=level2
```

---

## PASSO 6 — VERIFICAR HEALTH CHECK

Acesse `http://localhost:5000/health`

Resposta esperada:
```json
{
  "success": true,
  "status": "healthy",
  "version": "agentes_crew_2 v2.1",
  "env": {
    "has_google_places": true,
    "has_nrel": true,
    "has_tomtom": true
  }
}
```

Se alguma key aparecer como `false`, verifique o arquivo `.env`.

---

## RESOLUCAO DE PROBLEMAS

### "ModuleNotFoundError: No module named 'flask'"
```cmd
pip install -r requirements.txt
```

### "ModuleNotFoundError: No module named 'correcoes'"
Verifique se voce esta rodando de DENTRO da pasta `agentes_crew_2`:
```cmd
cd agentes_crew_2
python app.py
```

### "ModuleNotFoundError: No module named 'dotenv'"
```cmd
pip install python-dotenv
```

### App inicia mas busca retorna erro
Ative o debug detalhado editando `.env`:
```
DEBUG=1
```

### LocationIQ retorna erro
Sem problema! O sistema tem fallback automatico:
LocationIQ > OpenCage > Nominatim (OSM)
Pelo menos o Nominatim sempre funciona, sem necessidade de key.

---

## FEATURE FLAGS

Para ligar/desligar funcionalidades sem mudar o codigo,
edite o arquivo `config/feature_flags.json`:

```json
{
    "USE_DYNAMIC_PENALTIES":    true,
    "USE_CONFIDENCE_WEIGHTING": true,
    "USE_NEW_TIMEOUT":          true,
    "USE_NEW_RANKING":          true,
    "USE_PDF_GENERATION":       true,
    "USE_NOMINATIM_FALLBACK":   true,
    "DEBUG_API_CALLS":          false
}
```

Altere `true` para `false` para desativar qualquer correcao.

---

## DIFERENCA PARA A PASTA ANTIGA

| Item                  | Pasta antiga         | agentes_crew_2        |
|-----------------------|----------------------|-----------------------|
| Imports quebrados     | SIM (pasta vazia)    | CORRIGIDO             |
| JSONDecodeError       | SIM (sem validacao)  | CORRIGIDO (fetch_json)|
| API keys expostas     | SIM (hardcoded)      | CORRIGIDO (.env)      |
| Geocoding fallback    | NAO                  | SIM (3 tentativas)    |
| Timeout global        | NAO                  | SIM (8s)              |
| Feature flags         | Quebrado             | Funcional             |
| Nunca retorna 500     | NAO                  | SIM                   |

---

Projeto pronto. Boa reuniao!
