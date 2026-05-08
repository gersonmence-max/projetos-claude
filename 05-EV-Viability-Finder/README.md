# Buscador de Terrenos

Ferramenta local para encontrar terrenos baratos em **Alabama (AL)** e **Arkansas (AR)**. Raspa listagens do Zillow, enriquece com dados FEMA e Regrid, aplica filtros automáticos e pontua cada terreno com IA.

## Requisitos

- Python 3.11+
- Node.js 18+
- Chave de API da Anthropic (para análise IA)

## Instalação

### 1. Backend

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
```

Edite `backend/.env` e adicione sua chave:
```env
ANTHROPIC_API_KEY=sk-ant-...
REGRID_API_KEY=          # opcional
```

Inicie o backend:
```bash
uvicorn main:app --reload --port 8000
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Abra: **http://localhost:5173**

---

## Como Usar

1. Acesse `http://localhost:5173`
2. Vá para **Pipeline** → clique **Rodar Pipeline**
3. Acompanhe o progresso em tempo real
4. Volte ao **Dashboard** para ver os terrenos pontuados
5. Clique em qualquer terreno para ver detalhes completos, análise IA e links para Google Maps / Street View

---

## Filtros Disponíveis

| Filtro | Padrão |
|---|---|
| Preço máximo | $500.000 |
| Tamanho mínimo | 1 acre |
| Desconto mínimo vs. média | 10% |
| Preço/acre máximo | $10.000/ac |
| Zona FEMA | Apenas Zona X (sem risco de inundação) |

Os filtros de desconto e preço/acre requerem a chave Regrid. Sem ela, ficam desabilitados automaticamente.

---

## Score (0–100)

| Critério | Peso |
|---|---|
| Desconto vs. média regional | 35% |
| Preço por acre | 25% |
| Zona FEMA segura | 20% |
| Tamanho em acres | 10% |
| Acesso a estrada + utilidades | 10% |

Terrenos com **score ≥ 70** recebem análise textual do Claude com resumo, pontos positivos, pontos de atenção e veredicto.

---

## Testes

```bash
cd backend
pytest tests/ -v
```
