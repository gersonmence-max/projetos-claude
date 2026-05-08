# Clube USA — Setup de Seguranca

## 1. Gerar chaves secretas

```bash
cd clubeusa
python utils/security.py
```

Cole as chaves geradas no seu `.env`.

## 2. Configurar .env

```bash
cp .env.example .env
# Edite .env com suas credenciais reais
```

## 3. Aplicar schema no Supabase

No painel do Supabase > SQL Editor:
1. Cole e execute `db/schema.sql`
2. Cole e execute `db/rpc_functions.sql`

## 4. Instalar dependencias

```bash
pip install supabase cryptography python-jose[cryptography] requests
```

## 5. Variaveis obrigatorias

| Variavel | Onde obter |
|---|---|
| SUPABASE_URL | Supabase > Settings > API |
| SUPABASE_ANON_KEY | Supabase > Settings > API |
| SUPABASE_SERVICE_KEY | Supabase > Settings > API (nao expor no frontend) |
| ZAPI_INSTANCE | Z-API dashboard |
| ZAPI_TOKEN | Z-API dashboard |
| ZAPI_CLIENT_TOKEN | Z-API dashboard |
| ENCRYPTION_KEY | Gerado pelo script acima |
| JWT_SECRET | Gerado pelo script acima |

## Regras de seguranca que NUNCA podem ser quebradas

1. Nunca commitar .env no git
2. Nunca logar dados de PII (nome, telefone, email)
3. Nunca retornar dados criptografados para o frontend
4. Sempre validar inputs antes de qualquer operacao no banco
5. Sempre usar hash para busca — nunca buscar por dados em texto puro
6. Rotacionar ENCRYPTION_KEY e JWT_SECRET a cada 90 dias
