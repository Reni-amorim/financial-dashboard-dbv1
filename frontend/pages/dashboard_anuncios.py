import streamlit as st
import requests
import os
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

API_BASE_URL = os.getenv("API_BASE_URL", "http://backend:8000/api/v1")

st.set_page_config(page_title="Dashboard Anúncios", layout="wide")

# Proteção de rota
if "token" not in st.session_state or not st.session_state["token"]:
    st.warning("Você precisa fazer login.")
    st.switch_page("app.py")

headers = {"Authorization": f"Bearer {st.session_state['token']}"}

st.title("📢 Dashboard de Anúncios Patrocinados")

# Último upload
try:
    r = requests.get(f"{API_BASE_URL}/upload/list/anuncios", headers=headers, timeout=10)
    if r.status_code == 200 and r.json():
        latest = r.json()[0]
        upload_date = latest.get("uploaded_at", "")[:10] if latest.get("uploaded_at") else "N/A"
        st.caption(f"📅 Último upload: {upload_date} | 📄 {latest.get('filename', 'N/A')}")
except Exception:
    pass

# Busca dados
try:
    response = requests.get(f"{API_BASE_URL}/dashboard/anuncios/", headers=headers, timeout=20)
    if response.status_code != 200:
        st.error("Erro ao carregar dados")
        st.json(response.json())
        st.stop()
    data = response.json()
except Exception as e:
    st.error(f"Erro ao conectar no backend: {e}")
    st.stop()

if data.get("message"):
    st.info(data["message"])
    if st.button("📤 Ir para Upload"):
        st.switch_page("pages/upload.py")
    st.stop()

metrics = data.get("metrics", {})

# ─────────────────────────────────────────────
# Cards de métricas principais
# ─────────────────────────────────────────────
st.subheader("📊 Visão Geral")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("📢 Total de Anúncios", metrics.get("total_anuncios", 0))
with col2:
    ativos = metrics.get("status_counts", {}).get("Ativo", 0)
    st.metric("✅ Ativos", ativos)
with col3:
    st.metric("👁️ Impressões", f"{metrics.get('total_impressoes', 0):,}".replace(",", "."))
with col4:
    st.metric("🖱️ Cliques", f"{metrics.get('total_cliques', 0):,}".replace(",", "."))

col5, col6, col7, col8 = st.columns(4)
with col5:
    receita = metrics.get("total_receita", 0)
    st.metric("💰 Receita", f"R$ {receita:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
with col6:
    investimento = metrics.get("total_investimento", 0)
    st.metric("💸 Investimento", f"R$ {investimento:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
with col7:
    roas = metrics.get("roas_global", 0)
    st.metric("📈 ROAS", f"{roas:.2f}x", help="Receitas / Investimento")
with col8:
    acos = metrics.get("acos_global", 0)
    st.metric("📉 ACOS", f"{acos:.2f}%", help="Investimento / Receitas")

st.divider()

# ─────────────────────────────────────────────
# Métricas de performance (2ª linha)
# ─────────────────────────────────────────────
st.subheader("⚡ Performance")
col1, col2, col3, col4 = st.columns(4)
with col1:
    ctr = metrics.get("ctr_medio", 0)
    st.metric("CTR médio", f"{ctr:.2f}%", help="Click Through Rate — média dos anúncios com cliques")
with col2:
    cpc = metrics.get("cpc_medio", 0)
    st.metric("CPC médio", f"R$ {cpc:.2f}", help="Custo por Clique")
with col3:
    cvr = metrics.get("cvr_medio", 0)
    st.metric("CVR médio", f"{cvr:.2f}%", help="Conversion Rate")
with col4:
    vendas = metrics.get("total_vendas", 0)
    vdir = metrics.get("total_vendas_diretas", 0)
    vind = metrics.get("total_vendas_indiretas", 0)
    st.metric("🛒 Vendas Totais", vendas, help=f"{vdir} diretas + {vind} indiretas")

st.divider()

# ─────────────────────────────────────────────
# Gráfico por campanha
# ─────────────────────────────────────────────
por_campanha = data.get("por_campanha", [])
if por_campanha:
    st.subheader("🏷️ Performance por Campanha")
    df_camp = pd.DataFrame(por_campanha)

    tab1, tab2 = st.tabs(["💰 Receita vs Investimento", "📈 ROAS por Campanha"])

    with tab1:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df_camp["campanha"],
            y=df_camp["receita"],
            name="Receita",
            marker_color="#2ecc71"
        ))
        fig.add_trace(go.Bar(
            x=df_camp["campanha"],
            y=df_camp["investimento"],
            name="Investimento",
            marker_color="#e74c3c"
        ))
        fig.update_layout(
            barmode="group",
            xaxis_title="Campanha",
            yaxis_title="Valor (R$)",
            hovermode="x unified",
            height=400,
            xaxis_tickangle=-30,
        )
        st.plotly_chart(fig, width="stretch")

    with tab2:
        fig2 = px.bar(
            df_camp.sort_values("roas", ascending=True),
            x="roas",
            y="campanha",
            orientation="h",
            color="roas",
            color_continuous_scale="RdYlGn",
            labels={"roas": "ROAS", "campanha": "Campanha"},
            title="ROAS por Campanha (maior = melhor)",
        )
        fig2.update_layout(height=max(300, len(df_camp) * 40))
        st.plotly_chart(fig2, width="stretch")

    st.divider()

# ─────────────────────────────────────────────
# Top 10 anúncios
# ─────────────────────────────────────────────
top_anuncios = data.get("top_anuncios", [])
if top_anuncios:
    st.subheader("🏆 Top 10 Anúncios por Receita")

    df_top = pd.DataFrame(top_anuncios)

    # Formata para exibição
    df_display = df_top[[
        "titulo", "campanha", "status",
        "impressoes", "cliques", "vendas",
        "receita", "investimento", "roas", "ctr", "cpc"
    ]].copy()

    df_display["receita"]      = df_display["receita"].apply(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    df_display["investimento"] = df_display["investimento"].apply(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    df_display["roas"]         = df_display["roas"].apply(lambda x: f"{x:.2f}x")
    df_display["ctr"]          = df_display["ctr"].apply(lambda x: f"{x:.2f}%")
    df_display["cpc"]          = df_display["cpc"].apply(lambda x: f"R$ {x:.2f}")
    df_display["impressoes"]   = df_display["impressoes"].apply(lambda x: f"{x:,}".replace(",", "."))
    df_display["cliques"]      = df_display["cliques"].apply(lambda x: f"{x:,}".replace(",", "."))

    df_display.columns = [
        "Título", "Campanha", "Status",
        "Impressões", "Cliques", "Vendas",
        "Receita", "Investimento", "ROAS", "CTR", "CPC"
    ]

    st.dataframe(df_display, width="stretch", hide_index=True)

st.divider()

# ─────────────────────────────────────────────
# Status breakdown
# ─────────────────────────────────────────────
status_counts = metrics.get("status_counts", {})
if status_counts:
    with st.expander("📋 Distribuição por Status"):
        col1, col2 = st.columns(2)
        with col1:
            for status, count in status_counts.items():
                st.write(f"**{status}:** {count}")
        with col2:
            fig_pie = px.pie(
                names=list(status_counts.keys()),
                values=list(status_counts.values()),
                title="Anúncios por Status"
            )
            st.plotly_chart(fig_pie, width="stretch")

st.divider()

col1, col2 = st.columns(2)
with col1:
    if st.button("📤 Novo Upload"):
        st.switch_page("pages/upload.py")
with col2:
    if st.button("🚪 Logout"):
        st.session_state["token"] = None
        st.switch_page("app.py")