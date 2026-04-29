# 📦 Documentação do Banco de Dados — `meli` (v3)

> **Banco:** meli
> **Usuário:** usuario_meli
> **Tecnologia:** PostgreSQL 16 (via Docker)
> **Servidor:** VM Digital Ocean (Ubuntu)
> **Atualizado em:** 2026

---

## 🔌 Conexão

| Parâmetro | Valor |
|-----------|-------|
| **Host** | IP da VM (Docker interno: `localhost`) |
| **Porta** | `5432` |
| **Database** | `meli` |
| **Usuário** | `usuario_meli` |
| **Container** | `postgres_db` |

**String de conexão:**
```
postgresql://usuario_meli:****@localhost:5432/meli
```

**Acesso via Docker:**
```bash
docker exec -it postgres_db psql -U usuario_meli -d meli
```

---

## 📐 Visão Geral do Schema

O banco possui **10 tabelas** e **2 views**:

| Objeto | Tipo | Descrição |
|--------|------|-----------|
| `user` | tabela | Usuários do sistema — admin (dono), market e fiscal |
| `company` | tabela | Empresa cadastrada pelo admin, vinculada ao user dono |
| `business` | tabela | Vendedores/sellers vinculados a uma empresa |
| `account` | tabela | Contas do Mercado Livre vinculadas a um business |
| `account_address` | tabela | Endereços das contas |
| `orders` | tabela | Pedidos de venda sincronizados do ML |
| `items_order` | tabela | Itens dos pedidos |
| `shipping` | tabela | Dados de entrega/logística dos pedidos |
| `billing` | tabela | Dados fiscais dos pedidos |
| `product` | tabela | Cadastro de produtos |
| `v_accounts_ativas` | view | Contas com `status = 'active'` e `deleted_at IS NULL` |
| `v_business_ativos` | view | Businesses com `deleted_at IS NULL` |

### Mudanças em relação à v2

| O que mudou | v2 | v3 |
|---|---|---|
| Tabela `user` | não existia | nova — pai da `company` |
| Tabela `company` | não existia | nova — filha de `user`, pai de `business` |
| `business.company_id` | FK externa | FK → `company.id` |
| `faturamento_meli` | existia | renomeada → `billing` |
| `billing` | tinha `pedido_id` como PK | agora tem `id` bigint próprio + `order_id` FK |
| `billing` | não tinha `numero`, `complemento`, `bairro` | colunas adicionadas |
| `entregas_meli` | existia | renomeada → `shipping` |
| `shipping` | tinha `pedido_id` como PK, `shipping_id` | agora tem `id` bigint próprio + `order_id` FK; sem `shipping_id` |
| `orders` | tinha `id_pedido` bigint | agora tem `id` integer (PK interna) + `external_order_id` varchar(50) |
| Views | não existiam | `v_accounts_ativas`, `v_business_ativos` |

---

## 🗂️ Tabelas

---

### `user`
Nível raiz do sistema. Criado no momento do pagamento. O user com `role = admin` é o dono e é quem cadastra a company. Os demais users (market, fiscal) são criados pelo admin dentro do sistema, todos na mesma tabela.

| Coluna | Tipo | Nulo | Default | Descrição |
|--------|------|------|---------|-----------|
| `id` | `integer` | NOT NULL | auto-increment | **PK** — Identificador único |
| `company_id` | `integer` | YES | `NULL` | **FK → company.id** — NULL até o admin cadastrar a empresa |
| `name` | `varchar(255)` | NOT NULL | — | Nome completo do usuário |
| `email` | `varchar(255)` | NOT NULL | — | E-mail (usado no login) — UNIQUE |
| `password_hash` | `text` | NOT NULL | — | Senha criptografada |
| `role` | `varchar(50)` | NOT NULL | `'admin'` | Perfil de acesso: `admin`, `market` ou `fiscal` |
| `created_at` | `timestamp` | YES | `CURRENT_TIMESTAMP` | Data de criação |
| `updated_at` | `timestamp` | YES | `CURRENT_TIMESTAMP` | Data de atualização |
| `deleted_at` | `timestamp` | YES | — | Exclusão lógica (NULL = ativo) |

**Roles disponíveis:**

| Role | Criado por | Acesso |
|------|-----------|--------|
| `admin` | Sistema (no pagamento) | Tudo |
| `market` | Admin | Dashboard de anúncios e campanhas |
| `fiscal` | Admin | Dashboard analítico e billing |

**Impacto na deleção:**

| User deletado | Impacto |
|--------------|---------|
| `admin` (dono) | Deleta a `company` → cascade em todo o banco |
| `market` | Nenhum |
| `fiscal` | Nenhum |

> ⚠️ O `company_id` do admin começa como `NULL` e é preenchido após o cadastro da empresa.
> A lógica de deleção em cascade do admin é aplicada no backend.
> `email` deve ter constraint `UNIQUE`.

---

### `company`
Empresa cadastrada pelo user admin após o pagamento. Filha de `user`, pai de todo o restante do sistema.

| Coluna | Tipo | Nulo | Default | Descrição |
|--------|------|------|---------|-----------|
| `id` | `integer` | NOT NULL | auto-increment | **PK** — Identificador único |
| `user_id` | `integer` | NOT NULL | — | **FK → user.id** — user admin dono da empresa |
| `name` | `varchar(255)` | NOT NULL | — | Nome da empresa |
| `document` | `varchar(20)` | YES | — | CNPJ/CPF |
| `created_at` | `timestamp` | YES | `CURRENT_TIMESTAMP` | Data de criação ¹ |
| `updated_at` | `timestamp` | YES | `CURRENT_TIMESTAMP` | Data de atualização ¹ |
| `created_by` | `varchar(100)` | YES | — | Usuário que criou o registro ¹ |
| `updated_by` | `varchar(100)` | YES | — | Usuário que fez a última atualização ¹ |
| `deleted_at` | `timestamp` | YES | — | Exclusão lógica (NULL = ativo) ¹ |

> ¹ Campo com comentário no banco de dados.

---

### `business`
Vendedores/sellers vinculados a uma `company`.

| Coluna | Tipo | Nulo | Default | Descrição |
|--------|------|------|---------|-----------|
| `id` | `integer` | NOT NULL | auto-increment | **PK** — Identificador único |
| `company_id` | `integer` | NOT NULL | — | **FK → company.id** |
| `name` | `varchar(255)` | NOT NULL | — | Nome do vendedor/seller |
| `document` | `varchar(20)` | YES | — | CNPJ/CPF |
| `created_at` | `timestamp` | YES | `CURRENT_TIMESTAMP` | Data de criação ¹ |
| `updated_at` | `timestamp` | YES | `CURRENT_TIMESTAMP` | Data de atualização ¹ |
| `created_by` | `varchar(100)` | YES | — | Usuário que criou o registro ¹ |
| `updated_by` | `varchar(100)` | YES | — | Usuário que fez a última atualização ¹ |
| `deleted_at` | `timestamp` | YES | — | Exclusão lógica (NULL = ativo) ¹ |

> ¹ Campo com comentário no banco de dados.

---

### `account`
Contas do Mercado Livre vinculadas a um `business`.

| Coluna | Tipo | Nulo | Default | Descrição |
|--------|------|------|---------|-----------|
| `id` | `integer` | NOT NULL | auto-increment | **PK** — Identificador único |
| `business_id` | `integer` | YES | — | **FK → business.id** |
| `marketplace_id` | `bigint` | YES | — | ID da conta no Mercado Livre |
| `name` | `varchar(255)` | YES | — | Nome da conta/loja |
| `access_token` | `text` | YES | — | Token de acesso OAuth |
| `refresh_token` | `text` | YES | — | Token de renovação OAuth |
| `status` | `varchar` | YES | `'active'` | Status da conta |
| `created_at` | `timestamp` | YES | `CURRENT_TIMESTAMP` | Data de criação ¹ |
| `updated_at` | `timestamp` | YES | `now()` | Data de atualização |
| `created_by` | `varchar(100)` | YES | — | Usuário que criou o registro |
| `updated_by` | `varchar(100)` | YES | — | Usuário que fez a última atualização ¹ |
| `deleted_at` | `timestamp` | YES | — | Exclusão lógica (NULL = ativo) ¹ |

> ¹ Campo com comentário no banco de dados.

---

### `account_address`
Endereços associados às contas do Mercado Livre.

| Coluna | Tipo | Nulo | Default | Descrição |
|--------|------|------|---------|-----------|
| `id` | `integer` | NOT NULL | auto-increment | **PK** — Identificador único |
| `account_id` | `integer` | NOT NULL | — | **FK → account.id** |
| `tipo` | `text` | YES | — | Tipo do endereço (ex: comercial, residencial) |
| `logradouro` | `text` | NOT NULL | — | Rua/Avenida |
| `numero` | `text` | NOT NULL | — | Número |
| `complemento` | `text` | YES | — | Complemento |
| `bairro` | `text` | YES | — | Bairro |
| `cidade` | `text` | NOT NULL | — | Cidade |
| `estado` | `char(2)` | NOT NULL | — | UF (ex: SP, RJ) |
| `cep` | `text` | YES | — | CEP |
| `principal` | `boolean` | YES | `false` | Indica se é o endereço principal |
| `created_at` | `timestamp with tz` | YES | `now()` | Data de criação |

---

### `orders`
Pedidos de venda sincronizados do Mercado Livre.

| Coluna | Tipo | Nulo | Default | Descrição |
|--------|------|------|---------|-----------|
| `id` | `integer` | NOT NULL | auto-increment | **PK** — Identificador interno |
| `external_order_id` | `varchar(50)` | NOT NULL | — | ID do pedido no Mercado Livre |
| `account_id` | `integer` | NOT NULL | — | **FK → account.id** |
| `status` | `text` | YES | — | Status do pedido |
| `data_criacao` | `timestamp` | YES | — | Data de criação no ML |
| `valor` | `numeric` | YES | — | Valor total do pedido |
| `pago` | `numeric` | YES | — | Valor pago |
| `receita_produtos` | `numeric` | YES | — | Receita dos produtos |
| `acrescimo_parcelamento` | `numeric` | YES | — | Acréscimo por parcelamento |
| `tarifa_venda` | `numeric` | YES | — | Tarifa cobrada pelo ML |
| `parcelas` | `integer` | YES | — | Número de parcelas |
| `valor_parcela` | `numeric` | YES | — | Valor de cada parcela |
| `total_refund` | `numeric` | YES | — | Total de reembolsos |
| `rebate_meli` | `numeric` | YES | — | Rebate do Mercado Livre |
| `receita_envio` | `numeric` | YES | — | Receita de frete |
| `tarifa_envio` | `numeric` | YES | — | Tarifa de envio cobrada pelo ML |
| `custo_envio_declarado` | `numeric` | YES | `0` | Custo de envio declarado |
| `custo_diferenca_peso` | `numeric` | YES | `0` | Custo por diferença de peso |
| `updated_at` | `timestamp` | YES | `CURRENT_TIMESTAMP` | Data de atualização ¹ |
| `created_by` | `varchar(100)` | YES | — | Usuário que criou o registro ¹ |
| `updated_by` | `varchar(100)` | YES | — | Usuário que fez a última atualização ¹ |
| `deleted_at` | `timestamp` | YES | — | Exclusão lógica (NULL = ativo) ¹ |

> ⚠️ `external_order_id` é o ID do pedido no ML. O `id` é a PK interna — use-o nas FKs de `items_order`, `shipping` e `billing`.
>
> ¹ Campo com comentário no banco de dados.

---

### `items_order`
Itens (produtos) de cada pedido. Vinculados a `orders` via `order_id`.

| Coluna | Tipo | Nulo | Default | Descrição |
|--------|------|------|---------|-----------|
| `id` | `integer` | NOT NULL | auto-increment | **PK** — Identificador único |
| `order_id` | `integer` | NOT NULL | — | **FK → orders.id** |
| `external_item_id` | `varchar(50)` | NOT NULL | — | ID do item no Mercado Livre (MLB...) |
| `sku` | `text` | **YES** | — | ⚠️ SKU interno — pode ser NULL |
| `titulo` | `varchar(255)` | NOT NULL | — | Título do anúncio |
| `quantidade` | `integer` | NOT NULL | — | Quantidade vendida |
| `preco_unitario` | `numeric` | NOT NULL | — | Preço unitário |
| `created_at` | `timestamp` | YES | `CURRENT_TIMESTAMP` | Data de criação ¹ |
| `updated_at` | `timestamp` | YES | `CURRENT_TIMESTAMP` | Data de atualização ¹ |
| `created_by` | `varchar(100)` | YES | — | Usuário que criou o registro ¹ |
| `updated_by` | `varchar(100)` | YES | — | Usuário que fez a última atualização ¹ |
| `deleted_at` | `timestamp` | YES | — | Exclusão lógica (NULL = ativo) ¹ |

> ⚠️ O campo `sku` é **nullable**. Itens sem SKU não conseguem ser vinculados à tabela `product`. Use `LEFT JOIN` e trate o cenário de custo ausente.
>
> ¹ Campo com comentário no banco de dados.

---

### `shipping`
Dados de entrega/logística dos pedidos. Renomeada de `entregas_meli` (v2).

| Coluna | Tipo | Nulo | Default | Descrição |
|--------|------|------|---------|-----------|
| `id` | `bigint` | NOT NULL | — | **PK** — Identificador único |
| `order_id` | `bigint` | YES | — | **FK → orders.id** |
| `receiver_name` | `text` | YES | — | Nome do destinatário |
| `cep` | `text` | YES | — | CEP de entrega |
| `logradouro` | `text` | YES | — | Rua/Avenida |
| `numero` | `text` | YES | — | Número |
| `complemento` | `text` | YES | — | Complemento |
| `bairro` | `text` | YES | — | Bairro |
| `cidade` | `text` | YES | — | Cidade |
| `estado` | `text` | YES | — | UF |

> ⚠️ Diferente da v2: a PK agora é `id` próprio (não mais `pedido_id`). A FK para `orders` é `order_id`. O campo `shipping_id` (ID do envio no ML) foi removido.

---

### `billing`
Dados fiscais/nota fiscal dos pedidos. Renomeada de `faturamento_meli` (v2).

| Coluna | Tipo | Nulo | Default | Descrição |
|--------|------|------|---------|-----------|
| `id` | `bigint` | NOT NULL | auto-increment | **PK** — Identificador único |
| `order_id` | `bigint` | YES | — | **FK → orders.id** |
| `doc_tipo` | `text` | YES | — | Tipo do documento (CPF/CNPJ) |
| `doc_numero` | `text` | YES | — | Número do documento |
| `razao_social` | `text` | YES | — | Razão social do comprador |
| `ie` | `text` | YES | — | Inscrição estadual |
| `cep` | `text` | YES | — | CEP de faturamento |
| `logradouro` | `text` | YES | — | Rua/Avenida |
| `numero` | `text` | YES | — | Número |
| `complemento` | `text` | YES | — | Complemento |
| `bairro` | `text` | YES | — | Bairro |
| `cidade` | `text` | YES | — | Cidade |
| `estado` | `text` | YES | — | UF |

> ⚠️ Diferente da v2: a PK agora é `id` próprio com auto-increment (não mais `pedido_id`). A FK para `orders` é `order_id`. Colunas `numero`, `complemento` e `bairro` foram adicionadas.

---

### `product`
Cadastro de produtos da empresa. Vinculado a `items_order` via `sku`.

| Coluna | Tipo | Nulo | Default | Descrição |
|--------|------|------|---------|-----------|
| `id` | `integer` | NOT NULL | auto-increment | **PK** — Identificador único |
| `company_id` | `integer` | NOT NULL | — | **FK → company.id** |
| `sku` | `varchar(100)` | NOT NULL | — | SKU interno do produto |
| `name` | `varchar(255)` | NOT NULL | — | Nome do produto |
| `ncm` | `varchar(20)` | YES | — | Código NCM (classificação fiscal) |
| `cost_price` | `numeric` | YES | — | Preço de custo |
| `created_at` | `timestamp` | YES | `CURRENT_TIMESTAMP` | Data de criação |
| `updated_at` | `timestamp` | YES | `CURRENT_TIMESTAMP` | Data de atualização |

---

## 👁️ Views

### `v_accounts_ativas`
Contas ativas — equivalente a `SELECT * FROM account WHERE status = 'active' AND deleted_at IS NULL`.

Colunas idênticas à tabela `account`.

---

### `v_business_ativos`
Businesses ativos — equivalente a `SELECT * FROM business WHERE deleted_at IS NULL`.

Colunas idênticas à tabela `business`.

---

## 🔗 Diagrama de Relacionamentos

```
user (role = admin, criado no pagamento)
  └── company (user_id → user.id)
        ├── user market  (company_id → company.id, criado pelo admin)
        ├── user fiscal  (company_id → company.id, criado pelo admin)
        ├── business (company_id → company.id)
        │     └── account (business_id → business.id)
        │           ├── account_address (account_id → account.id)
        │           └── orders (account_id → account.id)  ← populado pelo n8n
        │                 ├── items_order (order_id → orders.id)
        │                 │     └── product (sku ↔ items_order.sku, company_id → company.id)
        │                 ├── shipping (order_id → orders.id)
        │                 └── billing (order_id → orders.id)
        └── product (company_id → company.id)
```

**Fluxo de criação:**
```
1. Dono faz pagamento  →  user criado (role = admin, company_id = NULL)
2. Admin cadastra company  →  company criada (user_id = admin.id)
3. user.company_id atualizado com o id da company recém-criada
4. n8n consulta ML  →  popula business, account, orders, items_order, shipping, billing
5. Admin cria users operacionais (market, fiscal) vinculados à company
6. Todos acessam o sistema conforme seu role
```

---

## ⚠️ Tratamento de SKU ausente

O campo `items_order.sku` é nullable. Itens sem SKU não se vinculam a `product` e, portanto, não têm `cost_price` disponível. Sempre use `LEFT JOIN` nessa relação:

```sql
SELECT
    io.id,
    io.titulo,
    io.quantidade,
    io.preco_unitario,
    p.cost_price,
    (io.preco_unitario - COALESCE(p.cost_price, 0)) AS margem_unitaria
FROM items_order io
LEFT JOIN product p ON p.sku = io.sku AND p.company_id = <company_id>
WHERE io.deleted_at IS NULL;
```

---

## 🔍 Queries úteis

### Pedidos com itens e custo de produto
```sql
SELECT
    o.external_order_id,
    o.data_criacao,
    o.status,
    io.titulo,
    io.sku,
    io.quantidade,
    io.preco_unitario,
    p.cost_price
FROM orders o
JOIN items_order io ON io.order_id = o.id
LEFT JOIN product p ON p.sku = io.sku
WHERE o.account_id = <account_id>
  AND o.deleted_at IS NULL
  AND io.deleted_at IS NULL;
```

### Pedidos com dados de entrega e fiscal
```sql
SELECT
    o.external_order_id,
    o.valor,
    s.receiver_name,
    s.cidade,
    s.estado,
    b.razao_social,
    b.doc_numero
FROM orders o
LEFT JOIN shipping s ON s.order_id = o.id
LEFT JOIN billing  b ON b.order_id = o.id
WHERE o.account_id = <account_id>
  AND o.deleted_at IS NULL;
```

### Contas ativas de um business
```sql
SELECT * FROM v_accounts_ativas
WHERE business_id = <business_id>;
```

### Businesses ativos de uma company
```sql
SELECT * FROM v_business_ativos
WHERE company_id = <company_id>;
```

### Usuários de uma company
```sql
SELECT id, name, email, role, created_at
FROM "user"
WHERE company_id = <company_id>
  AND deleted_at IS NULL
ORDER BY role, name;
```

### Company e dono pelo user_id
```sql
SELECT c.*, u.name AS owner_name, u.email AS owner_email
FROM company c
JOIN "user" u ON u.id = c.user_id
WHERE c.id = <company_id>
  AND c.deleted_at IS NULL;
```
