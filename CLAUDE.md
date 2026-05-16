# Financial Dashboard (Mercado Livre) — Contexto do Projeto

## Documentação do projeto

| Arquivo | Conteúdo |
|---------|----------|
| `CLAUDE.md` | Este arquivo — contexto geral, convenções, estado atual |
| `ARCHITECTURE_v3.md` | Arquitetura detalhada, endpoints, modelo de dados, fluxos |
| `REACT_MIGRATION_v3.md` | Guia de migração Streamlit → React |
| `DOC_DB_v1.md` | Banco externo `meli` (v1): tabelas, FKs, role read-only, network Docker |
| `DOC_TEST_IMPORT_v1.md` | Implantação do extractor (Blocos 0–8): substitui upload XLSX de faturamento |

> Antes de implementar qualquer feature, leia os arquivos relevantes acima.

---

## Stack

- **Backend:** FastAPI + SQLAlchemy + PostgreSQL
- **Frontend atual:** Streamlit (migração para React planejada — ver `REACT_MIGRATION_v3.md`)
- **Processamento:** Pandas + PyArrow (Parquet)
- **Auth:** JWT (30 min) + bcrypt
- **Deploy:** Docker Compose
- **Banco externo (faturamento):** PostgreSQL `meli` (read-only via role `meli_readonly`), acessado por `EXTERNAL_DB_URL` na network Docker `projeto-meli_app_rede`
- **Migrations:** Alembic (único método — `init_db.py` removido)

---

## Convenções de código

- **Monetário BR:** sempre usar `_to_money()` de `anuncios_processor.py`
- **Datas PT-BR:** sempre usar `_to_date()` de `anuncios_processor.py` — formato `"06-fev-2026"`
- **Parquet:** salvo em `data/{upload_type}/{user_id}/{uuid}.parquet`
- **Coluna-chave faturamento:** `"N.º de venda"`
- **Coluna-chave anúncios:** `"Título do anúncio patrocinado"`
- **Aba da planilha de anúncios:** `"Relatório Anúncios patrocinados"`, header linha 1 (0-indexed)
- **Novos endpoints:** seguir padrão de `backend/app/api/dashboard.py`
- **Hierarquia de dados:** `User → Company → Business → Account → Orders (no meli)`
- **FK do admin da Company:** `Company.admin_user_id` (renomeado de `user_id` no Bloco 1)
- **ID externo do seller:** `Account.marketplace_id` (BigInteger) — chave do JOIN em `meli.public.orders`
- **Cache de faturamento extraído:** `data/faturamento/{user_id}/{account_id}/<uuid>.parquet`
- **Conexão externa:** sempre read-only; nunca usar superuser nem o owner do banco

---

## Arquivos críticos

- `backend/app/services/anuncios_processor.py` — processador principal de anúncios
- `backend/app/services/xlsx_processor.py` — processador de faturamento
- `backend/app/api/dashboard.py` — padrão a seguir para novos endpoints
- `backend/app/api/company.py` — CRUD de empresa (company)
- `backend/app/schemas/company.py` — schemas Pydantic de company (validação de state_origin e regime_tributario)
- `tests/test_processor.py` — testes de validação
- `backend/app/api/business.py` — CRUD de Business (Bloco 2)
- `backend/app/api/account.py` — CRUD de Account (Bloco 3)
- `backend/app/db/external_database.py` — engine SQLAlchemy do banco `meli` (Bloco 4)
- `backend/app/services/faturamento_extractor.py` — extractor SQL → Parquet (Bloco 5, em andamento)
- `docker-compose.prod.yml` — network externa `meli_external` (alias para `projeto-meli_app_rede`)

---

## Colunas da planilha de anúncios patrocinados

| Tipo | Colunas |
|------|---------|
| Texto | Campanha, Título do anúncio patrocinado, Código do anúncio, Status |
| Data | Desde, Até |
| Inteiro | Impressões, Cliques, Vendas diretas, Vendas indiretas, Vendas por publicidade (Diretas + Indiretas) |
| Float % | CPC  (Custo por clique), CTR (Click Through Rate), CVR (Conversion rate), ACOS  (Investimento / Receitas), ROAS (Receitas / Investimento) |
| Monetário | Receita (Moeda local), Investimento (Moeda local), Receita por vendas diretas (Moeda Local), Receita por vendas indiretas |

### Métricas retornadas por `process_anuncios_to_parquet()`

```
total_anuncios, anuncios_ativos, anuncios_desativados, anuncios_movidos,
total_impressoes, total_cliques, total_vendas, total_receita, total_investimento,
ctr_medio, cvr_medio, cpc_medio, acos_medio, roas_medio, roas_global, acos_global
```

---

## Bugs resolvidos

- **Valores 100x:** remoção incorreta de ponto decimal. SEMPRE usar `_to_money()`.
- **Dashboard vazio:** mismatch de caminho. Usar `data/{upload_type}/{user_id}/`.
- **Session reset no Streamlit:** usar `st.session_state` para persistir dados entre páginas.
- **`shipping.id` sem sequência** no banco `meli` — aplicação deve fornecer o ID na inserção.
- **`orders` sem `created_at`** no `meli` — quebra padrão; usar `data_criacao`.
- **Schema externo é `public`, NÃO `meli`** — `meli` é o nome do **database**. SQL do extractor não precisa de prefixo (`search_path` default).
- **Senha de `meli_readonly` atualmente é `123`** — trocar antes de produção real.

---

## Estado atual e próximas tarefas

```
[x] Upload e processamento de XLSX (faturamento + anúncios)
[x] Dashboard financeiro (créditos/débitos/líquido por mês)
[x] Autenticação JWT
[x] Docker Compose com PostgreSQL
[x] Bloco 0 — Branch `testv1`
[x] Bloco 1 — Migration `Company.user_id → admin_user_id` + validação de role admin
[x] Bloco 2 — CRUD de Business
[x] Bloco 3 — CRUD de Account (com `marketplace_id`)
[x] Bloco 4 — Engine externo `meli` + `/health/external-db` + network Docker compartilhada

[ ] PRÓXIMA: Bloco 5 — `faturamento_extractor.py` (SQL JOIN orders+account+shipping+billing → Parquet + ICMS)
[ ] Bloco 6 — `GET /dashboard/accounts`, `POST /dashboard/atualizar?account_id=`, `GET /dashboard/?account_id=`
[ ] Bloco 7 — Frontend: renomear `cadastro_empresa.py` → `cadastro_company.py` (3 abas: Company/Business/Account) + selectbox no dashboard
[ ] Bloco 8 — Testes manuais ponta-a-ponta com 2 accounts
[ ] Dashboard de anúncios (adiado)
```

---

## Comandos úteis

```bash
# Backend local
uvicorn app.main:app --reload --app-dir backend

# Testes
pytest tests/ -v

# Docker
docker compose up -d
docker compose logs -f backend
docker compose logs -f frontend
docker compose restart backend
docker compose build --no-cache && docker compose up -d
docker compose down -v

# Banco
docker compose exec financial_db_docker psql -U usuario_financial -d financial_db
docker compose exec financial_db_docker psql -U usuario_financial -d financial_db -c \
  "SELECT id, user_id, upload_type, original_filename, processing_status FROM uploads;"

# Banco externo `meli` (read-only)
docker exec -it postgres_db psql -U meli_readonly -d meli -c "SELECT count(*) FROM public.orders;"

# Health-check do extractor
docker compose -f docker-compose.prod.yml exec backend sh -c "curl -s http://localhost:8000/health/external-db"

# DNS interno (validar network compartilhada)
docker exec financial-dashboard-dbv1-backend-1 sh -c "getent hosts postgres_db"

# Migrations (Alembic)
alembic upgrade head                              # aplicar migrations pendentes
alembic revision --autogenerate -m "descricao"   # gerar nova migration
alembic downgrade -1                              # reverter última migration
alembic history                                   # ver histórico de migrations
alembic current                                   # ver migration atualmente aplicada

# Debug parquet
python -c "import pandas as pd; print(pd.read_parquet('data/anuncios/1/').head())"
```