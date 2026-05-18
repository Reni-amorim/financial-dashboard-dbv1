# Documentação do Banco de Dados — `meli` (v1)

## Informações Gerais

| Campo               | Valor          |
|---------------------|----------------|
| Database            | `meli`         |
| Usuário             | `usuario_meli` |
| Versão do schema    | v1             |
| SGBD                | PostgreSQL     |

## Sumário de Objetos

| Tipo  | Nome                  |
|-------|-----------------------|
| Table | `account`             |
| Table | `account_address`     |
| Table | `billing`             |
| Table | `business`            |
| Table | `company`             |
| Table | `items_order`         |
| Table | `orders`              |
| Table | `product`             |
| Table | `shipping`            |
| View  | `v_accounts_ativas`   |
| View  | `v_business_ativos`   |

**Total:** 9 tabelas + 2 views = 11 objetos.

## Modelo de Relacionamentos

```
company (1) ──< business (N) ──< account (N) ──< account_address (N)
                                       │
                                       └──< orders (N) ──< items_order (N)
                                                  │
                                                  ├──< billing (1)
                                                  └──< shipping (1)

product ──> company  (N para 1, sem ligação direta com orders neste schema)
```

### Mapa de Foreign Keys

| Tabela origem      | Coluna        | Tabela referenciada | Coluna |
|--------------------|---------------|---------------------|--------|
| `account`          | `business_id` | `business`          | `id`   |
| `account_address`  | `account_id`  | `account`           | `id`   |
| `billing`          | `order_id`    | `orders`            | `id`   |
| `business`         | `company_id`  | `company`           | `id`   |
| `items_order`      | `order_id`    | `orders`            | `id`   |
| `orders`           | `account_id`  | `account`           | `id`   |
| `product`          | `company_id`  | `company`           | `id`   |
| `shipping`         | `order_id`    | `orders`            | `id`   |

> Observação: as FKs de `business.company_id` e `product.company_id` aparecem nas constraints sem a tabela referenciada explicitada na consulta original — pelo nome da coluna apontam para `company.id`.

## Tabelas

### `company`

Empresa (entidade jurídica raiz). Uma `company` pode ter várias `business`.

| Coluna        | Tipo                          | Nulo | Default                | Observações |
|---------------|-------------------------------|------|------------------------|-------------|
| `id`          | integer                       | NO   | nextval(seq)           | **PK**      |
| `name`        | varchar(255)                  | NO   |                        |             |
| `document`    | varchar(20)                   | YES  |                        | CNPJ/CPF    |
| `deleted_at`  | timestamp                     | YES  |                        | soft delete |
| `created_at`  | timestamp                     | YES  | CURRENT_TIMESTAMP      |             |
| `updated_at`  | timestamp                     | YES  | CURRENT_TIMESTAMP      |             |
| `created_by`  | varchar(100)                  | YES  |                        |             |
| `updated_by`  | varchar(100)                  | YES  |                        |             |

---

### `business`

Unidade de negócio vinculada a uma `company`.

| Coluna        | Tipo          | Nulo | Default            | Observações                                          |
|---------------|---------------|------|--------------------|------------------------------------------------------|
| `id`          | integer       | NO   | nextval(seq)       | **PK**                                               |
| `name`        | varchar(255)  | NO   |                    |                                                      |
| `document`    | varchar(20)   | YES  |                    |                                                      |
| `company_id`  | integer       | NO   |                    | **FK** → `company.id`                                |
| `deleted_at`  | timestamp     | YES  |                    | Data de exclusão lógica do registro (NULL = ativo)   |
| `created_at`  | timestamp     | YES  | CURRENT_TIMESTAMP  | Data de criação do registro                          |
| `updated_at`  | timestamp     | YES  | CURRENT_TIMESTAMP  | Data da última atualização do registro               |
| `created_by`  | varchar(100)  | YES  |                    | Usuário que criou o registro                         |
| `updated_by`  | varchar(100)  | YES  |                    | Usuário que fez a última atualização                 |

---

### `account`

Conta de marketplace (ex.: Mercado Livre) ligada a uma `business`.

| Coluna            | Tipo                 | Nulo | Default                  | Observações                                          |
|-------------------|----------------------|------|--------------------------|------------------------------------------------------|
| `id`              | integer              | NO   | nextval(seq)             | **PK**                                               |
| `business_id`     | integer              | YES  |                          | **FK** → `business.id`                               |
| `marketplace_id`  | bigint               | YES  |                          | ID da conta no marketplace externo                   |
| `access_token`    | text                 | YES  |                          | Token OAuth                                          |
| `refresh_token`   | text                 | YES  |                          | Token OAuth de refresh                               |
| `name`            | varchar(255)         | YES  |                          |                                                      |
| `status`          | varchar              | YES  | `'active'`               |                                                      |
| `deleted_at`      | timestamp            | YES  |                          | Data de exclusão lógica do registro (NULL = ativo)   |
| `created_at`      | timestamp            | YES  | CURRENT_TIMESTAMP        | Data de criação do registro                          |
| `updated_at`      | timestamp            | YES  | now()                    |                                                      |
| `created_by`      | varchar(100)         | YES  |                          |                                                      |
| `updated_by`      | varchar(100)         | YES  |                          | Usuário que fez a última atualização                 |

---

### `account_address`

Endereços vinculados a uma `account` (relacionamento 1:N).

| Coluna         | Tipo                       | Nulo | Default       | Observações              |
|----------------|----------------------------|------|---------------|--------------------------|
| `id`           | integer                    | NO   | nextval(seq)  | **PK**                   |
| `account_id`   | integer                    | NO   |               | **FK** → `account.id`    |
| `tipo`         | text                       | YES  |               |                          |
| `logradouro`   | text                       | NO   |               |                          |
| `numero`       | text                       | NO   |               |                          |
| `complemento`  | text                       | YES  |               |                          |
| `bairro`       | text                       | YES  |               |                          |
| `cidade`       | text                       | NO   |               |                          |
| `estado`       | char(2)                    | NO   |               | UF                       |
| `cep`          | text                       | YES  |               |                          |
| `principal`    | boolean                    | YES  | `false`       | Endereço padrão da conta |
| `created_at`   | timestamp with time zone   | YES  | now()         |                          |

---

### `orders`

Pedidos importados do marketplace, ligados a uma `account`.

| Coluna                   | Tipo           | Nulo | Default            | Observações                                          |
|--------------------------|----------------|------|--------------------|------------------------------------------------------|
| `id`                     | integer        | NO   | nextval(seq)       | **PK**                                               |
| `external_order_id`      | varchar(50)    | NO   |                    | ID do pedido no marketplace                          |
| `account_id`             | integer        | NO   |                    | **FK** → `account.id`                                |
| `status`                 | text           | YES  |                    |                                                      |
| `valor`                  | numeric        | YES  |                    | Valor total do pedido                                |
| `pago`                   | numeric        | YES  |                    | Valor efetivamente pago                              |
| `data_criacao`           | timestamp      | YES  |                    | Data do pedido na origem                             |
| `parcelas`               | integer        | YES  |                    |                                                      |
| `valor_parcela`          | numeric        | YES  |                    |                                                      |
| `acrescimo_parcelamento` | numeric        | YES  |                    |                                                      |
| `tarifa_venda`           | numeric        | YES  |                    | Taxa cobrada pelo marketplace                        |
| `receita_produtos`       | numeric        | YES  |                    |                                                      |
| `receita_envio`          | numeric        | YES  |                    |                                                      |
| `tarifa_envio`           | numeric        | YES  |                    |                                                      |
| `custo_envio_declarado`  | numeric        | YES  | `0`                |                                                      |
| `custo_diferenca_peso`   | numeric        | YES  | `0`                |                                                      |
| `rebate_meli`            | numeric        | YES  |                    | Subsídio/rebate do Mercado Livre                     |
| `total_refund`           | numeric        | YES  |                    | Total reembolsado                                    |
| `deleted_at`             | timestamp      | YES  |                    | Data de exclusão lógica do registro (NULL = ativo)   |
| `updated_at`             | timestamp      | YES  | CURRENT_TIMESTAMP  | Data da última atualização do registro               |
| `created_by`             | varchar(100)   | YES  |                    | Usuário que criou o registro                         |
| `updated_by`             | varchar(100)   | YES  |                    | Usuário que fez a última atualização                 |

> Observação: a tabela `orders` no schema atual **não possui** coluna `created_at`.

---

### `items_order`

Itens (linhas) de cada pedido.

| Coluna              | Tipo           | Nulo | Default            | Observações                                          |
|---------------------|----------------|------|--------------------|------------------------------------------------------|
| `id`                | integer        | NO   | nextval(seq)       | **PK**                                               |
| `order_id`          | integer        | NO   |                    | **FK** → `orders.id`                                 |
| `external_item_id`  | varchar(50)    | NO   |                    | ID do item no marketplace                            |
| `titulo`            | varchar(255)   | NO   |                    |                                                      |
| `sku`               | text           | YES  |                    |                                                      |
| `quantidade`        | integer        | NO   |                    |                                                      |
| `preco_unitario`    | numeric        | NO   |                    |                                                      |
| `deleted_at`        | timestamp      | YES  |                    | Data de exclusão lógica do registro (NULL = ativo)   |
| `created_at`        | timestamp      | YES  | CURRENT_TIMESTAMP  | Data de criação do registro                          |
| `updated_at`        | timestamp      | YES  | CURRENT_TIMESTAMP  | Data da última atualização do registro               |
| `created_by`        | varchar(100)   | YES  |                    | Usuário que criou o registro                         |
| `updated_by`        | varchar(100)   | YES  |                    | Usuário que fez a última atualização                 |

---

### `billing`

Dados fiscais/cobrança do pedido (1:1 com `orders`).

| Coluna         | Tipo    | Nulo | Default       | Observações            |
|----------------|---------|------|---------------|------------------------|
| `id`           | bigint  | NO   | nextval(seq)  | **PK**                 |
| `order_id`     | bigint  | YES  |               | **FK** → `orders.id`   |
| `doc_tipo`     | text    | YES  |               | CPF / CNPJ             |
| `doc_numero`   | text    | YES  |               |                        |
| `razao_social` | text    | YES  |               |                        |
| `ie`           | text    | YES  |               | Inscrição Estadual     |
| `cep`          | text    | YES  |               |                        |
| `logradouro`   | text    | YES  |               |                        |
| `numero`       | text    | YES  |               |                        |
| `complemento`  | text    | YES  |               |                        |
| `bairro`       | text    | YES  |               |                        |
| `cidade`       | text    | YES  |               |                        |
| `estado`       | text    | YES  |               |                        |

---

### `shipping`

Dados de envio do pedido (1:1 com `orders`).

| Coluna           | Tipo    | Nulo | Observações            |
|------------------|---------|------|------------------------|
| `id`             | bigint  | NO   | **PK** (sem default)   |
| `order_id`       | bigint  | YES  | **FK** → `orders.id`   |
| `receiver_name`  | text    | YES  |                        |
| `cep`            | text    | YES  |                        |
| `logradouro`     | text    | YES  |                        |
| `numero`         | text    | YES  |                        |
| `complemento`    | text    | YES  |                        |
| `bairro`         | text    | YES  |                        |
| `cidade`         | text    | YES  |                        |
| `estado`         | text    | YES  |                        |

> Atenção: `shipping.id` é PK mas **não possui sequência/default** — o ID precisa ser fornecido pela aplicação na inserção (provavelmente espelha o `id` vindo do marketplace).

---

### `product`

Catálogo de produtos da `company`.

| Coluna        | Tipo           | Nulo | Default            | Observações            |
|---------------|----------------|------|--------------------|------------------------|
| `id`          | integer        | NO   | nextval(seq)       | **PK**                 |
| `company_id`  | integer        | NO   |                    | **FK** → `company.id`  |
| `sku`         | varchar(100)   | NO   |                    |                        |
| `name`        | varchar(255)   | NO   |                    |                        |
| `ncm`         | varchar(20)    | YES  |                    | Classificação fiscal   |
| `cost_price`  | numeric        | YES  |                    | Preço de custo         |
| `created_at`  | timestamp      | YES  | CURRENT_TIMESTAMP  |                        |
| `updated_at`  | timestamp      | YES  | CURRENT_TIMESTAMP  |                        |

> Observação: `product` **não possui** colunas de auditoria (`deleted_at`, `created_by`, `updated_by`) nem ligação direta com `items_order`. O vínculo entre item de pedido e produto é feito via `sku` (campo textual em ambas).

## Views

### `v_accounts_ativas`

Espelha `account` filtrando contas ativas (provavelmente `deleted_at IS NULL` e/ou `status = 'active'`). Mesmas colunas de `account`.

### `v_business_ativos`

Espelha `business` filtrando registros ativos (`deleted_at IS NULL`). Mesmas colunas de `business`.

## Padrões e Convenções

### Soft delete
Todas as tabelas de domínio principais (`account`, `business`, `orders`, `items_order`) usam `deleted_at` para exclusão lógica. **Convenção:** `deleted_at IS NULL` significa registro ativo.

### Auditoria
O quarteto padrão de auditoria é `created_at` / `updated_at` / `created_by` / `updated_by`. Nem todas as tabelas implementam o conjunto completo:

| Tabela          | created_at | updated_at | created_by | updated_by | deleted_at |
|-----------------|:----------:|:----------:|:----------:|:----------:|:----------:|
| `company`       | ✅ | ✅ | ✅ | ✅ | ✅ |
| `business`      | ✅ | ✅ | ✅ | ✅ | ✅ |
| `account`       | ✅ | ✅ | ✅ | ✅ | ✅ |
| `account_address` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `orders`        | ❌ | ✅ | ✅ | ✅ | ✅ |
| `items_order`   | ✅ | ✅ | ✅ | ✅ | ✅ |
| `billing`       | ❌ | ❌ | ❌ | ❌ | ❌ |
| `shipping`      | ❌ | ❌ | ❌ | ❌ | ❌ |
| `product`       | ✅ | ✅ | ❌ | ❌ | ❌ |



---

## Conexão usada na implantação (Bloco 4 do `DOC_TEST_IMPORT_v1.md`)

Sessão de configuração do extractor (financial-dashboard-dbv1 ↔ banco externo `meli`).

### Infraestrutura

| Item                          | Valor                                       |
|-------------------------------|---------------------------------------------|
| Host (servidor)               | `ubuntu-s-1vcpu-1gb-sfo3-01` (DigitalOcean) |
| Projeto Docker (banco)        | `~/projeto-meli` (usuário `evandro`)        |
| Projeto Docker (app)          | `~/financial-dashboard-dbv1` (usuário `reni`) |
| Service Postgres no compose   | `postgres`                                  |
| Container Postgres            | `postgres_db`                               |
| Imagem                        | `postgres:16`                               |
| Porta interna                 | `5432` (não publicada no host)              |
| Docker network compartilhada  | `projeto-meli_app_rede` (driver `bridge`)   |
| Alias da network no app       | `meli_external` (`external: true`)          |

### Banco e roles

| Role            | Função                              | Privilégios                                         |
|-----------------|-------------------------------------|-----------------------------------------------------|
| `usuario_n8n`   | Superuser da instância (`POSTGRES_USER`) | Todos (criar roles, criar bancos, etc.)        |
| `usuario_meli`  | Owner do banco `meli`               | Owner de `ads`, `auditoria`; sem `CREATEROLE`        |
| `meli_readonly` | Conta usada pelo backend (read-only) | `CONNECT` em `meli`; `USAGE`+`SELECT` em `public`   |

> **Senha de teste atual de `meli_readonly`: `123`.** Trocar antes de uso real com:
> ```sql
> ALTER ROLE meli_readonly WITH PASSWORD '<senha_forte>';
> ```

### Schemas e tabelas relevantes

| Schema      | Owner               | Conteúdo
|
|-------------|---------------------|-----------------------------------------------------------------------------------|
| `public`    | `pg_database_owner` | Tabelas do extractor: `orders`, `account`, `shipping`, `billing`; views `v_accounts_ativas`, `v_business_ativos` |
| `ads`       | `usuario_meli`      | (não usado no Bloco 5 — provavelmente anúncios) |
| `auditoria` | `usuario_meli`      | View `v_alteracoes_recentes`(log)                                                                              |

> **Atenção:** o `DOC_TEST_IMPORT_v1.md` antigo assumia schema `meli`. Na v1 real, as tabelas estão em **`public`**. A SQL do extractor continua funcionando sem prefixo porque `public` é o schema default no `search_path`.

### Comandos SQL aplicados (criação do role)

Conectado como `usuario_n8n` em `meli`:

```sql
CREATE ROLE meli_readonly LOGIN PASSWORD '123';

GRANT CONNECT ON DATABASE meli   TO meli_readonly;
GRANT USAGE   ON SCHEMA   public TO meli_readonly;
GRANT SELECT  ON ALL TABLES IN SCHEMA public TO meli_readonly;

ALTER DEFAULT PRIVILEGES FOR ROLE usuario_meli IN SCHEMA public
  GRANT SELECT ON TABLES TO meli_readonly;
```

### Connection string

```env
EXTERNAL_DB_URL=postgresql://meli_readonly:123@postgres_db:5432/meli
```

> Host = `postgres_db` (resolvido por DNS interno do Docker dentro da network `projeto-meli_app_rede`).

### Ajuste no `docker-compose.prod.yml` (financial-dashboard-dbv1)

```yaml
services:
  backend:
    networks:
      - financial_network
      - meli_external

networks:
  financial_network:
    driver: bridge
  meli_external:
    external: true
    name: projeto-meli_app_rede
```

### Validação

```bash
# DNS interno
docker exec financial-dashboard-dbv1-backend-1 sh -c "getent hosts postgres_db"
# 172.18.0.2  postgres_db

# Conexão SQLAlchemy
docker compose -f docker-compose.prod.yml exec backend python -c \
  "from app.db.external_database import test_external_connection; print('OK' if test_external_connection() else 'FAIL')"
# OK

# Endpoint HTTP
docker compose -f docker-compose.prod.yml exec backend sh -c "curl -s http://localhost:8000/health/external-db"
# {"status":"healthy","db":"meli"}

# Leitura real
docker exec -it postgres_db psql -U meli_readonly -d meli -c "SELECT count(*) FROM public.orders;"
# count = 14
```

### Defaults
- IDs usam `nextval('<tabela>_id_seq')` exceto `shipping.id`.
- Timestamps usam `CURRENT_TIMESTAMP` ou `now()` (sem padronização única).
- `account.status` default `'active'`.
- `account_address.principal` default `false`.

## Observações e Possíveis Melhorias

1. **`shipping.id` sem sequência** — pode causar erros de inserção se a aplicação não fornecer o valor.
2. **`orders` sem `created_at`** — quebra o padrão das demais tabelas; considerar adicionar.
3. **`billing` e `shipping` sem auditoria** — sem `created_at`, `updated_at`, `deleted_at`.
4. **`product` sem `deleted_at`** — não permite soft delete; produtos só podem ser removidos fisicamente.
5. **`business.company_id` e `product.company_id`** — FKs aparecem nas constraints sem a tabela referenciada explicitada; vale validar se a constraint está realmente criada no banco.
6. **Mistura `now()` vs `CURRENT_TIMESTAMP`** nos defaults — equivalentes funcionalmente, mas vale padronizar.
7. **Tipos heterogêneos para mesma semântica** — IDs ora `integer` ora `bigint` (`shipping.id`, `billing.id`); endereços ora `text` ora `varchar`.
8. **Sem ligação formal `items_order` → `product`** — a junção depende do `sku` textual, sem FK garantindo integridade.
