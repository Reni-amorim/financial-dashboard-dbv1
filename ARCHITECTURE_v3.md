# ARCHITECTURE.md — Financial Dashboard (Mercado Livre)

> Documento de referência de arquitetura. Atualizar sempre que mudar estrutura,
> adicionar endpoints, tabelas ou serviços.

---

## Visão geral

```
Usuário
  │
  ▼
Frontend (Streamlit :8501)
  │  HTTP/REST + JWT
  ▼
Backend (FastAPI :8000)
  ├── API Layer      /auth  /upload  /dashboard
  ├── Core Layer     JWT · bcrypt · Depends
  ├── Service Layer  xlsx_processor · anuncios_processor
  └── Data Layer     SQLAlchemy · PostgreSQL
        │
        ├── PostgreSQL :5432   (metadados, auth)
        └── File System        (XLSX raw + Parquet processado)
```

---

## Camadas do backend

| Camada | Pasta | Responsabilidade |
|--------|-------|-----------------|
| API | `app/api/` | Roteamento, validação de request/response (Pydantic) |
| Core | `app/core/` | JWT, bcrypt, injeção de dependências |
| Service | `app/services/` | Processamento de XLSX → Parquet, cálculo de métricas |
| Data | `app/models/` | Modelos SQLAlchemy, sessão de banco |

---

## Endpoints

| Método | Rota | Auth | Descrição |
|--------|------|------|-----------|
| POST | `/api/v1/auth/register` | ✗ | Cadastro de usuário |
| POST | `/api/v1/auth/login` | ✗ | Login, retorna JWT |
| POST | `/api/v1/upload/faturamento` | ✓ | Upload XLSX faturamento (reset automático) |
| POST | `/api/v1/upload/anuncios` | ✓ | Upload XLSX anúncios (histórico preservado) |
| GET  | `/api/v1/dashboard/` | ✓ | Métricas financeiras do faturamento |
| GET  | `/api/v1/dashboard/anuncios` | ✓ | **[ TODO ]** Métricas de anúncios |
| GET  | `/health` | ✗ | Health check |

---

## Modelo de dados

```sql
CREATE TABLE users (
    id               SERIAL PRIMARY KEY,
    email            VARCHAR(255) UNIQUE NOT NULL,
    username         VARCHAR(255) UNIQUE NOT NULL,
    hashed_password  VARCHAR(255) NOT NULL,
    is_active        BOOLEAN DEFAULT TRUE,
    created_at       TIMESTAMP DEFAULT NOW()
);

CREATE TABLE uploads (
    id                  SERIAL PRIMARY KEY,
    user_id             INTEGER REFERENCES users(id),
    upload_type         VARCHAR(50),          -- 'faturamento' | 'anuncios'
    filename            VARCHAR(255) NOT NULL,
    original_filename   VARCHAR(255) NOT NULL,
    file_path           VARCHAR(500) NOT NULL,
    parquet_path        VARCHAR(500),
    processing_status   VARCHAR(50) DEFAULT 'pending',  -- pending | completed | error
    rows_processed      INTEGER,
    error_message       TEXT,
    metrics_json        TEXT,                 -- JSON com métricas calculadas
    uploaded_at         TIMESTAMP DEFAULT NOW(),
    processed_at        TIMESTAMP
);

CREATE INDEX idx_uploads_user_id    ON uploads(user_id);
CREATE INDEX idx_uploads_status     ON uploads(processing_status);
CREATE INDEX idx_uploads_uploaded_at ON uploads(uploaded_at DESC);
```

---

## File system

```
data/
├── raw/
│   ├── faturamento/    ← XLSX originais de faturamento
│   └── anuncios/       ← XLSX originais de anúncios
├── faturamento/
│   └── {user_id}/      ← Parquet por usuário (reset a cada upload)
└── anuncios/
    └── {user_id}/      ← Parquet por usuário (histórico acumulado)
```

Convenção de path: `data/{upload_type}/{user_id}/{uuid}.parquet`

---

## Fluxo: upload e processamento

```
POST /upload/faturamento  (multipart/form-data)
  │
  ├── Valida extensão e tamanho
  ├── Salva XLSX em data/raw/faturamento/
  ├── Cria registro no banco  (status=pending)
  ├── Dispara BackgroundTask
  └── Retorna {id, status: "pending"}  ← não bloqueia

[BackgroundTask]
  │
  ├── xlsx_processor.py
  │     ├── pd.read_excel()
  │     ├── Detecta linha de cabeçalho  ("N.º de venda")
  │     ├── _to_brl_number()  →  converte monetário BR/US
  │     ├── Calcula créditos / débitos / líquido
  │     └── df.to_parquet(data/faturamento/{user_id}/{uuid}.parquet)
  │
  └── Atualiza banco  (status=completed, metrics_json)
```

---

## Fluxo: dashboard

```
GET /api/v1/dashboard/
  │
  ├── Busca último Parquet:  glob("data/faturamento/{user_id}/*.parquet")
  ├── pd.read_parquet()
  ├── Calcula totais por coluna
  ├── Agrupa por mês  (df.groupby("ano_mes"))
  └── Retorna JSON  {overall, by_month, recent_uploads}
```

---

## Fluxo: autenticação JWT

```
Login
  POST /auth/login {username, password}
  → verify_password(plain, hashed)  [bcrypt]
  → create_access_token({sub: username})
  → JWT = HS256(Header.Payload, SECRET_KEY)  expira em 30 min
  → Retorna {access_token}

Requisição autenticada
  Header: Authorization: Bearer <token>
  → verify_token(token)  →  extrai username
  → Query user  →  valida is_active
  → Injeta current_user via Depends()
```

---

## Serviços de processamento

### `xlsx_processor.py` — Faturamento

- Detecta linha de cabeçalho pela coluna `"N.º de venda"`
- Converte monetário com `_to_brl_number()` (suporta formato BR e US)
- Colunas de crédito: `Receita por produtos`, `Receita por acréscimo`, `Receita por envio`
- Colunas de débito: `Taxa de parcelamento`, `Tarifa de venda e impostos`, `Custo de envio`, `Cancelamentos e reembolsos`

### `anuncios_processor.py` — Anúncios Patrocinados

- Aba: `"Relatório Anúncios patrocinados"`, header linha 1 (0-indexed)
- Detecta cabeçalho pela coluna `"Título do anúncio patrocinado"`
- Monetário: `_to_money()` — suporta `"R$ 1.234,56"`, `"1234.56"`, `"-"`, `NaN`
- Datas: `_to_date()` — suporta `"06-fev-2026"` (PT-BR)
- Retorna métricas: `total_anuncios`, `anuncios_ativos`, `total_receita`, `total_investimento`, `roas_global`, `acos_global`, `ctr_medio`, `cvr_medio`, `cpc_medio`

---

## Performance

| Decisão | Motivo |
|---------|--------|
| Parquet em vez de CSV | ~5x menor, leitura colunar, tipos preservados |
| BackgroundTasks no upload | Retorno imediato ao usuário, processamento assíncrono |
| Índices no banco | `user_id`, `status`, `uploaded_at DESC` |
| Glob no file system | Sem query extra ao banco para ler último Parquet |

---

## Evolução planejada

```
Atual
  Streamlit → FastAPI → PostgreSQL + File System

Próximo (médio prazo)
  React → FastAPI → PostgreSQL + File System
  + Celery para processamento assíncrono robusto
  + Redis para cache de dashboard

Futuro (SaaS)
  Next.js → API Gateway → Microserviços
  + Auth Service · Upload Service · Analytics Service
  + S3 (storage) · RDS · ElastiCache
```

---

## Decisões de arquitetura registradas

| # | Decisão | Alternativa descartada | Motivo |
|---|---------|----------------------|--------|
| 1 | Parquet para armazenar dados processados | CSV | Performance de leitura e tamanho |
| 2 | BackgroundTasks do FastAPI para processar XLSX | Processamento síncrono | Não bloquear o endpoint de upload |
| 3 | File system local para Parquet | Banco de dados | Simplicidade; migrar para S3 no futuro |
| 4 | Streamlit para frontend | React (inicial) | Prototipagem rápida; React planejado para v2 |
| 5 | Reset automático no upload de faturamento | Histórico acumulado | Faturamento é substituído mensalmente |
| 6 | Histórico preservado no upload de anúncios | Reset automático | Comparação entre períodos de campanhas |
