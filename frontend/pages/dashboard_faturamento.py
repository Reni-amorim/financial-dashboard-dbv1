import streamlit as st
import requests
import os
import pandas as pd
import plotly.graph_objects as go
from utils.styles import aplicar_estilos
aplicar_estilos()

API_BASE_URL = os.getenv("API_BASE_URL", "http://backend:8000/api/v1")

st.set_page_config(page_title="Dashboard Faturamento", layout="wide")

# Proteção de rota
if "token" not in st.session_state or not st.session_state["token"]:
    st.warning("Você precisa fazer login.")
    st.switch_page("app.py")

headers = {"Authorization": f"Bearer {st.session_state['token']}"}

st.title("📊 Dashboard Faturamento")

# Info do upload atual
try:
    response_uploads = requests.get(
        f"{API_BASE_URL}/upload/list/faturamento",
        headers=headers,
        timeout=10
    )
    if response_uploads.status_code == 200:
        uploads = response_uploads.json()
        if uploads:
            latest = uploads[0]
            upload_date = latest.get('uploaded_at', '')[:10] if latest.get('uploaded_at') else 'N/A'
            st.caption(f"📅 Último upload: {upload_date} | 📄 Arquivo: {latest.get('filename', 'N/A')}")
except Exception:
    pass

# Buscar dados do dashboard
try:
    response = requests.get(f"{API_BASE_URL}/dashboard/", headers=headers, timeout=20)

    if response.status_code != 200:
        st.error("Erro ao carregar dados")
        st.json(response.json())
        st.stop()

    data = response.json()

    if data.get("message"):
        st.info(data["message"])
        st.stop()

except Exception as e:
    st.error("Erro ao conectar no backend")
    st.write(e)
    st.stop()

# Todas as métricas vêm do financial_calculator via API
m = data.get("metricas", {})


def fmt(x):
    """Formata float para padrão BR"""
    return f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ─────────────────────────────────────────────────────────────
# RESUMO FINANCEIRO
# ─────────────────────────────────────────────────────────────
st.subheader("💰 Resumo Financeiro")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "✅ Total Créditos",
        fmt(m.get("total_creditos", 0)),
        help="Receitas por produtos + acréscimos + envio"
    )

with col2:
    st.metric(
        "🏦 Líquido da Operação",
        fmt(m.get("total_brl_acumulado", 0)),
        help="Total (BRL) acumulado — resultado líquido calculado pelo Mercado Livre por venda"
    )

with col3:
    st.metric(
        "❌ Total Débitos",
        fmt(m.get("total_debitos_com_icms", 0)),
        help="Débitos da operação + ICMS estimado"
    )

with col4:
    st.metric(
        "💵 Líquido Sem Rebate",
        fmt(m.get("total_liquido_sem_rebate", 0)),
        delta=f"{m.get('margem_liquido', 0):.1f}%",
        help="Créditos - Débitos da operação - ICMS estimado"
    )

# ─────────────────────────────────────────────────────────────
# LÍQUIDO REAL COM REBATE (calculado no financial_calculator)
# Fórmula: Total (BRL) acumulado − ICMS Total
# ─────────────────────────────────────────────────────────────
col_rebate, _, _ = st.columns(3)
with col_rebate:
    st.metric(
        "💎 Líquido Real com Rebate",
        fmt(m.get("liquido_real_com_rebate", 0)),
        delta=f"{m.get('margem_liquido_com_rebate', 0):.1f}%",
        help="Total (BRL) acumulado − ICMS Total"
    )

st.divider()

# ─────────────────────────────────────────────────────────────
# RESUMO DE ICMS
# ─────────────────────────────────────────────────────────────
st.subheader("🧾 Resumo de ICMS")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "🧾 ICMS",
        fmt(m.get("total_icms", 0)),
        help="ICMS sobre as vendas"
    )

with col2:
    st.metric(
        "🧾 DIFAL",
        fmt(m.get("total_difal", 0)),
        help="Diferencial de alíquota (vendas para não contribuintes)"
    )

with col3:
    st.metric(
        "🧾 ICMS Total",
        fmt(m.get("total_icms_total", 0)),
        delta=f"{m.get('perc_icms_sobre_receita', 0):.1f}% da receita",
        help="ICMS + DIFAL (já incluído nos débitos acima)"
    )

st.divider()

st.caption(f"📁 Fonte: {data.get('source_file', '-')}")
st.write(f"📊 Transações: **{data.get('transactions', 0):,}**")

st.divider()

# ─────────────────────────────────────────────────────────────
# DETALHAMENTO POR COLUNA
# ─────────────────────────────────────────────────────────────
totals = m.get("totals_por_coluna", {})
if totals:
    with st.expander("📊 Ver detalhamento por coluna", expanded=True):

        items = list(totals.items())
        for i in range(0, len(items), 4):
            cols = st.columns(4)
            chunk = items[i:i+4]
            for col_idx, (name, value) in enumerate(chunk):
                cols[col_idx].metric(name, fmt(value))

        # ICMS no detalhamento
        st.divider()
        st.caption("🧾 ICMS Estimado")
        col1, col2, col3, _ = st.columns(4)

        with col1:
            st.metric("ICMS",       fmt(m.get("total_icms", 0)))
        with col2:
            st.metric("DIFAL",      fmt(m.get("total_difal", 0)))
        with col3:
            st.metric("ICMS Total", fmt(m.get("total_icms_total", 0)))

st.divider()

if st.button("🚪 Logout"):
    st.session_state["token"] = None
    st.switch_page("app.py")

# ─────────────────────────────────────────────────────────────
# GRÁFICOS E TABELA MENSAIS
# ─────────────────────────────────────────────────────────────
monthly = m.get("monthly", [])
if monthly:
    dfm = pd.DataFrame(monthly).sort_values("ano_mes")


    # Tabela mensal
    # Ordem: Mês | Créditos | Débitos da Operação | ICMS | DIFAL | ICMS Total | Líquido sem Rebate
    st.subheader("📋 Detalhamento Mensal")

    dfm_display = pd.DataFrame({
        "Mês":                 dfm["ano_mes"],
        "Créditos":            dfm["creditos"].apply(fmt),
        "Débitos da Operação": dfm["debitos_operacao"].apply(fmt),
        "ICMS":                dfm["icms"].apply(fmt),
        "DIFAL":               dfm["difal"].apply(fmt),
        "ICMS Total":          dfm["icms_total_venda"].apply(fmt),
        "Líquido sem Rebate":             dfm["liquido_sem_rebate"].apply(fmt),
    })

    st.dataframe(dfm_display, use_container_width=True, hide_index=True)

    st.divider()


    # Gráfico Créditos vs Débitos
    st.subheader("📈 Evolução Mensal: Créditos vs Débitos")

    fig = go.Figure()
    fig.add_trace(go.Bar(x=dfm["ano_mes"], y=dfm["creditos"],
                         name="Créditos", marker_color="#2ecc71"))
    fig.add_trace(go.Bar(x=dfm["ano_mes"], y=dfm["debitos_operacao"],
                         name="Débitos da Operação", marker_color="#e74c3c"))
    fig.add_trace(go.Scatter(x=dfm["ano_mes"], y=dfm["liquido_sem_rebate"],
                             name="Líquido sem Rebate", mode="lines+markers",
                             marker=dict(size=10, color="#3498db"),
                             line=dict(width=3, color="#3498db")))
    fig.update_layout(barmode="group", xaxis_title="Mês",
                      yaxis_title="Valor (R$)", hovermode="x unified", height=500)
    st.plotly_chart(fig, use_container_width=True)

    st.divider()


    # Gráfico ICMS
    if "icms_total_venda" in dfm.columns:
        st.subheader("🧾 Evolução Mensal: ICMS")

        fig_icms = go.Figure()
        fig_icms.add_trace(go.Bar(x=dfm["ano_mes"], y=dfm["icms"],
                                  name="ICMS", marker_color="#f39c12"))
        fig_icms.add_trace(go.Bar(x=dfm["ano_mes"], y=dfm["difal"],
                                  name="DIFAL", marker_color="#e67e22"))
        fig_icms.add_trace(go.Scatter(x=dfm["ano_mes"], y=dfm["icms_total_venda"],
                                      name="ICMS Total", mode="lines+markers",
                                      marker=dict(size=10, color="#c0392b"),
                                      line=dict(width=3, color="#c0392b")))
        fig_icms.update_layout(barmode="stack", xaxis_title="Mês",
                               yaxis_title="Valor (R$)", hovermode="x unified", height=400)
        st.plotly_chart(fig_icms, use_container_width=True)

        st.divider()

else:
    st.info("Sem dados mensais disponíveis.")

st.divider()