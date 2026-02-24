# 📐 Arquitetura Detalhada do Sistema

## 🎯 Visão Geral

```
┌────────────────────────────────────────────────────────────────┐
│                        USUÁRIO FINAL                           │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│                    FRONTEND (Streamlit)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │ Login/Registro│  │ Upload XLSX  │  │  Dashboard   │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
│                    utils/api_client.py                         │
└────────────────────────────────────────────────────────────────┘
                              │
                    HTTP/REST (JSON)
                              ▼
┌────────────────────────────────────────────────────────────────┐
│                    BACKEND (FastAPI)                           │
│  ┌──────────────────────────────────────────────────────┐     │
│  │                    API LAYER                         │     │
│  │  /auth      /upload      /dashboard                  │     │
│  └──────────────────────────────────────────────────────┘     │
│                              │                                 │
│  ┌──────────────────────────────────────────────────────┐     │
│  │                  CORE LAYER                          │     │
│  │  Security (JWT)   Dependencies   Config              │     │
│  └──────────────────────────────────────────────────────┘     │
│                              │                                 │
│  ┌──────────────────────────────────────────────────────┐     │
│  │                SERVICE LAYER                         │     │
│  │  XLSXProcessor     MetricsCalculator                 │     │
│  └──────────────────────────────────────────────────────┘     │
│                              │                                 │
│  ┌──────────────────────────────────────────────────────┐     │
│  │                 DATA LAYER                           │     │
│  │  SQLAlchemy Models    Database Session               │     │
│  └──────────────────────────────────────────────────────┘     │
└────────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
┌──────────────────────────┐  ┌──────────────────────────┐
│    PostgreSQL            │  │  File System             │
│  ┌────────────────────┐  │  │  ┌────────────────────┐  │
│  │ users              │  │  │  │ /data/raw/         │  │
│  │ uploads            │  │  │  │   - XLSX files     │  │
│  └────────────────────┘  │  │  └────────────────────┘  │
│  Metadados, Auth         │  │  ┌────────────────────┐  │
└──────────────────────────┘  │  │ /data/processed/   │  │
                              │  │   - Parquet files  │  │
                              │  └────────────────────┘  │
                              │  Dados processados       │
                              └──────────────────────────┘
```

---

## 🔄 Fluxo de Dados Completo

### 1. Autenticação (Login)

```
[Usuário] → [Frontend: Login Form]
              │
              ▼ POST /api/v1/auth/login {username, password}
         [Backend: auth.py]
              │
              ├─→ [Database] Query User
              │
              ├─→ [Security] verify_password()
              │
              ├─→ [Security] create_access_token()
              │
              ▼ Response: {access_token, token_type}
         [Frontend: Salva token]
              │
              ▼
         [Session State: authenticated=True]
```

### 2. Upload e Processamento

```
[Usuário] → [Frontend: File Uploader]
              │
              ▼ POST /api/v1/upload/ (multipart/form-data)
         [Backend: upload.py]
              │
              ├─→ Valida arquivo (ext, size)
              │
              ├─→ Salva em /data/raw/
              │
              ├─→ [Database] Cria registro Upload (status: pending)
              │
              ├─→ [BackgroundTasks] process_file_background()
              │
              ▼ Response: {id, status: "pending"}
         [Frontend: Mostra "Processando..."]

[Background Task]
              │
              ▼ [XLSXProcessor.read_xlsx()]
              │
              ├─→ pd.read_excel() → DataFrame raw
              │
              ▼ [XLSXProcessor.detect_delimiter()]
              │
              ├─→ Detecta TAB/|/;
              │
              ▼ [XLSXProcessor.parse_single_cell_rows()]
              │
              ├─→ str.split(delimiter) → Colunas estruturadas
              │
              ▼ [XLSXProcessor.clean_and_convert()]
              │
              ├─→ Converte datas (pd.to_datetime)
              ├─→ Converte valores monetários
              ├─→ Remove símbolos (R$, vírgulas)
              │
              ▼ [XLSXProcessor.calculate_metrics()]
              │
              ├─→ total_revenue = df[coluna_faturamento].sum()
              ├─→ total_debits = df[colunas_debito].sum()
              ├─→ net_amount = revenue - debits
              │
              ▼ Salva DataFrame em Parquet
              │
              ├─→ df.to_parquet(/data/processed/ID.parquet)
              │
              ▼ [Database] Atualiza Upload
              │
              └─→ status: "completed"
                  rows_processed: len(df)
                  total_revenue, total_debits, net_amount
```

### 3. Dashboard (Visualização)

```
[Usuário] → [Frontend: Dashboard Page]
              │
              ▼ GET /api/v1/dashboard/
         [Backend: dashboard.py]
              │
              ├─→ [Database] Query uploads do usuário (status=completed)
              │
              ├─→ Agrega métricas de todos uploads
              │
              ├─→ [MetricsCalculator] load_and_calculate_metrics()
              │   │
              │   ├─→ pd.read_parquet(arquivo.parquet)
              │   │
              │   ├─→ get_overall_metrics()
              │   │   └─→ Soma total, conta transações
              │   │
              │   ├─→ get_monthly_metrics()
              │   │   └─→ df.groupby(month).agg(sum)
              │   │
              │   └─→ get_quarterly_metrics()
              │       └─→ df.groupby(quarter).agg(sum)
              │
              ▼ Response: {overall, by_month, by_quarter, recent_uploads}
         [Frontend: Renderiza Dashboard]
              │
              ├─→ st.metric() para métricas principais
              ├─→ st.bar_chart() para gráficos mensais
              └─→ st.bar_chart() para gráficos trimestrais
```

---

## 🗄️ Modelo de Dados

### Tabela: `users`

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Tabela: `uploads`

```sql
CREATE TABLE uploads (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    parquet_path VARCHAR(500),
    
    -- Metadados do processamento
    rows_processed INTEGER,
    processing_status VARCHAR(50) DEFAULT 'pending',
    error_message TEXT,
    
    -- Métricas calculadas
    total_revenue DECIMAL(15, 2),
    total_debits DECIMAL(15, 2),
    net_amount DECIMAL(15, 2),
    
    -- Timestamps
    uploaded_at TIMESTAMP DEFAULT NOW(),
    processed_at TIMESTAMP
);
```

### Índices

```sql
CREATE INDEX idx_uploads_user_id ON uploads(user_id);
CREATE INDEX idx_uploads_status ON uploads(processing_status);
CREATE INDEX idx_uploads_uploaded_at ON uploads(uploaded_at DESC);
```

---

## 🔐 Fluxo de Segurança

### Registro de Usuário

```
1. Frontend: Coleta email, username, password
2. Backend: Valida formato (Pydantic)
3. Backend: Verifica se email/username já existe
4. Backend: get_password_hash(password) → bcrypt
5. Database: INSERT INTO users
6. Response: User criado (sem senha)
```

### Login e Token JWT

```
1. Frontend: Envia username + password
2. Backend: Query user pelo username
3. Backend: verify_password(plain, hashed) → True/False
4. Backend: create_access_token({sub: username})
   └─→ JWT = Header.Payload.Signature
       Header: {alg: "HS256"}
       Payload: {sub: "username", exp: timestamp}
       Signature: HMAC-SHA256(Header.Payload, SECRET_KEY)
5. Response: {access_token: "eyJ..."}
6. Frontend: Salva token (session_state / localStorage)
```

### Requisição Autenticada

```
1. Frontend: Adiciona header: Authorization: Bearer eyJ...
2. Backend: Extrai token do header (HTTPBearer)
3. Backend: verify_token(token)
   ├─→ jwt.decode(token, SECRET_KEY)
   ├─→ Valida assinatura
   ├─→ Verifica expiração
   └─→ Extrai username do payload
4. Backend: Query user pelo username (Dependency)
5. Backend: Valida is_active
6. Endpoint: Recebe current_user injetado
```

---

## 📊 Pipeline de Processamento XLSX

### Exemplo de Transformação

**Entrada (célula única):**
```
01/01/2024[TAB]TRX001[TAB]Venda A[TAB]1500,00[TAB]45,00[TAB]97,50
```

**Após split:**
```python
{
  'data': '01/01/2024',
  'codigo': 'TRX001',
  'descricao': 'Venda A',
  'faturamento': '1500,00',
  'taxa': '45,00',
  'imposto': '97,50'
}
```

**Após clean_and_convert:**
```python
{
  'data': Timestamp('2024-01-01'),
  'codigo': 'TRX001',
  'descricao': 'Venda A',
  'faturamento': 1500.00,
  'taxa': 45.00,
  'imposto': 97.50
}
```

**Métricas calculadas:**
```python
{
  'total_revenue': 1500.00,
  'total_debits': 45.00 + 97.50 = 142.50,
  'net_amount': 1500.00 - 142.50 = 1357.50
}
```

---

## ⚡ Performance e Otimizações

### 1. Processamento Assíncrono

```python
# Upload retorna imediatamente (202 Accepted)
# Processamento roda em BackgroundTasks
@router.post("/upload/")
async def upload(background_tasks: BackgroundTasks, ...):
    # Salva arquivo
    # Cria registro
    background_tasks.add_task(process_file_background, ...)
    return upload  # Não aguarda processamento
```

### 2. Parquet vs CSV

| Formato | Tamanho | Leitura | Query |
|---------|---------|---------|-------|
| CSV | 100 MB | 5s | Lento |
| Parquet | 20 MB | 0.5s | Rápido |

**Parquet:**
- Compressão eficiente
- Leitura colunar (só lê colunas necessárias)
- Tipos de dados preservados
- Suporte a engines (PyArrow, fastparquet)

### 3. Database Indexing

```sql
-- Acelera queries de upload por usuário
CREATE INDEX idx_uploads_user_id ON uploads(user_id);

-- Acelera ordenação por data
CREATE INDEX idx_uploads_uploaded_at ON uploads(uploaded_at DESC);
```

### 4. Caching (Futuro)

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def get_dashboard_data(user_id: int):
    # Cacheia resultado por 5 minutos
    ...
```

---

## 🚀 Evolução da Arquitetura

### Atual: Monolito

```
Frontend (Streamlit) → Backend (FastAPI) → DB (PostgreSQL)
```

### Próximo Nível: Microserviços

```
Frontend (React)
    │
    ├─→ Auth Service (FastAPI)
    ├─→ Upload Service (FastAPI + Celery)
    ├─→ Analytics Service (FastAPI)
    └─→ API Gateway (Kong/Nginx)
```

### Enterprise: Cloud Native

```
Frontend (Next.js)
    │
    ├─→ API Gateway (AWS API Gateway)
    │
    ├─→ Auth (AWS Cognito)
    ├─→ Upload (Lambda + S3 + SQS)
    ├─→ Processing (ECS Fargate + Celery)
    ├─→ Analytics (Lambda + Athena)
    │
    ├─→ Database (RDS PostgreSQL)
    ├─→ Storage (S3)
    └─→ Cache (ElastiCache Redis)
```

---

## 📈 Métricas e Monitoramento

### Logs Estruturados

```python
import logging

logger.info("Processing file", extra={
    "user_id": user.id,
    "upload_id": upload.id,
    "file_size": file_size,
    "rows": len(df)
})
```

### Health Checks

```python
@app.get("/health")
def health():
    return {
        "status": "healthy",
        "database": check_database(),
        "storage": check_storage(),
        "version": settings.VERSION
    }
```

### Métricas (Futuro: Prometheus)

```python
from prometheus_client import Counter, Histogram

upload_counter = Counter('uploads_total', 'Total uploads')
processing_time = Histogram('processing_seconds', 'Processing time')

@processing_time.time()
def process_file(...):
    upload_counter.inc()
    ...
```

---

## 🎓 Conceitos-Chave Implementados

1. **RESTful API** - Endpoints padronizados (GET, POST, DELETE)
2. **JWT Authentication** - Autenticação stateless
3. **Async Processing** - Background tasks não bloqueantes
4. **ORM** - SQLAlchemy para abstração de banco
5. **Schema Validation** - Pydantic para validação de dados
6. **Dependency Injection** - FastAPI Depends para reuso
7. **File Storage** - Separação de raw/processed
8. **Columnar Storage** - Parquet para eficiência
9. **Containerization** - Docker para portabilidade
10. **API Documentation** - OpenAPI/Swagger automático

---

**Esta arquitetura é escalável, manutenível e pronta para produção! 🚀**
