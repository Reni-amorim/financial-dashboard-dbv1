# 📦 Implantação do Banco de Dados — `financial_db` (v3)

> **Referência principal:** `db_meli_documentacao_v3.md`
> **Arquitetura:** `ARCHITECTURE_v3.md`
> **Contexto:** `CLAUDE.md`
> **Banco:** `financial_db`
> **Usuário:** `usuario_financial`
> **Container:** `financial_db_docker`
> **Tecnologia:** PostgreSQL 16 via Docker
> **Backend:** FastAPI + SQLAlchemy + Alembic
> **Atualizado em:** 2026

---

## 🔌 Parâmetros Definitivos de Conexão

| Parâmetro | Valor |
|---|---|
| Database | `financial_db` |
| Usuário | `usuario_financial` |
| Container | `financial_db_docker` |
| Porta | `5432` |
| Host dentro do Docker | `financial_db_docker` |
| Host fora do Docker | `localhost` |

**String de conexão — `.env` (dentro do Docker):**
```
DATABASE_URL=postgresql://usuario_financial:****@financial_db_docker:5432/financial_db
```

**String de conexão — `alembic.ini` (fora do Docker):**
```
sqlalchemy.url = postgresql://usuario_financial:****@localhost:5432/financial_db
```

**Acesso direto via Docker:**
```bash
docker exec -it financial_db_docker psql -U usuario_financial -d financial_db
```

---

## 📐 Schema Final — 10 Tabelas + 2 Views

| Objeto | Tipo | Camada | Descrição |
|---|---|---|---|
| `user` | tabela | Sistema | Usuários — admin, market, fiscal |
| `company` | tabela | Sistema | Empresa cadastrada pelo admin |
| `business` | tabela | Mercado Livre | Sellers vinculados à company |
| `account` | tabela | Mercado Livre | Contas ML vinculadas ao business |
| `account_address` | tabela | Mercado Livre | Endereços das contas |
| `orders` | tabela | Mercado Livre | Pedidos sincronizados via n8n |
| `items_order` | tabela | Mercado Livre | Itens dos pedidos |
| `shipping` | tabela | Mercado Livre | Dados de entrega/logística |
| `billing` | tabela | Mercado Livre | Dados fiscais dos pedidos |
| `product` | tabela | Sistema | Cadastro de produtos |
| `v_accounts_ativas` | view | — | Contas `status = 'active'` e `deleted_at IS NULL` |
| `v_business_ativos` | view | — | Businesses com `deleted_at IS NULL` |

### Hierarquia de Relacionamentos

```
user (role = admin — criado no pagamento)
  └── company (user_id → user.id)
        ├── user market  (company_id → company.id)
        ├── user fiscal  (company_id → company.id)
        ├── business (company_id → company.id)
        │     └── account (business_id → business.id)
        │           ├── account_address (account_id → account.id)
        │           └── orders (account_id → account.id)  ← n8n
        │                 ├── items_order (order_id → orders.id)
        │                 │     └── product (sku ↔ items_order.sku)
        │                 ├── shipping (order_id → orders.id)
        │                 └── billing (order_id → orders.id)
        └── product (company_id → company.id)
```

---

## 🗂️ Estado Atual do Sistema (pré-implantação)

| Arquivo | Situação atual | Ação |
|---|---|---|
| `backend/app/models/user.py` | Tabela `users` — campos incompletos | **Reescrever** |
| `backend/app/models/upload.py` | FK aponta para `users.id` | **Dropar e recriar** |
| `backend/app/models/empresa.py` | Substituído pelo `company` da v3 | **Remover** |
| `backend/app/models/__init__.py` | Importa `Empresa` | **Atualizar imports** |
| `backend/app/init_db.py` | Usa `Base.metadata.create_all` | **Remover** |
| `backend/app/db/database.py` | OK | Sem alteração |
| `docker-compose.yml` | Container e usuário antigos | **Atualizar** |
| `.env` | String de conexão antiga | **Atualizar** |
| `CLAUDE.md` | Comandos com parâmetros antigos | **Atualizar** |

---

## 🚀 Fases de Implantação

---

### FASE 1 — Atualizar `docker-compose.yml`

Localizar o serviço `postgres` e aplicar as alterações:

**Antes:**
```yaml
postgres:
  image: postgres:16-alpine
  container_name: financial_db
  environment:
    POSTGRES_USER: postgres
    POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    POSTGRES_DB: financial_db
```

**Depois:**
```yaml
postgres:
  image: postgres:16-alpine
  container_name: financial_db_docker
  environment:
    POSTGRES_USER: usuario_financial
    POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    POSTGRES_DB: financial_db
  ports:
    - "5432:5432"
  volumes:
    - postgres_data:/var/lib/postgresql/data
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U usuario_financial"]
    interval: 10s
    timeout: 5s
    retries: 5
  networks:
    - financial_network
```

> ⚠️ O `healthcheck` também deve ser atualizado para usar `usuario_financial`.

---

### FASE 2 — Atualizar `.env`

**Antes:**
```env
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/financial_db
```

**Depois:**
```env
DATABASE_URL=postgresql://usuario_financial:****@financial_db_docker:5432/financial_db
```

> ⚠️ Dentro do Docker o host é o nome do container (`financial_db_docker`), não `localhost`.

---

### FASE 3 — Instalar e configurar o Alembic

#### 3.1 — Instalar

```bash
cd backend
pip install alembic
```

Adicionar ao `requirements.txt`:
```
alembic==1.13.1
```

#### 3.2 — Inicializar

```bash
cd backend
alembic init alembic
```

Estrutura gerada:
```
backend/
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/        ← migrations ficam aqui
└── alembic.ini
```

#### 3.3 — Configurar `alembic.ini`

```ini
sqlalchemy.url = postgresql://usuario_financial:****@localhost:5432/financial_db
```

> ⚠️ Aqui o host é `localhost` pois o Alembic roda fora do container.

#### 3.4 — Configurar `alembic/env.py`

Substituir o bloco `target_metadata` pelo código abaixo.
O `env.py` deve importar **todos os models** para o autogenerate detectá-los:

```python
# alembic/env.py
import os
import sys
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.db.database import Base

# Importar TODOS os models — obrigatório para o autogenerate
from app.models.user            import User
from app.models.company         import Company
from app.models.business        import Business
from app.models.account         import Account
from app.models.account_address import AccountAddress
from app.models.orders          import Orders
from app.models.items_order     import ItemsOrder
from app.models.shipping        import Shipping
from app.models.billing         import Billing
from app.models.product         import Product
from app.models.upload          import Upload

config = context.config
fileConfig(config.config_file_name)
target_metadata = Base.metadata

def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    connectable = engine_from_config(
        config.config_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

---

### FASE 4 — Remover arquivos obsoletos

#### 4.1 — Remover `init_db.py`

```bash
rm backend/app/init_db.py
```

> O Alembic é o único método de criação de tabelas. O `init_db.py` não deve mais existir.

#### 4.2 — Remover `empresa.py`

```bash
rm backend/app/models/empresa.py
```

> Substituído pelo model `Company` da v3. A tabela `empresas` será dropada na migration.

#### 4.3 — Remover chamada no `main.py`

Localizar e remover do `main.py`:

```python
# Remover estas linhas:
from app.init_db import init_database
init_database()
```

---

### FASE 5 — Reescrever os Models existentes

#### 5.1 — `backend/app/models/user.py`

Substituir completamente:

```python
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.db.database import Base


class User(Base):
    """
    Nível raiz do sistema.
    Roles: admin (dono) | market | fiscal
    company_id começa NULL — preenchido após cadastro da company.
    """
    __tablename__ = "user"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    company_id    = Column(Integer, ForeignKey("company.id"), nullable=True)
    name          = Column(String(255), nullable=False)
    email         = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String, nullable=False)
    role          = Column(String(50), nullable=False, default="admin")
    created_at    = Column(DateTime, server_default=func.now())
    updated_at    = Column(DateTime, server_default=func.now(), onupdate=func.now())
    deleted_at    = Column(DateTime, nullable=True)

    company       = relationship("Company", foreign_keys=[company_id],
                                 back_populates="users")
    owned_company = relationship("Company", foreign_keys="Company.user_id",
                                 back_populates="owner", uselist=False)
```

#### 5.2 — `backend/app/models/upload.py`

Substituir completamente (FK atualizada para `user.id`):

```python
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, func
from sqlalchemy.orm import relationship
from app.db.database import Base


class Upload(Base):
    """
    Controle de uploads de planilhas XLSX.
    FK: user_id → user.id  (tabela 'user', não mais 'users')
    upload_type: faturamento (reset) | anuncios (histórico)
    """
    __tablename__ = "uploads"

    id                = Column(Integer, primary_key=True, autoincrement=True)
    user_id           = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"),
                               nullable=False, index=True)
    upload_type       = Column(String(50), nullable=False, default="faturamento", index=True)
    filename          = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path         = Column(String(500), nullable=False)
    parquet_path      = Column(String(500), nullable=True)
    processing_status = Column(String(50), nullable=False, default="pending")
    rows_processed    = Column(Integer, nullable=True)
    error_message     = Column(Text, nullable=True)
    metrics_json      = Column(Text, nullable=True)
    uploaded_at       = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    processed_at      = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", backref="uploads")
```

---

### FASE 6 — Criar os novos Models (tabelas da v3)

Criar um arquivo por tabela em `backend/app/models/`:

#### `company.py`

```python
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.db.database import Base


class Company(Base):
    __tablename__ = "company"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    user_id    = Column(Integer, ForeignKey("user.id"), nullable=False)
    name       = Column(String(255), nullable=False)
    document   = Column(String(20), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    created_by = Column(String(100), nullable=True)
    updated_by = Column(String(100), nullable=True)
    deleted_at = Column(DateTime, nullable=True)

    owner      = relationship("User", foreign_keys=[user_id], back_populates="owned_company")
    users      = relationship("User", foreign_keys="User.company_id", back_populates="company")
    businesses = relationship("Business", back_populates="company")
    products   = relationship("Product", back_populates="company")
```

#### `business.py`

```python
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.db.database import Base


class Business(Base):
    __tablename__ = "business"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("company.id"), nullable=False)
    name       = Column(String(255), nullable=False)
    document   = Column(String(20), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    created_by = Column(String(100), nullable=True)
    updated_by = Column(String(100), nullable=True)
    deleted_at = Column(DateTime, nullable=True)

    company  = relationship("Company", back_populates="businesses")
    accounts = relationship("Account", back_populates="business")
```

#### `account.py`

```python
from sqlalchemy import Column, Integer, BigInteger, String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.db.database import Base


class Account(Base):
    __tablename__ = "account"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    business_id    = Column(Integer, ForeignKey("business.id"), nullable=True)
    marketplace_id = Column(BigInteger, nullable=True)
    name           = Column(String(255), nullable=True)
    access_token   = Column(Text, nullable=True)
    refresh_token  = Column(Text, nullable=True)
    status         = Column(String, nullable=True, default="active")
    created_at     = Column(DateTime, server_default=func.now())
    updated_at     = Column(DateTime, server_default=func.now(), onupdate=func.now())
    created_by     = Column(String(100), nullable=True)
    updated_by     = Column(String(100), nullable=True)
    deleted_at     = Column(DateTime, nullable=True)

    business  = relationship("Business", back_populates="accounts")
    addresses = relationship("AccountAddress", back_populates="account")
    orders    = relationship("Orders", back_populates="account")
```

#### `account_address.py`

```python
from sqlalchemy import CHAR, Column, Integer, Text, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.db.database import Base


class AccountAddress(Base):
    __tablename__ = "account_address"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    account_id  = Column(Integer, ForeignKey("account.id"), nullable=False)
    tipo        = Column(Text, nullable=True)
    logradouro  = Column(Text, nullable=False)
    numero      = Column(Text, nullable=False)
    complemento = Column(Text, nullable=True)
    bairro      = Column(Text, nullable=True)
    cidade      = Column(Text, nullable=False)
    estado      = Column(CHAR(2), nullable=False)   # ⚠️ char(2) conforme db_meli_v3 — ex: "SP", "RJ"
    cep         = Column(Text, nullable=True)
    principal   = Column(Boolean, nullable=True, default=False)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    account = relationship("Account", back_populates="addresses")
```

#### `orders.py`

```python
from sqlalchemy import Column, Integer, String, Text, Numeric, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.db.database import Base


class Orders(Base):
    __tablename__ = "orders"

    id                     = Column(Integer, primary_key=True, autoincrement=True)
    external_order_id      = Column(String(50), nullable=False)
    account_id             = Column(Integer, ForeignKey("account.id"), nullable=False)
    status                 = Column(Text, nullable=True)
    data_criacao           = Column(DateTime, nullable=True)
    valor                  = Column(Numeric, nullable=True)
    pago                   = Column(Numeric, nullable=True)
    receita_produtos       = Column(Numeric, nullable=True)
    acrescimo_parcelamento = Column(Numeric, nullable=True)
    tarifa_venda           = Column(Numeric, nullable=True)
    parcelas               = Column(Integer, nullable=True)
    valor_parcela          = Column(Numeric, nullable=True)
    total_refund           = Column(Numeric, nullable=True)
    rebate_meli            = Column(Numeric, nullable=True)
    created_at             = Column(DateTime, server_default=func.now())
    updated_at             = Column(DateTime, server_default=func.now(), onupdate=func.now())
    created_by             = Column(String(100), nullable=True)
    updated_by             = Column(String(100), nullable=True)
    deleted_at             = Column(DateTime, nullable=True)

    account  = relationship("Account", back_populates="orders")
    items    = relationship("ItemsOrder", back_populates="order")
    shipping = relationship("Shipping", back_populates="order", uselist=False)
    billing  = relationship("Billing", back_populates="order", uselist=False)
```

#### `items_order.py`

```python
from sqlalchemy import Column, Integer, String, Text, Numeric, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.db.database import Base


class ItemsOrder(Base):
    __tablename__ = "items_order"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    order_id       = Column(Integer, ForeignKey("orders.id"), nullable=False)
    sku            = Column(Text, nullable=True)   # ⚠️ nullable — sempre LEFT JOIN com product
    titulo         = Column(String(255), nullable=False)
    quantidade     = Column(Integer, nullable=False)
    preco_unitario = Column(Numeric, nullable=False)
    created_at     = Column(DateTime, server_default=func.now())
    updated_at     = Column(DateTime, server_default=func.now(), onupdate=func.now())
    created_by     = Column(String(100), nullable=True)
    updated_by     = Column(String(100), nullable=True)
    deleted_at     = Column(DateTime, nullable=True)

    order = relationship("Orders", back_populates="items")
```

#### `shipping.py`

```python
from sqlalchemy import BigInteger, Column, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base


class Shipping(Base):
    __tablename__ = "shipping"

    # ⚠️ autoincrement=False — o id é o ID do envio vindo do ML via n8n, não gerado internamente
    id            = Column(BigInteger, primary_key=True, autoincrement=False)
    order_id      = Column(BigInteger, ForeignKey("orders.id"), nullable=True)
    receiver_name = Column(Text, nullable=True)
    cep           = Column(Text, nullable=True)
    logradouro    = Column(Text, nullable=True)
    numero        = Column(Text, nullable=True)
    complemento   = Column(Text, nullable=True)
    bairro        = Column(Text, nullable=True)
    cidade        = Column(Text, nullable=True)
    estado        = Column(Text, nullable=True)

    order = relationship("Orders", back_populates="shipping")
```

#### `billing.py`

```python
from sqlalchemy import BigInteger, Column, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base


class Billing(Base):
    __tablename__ = "billing"

    id           = Column(BigInteger, primary_key=True, autoincrement=True)
    order_id     = Column(BigInteger, ForeignKey("orders.id"), nullable=True)
    doc_tipo     = Column(Text, nullable=True)
    doc_numero   = Column(Text, nullable=True)
    razao_social = Column(Text, nullable=True)
    ie           = Column(Text, nullable=True)
    cep          = Column(Text, nullable=True)
    logradouro   = Column(Text, nullable=True)
    numero       = Column(Text, nullable=True)
    complemento  = Column(Text, nullable=True)
    bairro       = Column(Text, nullable=True)
    cidade       = Column(Text, nullable=True)
    estado       = Column(Text, nullable=True)

    order = relationship("Orders", back_populates="billing")
```

#### `product.py`

```python
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.db.database import Base


class Product(Base):
    __tablename__ = "product"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("company.id"), nullable=False)
    sku        = Column(String(100), nullable=False)
    name       = Column(String(255), nullable=False)
    ncm        = Column(String(20), nullable=True)
    cost_price = Column(Numeric, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    company = relationship("Company", back_populates="products")
```

---

### FASE 7 — Atualizar `models/__init__.py`

Substituir completamente:

```python
# backend/app/models/__init__.py
from app.models.user            import User
from app.models.company         import Company
from app.models.business        import Business
from app.models.account         import Account
from app.models.account_address import AccountAddress
from app.models.orders          import Orders
from app.models.items_order     import ItemsOrder
from app.models.shipping        import Shipping
from app.models.billing         import Billing
from app.models.product         import Product
from app.models.upload          import Upload

__all__ = [
    "User", "Company", "Business", "Account", "AccountAddress",
    "Orders", "ItemsOrder", "Shipping", "Billing", "Product", "Upload",
]
```

---

### FASE 8 — Gerar a Migration

```bash
cd backend
alembic revision --autogenerate -m "initial_schema_v3"
```

Isso cria o arquivo `alembic/versions/xxxx_initial_schema_v3.py`.

#### ⚠️ Revisar o arquivo gerado antes de aplicar

Verificar se estão presentes:
- Drop da tabela `users` (antiga)
- Drop da tabela `uploads` (antiga — FK errada)
- Drop da tabela `empresas` (obsoleta)
- Criação das 10 tabelas novas

Se os drops não aparecerem automaticamente, adicionar manualmente no `upgrade()`:

```python
def upgrade():
    # Drops manuais das tabelas obsoletas
    op.drop_table("uploads")   # recriada com FK correta abaixo
    op.drop_table("empresas")  # substituída por company
    op.drop_table("users")     # substituída por user

    # ... restante gerado automaticamente pelo Alembic ...
```

---

### FASE 9 — Adicionar as Views na Migration

O Alembic não detecta views automaticamente.
Adicionar manualmente ao final do `upgrade()` no arquivo de migration:

```python
def upgrade():
    # ... tabelas geradas automaticamente ...

    # Views — adicionadas manualmente
    op.execute("""
        CREATE OR REPLACE VIEW v_accounts_ativas AS
        SELECT * FROM account
        WHERE status = 'active'
          AND deleted_at IS NULL
    """)

    op.execute("""
        CREATE OR REPLACE VIEW v_business_ativos AS
        SELECT * FROM business
        WHERE deleted_at IS NULL
    """)


def downgrade():
    op.execute("DROP VIEW IF EXISTS v_business_ativos")
    op.execute("DROP VIEW IF EXISTS v_accounts_ativas")
    # ... drops das tabelas gerados automaticamente ...
```

---

### FASE 10 — Aplicar a Migration no Banco

```bash
# Subir o container
docker-compose up -d postgres

# Aplicar todas as migrations
cd backend
alembic upgrade head
```

Verificar:

```bash
# Listar tabelas — deve exibir 10 tabelas + alembic_version
docker exec -it financial_db_docker psql -U usuario_financial -d financial_db -c "\dt"

# Listar views — deve exibir v_accounts_ativas e v_business_ativos
docker exec -it financial_db_docker psql -U usuario_financial -d financial_db -c "\dv"
```

---

### FASE 11 — Atualizar `CLAUDE.md`

#### Atualizar seção `Stack` — adicionar Alembic:

```markdown
- **Migrations:** Alembic (único método — `init_db.py` removido)
```

#### Atualizar seção `Comandos úteis`:

**Antes:**
```bash
docker-compose exec postgres psql -U postgres -d financial_db
docker-compose exec postgres psql -U postgres -d financial_db -c \
  "SELECT id, user_id, upload_type, original_filename, processing_status FROM uploads;"
```

**Depois:**
```bash
# Banco
docker exec -it financial_db_docker psql -U usuario_financial -d financial_db

# Ver uploads
docker exec -it financial_db_docker psql -U usuario_financial -d financial_db -c \
  "SELECT id, user_id, upload_type, original_filename, processing_status FROM uploads;"

# Migrations (Alembic)
alembic upgrade head                              # aplicar migrations pendentes
alembic revision --autogenerate -m "descricao"   # gerar nova migration
alembic downgrade -1                              # reverter última migration
alembic history                                   # ver histórico de migrations
alembic current                                   # ver migration atualmente aplicada
```

---

## ✅ Checklist de Implantação

```
[ ] FASE 1  — Atualizar docker-compose.yml
              container_name: financial_db_docker
              POSTGRES_USER: usuario_financial
              healthcheck atualizado

[ ] FASE 2  — Atualizar .env
              DATABASE_URL com financial_db_docker e usuario_financial

[ ] FASE 3  — Instalar Alembic
              pip install alembic + requirements.txt
              alembic init alembic
              alembic.ini → sqlalchemy.url com localhost
              env.py → Base + todos os imports de models

[ ] FASE 4  — Remover obsoletos
              rm backend/app/init_db.py
              rm backend/app/models/empresa.py
              Remover init_database() do main.py

[ ] FASE 5  — Reescrever models existentes
              user.py  → tabela 'user', campos completos (role, company_id, deleted_at)
              upload.py → FK user_id → user.id

[ ] FASE 6  — Criar 8 novos models
              company.py, business.py, account.py, account_address.py
              orders.py, items_order.py, shipping.py, billing.py, product.py

[ ] FASE 7  — Atualizar models/__init__.py
              Importar todos os 11 models (10 tabelas + Upload)

[ ] FASE 8  — Gerar migration
              alembic revision --autogenerate -m "initial_schema_v3"
              Revisar arquivo gerado
              Adicionar drops manuais se necessário (users, uploads, empresas)

[ ] FASE 9  — Adicionar views na migration
              v_accounts_ativas e v_business_ativos no upgrade()
              Drops correspondentes no downgrade()

[ ] FASE 10 — Aplicar no banco
              docker-compose up -d postgres
              alembic upgrade head
              Validar com \dt e \dv

[ ] FASE 11 — Atualizar CLAUDE.md
              Stack: adicionar Alembic
              Comandos: financial_db_docker + usuario_financial + comandos alembic
```

---

## ⚠️ Avisos Importantes

**SKU nullable em `items_order`**
O campo `sku` é nullable. Sempre usar `LEFT JOIN` com `product`:
```sql
SELECT io.*, p.cost_price
FROM items_order io
LEFT JOIN product p ON p.sku = io.sku AND p.company_id = <company_id>
WHERE io.deleted_at IS NULL;
```

**`company_id` do admin começa como NULL — UPDATE obrigatório após criar company**
O `user` admin é criado no pagamento com `company_id = NULL`.
O fluxo completo que o backend deve implementar é:

```
1. Pagamento confirmado  →  user criado (role = admin, company_id = NULL)
2. Admin cadastra company  →  company criada (user_id = admin.id)
3. Backend faz UPDATE user SET company_id = <company.id> WHERE id = <admin.id>  ← obrigatório
4. n8n consulta ML  →  popula business, account, orders, items_order, shipping, billing
5. Admin cria users market e fiscal (company_id já preenchido)
```

> ⚠️ O passo 3 não é automático. O backend deve executar o UPDATE explicitamente
> após inserir a company. Sem esse UPDATE, o admin ficará com `company_id = NULL`
> e os relacionamentos não funcionarão.

**Deleção em cascade do admin**
Quando o `user` admin é deletado, a `company` é deletada em cascade.
Essa lógica é aplicada no backend — não via FK CASCADE no banco.

**Faturamento vs Anúncios**
Conforme `ARCHITECTURE_v3.md`:
- `faturamento` → reset automático a cada upload
- `anuncios` → histórico preservado (acumulado)

Regra aplicada em `backend/app/api/upload.py`, não no banco.

**Alembic é o único método**
O `init_db.py` foi removido. Qualquer nova tabela ou alteração
deve ser feita via `alembic revision --autogenerate`.

---

## 🔍 Comandos de Verificação Pós-Implantação

```bash
# Listar tabelas criadas (esperado: 10 tabelas + alembic_version)
docker exec -it financial_db_docker psql -U usuario_financial -d financial_db -c "\dt"

# Listar views (esperado: v_accounts_ativas, v_business_ativos)
docker exec -it financial_db_docker psql -U usuario_financial -d financial_db -c "\dv"

# Verificar migration aplicada
cd backend && alembic current

# Verificar histórico de migrations
cd backend && alembic history

# Verificar logs do backend (sem erros de conexão)
docker-compose logs -f backend
```
