# LandHQ — Frontend

Dashboard em português para monitoramento de imóveis em leilão fiscal (tax deed) nos EUA.

Construído com Next.js 14, TypeScript e Tailwind CSS.

## Telas

| Rota | Tela |
|------|------|
| `/` | Home — resumo + oportunidades quentes + alertas 48h |
| `/imoveis` | Lista de imóveis com 14 filtros + exportar CSV |
| `/imoveis/[id]` | Detalhe — 7 Passos + liens + calculadora owner financing + análise IA |
| `/salvos` | Imóveis salvos com notas |
| `/analytics` | Distribuição de scores e estatísticas |
| `/configuracoes` | Gerenciar condados + acionar pipeline |

## Rodar

```bash
npm run dev       # desenvolvimento — http://localhost:3000
npm run build     # build de produção
npm start         # servir build de produção
```

## Variável de ambiente

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Dependências principais

- `@tanstack/react-query` — cache e sincronização de dados
- `recharts` — gráfico de distribuição de scores
- `axios` — cliente HTTP para a API FastAPI

Consulte o README principal em `../../README.md` para documentação completa do sistema.
