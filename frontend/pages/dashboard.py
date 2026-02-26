import streamlit as st
import requests
import os
import pandas as pd
import plotly.graph_objects as go

API_BASE_URL = os.getenv("API_BASE_URL", "http://backend:8000/api/v1")

st.set_page_config(page_title="Dashboard", layout="wide")

# Proteção de rota
if "token" not in st.session_state or not st.session_state["token"]:
    st.warning("Você precisa fazer login.")
    st.switch_page("app.py")

headers = {"Authorization": f"Bearer {st.session_state['token']}"}

st.title("📊 Dashboard Financeiro")

# Buscar dados
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

# 🔥 NOVO: Cards de Resumo Financeiro
st.subheader("💰 Resumo Financeiro")

summary = data.get("summary", {})
col1, col2, col3 = st.columns(3)

with col1:
    creditos = summary.get("total_creditos", 0)
    st.metric(
        "✅ Total Créditos",
        f"R$ {creditos:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
        help="Receitas por produtos + acréscimos + envio"
    )

with col2:
    debitos = summary.get("total_debitos", 0)
    st.metric(
        "❌ Total Débitos",
        f"R$ {debitos:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
        help="Taxas + impostos + custos de envio + cancelamentos"
    )

with col3:
    liquido = summary.get("total_liquido", 0)
    margem = (liquido / creditos * 100) if creditos > 0 else 0
    st.metric(
        "💵 Líquido",
        f"R$ {liquido:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
        delta=f"{margem:.1f}%",
        help="Créditos - Débitos"
    )

st.divider()

# Info do arquivo
st.caption(f"📁 Fonte: {data.get('source_file', '-')}")
st.write(f"📊 Transações: **{data.get('transactions', 0):,}**")

st.divider()

# 🔥 NOVO: Gráfico de Créditos vs Débitos Mensal
monthly = data.get("monthly", [])
if monthly:
    st.subheader("📈 Evolução Mensal: Créditos vs Débitos")
    
    dfm = pd.DataFrame(monthly).sort_values("ano_mes")
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=dfm["ano_mes"],
        y=dfm["creditos"],
        name="Créditos",
        marker_color="#2ecc71"
    ))
    
    fig.add_trace(go.Bar(
        x=dfm["ano_mes"],
        y=dfm["debitos"],
        name="Débitos",
        marker_color="#e74c3c"
    ))
    
    fig.add_trace(go.Scatter(
        x=dfm["ano_mes"],
        y=dfm["liquido"],
        name="Líquido",
        mode="lines+markers",
        marker=dict(size=10, color="#3498db"),
        line=dict(width=3, color="#3498db")
    ))
    
    fig.update_layout(
        barmode="group",
        xaxis_title="Mês",
        yaxis_title="Valor (R$)",
        hovermode="x unified",
        height=500
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    st.divider()
    
    # Tabela detalhada
    st.subheader("📋 Detalhamento Mensal")
    
    # Formata valores
    dfm_display = dfm.copy()
    for col in ["creditos", "debitos", "liquido"]:
        if col in dfm_display.columns:
            dfm_display[col] = dfm_display[col].apply(
                lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            )
    
    st.dataframe(dfm_display, use_container_width=True, hide_index=True)

else:
    st.info("Sem dados mensais disponíveis.")

st.divider()

# Totais detalhados (todas as colunas)
totals = data.get("totals", {})
if totals:
    with st.expander("📊 Ver detalhamento por coluna"):
        items = list(totals.items())
        for i in range(0, len(items), 4):
            cols = st.columns(4)
            chunk = items[i:i+4]
            for col_idx, (name, value) in enumerate(chunk):
                cols[col_idx].metric(
                    name,
                    f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                )

st.divider()

if st.button("🚪 Logout"):
    st.session_state["token"] = None
    st.switch_page("app.py")