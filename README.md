# Personal Shopper App

App para compras e entregas em condomínios.

## Estrutura

- `backend/` - API FastAPI
- `frontend/` - PWA
- `supabase/` - Schema do banco de dados

## Configuração

1. Copie `.env.example` para `.env` e preencha as chaves
2. Execute `schema.sql` no Supabase
3. Rode `pip install -r backend/requirements.txt`
4. Execute `uvicorn backend.app.main:app --reload`
