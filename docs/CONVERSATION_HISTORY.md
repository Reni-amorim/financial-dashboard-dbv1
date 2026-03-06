# Histórico da Conversa - Desenvolvimento Financial Dashboard

## Sessão: Março 2026

### Tópicos Abordados:

1. **Setup Inicial**
   - Escolha de stack (FastAPI + Streamlit)
   - Estrutura de pastas
   - Docker Compose

2. **Implementação de Upload**
   - Upload de XLSX com Pandas
   - Conversão para Parquet
   - Sistema dual (Faturamento/Anúncios)

3. **Bug de Conversão Monetária**
   - Problema: Valores 50x maiores
   - Causa: Formato US vs BR
   - Solução: Detecção inteligente de formato

4. **Dashboard Financeiro**
   - Cálculo de créditos/débitos
   - Gráficos com Plotly
   - Métricas mensais

5. **Correções Finais**
   - Dashboard vazio (caminho errado)
   - Perda de histórico (session_state)
   - Código duplicado

### Decisões Técnicas:

**Não usar Alembic (por enquanto):**
- Projeto em desenvolvimento ativo
- Banco pode ser resetado facilmente
- Menos complexidade
- Migrar quando em produção

**Storage em Parquet:**
- 5x mais rápido que CSV
- Compressão nativa
- Tipos de dados preservados

**Reset de Faturamento:**
- Simplifica UX
- Dashboard sempre atualizado
- Histórico de anúncios preservado

### Arquivos Importantes:

**Core:**
- `backend/app/services/xlsx_processor.py` - Processamento XLSX
- `backend/app/api/dashboard.py` - API do dashboard
- `frontend/pages/dashboard.py` - UI do dashboard

**Críticos:**
- `_to_brl_number()` - Conversão monetária (bug corrigido)
- `process_xlsx_to_parquet()` - Pipeline de processamento
- `get_dashboard()` - Agregação de métricas