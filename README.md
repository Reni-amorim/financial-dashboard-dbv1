# 📊 Financial Dashboard - Sistema Completo de Upload e Análise XLSX

Sistema web full-stack para upload, processamento e visualização de dados financeiros em arquivos XLSX.

## 🎯 Visão Geral

Sistema que permite:
- ✅ **Autenticação** de usuários com JWT
- ✅ **Upload** de arquivos XLSX com processamento assíncrono
- ✅ **Processamento** inteligente de dados usando Pandas
- ✅ **Armazenamento** otimizado em Parquet
- ✅ **Dashboard** interativo com métricas financeiras
- ✅ **APIs REST** documentadas automaticamente

---

## 🏗️ Arquitetura

```
┌─────────────────┐      ┌──────────────────┐      ┌─────────────────┐
│   Streamlit     │─────▶│   FastAPI        │─────▶│   PostgreSQL    │
│   Frontend      │◀─────│   Backend        │◀─────│   + Parquet     │
└─────────────────┘      └──────────────────┘      └─────────────────┘
                                │
                                ▼
                         ┌──────────────┐
                         │    Pandas    │
                         │   Pipeline   │
                         └──────────────┘
```

### Stack Tecnológico

| Camada | Tecnologia | Justificativa |
|--------|------------|---------------|
| **Backend** | FastAPI | Performance, async, auto-docs |
| **Frontend** | Streamlit | Prototipagem rápida, interativo |
| **Processamento** | Pandas + PyArrow | Alto desempenho com XLSX |
| **Database** | PostgreSQL | Confiável, ACID, JSON support |
| **Storage** | Parquet | Compressão eficiente, query rápida |
| **Auth** | JWT | Stateless, escalável |

---

## 📂 Estrutura de Pastas

```
financial-dashboard/
├── backend/
│   ├── app/
│   │   ├── main.py                 # Entry point FastAPI
│   │   ├── config.py               # Configurações
│   │   ├── database.py             # SQLAlchemy setup
│   │   ├── models/
│   │   │   └── user.py             # Models (User, Upload)
│   │   ├── schemas/
│   │   │   └── user.py             # Pydantic schemas
│   │   ├── api/
│   │   │   ├── auth.py             # Endpoints de autenticação
│   │   │   ├── upload.py           # Endpoints de upload
│   │   │   └── dashboard.py        # Endpoints de dashboard
│   │   ├── core/
│   │   │   ├── security.py         # JWT, hashing
│   │   │   └── deps.py             # Dependências (get_current_user)
│   │   └── services/
│   │       ├── xlsx_processor.py   # 🔥 Pipeline de processamento
│   │       └── metrics.py          # Cálculo de métricas
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── app.py                      # Streamlit app principal
│   ├── utils/
│   │   └── api_client.py           # Cliente HTTP para backend
│   ├── requirements.txt
│   └── Dockerfile
│
├── data/
│   ├── raw/                        # XLSX originais (temporário)
│   └── processed/                  # Parquet files
│
├── scripts/
│   └── generate_sample_xlsx.py     # Gerador de XLSX exemplo
│
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 🚀 Instalação e Execução

### Opção 1: Docker (Recomendado)

```bash
# 1. Clone o repositório
git clone <repo-url>
cd financial-dashboard

# 2. Configure variáveis de ambiente
cp .env.example .env
# Edite .env com suas configurações

# 3. Suba os containers
docker-compose up -d

# 4. Acesse as aplicações
# Frontend: http://localhost:8501
# Backend API: http://localhost:8000
# Docs API: http://localhost:8000/docs
```

### Opção 2: Desenvolvimento Local

#### Backend

```bash
cd backend

# Criar ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Instalar dependências
pip install -r requirements.txt

# Configurar banco de dados
# Crie um banco PostgreSQL chamado 'financial_db'
# Ou use SQLite alterando DATABASE_URL em .env

# Rodar migrações (criar tabelas)
python -c "from app.database import init_db; init_db()"

# Iniciar servidor
uvicorn app.main:app --reload --port 8000
```

#### Frontend

```bash
cd frontend

# Criar ambiente virtual
python -m venv venv
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt

# Iniciar aplicação
streamlit run app.py
```

---

## 📖 Uso do Sistema

### 1. Registro e Login

1. Acesse `http://localhost:8501`
2. Na aba "Registrar":
   - Email: `usuario@exemplo.com`
   - Usuário: `usuario`
   - Senha: `senha123` (mínimo 8 caracteres)
3. Clique em "Registrar"
4. Faça login com suas credenciais

### 2. Upload de Arquivo

1. Navegue para "📤 Upload"
2. Clique em "Browse files"
3. Selecione seu arquivo XLSX
4. Clique em "🚀 Processar Arquivo"
5. Aguarde o processamento (background task)

### 3. Visualizar Dashboard

1. Navegue para "📊 Dashboard"
2. Veja métricas principais:
   - 💰 Faturamento Total
   - 💸 Débitos Totais
   - 💵 Valor Líquido
   - 📈 Número de Transações
3. Analise gráficos mensais e trimestrais

### 4. Histórico de Uploads

1. Navegue para "📋 Histórico"
2. Veja todos os seus uploads
3. Expanda para ver detalhes
4. Delete uploads antigos se necessário

---

## 🔄 Fluxo de Processamento XLSX

### Formato do Arquivo

O sistema espera arquivos XLSX onde **cada linha contém todos os dados em uma única célula**, separados internamente por **TAB** (ou outro delimitador).

**Exemplo:**

```
Linha 1: data[TAB]codigo[TAB]descricao[TAB]faturamento[TAB]taxa[TAB]imposto
Linha 2: 01/01/2024[TAB]TRX001[TAB]Venda A[TAB]1500.00[TAB]45.00[TAB]97.50
```

### Pipeline de Processamento

```python
# 1. Leitura do XLSX
df_raw = pd.read_excel(file_path, header=None, dtype=str)

# 2. Detecção automática do delimitador
delimiter = detect_delimiter(df_raw.iloc[0, 0])  # Detecta TAB, |, ;, etc

# 3. Split das células em colunas
df_structured = df_raw[0].str.split(delimiter, expand=True)

# 4. Limpeza e conversão de tipos
# - Remove espaços
# - Converte datas (pd.to_datetime)
# - Converte valores monetários (remove R$, vírgulas, etc)

# 5. Cálculo de métricas
metrics = {
    'total_revenue': df['faturamento'].sum(),
    'total_debits': df[['taxa', 'imposto']].sum().sum(),
    'net_amount': revenue - debits
}

# 6. Salvamento em Parquet
df.to_parquet(output_path, engine='pyarrow')
```

### Customização do Processamento

Para adaptar ao seu formato específico, edite:

**`backend/app/services/xlsx_processor.py`**

```python
# Ajuste os nomes das colunas esperadas
expected_columns = [
    "data",
    "codigo_transacao",
    "descricao",
    "faturamento",
    "taxa_cartao",
    "imposto",
    "taxa_plataforma"
]

# Ou use detecção automática
columns = detect_columns_from_xlsx(file_path)
```

---

## 🧪 Gerar Arquivo XLSX de Exemplo

```bash
cd scripts
python generate_sample_xlsx.py
```

Isso criará `data/exemplo_financeiro.xlsx` com 100 transações fictícias.

---

## 🔐 Segurança

### Autenticação JWT

```python
# Token gerado no login
POST /api/v1/auth/login
{
  "username": "usuario",
  "password": "senha123"
}

# Resposta
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}

# Usar em requisições subsequentes
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

### Proteção de Rotas

Todas as rotas de upload e dashboard requerem autenticação:

```python
@router.get("/dashboard/")
def get_dashboard(current_user: User = Depends(get_current_user)):
    # current_user extraído automaticamente do token
    ...
```

### Isolamento de Dados

Cada usuário vê apenas seus próprios uploads:

```python
uploads = db.query(Upload).filter(Upload.user_id == current_user.id).all()
```

---

## 📊 API Endpoints

### Autenticação

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/api/v1/auth/register` | Registra novo usuário |
| POST | `/api/v1/auth/login` | Autentica e retorna token |
| GET | `/api/v1/auth/me` | Dados do usuário atual |

### Upload

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/api/v1/upload/` | Upload de XLSX (async) |
| GET | `/api/v1/upload/` | Lista uploads do usuário |
| GET | `/api/v1/upload/{id}` | Busca upload específico |
| DELETE | `/api/v1/upload/{id}` | Deleta upload |

### Dashboard

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/v1/dashboard/` | Dados completos do dashboard |
| GET | `/api/v1/dashboard/upload/{id}/metrics` | Métricas de um upload |

**Documentação interativa:** `http://localhost:8000/docs`

---

## 🎨 Customização do Frontend

### Alterar Cores/Tema

Edite `frontend/app.py`:

```python
st.set_page_config(
    page_title="Meu Dashboard",
    page_icon="🚀",
    layout="wide"
)

# CSS customizado
st.markdown("""
<style>
    .metric-card {
        background-color: #YOUR_COLOR;
    }
</style>
""", unsafe_allow_html=True)
```

### Adicionar Novos Gráficos

```python
import plotly.express as px

fig = px.line(df_month, x='period', y='revenue', title='Receita Mensal')
st.plotly_chart(fig)
```

---

## 🚀 Deploy em Produção

### 1. Variáveis de Ambiente

```bash
# Gere uma SECRET_KEY forte
openssl rand -hex 32

# .env de produção
DATABASE_URL=postgresql://user:pass@db-host:5432/prod_db
SECRET_KEY=<chave-gerada>
BACKEND_CORS_ORIGINS=["https://seu-dominio.com"]
```

### 2. Docker em Cloud

```bash
# Build
docker-compose build

# Deploy (exemplo: AWS ECS, Google Cloud Run, Azure)
# Configure os serviços apontando para seu docker-compose.yml
```

### 3. Nginx Reverse Proxy

```nginx
server {
    listen 80;
    server_name seu-dominio.com;

    location /api/ {
        proxy_pass http://localhost:8000;
    }

    location / {
        proxy_pass http://localhost:8501;
    }
}
```

### 4. SSL/HTTPS

```bash
# Usando Certbot (Let's Encrypt)
sudo certbot --nginx -d seu-dominio.com
```

---

## 📈 Evolução para SaaS

### Funcionalidades Adicionais

1. **Multi-tenancy**
   - Organizações/Empresas
   - Múltiplos usuários por organização
   - Permissões por role (admin, viewer, editor)

2. **Planos de Assinatura**
   - Free: 10 uploads/mês
   - Pro: 100 uploads/mês
   - Enterprise: Ilimitado
   - Integração com Stripe/PagSeguro

3. **Processamento Avançado**
   - ML para detecção de anomalias
   - Previsão de faturamento
   - Alertas automáticos

4. **Integrações**
   - APIs de bancos
   - Importação de nota fiscal (XML)
   - Exportação para Google Sheets

5. **Relatórios**
   - Exportação PDF
   - Agendamento de relatórios
   - Email automático

### Escalabilidade

```python
# Use Celery para processamento assíncrono pesado
from celery import Celery

@celery.task
def process_xlsx_task(file_path):
    ...

# Use Redis para cache
from redis import Redis
cache = Redis()

@app.get("/dashboard/")
def get_dashboard():
    cached = cache.get(f"dashboard:{user_id}")
    if cached:
        return cached
    ...
```

---

## 🐛 Troubleshooting

### Backend não inicia

```bash
# Verifica se PostgreSQL está rodando
docker ps | grep postgres

# Verifica logs
docker logs financial_backend

# Recria banco de dados
docker-compose down -v
docker-compose up -d
```

### Frontend não conecta

```bash
# Verifica variável de ambiente
echo $API_BASE_URL

# Testa API diretamente
curl http://localhost:8000/health
```

### Processamento falha

```bash
# Verifica logs do backend
docker logs -f financial_backend

# Testa arquivo manualmente
python scripts/test_processor.py
```

---

## 🧪 Testes

### Backend

```bash
cd backend
pytest tests/
```

### Exemplo de teste

```python
def test_upload_xlsx(client, auth_headers):
    with open("sample.xlsx", "rb") as f:
        response = client.post(
            "/api/v1/upload/",
            files={"file": f},
            headers=auth_headers
        )
    assert response.status_code == 202
```

---

## 📝 Licença

MIT License - use livremente para projetos pessoais e comerciais.

---

## 🤝 Contribuindo

1. Fork o projeto
2. Crie uma branch (`git checkout -b feature/nova-funcionalidade`)
3. Commit suas mudanças (`git commit -m 'Add nova funcionalidade'`)
4. Push para a branch (`git push origin feature/nova-funcionalidade`)
5. Abra um Pull Request

---

## 📧 Suporte

- 📖 Documentação: `http://localhost:8000/docs`
- 🐛 Issues: [GitHub Issues]
- 💬 Discussões: [GitHub Discussions]

---

**Desenvolvido com ❤️ usando FastAPI + Streamlit + Pandas**
