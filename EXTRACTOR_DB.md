# Refactor: Extractor DB Externo — Documentação do Processo

> Estado: **nada implementado ainda**. Todo o trabalho descrito abaixo é pendente.
> Schema externo de referência: `meli` v1 (ver `doc_dbv1.md`).

---

## Objetivo

Substituir o upload manual de XLSX de faturamento por uma **extração direta do
banco de dados externo `meli`**, mantendo o restante do pipeline (processamento
e cache em Parquet) inalterado.

Fluxo final desejado:

```
[Botão "Atualizar Dados" no frontend]
        ↓
POST /api/v1/dashboard/atualizar  (usa seller_id da company autenticada)
        ↓
extractor.py: SELECT em meli.orders (JOIN account por marketplace_id)
        ↓
Mapeia colunas → reaproveita xlsx_processor (créditos/débitos/líquido)
        ↓
Salva Parquet em data/faturamento/{seller_id}/{uuid}.parquet
        ↓
GET /api/v1/dashboard/ continua lendo o Parquet (sem alteração)
```

---

## Schema externo (`meli` v1) — pontos relevantes

- Tabela de pedidos: **`orders`** (não `pedidos_vendas`).
- `orders` **não tem** `seller_id` direto. O caminho é:
  `orders.account_id → account.id`, e `account.marketplace_id` (bigint) é o
  ID público do seller no Mercado Livre.
- `orders.data_criacao` é **`timestamp`** (não string) — sem ambiguidade de parsing.
- `orders` **não tem** `created_at`, mas tem `updated_at` (útil para deltas).
- Soft delete via `deleted_at IS NULL` em quase todas as tabelas.
- Existem views prontas: `v_accounts_ativas` e `v_business_ativos`.
- Hierarquia: `company → business → account → orders → (items_order, billing, shipping)`.

---

## Passos pendentes

### Passo 1 — Configuração

**1.1 `.env`** — adicionar:
```env
EXTERNAL_DB_URL=postgresql://usuario_meli:senha@host:5432/meli
EXTERNAL_DB_READONLY=true   # opcional, apenas indicativo; usuário deve ser RO no Postgres
```

**1.2 `backend/requirements.txt`** — garantir dependências:
```
sqlalchemy
psycopg2-binary
pandas
pyarrow
alembic
```

**1.3 `backend/app/db/external_database.py`** — criar:
- Engine **lazy** para o DB externo (`create_engine(EXTERNAL_DB_URL, pool_pre_ping=True)`).
- `get_external_engine()` — retorna engine singleton.
- `test_external_connection()` — `SELECT 1` para health-check.
- Conexão preferencialmente com usuário **read-only**.

**1.4 `backend/app/models/company.py`** — adicionar campos:
```python
seller_id          = Column(BigInteger, nullable=True, index=True)  # = account.marketplace_id
external_account_id = Column(Integer,    nullable=True, index=True) # cache de account.id
```

**1.5 `backend/app/schemas/company.py`** — refletir os campos em
`CompanyCreate`, `CompanyUpdate` e `CompanyOut`:
```python
seller_id:           Optional[int] = None
external_account_id: Optional[int] = None
```

**1.6 Alembic** — gerar e aplicar migration:
```bash
docker compose exec backend python -m alembic revision --autogenerate -m "add seller_id and external_account_id to company"
docker compose exec backend python -m alembic upgrade head
```

---

### Passo 2 — Serviço de Extração (`extractor.py`)

Criar `backend/app/services/faturamento_extractor.py` com:

- `resolve_account_id(seller_id) -> int`
  Resolve `marketplace_id → account.id` usando `v_accounts_ativas`.
  Cacheia o resultado em `company.external_account_id` para não repetir.

- `extract_orders(account_id, since=None) -> pd.DataFrame`
  Executa o SELECT (ver SQL abaixo). Se `since` for passado, filtra por
  `updated_at > since` (sincronização incremental — opcional na primeira fase).

- `map_to_processor_format(df) -> pd.DataFrame`
  Renomeia/converte colunas para o formato esperado pelo `xlsx_processor`
  (ver tabela de mapeamento adiante).

- `extract_and_cache(seller_id) -> dict`
  Orquestra: resolve account → extrai → mapeia → processa → salva parquet.
  Retorna `{ rows, summary }`.

**SQL de extração (Opção A — JOIN único):**
```sql
SELECT
  o.external_order_id,
  o.data_criacao,
  o.status,
  o.valor,
  o.pago,
  o.parcelas,
  o.valor_parcela,
  o.acrescimo_parcelamento,
  o.tarifa_venda,
  o.receita_produtos,
  o.receita_envio,
  o.tarifa_envio,
  o.custo_envio_declarado,
  o.custo_diferenca_peso,
  o.rebate_meli,
  o.total_refund,
  o.updated_at
FROM orders o
JOIN account a ON a.id = o.account_id
WHERE a.marketplace_id = :seller_id
  AND o.deleted_at IS NULL
  AND a.deleted_at IS NULL;
```

---

### Passo 3 — Reutilizar `xlsx_processor`

Adaptar `backend/app/services/xlsx_processor.py` para aceitar **DataFrame**
além de arquivo XLSX. Reaproveitar `_to_money()`, `_to_date()` e o cálculo
de créditos/débitos/líquido. Não duplicar lógica no extractor.

---

### Passo 4 — Cache em Parquet

- Salvar em `data/faturamento/{seller_id}/{uuid}.parquet`.
- **Apagar** parquet anterior do mesmo `seller_id` antes de gravar o novo
  (mantém apenas o snapshot mais recente).
- Mesma estrutura do upload via XLSX para que `GET /dashboard/` não precise
  mudar.

---

### Passo 5 — Endpoint `POST /api/v1/dashboard/atualizar`

- Autenticação via JWT (padrão atual).
- Busca a `company` do usuário e lê `company.seller_id`.
  Erro 400 se não estiver cadastrado.
- Chama `faturamento_extractor.extract_and_cache(seller_id)`.
- Retorna `{ rows, summary, generated_at }`.

---

### Passo 6 — Endpoint `GET /api/v1/dashboard/`

Sem alteração — continua lendo o Parquet em cache.

---

### Passo 7 — Frontend

- Botão **"🔄 Atualizar Dados"** na página do dashboard.
- Chama `POST /atualizar` e exibe spinner.
- Em caso de sucesso, recarrega o dashboard.
- Em caso de erro, mostra mensagem amigável (seller não cadastrado, falha de
  conexão com `meli`, etc.).

---

## Mapeamento de Colunas (`meli.orders` → `xlsx_processor`)

| Coluna `meli.orders`                | Coluna `xlsx_processor`                                          |
|-------------------------------------|------------------------------------------------------------------|
| `external_order_id`                 | `N.º de venda`                                                   |
| `data_criacao`                      | `Data da venda`                                                  |
| `status`                            | `Estado`                                                         |
| `receita_produtos`                  | `Receita por produtos (BRL)`                                     |
| `acrescimo_parcelamento`            | `Receita por acréscimo no preço (pago pelo comprador)`           |
| `tarifa_venda`                      | `Tarifa de venda e impostos (BRL)`                               |
| `receita_envio`                     | `Receita por envio (BRL)`                                        |
| `tarifa_envio`                      | `Tarifas de envio (BRL)`                                         |
| `total_refund`                      | `Cancelamentos e reembolsos (BRL)`                               |
| `valor`                             | `Total (BRL)`                                                    |
| `custo_envio_declarado`             | `Custo de envio com base nas medidas e peso declarados`          |
| `custo_diferenca_peso`              | `Custo por diferenças nas medidas e no peso do pacote`           |
| `rebate_meli`                       | *(novo — incluir como crédito; revisar com o `xlsx_processor`)*  |
| `parcelas * valor_parcela` *(calc.)*| `Taxa de parcelamento equivalente ao acréscimo`                  |

---

## Opções de Implantação do Extractor

A escolha define **como** os passos 2–7 serão implementados. Cada opção tem
trade-offs distintos de complexidade, escalabilidade e UX.

### Opção A — Síncrono, query única com JOIN (mais simples)

Endpoint executa o SQL acima, processa e grava o parquet **dentro do request**.

- **Prós:** simples, reaproveita 100% o `xlsx_processor`, fácil testar.
- **Contras:** request longa para sellers grandes; risco de timeout no
  proxy/uvicorn; frontend trava no spinner.
- **Indicado para:** volume baixo/médio (até ~50k pedidos por seller).

---

### Opção B — Síncrono em duas etapas (resolução + extração)

1. `account_id ← v_accounts_ativas.marketplace_id = :seller_id`
2. `SELECT * FROM orders WHERE account_id = :account_id AND deleted_at IS NULL`

Permite cachear `account_id` em `company.external_account_id` e pular a
resolução em chamadas subsequentes.

- **Prós:** queries mais simples e indexáveis individualmente; remove o JOIN
  do hot path após o primeiro carregamento.
- **Contras:** dois roundtrips na primeira chamada.
- **Indicado para:** quando o JOIN da Opção A virar gargalo.

---

### Opção C — Assíncrono com job em background

`POST /atualizar` enfileira via `BackgroundTasks` (FastAPI), Celery ou RQ e
retorna `job_id`. Frontend faz polling em
`GET /atualizar/status/{job_id}` até finalizar.

- **Prós:** sem timeout HTTP; UX com progresso real; escala para múltiplos
  sellers concorrentes.
- **Contras:** adiciona tabela de jobs (ou Redis) + endpoint de status; mais
  código para manter.
- **Indicado para:** volume alto ou uso simultâneo por vários sellers.

---

### Opção D — Sincronização incremental (delta) por `updated_at`

Guardar `last_synced_at` por `company.id` e filtrar
`WHERE updated_at > :last_synced_at`. Fazer **upsert** no parquet existente
usando `external_order_id` como chave (ou trocar parquet por SQLite/DuckDB
local para facilitar o upsert).

- **Prós:** muito mais rápido em atualizações repetidas; baixa carga no DB
  externo; permite refresh frequente (status, refunds mudando).
- **Contras:** primeira sincronização ainda é completa; lógica de upsert é
  mais complexa que reescrever o parquet.
- **Indicado para:** datasets grandes com mudanças frequentes.

---

### Opção E — View materializada no DB externo

Criar uma view (ou MV) em `meli` que já entrega o formato esperado pelo
`xlsx_processor`. Backend só faz `SELECT * FROM v_faturamento WHERE marketplace_id = :seller_id`.

- **Prós:** tira a transformação do app; centraliza regra em SQL; parquet
  vira opcional.
- **Contras:** exige permissão DDL no DB externo; refresh da MV precisa ser
  orquestrado; acopla o app ao schema do `meli`.
- **Indicado para:** quando há equipe de dados/DBA mantendo o `meli`.

---

### Opção F — Conexão read-only (transversal)

Não é alternativa às outras — combina com qualquer uma. Apontar
`EXTERNAL_DB_URL` para um usuário **read-only** (e idealmente uma replica de
leitura). Evita que um bug no extractor escreva no DB externo.

---

## Recomendação

Começar pela **Opção A + F**: query única com JOIN usando conexão read-only.
Entrega o fluxo ponta-a-ponta rápido e valida o mapeamento de colunas.
Quando o volume justificar, evoluir para **C + D** (job assíncrono com delta
por `updated_at`). A **Opção E** só se justifica se houver alguém mantendo o
schema do `meli` ativamente.

---

## Contexto de Dados (resumo)

```
financial_db.users.id
        └── financial_db.company.user_id
              └── financial_db.company.seller_id  ──┐
                                                    │  (= meli.account.marketplace_id)
                                                    ▼
                                       meli.account.id
                                              └── meli.orders.account_id
                                                        ├── meli.items_order
                                                        ├── meli.billing
                                                        └── meli.shipping
```