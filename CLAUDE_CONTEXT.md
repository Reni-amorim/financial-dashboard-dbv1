# Contexto do Projeto - Financial Dashboard

## 📊 Visão Geral
Sistema web full-stack para upload e análise de planilhas financeiras do Mercado Livre.
Desenvolvido durante sessão de pair programming com Claude AI.

## 🏗️ Arquitetura

### Stack Tecnológica
- **Backend:** FastAPI + SQLAlchemy + PostgreSQL
- **Frontend:** Streamlit
- **Processamento:** Pandas + PyArrow (Parquet)
- **Autenticação:** JWT + bcrypt
- **Deploy:** Docker Compose

### Estrutura de Pastas
```
financial-dashboard/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── init_db.py
│   │   ├── models/
│   │   │   ├── user.py
│   │   │   └── upload.py
│   │   ├── api/
│   │   │   ├── auth.py
│   │   │   ├── upload.py
│   │   │   └── dashboard.py
│   │   ├── core/
│   │   │   ├── security.py
│   │   │   └── deps.py
│   │   └── services/
│   │       ├── xlsx_processor.py
│   │       └── anuncios_processor.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── app.py
│   ├── pages/
│   │   ├── upload.py
│   │   └── dashboard.py
│   ├── requirements.txt
│   └── Dockerfile
├── data/
│   ├── faturamento/{user_id}/*.parquet
│   ├── anuncios/{user_id}/*.parquet
│   └── raw/{tipo}/*.xlsx
├── docker-compose.yml
└── .env
```

## 🔑 Funcionalidades Implementadas

### 1. Sistema de Upload Dual
- **Faturamento:** Upload com reset automático (deleta anterior)
- **Anúncios:** Upload com histórico preservado
- Endpoints: `/api/v1/upload/faturamento` e `/api/v1/upload/anuncios`

### 2. Processamento de XLSX
- Detecção automática de formato monetário (BR/US)
- Conversão: `"R$ 1.234,56"` → `1234.56`
- Pipeline: XLSX → Pandas → Parquet
- Cálculo automático de métricas

### 3. Dashboard Financeiro
- Cards: Créditos, Débitos, Líquido
- Gráfico mensal: Barras (créditos/débitos) + Linha (líquido)
- Tabela detalhada por mês
- Detalhamento por coluna (expandível)

### 4. Autenticação
- JWT com expiração de 30 minutos
- Bcrypt para hash de senhas
- Proteção de rotas

## 🐛 Bugs Corrigidos Recentemente

### Bug #1: Valores 100x Maiores
**Problema:** Conversão de `"18.75"` resultava em `1875.0`
**Causa:** Função removendo ponto decimal como separador de milhar
**Solução:** Detecção inteligente de formato em `_to_brl_number()`
```python
# Antes (errado):
s = s.str.replace(".", "", regex=False)  # Remove TODO ponto
s = s.str.replace(",", ".", regex=False)

# Depois (correto):
# Detecta se ponto é milhar ou decimal baseado no contexto
if num_pontos > 0 and num_virgulas == 0:
    # Um ponto apenas → decimal (formato US)
    pass  # Mantém como está
elif num_virgulas > 0 and num_pontos > 0:
    # Ponto E vírgula → formato BR "1.234,56"
    val = val.replace(".", "").replace(",", ".")
```

### Bug #2: Dashboard Vazio
**Problema:** Dashboard não exibia dados após upload
**Causa:** Mismatch de caminhos (processor salvava em `data/processed/`, dashboard buscava em `data/faturamento/`)
**Solução:** Padronizar para `data/{upload_type}/{user_id}/`

### Bug #3: Perda de Histórico ao Trocar Páginas
**Problema:** Streamlit resetava session ao navegar
**Solução:** Implementar `st.session_state` e botão de refresh

## 📊 Modelo de Dados

### Tabela: users
```sql
id, username, email, password_hash, created_at
```

### Tabela: uploads
```sql
id, user_id, upload_type, filename, original_filename,
file_path, parquet_path, processing_status, rows_processed,
error_message, metrics_json, uploaded_at, processed_at
```

## 🔄 Fluxo de Processamento

### Upload de Faturamento:
```
1. User faz upload → POST /api/v1/upload/faturamento
2. Delete uploads anteriores (tipo=faturamento)
3. Salva XLSX em data/raw/faturamento/
4. Cria registro no banco (status=pending)
5. process_xlsx_to_parquet():
   - Lê XLSX com pandas
   - Encontra linha de cabeçalho ("N.º de venda")
   - Converte colunas monetárias (_to_brl_number)
   - Calcula créditos/débitos
   - Salva Parquet em data/faturamento/{user_id}/
6. Atualiza registro (status=completed, metrics)
7. Retorna sucesso
```

### Dashboard:
```
1. GET /api/v1/dashboard/
2. Busca último Parquet: glob("data/faturamento/{user_id}/*.parquet")
3. Lê Parquet com pandas
4. Calcula totais por coluna
5. Calcula créditos/débitos/líquido
6. Agrupa por mês (ano_mes)
7. Retorna JSON
```

## 💰 Cálculo de Métricas Financeiras

### Créditos (Receitas):
```python
creditos_cols = [
    "Receita por produtos (BRL)",
    "Receita por acréscimo no preço (pago pelo comprador)",
    "Receita por envio (BRL)",
]
total_creditos = sum(df[col].sum() for col in creditos_cols if col in df.columns)
```

### Débitos (Custos):
```python
debitos_cols = [
    "Taxa de parcelamento equivalente ao acréscimo",
    "Tarifa de venda e impostos (BRL)",
    "Custo de envio com base nas medidas e peso declarados",
    "Custo por diferenças nas medidas e no peso do pacote",
    "Cancelamentos e reembolsos (BRL)",
]
total_debitos = sum(abs(df[col].sum()) for col in debitos_cols if col in df.columns)
```

### Líquido:
```python
total_liquido = total_creditos - total_debitos
margem = (total_liquido / total_creditos * 100) if total_creditos > 0 else 0
```

## 🔧 Configurações Importantes

### Backend (.env):
```env
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/financial_db
SECRET_KEY={gerado automaticamente}
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### Docker Compose:
```yaml
services:
  postgres: PostgreSQL 16
  backend: FastAPI (porta 8000)
  frontend: Streamlit (porta 8501)
```

## 🚨 Problemas Conhecidos

### 1. Warning de Date Parsing
```
UserWarning: Could not infer format, so each element will be parsed individually
```
**Status:** Não crítico, apenas warning de performance
**TODO:** Especificar formato de data explicitamente

### 2. Processor de Anúncios
**Status:** Estrutura criada, aguardando formato real do arquivo
**TODO:** Ajustar colunas em `ANUNCIOS_COLS` e `ANUNCIOS_KEY_HEADER`

### 3. Duplicate Operation ID
```
Duplicate Operation ID get_dashboard_api_v1_dashboard__get
```
**Status:** Resolvido (removidos decoradores duplicados)

## 📝 Próximos Passos Sugeridos

1. **Dashboard de Anúncios:**
   - Endpoint `/api/v1/dashboard/anuncios`
   - Métricas: total anúncios, ativos, visitas, vendas, taxa conversão
   - Gráficos: performance por anúncio, tendências

2. **Integração de Dados:**
   - Cruzar faturamento com anúncios
   - ROI por anúncio
   - Performance de vendas

3. **Melhorias:**
   - Implementar Alembic (migrations)
   - Background tasks com Celery
   - Cache com Redis
   - Testes automatizados
   - CI/CD

4. **UX:**
   - Filtros por data
   - Exportação de relatórios (PDF/Excel)
   - Comparação de períodos
   - Alertas e notificações

## 🐳 Comandos Docker Úteis
```bash
# Iniciar
docker-compose up -d

# Ver logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Reiniciar
docker-compose restart backend

# Rebuild
docker-compose build --no-cache
docker-compose up -d

# Parar e limpar
docker-compose down -v

# Shell no container
docker-compose exec backend bash
docker-compose exec postgres psql -U postgres -d financial_db
```

## 🔍 Debug Rápido
```bash
# Ver uploads no banco
docker-compose exec postgres psql -U postgres -d financial_db -c \
  "SELECT id, user_id, upload_type, original_filename, processing_status FROM uploads;"

# Ver arquivos Parquet
docker-compose exec backend ls -lh /app/data/faturamento/1/

# Testar API
curl -X POST http://localhost:8000/api/v1/auth/login \
  -d "username=XXX&password=XXX"
```

## 📚 Referências Técnicas

- FastAPI: https://fastapi.tiangolo.com/
- Pandas: https://pandas.pydata.org/
- Streamlit: https://streamlit.io/
- SQLAlchemy: https://www.sqlalchemy.org/
- Python-Jose (JWT): https://python-jose.readthedocs.io/

## 🎯 Objetivos do Projeto

**Curto Prazo:**
- ✅ Upload e processamento de XLSX
- ✅ Dashboard financeiro básico
- ✅ Autenticação de usuários
- ⏳ Dashboard de anúncios

**Médio Prazo:**
- Integração de dados
- Relatórios avançados
- Performance optimization

**Longo Prazo:**
- SaaS multi-tenant
- API pública
- Mobile app

## 👤 Autor
Desenvolvido em pair programming com Claude AI (Anthropic)
Data: Março 2026