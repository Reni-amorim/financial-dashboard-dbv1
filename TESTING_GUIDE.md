# 🧪 Guia de Testes e Validação

## 📋 Índice
1. [Teste Rápido (5 minutos)](#teste-rápido)
2. [Teste Completo (15 minutos)](#teste-completo)
3. [Testes de API](#testes-de-api)
4. [Testes de Performance](#testes-de-performance)
5. [Troubleshooting](#troubleshooting)

---

## ⚡ Teste Rápido

### 1. Inicializar Sistema

```bash
# Com Docker (mais fácil)
docker-compose up -d

# Aguarde ~30 segundos para os serviços iniciarem
docker-compose logs -f
```

### 2. Verificar Health

```bash
# Backend
curl http://localhost:8000/health

# Esperado:
# {"status":"healthy","database":"connected","upload_dir":"True","processed_dir":"True"}
```

### 3. Acessar Frontend

1. Abra `http://localhost:8501`
2. Você deve ver a tela de login

### 4. Criar Conta e Fazer Upload

1. Clique em "Registrar"
2. Preencha:
   - Email: `teste@exemplo.com`
   - Usuário: `teste`
   - Senha: `senha12345`
3. Clique em "Registrar"
4. Faça login com as mesmas credenciais
5. Vá em "📤 Upload"
6. Selecione o arquivo `data/exemplo_financeiro.xlsx`
7. Clique em "🚀 Processar Arquivo"

### 5. Visualizar Dashboard

1. Vá em "📊 Dashboard"
2. Você deve ver:
   - ✅ Métricas com valores (Faturamento, Débitos, Líquido)
   - ✅ Gráficos mensais e trimestrais
   - ✅ Dados carregados corretamente

✅ **Se chegou aqui, o sistema está funcionando!**

---

## 🔍 Teste Completo

### 1. Testes de Autenticação

#### 1.1 Registro com Validações

**Teste: Senha curta**
- Senha: `123` (menos de 8 caracteres)
- Esperado: ❌ "A senha deve ter no mínimo 8 caracteres"

**Teste: Senhas diferentes**
- Senha: `senha123`
- Confirmar: `senha456`
- Esperado: ❌ "As senhas não coincidem"

**Teste: Email duplicado**
- Crie usuário `user1@test.com`
- Tente criar novamente
- Esperado: ❌ "Email already registered"

**Teste: Username duplicado**
- Crie usuário `testuser`
- Tente criar novamente
- Esperado: ❌ "Username already taken"

#### 1.2 Login com Credenciais Inválidas

**Teste: Usuário inexistente**
- Username: `naoexiste`
- Password: `qualquer`
- Esperado: ❌ "Usuário ou senha incorretos"

**Teste: Senha incorreta**
- Username: `teste` (existente)
- Password: `senhaerrada`
- Esperado: ❌ "Usuário ou senha incorretos"

### 2. Testes de Upload

#### 2.1 Arquivo Inválido

**Teste: Extensão errada**
- Arquivo: `documento.pdf`
- Esperado: ❌ Erro ao fazer upload (apenas .xlsx aceito)

**Teste: Arquivo muito grande**
- Arquivo: `arquivo_60mb.xlsx` (> 50MB)
- Esperado: ❌ "File too large"

#### 2.2 Upload Bem-Sucedido

**Teste: XLSX válido**
1. Upload `data/exemplo_financeiro.xlsx`
2. Esperado:
   - ✅ "Arquivo enviado com sucesso!"
   - ✅ Status: "pending" → "processing" → "completed"
3. Aguarde 5-10 segundos
4. Vá em "📋 Histórico"
5. Esperado:
   - ✅ Upload aparece na lista
   - ✅ Status: "completed"
   - ✅ Linhas processadas: 100
   - ✅ Valores de faturamento/débitos preenchidos

### 3. Testes de Dashboard

#### 3.1 Métricas Calculadas

Com o arquivo `exemplo_financeiro.xlsx`:

**Valores esperados (aproximados):**
- Faturamento Total: ~R$ 250.000,00
- Débitos Totais: ~R$ 25.000,00
- Líquido: ~R$ 225.000,00
- Transações: 100

**Validação:**
```
Líquido = Faturamento - Débitos
Débitos = Taxas + Impostos + Plataforma
```

#### 3.2 Gráficos

**Teste: Gráfico Mensal**
- Esperado: Barras agrupadas por mês (2024-01, 2024-02, ...)
- Esperado: 3 séries (receita, débitos, net)

**Teste: Gráfico Trimestral**
- Esperado: Barras agrupadas por trimestre (2024Q1, 2024Q2, ...)

### 4. Testes de Histórico

#### 4.1 Listagem

**Teste: Ver todos uploads**
1. Faça 3 uploads diferentes
2. Vá em "📋 Histórico"
3. Esperado: 3 uploads na lista, ordenados do mais recente

#### 4.2 Deletar Upload

**Teste: Deletar arquivo**
1. Clique em "🗑️ Deletar" em um upload
2. Esperado:
   - ✅ "Upload deletado!"
   - ✅ Upload removido da lista
   - ✅ Arquivos físicos deletados (raw e parquet)

---

## 🔌 Testes de API

### Setup

```bash
# Criar usuário via API
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "api@test.com",
    "username": "apiuser",
    "password": "senha12345"
  }'

# Fazer login e pegar token
TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"apiuser","password":"senha12345"}' \
  | jq -r '.access_token')

echo $TOKEN
```

### Testes de Endpoints

#### 1. GET /api/v1/auth/me

```bash
curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer $TOKEN"

# Esperado:
# {"id":1,"email":"api@test.com","username":"apiuser",...}
```

#### 2. POST /api/v1/upload/

```bash
curl -X POST http://localhost:8000/api/v1/upload/ \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@data/exemplo_financeiro.xlsx"

# Esperado:
# {"id":1,"processing_status":"pending",...}
```

#### 3. GET /api/v1/upload/

```bash
curl -X GET http://localhost:8000/api/v1/upload/ \
  -H "Authorization: Bearer $TOKEN"

# Esperado: Lista de uploads
```

#### 4. GET /api/v1/dashboard/

```bash
curl -X GET http://localhost:8000/api/v1/dashboard/ \
  -H "Authorization: Bearer $TOKEN"

# Esperado: Dados completos do dashboard
```

#### 5. Teste sem autenticação

```bash
curl -X GET http://localhost:8000/api/v1/dashboard/

# Esperado: 401 Unauthorized
```

### Swagger UI

Acesse `http://localhost:8000/docs` para testar interativamente.

---

## ⚡ Testes de Performance

### 1. Processamento de Arquivo Grande

**Gerar XLSX grande (1000 linhas):**

```python
# scripts/generate_large_xlsx.py
from scripts.generate_sample_xlsx import generate_sample_xlsx

# Modifique o range para 1000
generate_sample_xlsx("data/exemplo_grande.xlsx", num_rows=1000)
```

**Teste:**
1. Upload do arquivo grande
2. Meça o tempo de processamento
3. Esperado: < 30 segundos para 1000 linhas

### 2. Múltiplos Uploads Simultâneos

```bash
# Upload 5 arquivos ao mesmo tempo
for i in {1..5}; do
  curl -X POST http://localhost:8000/api/v1/upload/ \
    -H "Authorization: Bearer $TOKEN" \
    -F "file=@data/exemplo_financeiro.xlsx" &
done
wait

# Verifique que todos foram processados
curl -X GET http://localhost:8000/api/v1/upload/ \
  -H "Authorization: Bearer $TOKEN"
```

### 3. Carga no Dashboard

```bash
# 100 requisições consecutivas
for i in {1..100}; do
  curl -X GET http://localhost:8000/api/v1/dashboard/ \
    -H "Authorization: Bearer $TOKEN" > /dev/null
done

# Verifique logs para erros
docker-compose logs backend | grep ERROR
```

---

## 🐛 Troubleshooting

### Backend não inicia

**Sintoma:** `docker-compose up` falha

**Verificações:**
```bash
# PostgreSQL está rodando?
docker ps | grep postgres

# Logs do backend
docker-compose logs backend

# Porta 8000 está livre?
lsof -i :8000
```

**Solução:**
```bash
docker-compose down -v
docker-compose up -d --build
```

### Frontend não conecta com backend

**Sintoma:** Erro ao fazer login

**Verificações:**
```bash
# Backend está acessível?
curl http://localhost:8000/health

# Variável de ambiente correta?
docker-compose exec frontend env | grep API_BASE_URL
```

**Solução:**
```bash
# Edite docker-compose.yml
environment:
  API_BASE_URL: http://backend:8000/api/v1
```

### Processamento de XLSX falha

**Sintoma:** Upload fica "pending" ou "failed"

**Verificações:**
```bash
# Ver logs detalhados
docker-compose logs -f backend

# Verificar erro específico
curl http://localhost:8000/api/v1/upload/1 \
  -H "Authorization: Bearer $TOKEN" \
  | jq '.error_message'
```

**Causas comuns:**
1. Delimitador diferente de TAB
2. Formato de data não reconhecido
3. Valores com símbolos não esperados

**Solução:**
Edite `backend/app/services/xlsx_processor.py`:
```python
# Ajuste detecção de delimitador
delimiters = ['\t', '|', ';', '  ']  # Adicione o seu

# Ajuste conversão de valores
.str.replace('R$', '', regex=False)
.str.replace('€', '', regex=False)  # Se usar Euro
```

### Dashboard vazio

**Sintoma:** Métricas zeradas

**Verificações:**
```bash
# Há uploads processados?
curl http://localhost:8000/api/v1/upload/ \
  -H "Authorization: Bearer $TOKEN" \
  | jq '.[].processing_status'

# Arquivo parquet existe?
docker-compose exec backend ls -la /app/data/processed/
```

**Solução:**
Reprocesse os arquivos:
```bash
# Delete uploads com erro
# Faça novo upload
```

---

## ✅ Checklist Final

### Funcionalidades

- [ ] ✅ Registro de usuário funciona
- [ ] ✅ Login funciona
- [ ] ✅ Token JWT é gerado e validado
- [ ] ✅ Upload de XLSX funciona
- [ ] ✅ Processamento assíncrono funciona
- [ ] ✅ Dados são salvos em Parquet
- [ ] ✅ Dashboard carrega métricas
- [ ] ✅ Gráficos são renderizados
- [ ] ✅ Histórico mostra uploads
- [ ] ✅ Deletar upload funciona
- [ ] ✅ Isolamento de dados por usuário funciona

### Segurança

- [ ] ✅ Senhas são hasheadas (bcrypt)
- [ ] ✅ Tokens JWT expiram
- [ ] ✅ Rotas protegidas requerem autenticação
- [ ] ✅ Usuários só veem seus próprios dados
- [ ] ✅ Validação de tamanho de arquivo

### Performance

- [ ] ✅ Processamento < 30s para 1000 linhas
- [ ] ✅ Dashboard carrega < 2s
- [ ] ✅ Uploads simultâneos funcionam
- [ ] ✅ Sem memory leaks

### UX

- [ ] ✅ Mensagens de erro claras
- [ ] ✅ Indicadores de loading
- [ ] ✅ Navegação intuitiva
- [ ] ✅ Feedback visual de ações

---

## 📊 Métricas de Sucesso

| Métrica | Valor Esperado |
|---------|----------------|
| Tempo de setup | < 5 minutos |
| Tempo de upload (100 linhas) | < 10 segundos |
| Tempo de processamento (100 linhas) | < 15 segundos |
| Tempo de carga do dashboard | < 2 segundos |
| Taxa de erro em uploads | < 1% |
| Disponibilidade | > 99% |

---

**Se todos os testes passarem, seu sistema está pronto para uso! 🎉**
