# 🔍 AUDITORIA DETALHADA - JSONDecodeError: Expecting value: line 2 column 1

**Data:** 25/02/2026  
**Arquivo:** `app_FINAL_FLASK.py`  
**Status:** 🔴 CRÍTICO - Bug Identificado

---

## 🎯 RESUMO EXECUTIVO

**O erro acontece na linha 385-388 da função `buscar_cidade()`.**

Quando LocationIQ API retorna algo que NÃO é JSON válido (HTML, texto vazio, status != 200), o código tenta chamar `.json()` sem validação, causando `JSONDecodeError`.

---

## 🔴 PROBLEMA #1: LocationIQ Geocoding (Linhas 377-390)

```python
# ❌ CÓDIGO PROBLEMÁTICO:
response = requests.get(url, params=params, timeout=10)

if not response.json():  # ← LINHA 385: CRASH AQUI!
    return jsonify({'success': False, 'error': 'Cidade não encontrada'}), 404

result = response.json()[0]  # ← LINHA 388: E AQUI!
lat, lng = float(result['lat']), float(result['lon'])
```

### Por que falha:

```
1. LocationIQ retorna HTTP 404 (chave inválida)
2. response.status_code = 404
3. response.content = HTML (página de erro)
4. response.json() tenta parsear HTML como JSON
5. ❌ JSONDecodeError: Expecting value: line 2 column 1 (char 1)
```

### Fluxo do erro:

```
GET /api/buscar/Andover
  ↓
Linha 377-383: requests.get(LocationIQ API)
  ↓
LocationIQ retorna: HTTP 404 + HTML
  ↓
Linha 385: if not response.json()
  ↓
❌ CRASH: JSONDecodeError
  ↓
Flask retorna: HTTP 500 (Internal Server Error)
  ↓
Frontend: "This site can't be reached"
```

---

## 🔴 PROBLEMA #2: Google Places (Linhas 205-207)

```python
# ❌ CÓDIGO PROBLEMÁTICO (buscar_google_places):
response = requests.get(url, params=params, timeout=10)
data = response.json()  # ← Sem validação de status_code
```

**Mesmo problema:** Se Google retorna status != 200, `.json()` falha.

---

## 🔴 PROBLEMA #3: NREL (Linhas 260-262)

```python
# ❌ CÓDIGO PROBLEMÁTICO (obter_chargers_proximos):
response = requests.get(url, params=params, timeout=5)
data = response.json()  # ← Sem validação de status_code
```

**Mesmo problema.**

---

## 🔴 PROBLEMA #4: Census API (Linhas 348-350)

```python
# ❌ CÓDIGO PROBLEMÁTICO (obter_demographics_census):
response = requests.get(url, params=params, timeout=5)
data = response.json()  # ← Sem validação de status_code
```

**Mesmo problema.**

---

## 🔴 PROBLEMA #5: TomTom (Linhas 327-330)

```python
# ⚠️ PARCIALMENTE CORRIGIDO:
if response.status_code == 200:
    data = response.json()  # ← OK aqui, tem validação
```

**Este está mais seguro, mas falta validação de content-type.**

---

## 📊 RESUMO DE FALHAS

| Linha | Função | Problema | Severidade |
|-------|--------|----------|-----------|
| 385-388 | buscar_cidade() | LocationIQ sem validação status | 🔴 CRÍTICO |
| 205 | buscar_google_places() | Google Places sem validação | 🔴 CRÍTICO |
| 260 | obter_chargers_proximos() | NREL sem validação | 🔴 CRÍTICO |
| 348 | obter_demographics_census() | Census sem validação | 🔴 CRÍTICO |
| 327 | obter_trafego_tomtom() | TomTom parcialmente OK | 🟡 PARCIAL |

---

## 🎯 POR QUE NÃO FUNCIONA A LocationIQ

### Sua chave: `pk.50e7c9d4f3fdcaad74cf780520d73fef`

Quando você faz:
```
GET https://api.locationiq.com/v1/search.json?key=pk.50e7c9d4f3fdcaad74cf780520d73fef&q=Boston,Massachusetts&format=json
```

LocationIQ retorna:

```
HTTP 404
Content-Type: text/html; charset=utf-8
Body: <!DOCTYPE html><html>...</html>
```

Seu código tenta:
```python
response.json()  # ← Tenta parsear HTML como JSON
```

Resultado:
```
JSONDecodeError: Expecting value: line 2 column 1 (char 1)
```

---

## ✅ COMO DETECTAR O ERRO ANTES DE CHAMAR `.json()`

### Validação correta:

```python
# ✅ SOLUÇÃO:
response = requests.get(url, params=params, timeout=10)

# Validação 1: Status code
if response.status_code != 200:
    print(f"❌ HTTP {response.status_code}")
    print(f"Body preview: {response.text[:200]}")
    return None, {
        'error': f'HTTP {response.status_code}',
        'status_code': response.status_code
    }

# Validação 2: Content-Type
if 'json' not in response.headers.get('content-type', '').lower():
    print(f"❌ Not JSON: {response.headers.get('content-type')}")
    return None, {
        'error': 'Response is not JSON',
        'content_type': response.headers.get('content-type')
    }

# Validação 3: Body vazio
if not response.text.strip():
    print(f"❌ Empty body")
    return None, {
        'error': 'Response body is empty'
    }

# Validação 4: Agora é seguro chamar .json()
try:
    data = response.json()
    return data, None
except json.JSONDecodeError as e:
    print(f"❌ JSON parse error: {e}")
    return None, {
        'error': f'JSON parse error: {str(e)}'
    }
```

---

## 📋 CHECKLIST DE PROBLEMAS

```
[X] LocationIQ: Status code não validado (Linha 383-385)
[X] LocationIQ: response.json() chamado 2x sem validação (Linha 385, 388)
[X] Google Places: Status code não validado (Linha 205)
[X] NREL: Status code não validado (Linha 260)
[X] Census: Status code não validado (Linha 348)
[X] Todos: Sem validação de content-type
[X] Todos: Sem try/except em .json()
[X] Todos: Sem preview do body em erro
[X] Todos: API keys hardcoded (linhas 60-64)
[X] Todos: Sem fallback (ex: se LocationIQ falha, deveria tentar OpenCage/Nominatim)
```

---

## 🎯 IMPACTO

```
🔴 Crítico: 5 APIs sem validação
🔴 100% das buscas podem retornar 500 se uma API falhar
🔴 Frontend trava porque backend retorna erro ao invés de dados parciais
🔴 LocationIQ bloqueado = sistema inteiro quebrado
```

---

## ✅ SOLUÇÃO

Implementar função centralizada `fetch_json()` que:

1. ✅ Valida status_code == 200
2. ✅ Valida content-type contém "json"
3. ✅ Valida body não vazio
4. ✅ Faz try/except de .json()
5. ✅ Retorna (data, None) ou (None, error_dict)
6. ✅ Loga erros em detalhe
7. ✅ Nunca retorna 500 para erro externo

---

## 📊 ARQUIVOS AFETADOS

```
app_FINAL_FLASK.py:
├─ Linha 383-388: LocationIQ (CRÍTICO)
├─ Linha 205: Google Places (CRÍTICO)
├─ Linha 260: NREL (CRÍTICO)
├─ Linha 348: Census (CRÍTICO)
├─ Linha 327: TomTom (PARCIAL)
├─ Linhas 60-64: API Keys hardcoded (SEGURANÇA)
└─ Linha 364+: Rota buscar_cidade sem fallback (RESILIÊNCIA)
```

---

## 📝 PRÓXIMO PASSO

Você quer que eu crie o refactor completo seguindo os 10 requisitos do GPT? Vou entregar:

1. ✅ Função `fetch_json()` robusta
2. ✅ Geocoding com fallback (LocationIQ → OpenCage → Nominatim)
3. ✅ Rota `/api/buscar/<cidade>` revisada (nunca retorna 500)
4. ✅ API keys em .env
5. ✅ requirements.txt correto
6. ✅ Procfile correto
7. ✅ .env.example
8. ✅ Logging estruturado
9. ✅ Schema padronizado para scoring_engine
10. ✅ Resiliência em falhas parciais

**Quer que eu execute?** 👇
