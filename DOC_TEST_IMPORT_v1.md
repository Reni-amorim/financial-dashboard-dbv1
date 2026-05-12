# Implantação do Extractor — Opção A (Síncrono, JOIN único)

> Estado: **nada implementado**. Todo o trabalho abaixo é pendente.
> Schema externo de referência: `meli` v1 (ver `doc_dbv1.md`).
> Branch de trabalho: `testv1` no fork `financial-dashboard-test`.

---

## 1. Visão geral

Substituir o upload manual de XLSX de faturamento por uma **extração direta do
banco externo `meli`**, mantendo o pipeline atual (processamento + cache em
Parquet + cálculo de ICMS) e suportando **múltiplos accounts por usuário**.

### Fluxo final

```
[Cadastro: Company → Business → Account (com marketplace_id)]
                              ↓
[Dashboard: select de Account] + [Botão 🔄 Atualizar Dados]
                              ↓
POST /api/v1/dashboard/atualizar?account_id=X
                              ↓
extractor.py: SELECT em meli.orders JOIN account JOIN shipping JOIN billing
                              ↓
ICMS por linha + cálculo de métricas
                              ↓
Salva Parquet em data/faturamento/{user_id}/{account_id}/<uuid>.parquet
                              ↓
GET /api/v1/dashboard/?account_id=X lê o Parquet correspondente
```

### Decisões fixadas

- **Hierarquia:** `User → Company → Business → Account → (Orders no meli)`.
- **Identificador externo:** `Account.marketplace_id` (BigInteger) = seller_id no Mercado Livre.
- **`Company.user_id` será renomeado para `admin_user_id`** (alinhar com o diagrama).
- **Multi-account:** cache em `data/faturamento/{user_id}/{account_id}/<uuid>.parquet`.
- **Sem `account_id` na request:** `GET /dashboard/` retorna a **lista de accounts** para o frontend escolher.
- **Business e Account precisam de CRUD** (backend + frontend).
- **Frontend renomeado:** `frontend/pages/cadastro_empresa.py` → `cadastro_company.py`.
- **Conexão ao DB externo deve ser read-only** (usuário Postgres com `GRANT SELECT` apenas).

---

## 2. Schema externo `meli` — pontos relevantes

- Tabela de pedidos: **`orders`**.
- `orders.account_id → account.id`; `account.marketplace_id` (bigint) é o seller_id público.
- `orders.data_criacao` é **`timestamp`** (sem ambiguidade de parsing).
- Soft delete via `deleted_at IS NULL` em quase todas as tabelas.
- Views úteis: `v_accounts_ativas`, `v_business_ativos`.
- ICMS exige colunas que vêm de `shipping` (UF destino) e `billing` (doc + IE).

---

## 3. Blocos de implementação

### Bloco 0 — Setup do branch

```bash
# já com fork apontado em origin
git checkout main
git pull origin main
git checkout -b testv1
git push -u origin testv1
```

---

### Bloco 1 — Migration: renomear `Company.user_id` → `admin_user_id` + validação de role

**Editar `backend/app/models/company.py`:**
- Renomear `user_id` → `admin_user_id` na Column e no relationship `owner`.

**Editar `backend/app/models/user.py`:**
- Ajustar `owned_company`: `foreign_keys="Company.admin_user_id"`.

**Editar `backend/app/schemas/company.py`:**
- Em `CompanyOut`: `user_id: int` → `admin_user_id: int`.

**Editar `backend/app/api/company.py`:**
- Substituir todas as ocorrências de `Company.user_id` por `Company.admin_user_id`.
- Substituir `user_id=current_user.id` por `admin_user_id=current_user.id` na criação.
- Adicionar validação de role `"admin"` em `criar_company`, `atualizar_company` e `deletar_company`:
```python
if current_user.role != "admin":
    raise HTTPException(status_code=403, detail="Apenas usuários com role 'admin' podem criar uma company.")
```

---

### Bloco 1 — Migration: renomear `Company.user_id` → `admin_user_id`

**Editar `backend/app/models/company.py`:**
```python
admin_user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
```
Atualizar relacionamento `owner = relationship("User", foreign_keys=[admin_user_id], ...)`.

**Atualizar referências:**
- `backend/app/schemas/company.py` — renomear o campo no Pydantic.
- `backend/app/api/company.py` — usar `admin_user_id` nas queries.
- `backend/app/api/upload.py` — `Company.user_id` aparece em filtros, trocar.
- `backend/app/api/dashboard_*.py` — idem.
- `backend/app/models/user.py` — ajustar `relationship` `owned_company` para `foreign_keys=[Company.admin_user_id]`.

**Migration:**
```bash
docker compose exec backend python -m alembic revision --autogenerate -m "rename company.user_id to admin_user_id"
docker compose exec backend python -m alembic upgrade head
```

---

### Bloco 2 — CRUD de Business (backend)

**Criar `backend/app/schemas/business.py`:**
```python
from pydantic import BaseModel
from typing import Optional

class BusinessBase(BaseModel):
    name: str
    document: Optional[str] = None

class BusinessCreate(BusinessBase):
    pass

class BusinessUpdate(BaseModel):
    name: Optional[str] = None
    document: Optional[str] = None

class BusinessOut(BusinessBase):
    id: int
    company_id: int
    class Config:
        from_attributes = True
```

**Criar `backend/app/api/business.py`** (espelhar `company.py`):
- `POST   /api/v1/business`           — cria; `company_id` resolvido pelo usuário logado.
- `GET    /api/v1/business`           — lista os businesses da company do usuário.
- `GET    /api/v1/business/{id}`      — retorna 1, validando pertencimento.
- `PUT    /api/v1/business/{id}`      — atualiza.
- `DELETE /api/v1/business/{id}`      — soft delete (set `deleted_at = now()`).

Filtrar sempre por `deleted_at IS NULL` e validar `business.company_id == company_do_usuario.id`.

**Registrar em `backend/app/main.py`:**
```python
from app.api import business
app.include_router(business.router)
```

---

### Bloco 3 — CRUD de Account (backend)

**Criar `backend/app/schemas/account.py`:**
```python
class AccountBase(BaseModel):
    business_id: int
    name: Optional[str] = None
    marketplace_id: Optional[int] = None
    status: Optional[str] = "active"

class AccountCreate(AccountBase): ...
class AccountUpdate(BaseModel):
    name: Optional[str] = None
    marketplace_id: Optional[int] = None
    status: Optional[str] = None

class AccountOut(AccountBase):
    id: int
    class Config:
        from_attributes = True
```

**Criar `backend/app/api/account.py`:**
- `POST   /api/v1/account`                — cria; valida que `business_id` pertence à company do usuário.
- `GET    /api/v1/account`                — lista (filtros opcionais `business_id`).
- `GET    /api/v1/account/{id}`           — retorna 1.
- `PUT    /api/v1/account/{id}`           — atualiza.
- `DELETE /api/v1/account/{id}`           — soft delete.

**Registrar em `main.py`** (mesmo padrão).

---

### Bloco 4 — Engine do DB externo

**`.env`:**
```env
EXTERNAL_DB_URL=postgresql://meli_readonly:senha@host:5432/meli
```

**Criar `backend/app/db/external_database.py`:**
```python
import os
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

_engine: Engine | None = None

def get_external_engine() -> Engine:
    global _engine
    if _engine is None:
        url = os.getenv("EXTERNAL_DB_URL")
        if not url:
            raise RuntimeError("EXTERNAL_DB_URL não configurada")
        _engine = create_engine(url, pool_pre_ping=True, pool_size=2, max_overflow=2)
    return _engine

def test_external_connection() -> bool:
    with get_external_engine().connect() as c:
        c.execute(text("SELECT 1"))
    return True
```

---

### Bloco 5 — Serviço extractor

**Criar `backend/app/services/faturamento_extractor.py`:**

```python
import uuid
from pathlib import Path
import pandas as pd
from sqlalchemy import text

from app.db.external_database import get_external_engine
from app.services.xlsx_processor import _calcular_icms_linha
from app.services.financial_calculator import calcular_metricas

SQL = """
SELECT
  o.external_order_id           AS "N.º de venda",
  o.data_criacao                AS "Data da venda",
  o.status                      AS "Estado",
  o.receita_produtos            AS "Receita por produtos (BRL)",
  o.acrescimo_parcelamento      AS "Receita por acréscimo no preço (pago pelo comprador)",
  COALESCE(o.parcelas,0) * COALESCE(o.valor_parcela,0)
                                AS "Taxa de parcelamento equivalente ao acréscimo",
  o.tarifa_venda                AS "Tarifa de venda e impostos (BRL)",
  o.receita_envio               AS "Receita por envio (BRL)",
  o.tarifa_envio                AS "Tarifas de envio (BRL)",
  o.custo_envio_declarado       AS "Custo de envio com base nas medidas e peso declarados",
  o.custo_diferenca_peso        AS "Custo por diferenças nas medidas e no peso do pacote",
  o.total_refund                AS "Cancelamentos e reembolsos (BRL)",
  o.valor                       AS "Total (BRL)",
  o.rebate_meli                 AS "rebate_meli",
  s.estado                      AS "Estado.1",
  COALESCE(b.doc_tipo,'') || ' ' || COALESCE(b.doc_numero,'')
                                AS "Tipo e número do documento",
  CASE WHEN b.ie IS NULL OR b.ie = '' THEN 'Não contribuinte'
       ELSE 'Contribuinte' END  AS "Tipo de contribuinte"
FROM orders o
JOIN account  a ON a.id = o.account_id
LEFT JOIN shipping s ON s.order_id = o.id
LEFT JOIN billing  b ON b.order_id = o.id
WHERE a.marketplace_id = :marketplace_id
  AND o.deleted_at IS NULL
  AND a.deleted_at IS NULL;
"""

def extract_and_cache(
    user_id: int,
    account_id: int,
    marketplace_id: int,
    estado_origem: str,
) -> dict:
    engine = get_external_engine()
    with engine.connect() as conn:
        df = pd.read_sql(text(SQL), conn, params={"marketplace_id": marketplace_id})

    if df.empty:
        raise ValueError(f"Nenhum pedido encontrado para marketplace_id={marketplace_id}")

    # ICMS por linha
    icms_df = df.apply(lambda r: _calcular_icms_linha(r, estado_origem), axis=1)
    df = pd.concat([df, icms_df], axis=1)

    # Cache por account
    out_dir = Path("data/faturamento") / str(user_id) / str(account_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("*.parquet"):
        old.unlink()
    parquet_path = out_dir / f"{uuid.uuid4()}.parquet"
    df.to_parquet(parquet_path, index=False)

    return {
        "rows": int(len(df)),
        "parquet_path": str(parquet_path),
        "summary": calcular_metricas(df),
        "account_id": account_id,
    }
```

---

### Bloco 6 — Endpoints do dashboard

**Editar `backend/app/api/dashboard_faturamento.py`:**

```python
from app.models.company import Company
from app.models.business import Business
from app.models.account import Account
from app.services.faturamento_extractor import extract_and_cache

def _user_accounts(db, user_id: int):
    return (
        db.query(Account)
        .join(Business, Business.id == Account.business_id)
        .join(Company,  Company.id  == Business.company_id)
        .filter(
            Company.admin_user_id == user_id,
            Account.deleted_at.is_(None),
            Business.deleted_at.is_(None),
            Company.deleted_at.is_(None),
        )
        .all()
    )

@router.get("/accounts")
def list_user_accounts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    accounts = _user_accounts(db, current_user.id)
    return [
        {"id": a.id, "name": a.name, "marketplace_id": a.marketplace_id, "business_id": a.business_id}
        for a in accounts
    ]

@router.post("/atualizar")
def atualizar_faturamento(
    account_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    company = db.query(Company).filter(Company.admin_user_id == current_user.id).first()
    if not company or not company.state_origin:
        raise HTTPException(400, "Cadastre uma company com state_origin.")

    account = next((a for a in _user_accounts(db, current_user.id) if a.id == account_id), None)
    if not account or not account.marketplace_id:
        raise HTTPException(400, "Account inválido ou sem marketplace_id.")

    return extract_and_cache(
        user_id=current_user.id,
        account_id=account.id,
        marketplace_id=account.marketplace_id,
        estado_origem=company.state_origin,
    )
```

**Adaptar `GET /api/v1/dashboard/`:**
- Aceita `account_id` (query param).
- Sem `account_id`: retorna `{"accounts": [...]}` (mesmo payload do `/accounts`) + `message: "Selecione um account"`.
- Com `account_id`: lê `data/faturamento/{user_id}/{account_id}/*.parquet` mais recente; se vazio, retorna `message: "Clique em Atualizar Dados"`.

---

### Bloco 7 — Frontend

**Renomear:** `frontend/pages/cadastro_empresa.py` → `frontend/pages/cadastro_company.py`. Atualizar imports/links em `frontend/app.py`.

**`cadastro_company.py`** (estrutura sugerida, 3 abas Streamlit):
- **Aba Company** — form atual (name, document, state_origin, regime_tributario).
- **Aba Business** — lista businesses da company; form para criar/editar.
- **Aba Account** — lista accounts; form com `business_id` (selectbox), `name`, `marketplace_id`.

**`dashboard_faturamento.py`:**
1. `accounts = GET /api/v1/dashboard/accounts`.
2. `selected = st.selectbox("Account", accounts, format_func=lambda a: f"{a['name']} (seller {a['marketplace_id']})")`.
3. `st.button("🔄 Atualizar Dados")`:
   - `with st.spinner("Buscando dados do Mercado Livre..."): POST /atualizar?account_id={selected['id']}`.
   - Em sucesso, `st.rerun()`.
   - Em erro, `st.error(detail)`.
4. Carregar dashboard com `GET /api/v1/dashboard/?account_id={selected['id']}`.

---

### Bloco 8 — Testes manuais

1. `docker compose up -d` e aplicar migrations.
2. Configurar `EXTERNAL_DB_URL` com usuário read-only.
3. Cadastrar **Company** (com `state_origin`).
4. Cadastrar **Business** sob a company.
5. Cadastrar **Account** com `marketplace_id` real do Mercado Livre.
6. Dashboard → selecionar Account → **🔄 Atualizar Dados**.
7. Validar:
   - Arquivo em `data/faturamento/{user_id}/{account_id}/`.
   - Métricas batem com o esperado.
   - Comparar 1-2 pedidos manualmente entre `meli.orders` e o dashboard.
8. Repetir com um segundo Account para validar isolamento por pasta.

---

## 4. Mapeamento de colunas (`meli.orders` + JOINs → `xlsx_processor`)

| Origem                                            | Coluna `xlsx_processor`                                          |
|---------------------------------------------------|------------------------------------------------------------------|
| `orders.external_order_id`                        | `N.º de venda`                                                   |
| `orders.data_criacao`                             | `Data da venda`                                                  |
| `orders.status`                                   | `Estado`                                                         |
| `orders.receita_produtos`                         | `Receita por produtos (BRL)`                                     |
| `orders.acrescimo_parcelamento`                   | `Receita por acréscimo no preço (pago pelo comprador)`           |
| `orders.parcelas * orders.valor_parcela` *(calc)* | `Taxa de parcelamento equivalente ao acréscimo`                  |
| `orders.tarifa_venda`                             | `Tarifa de venda e impostos (BRL)`                               |
| `orders.receita_envio`                            | `Receita por envio (BRL)`                                        |
| `orders.tarifa_envio`                             | `Tarifas de envio (BRL)`                                         |
| `orders.custo_envio_declarado`                    | `Custo de envio com base nas medidas e peso declarados`          |
| `orders.custo_diferenca_peso`                     | `Custo por diferenças nas medidas e no peso do pacote`           |
| `orders.total_refund`                             | `Cancelamentos e reembolsos (BRL)`                               |
| `orders.valor`                                    | `Total (BRL)`                                                    |
| `orders.rebate_meli`                              | `rebate_meli` *(não usado ainda)*                                |
| `shipping.estado`                                 | `Estado.1` *(UF destino, para ICMS)*                             |
| `billing.doc_tipo` + `billing.doc_numero`         | `Tipo e número do documento`                                     |
| `billing.ie` (preenchido?)                        | `Tipo de contribuinte`                                           |

---

## 5. Pontos de atenção

- **Conexão read-only:** crie um role Postgres com `GRANT CONNECT, USAGE, SELECT` apenas no schema `meli` e use ele em `EXTERNAL_DB_URL`.
- **`Tipo de contribuinte`:** estamos inferindo `Contribuinte` quando `billing.ie` existe. Confirmar regra com a equipe.
- **`shipping` ausente:** se não houver shipping para um pedido, `Estado.1` vem `NULL` e o ICMS dessa linha cai para 0 (já tratado em `_calcular_icms_linha`).
- **Volume grande:** se uma extração demorar mais de 30s, considerar migrar para job assíncrono (Opção C do refactor original) e sincronização incremental por `updated_at` (Opção D).
- **Renomear `user_id`:** garantir que todos os endpoints sejam atualizados antes de aplicar a migration, senão a API quebra.

---

## 6. Contexto de dados (resumo)

```
financial_db.users.user_id
       └── financial_db.company.admin_user_id
                  └── financial_db.business.company_id
                             └── financial_db.account.business_id
                                        └── financial_db.account.marketplace_id ─┐
                                                                                  │
                              (read-only)                                         ▼
                                                                meli.account.marketplace_id
                                                                       └── meli.orders.account_id
                                                                                 ├── meli.shipping (LEFT)
                                                                                 └── meli.billing  (LEFT)
```

---

## 7. Checklist resumido

- [ ] Bloco 0 — Branch `testv1` criado no fork.
- [ ] Bloco 1 — Migration `user_id → admin_user_id` em `Company`.
- [ ] Bloco 2 — Schemas + API CRUD de **Business**.
- [ ] Bloco 3 — Schemas + API CRUD de **Account**.
- [ ] Bloco 4 — `.env` + `external_database.py`.
- [ ] Bloco 5 — `faturamento_extractor.py` com `extract_and_cache(...)`.
- [ ] Bloco 6 — `POST /dashboard/atualizar`, `GET /dashboard/accounts`, `GET /dashboard/?account_id=`.
- [ ] Bloco 7 — `cadastro_company.py` (renomeado, 3 abas) + selectbox/botão no dashboard.
- [ ] Bloco 8 — Testes manuais ponta-a-ponta com 2 accounts.