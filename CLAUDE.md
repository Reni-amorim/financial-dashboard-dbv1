# Financial Dashboard (Mercado Livre) — Contexto do Projeto

## Documentação do projeto

| Arquivo | Conteúdo |
|---------|----------|
| `CLAUDE.md` | Este arquivo — contexto geral, convenções, estado atual |
| `ARCHITECTURE_v3.md` | Arquitetura detalhada, endpoints, modelo de dados, fluxos, decisões técnicas |
| `REACT_MIGRATION_v3.md` | Guia de migração Streamlit → React, stack, componentes, checklist |
| `DB_DOCUMENTACAO_v3.md` | Documentação do banco de dados e estrutura das planilhas Mercado Livre |

> Antes de implementar qualquer feature, leia os arquivos relevantes acima.

---

## Stack

- **Backend:** FastAPI + SQLAlchemy + PostgreSQL
- **Frontend atual:** Streamlit (migração para React planejada — ver `REACT_MIGRATION_v3.md`)
- **Processamento:** Pandas + PyArrow (Parquet)
- **Auth:** JWT (30 min) + bcrypt
- **Deploy:** Docker Compose
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

---

## Arquivos críticos

- `backend/app/services/anuncios_processor.py` — processador principal de anúncios
- `backend/app/services/xlsx_processor.py` — processador de faturamento
- `backend/app/api/dashboard.py` — padrão a seguir para novos endpoints
- `backend/app/api/company.py` — CRUD de empresa (company)
- `backend/app/schemas/company.py` — schemas Pydantic de company (validação de state_origin e regime_tributario)
- `tests/test_processor.py` — testes de validação

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

---

## Estado atual e próximas tarefas

```
[x] Upload e processamento de XLSX (faturamento + anúncios)
[x] Dashboard financeiro (créditos/débitos/líquido por mês)
[x] Autenticação JWT
[x] Docker Compose com PostgreSQL

[ ] PRÓXIMA: Dashboard de anúncios
      → backend/app/api/dashboard_anuncios.py  (GET /api/v1/dashboard/anuncios)
      → frontend/pages/dashboard_anuncios.py   (Streamlit)
      → Métricas: total, ativos, receita, investimento, ROAS, CTR, CVR
      → Gráfico: receita vs investimento por campanha
      → Top 10 anúncios por receita (tabela)

[ ] Testes automatizados (pytest) com arquivo XLSX real
[ ] Integração faturamento × anúncios (ROI por anúncio)
[ ] Migração frontend para React (ver REACT_MIGRATION_v3.md)
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

# Migrations (Alembic)
alembic upgrade head                              # aplicar migrations pendentes
alembic revision --autogenerate -m "descricao"   # gerar nova migration
alembic downgrade -1                              # reverter última migration
alembic history                                   # ver histórico de migrations
alembic current                                   # ver migration atualmente aplicada

# Debug parquet
python -c "import pandas as pd; print(pd.read_parquet('data/anuncios/1/').head())"
```