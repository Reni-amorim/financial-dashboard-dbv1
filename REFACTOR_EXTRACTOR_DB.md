# Refactor: Extractor DB Externo — Documentação do Processo

---

## ✅ PASSOS CONCLUÍDOS

---

### Passo 1 — Configuração

**1.1 `.env`** — Adicionar variáveis:
```env
EXTERNAL_DB_URL=postgresql://user:password@host:5432/external_db
FATURAMENTO_TABLE=faturamento
```

**1.2 `backend/requirements.txt`** — Adicionar:
```
alembic
```

**1.3 `backend/app/db/external_database.py`** — Criar arquivo:
- Engine lazy para o DB externo
- Função `get_external_engine()`
- Função `test_external_connection()`

**1.4 `backend/app/models/empresa.py`** — Adicionar campos:
```python
vendedor_id = Column(BigInteger, nullable=True, index=True)
seller_id   = Column(BigInteger, nullable=True, index=True)
```

**1.5 `backend/app/schemas/empresa.py`** — Adicionar nos schemas:
```python
# EmpresaCreate, EmpresaUpdate e EmpresaOut
vendedor_id: Optional[int] = None
seller_id:   Optional[int] = None
```

**1.6 `backend/app/models/__init__.py`** — Adicionar export do Base:
```python
from app.db.database import Base
```

**1.7 Alembic** — Configuração inicial:
- Criar `backend/alembic.ini` com `python -m alembic init migrations`
- Editar `alembic.ini`: `sqlalchemy.url = postgresql://user:pass@postgres:5432/financial_db`
- Editar `backend/migrations/env.py`: importar `Base` e setar `target_metadata`
- Gerar migration:
```bash
docker-compose exec backend python -m alembic revision --autogenerate -m "add vendedor_id and seller_id to empresas"
```
- Aplicar migration:
```bash
docker-compose exec backend python -m alembic upgrade head
```

---

## 🔄 PASSOS PENDENTES

---

### Passo 2 — Serviço de Extração

- Criar `backend/app/services/faturamento_extractor.py`
- Conecta no DB externo
- Faz `SELECT * FROM pedidos_vendas WHERE seller_id = ?`
- Mapeia colunas do DB externo para o padrão do `xlsx_processor`
- Retorna DataFrame processado

> ⚠️ **Pendente:** Confirmar formato da coluna `data_criacao` (datetime ou string) via testes antes de implementar

---

### Passo 3 — Reutilizar Processamento Existente

- Adaptar `backend/app/services/xlsx_processor.py` para aceitar DataFrame além de arquivo XLSX
- Reutilizar funções: `_to_brl_number()`, `_parse_data_pt()`, cálculo de créditos/débitos/líquido

---

### Passo 4 — Cache em Parquet

- Salvar em `data/faturamento/{seller_id}/{uuid}.parquet`
- Deletar parquet anterior antes de salvar novo
- Mesma estrutura do upload via XLSX

---

### Passo 5 — Endpoint `POST /api/v1/dashboard/atualizar`

- Recebe `seller_id` do usuário autenticado (via cadastro de empresa)
- Chama `faturamento_extractor.extract_and_cache(seller_id)`
- Retorna `{ rows, summary }` com quantidade de linhas processadas

---

### Passo 6 — Endpoint `GET /api/v1/dashboard/`

- Sem alterações — continua lendo o Parquet em cache

---

### Passo 7 — Frontend

- Adicionar botão **"🔄 Atualizar Dados"** na página do dashboard
- Chama `POST /atualizar`
- Exibe spinner enquanto processa
- Atualiza dashboard após conclusão

---

## Fluxo Final

```
[Botão Atualizar]
      ↓
POST /dashboard/atualizar  (recebe seller_id da empresa cadastrada)
      ↓
Extrai do DB externo (SELECT pedidos_vendas WHERE seller_id = ?)
      ↓
Mapeia colunas → processa (_to_brl_number, créditos/débitos)
      ↓
Salva Parquet (cache)
      ↓
GET /dashboard/ lê o Parquet
      ↓
[Dashboard atualizado]
```

---

## Contexto de Dados

```
users.id
  └── empresas.user_id
        ├── empresas.vendedor_id  →  vendedores.id (DB externo)
        └── empresas.seller_id   →  contas_meli.seller_id (DB externo)
                                          └── pedidos_vendas.seller_id
```

---

## Mapeamento de Colunas (DB externo → xlsx_processor)

| Coluna DB externo | Coluna xlsx_processor |
|---|---|
| `id_pedido` | `N.º de venda` |
| `data_criacao` | `Data da venda` |
| `status` | `Estado` |
| `receita_produtos` | `Receita por produtos (BRL)` |
| `acrescimo_parcelamento` | `Receita por acréscimo no preço (pago pelo comprador)` |
| `tarifa_venda` | `Tarifa de venda e impostos (BRL)` |
| `receita_envio` | `Receita por envio (BRL)` |
| `tarifa_envio` | `Tarifas de envio (BRL)` |
| `total_refund` | `Cancelamentos e reembolsos (BRL)` |
| `valor` | `Total (BRL)` |
| `custo_envio_declarado` | `Custo de envio com base nas medidas e peso declarados` |
| `custo_diferenca_peso` | `Custo por diferenças nas medidas e no peso do pacote` |
| `parcelas * valor_parcela` *(calculado)* | `Taxa de parcelamento equivalente ao acréscimo` |
