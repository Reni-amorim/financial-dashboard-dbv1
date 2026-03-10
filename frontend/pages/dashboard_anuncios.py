import streamlit as st
import requests
import os
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

API_BASE_URL = os.getenv("API_BASE_URL", "http://backend:8000/api/v1")

st.set_page_config(page_title="Anúncios Patrocinados", layout="wide")

# ── Proteção de rota ──────────────────────────────────────
if "token" not in st.session_state or not st.session_state["token"]:
    st.warning("Você precisa fazer login.")
    st.switch_page("app.py")

headers = {"Authorization": f"Bearer {st.session_state['token']}"}

# ── CSS ───────────────────────────────────────────────────
st.markdown("""
<style>
    .metric-good  { color: #2ecc71; font-weight: 700; }
    .metric-bad   { color: #e74c3c; font-weight: 700; }
    .metric-neutral { color: #3498db; font-weight: 700; }
    .section-title { font-size: 1.1rem; font-weight: 600; margin-bottom: 0.3rem; }
    div[data-testid="stMetric"] {
        background-color: #000000 !important;
        border-radius: 8px;
        padding: 12px;
    }
    div[data-testid="stMetric"] label,
    div[data-testid="stMetric"] div[data-testid="stMetricValue"],
    div[data-testid="stMetricValue"] > div,
    div[data-testid="stMetricDelta"] > div,
    div[data-testid="stMetricLabel"] > div {
        color: #ffffff !important;
    }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────
st.title("📢 Dashboard — Anúncios Patrocinados")

# ── Busca dados ───────────────────────────────────────────
try:
    response = requests.get(
        f"{API_BASE_URL}/dashboard/anuncios",
        headers=headers,
        timeout=20,
    )
    if response.status_code != 200:
        st.error(f"Erro ao carregar dados: {response.status_code}")
        st.json(response.json())
        st.stop()
    data = response.json()
except Exception as e:
    st.error(f"Erro ao conectar no backend: {e}")
    st.stop()

# ── Sem dados ─────────────────────────────────────────────
if data.get("message"):
    st.info(data["message"])
    if st.button("📤 Ir para Upload"):
        st.switch_page("pages/upload.py")
    st.stop()

summary      = data["summary"]
por_campanha = data["por_campanha"]
top_anuncios = data["top_anuncios"]
piores_acos  = data["piores_acos"]
por_status   = data["por_status"]

st.caption(f"📁 Fonte: {data.get('source_file', '-')}")

# ════════════════════════════════════════════════════════════
# 1. CARDS DE RESUMO
# ════════════════════════════════════════════════════════════
st.subheader("📊 Visão Geral")

col1, col2, col3, col4, col5 = st.columns(5)

def brl(val):
    return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

with col1:
    st.metric("💰 Receita Total", brl(summary["total_receita"]))
with col2:
    st.metric("📤 Investimento", brl(summary["total_investimento"]))
with col3:
    st.metric(
        "📈 ROAS Global",
        f"{summary['roas_global']:.2f}x",
        help="Receitas / Investimento. Acima de 4x é bom.",
    )
with col4:
    st.metric(
        "📉 ACOS Global",
        f"{summary['acos_global']:.2f}%",
        help="Investimento / Receita × 100. Abaixo de 15% é bom.",
    )
with col5:
    st.metric("🛒 Vendas Totais", f"{summary['total_vendas']:,}")

st.divider()

# ── Segunda linha de métricas ─────────────────────────────
col1, col2, col3, col4, col5, col6 = st.columns(6)

with col1:
    st.metric("👁️ Impressões", f"{summary['total_impressoes']:,}")
with col2:
    st.metric("🖱️ Cliques", f"{summary['total_cliques']:,}")
with col3:
    st.metric("📊 CTR", f"{summary['ctr_global']:.2f}%", help="Cliques / Impressões")
with col4:
    st.metric("🎯 CVR", f"{summary['cvr_global']:.2f}%", help="Vendas / Cliques")
with col5:
    st.metric("💵 CPC Médio", brl(summary["cpc_global"]), help="Custo por clique")
with col6:
    st.metric("📦 Anúncios Ativos", summary["anuncios_ativos"])

st.divider()

# ════════════════════════════════════════════════════════════
# 2. CAMPANHAS — comparativo
# ════════════════════════════════════════════════════════════
if por_campanha:
    st.subheader("🏹 Performance por Campanha")

    left, right = st.columns([3, 2])

    with left:
        # Gráfico de barras agrupadas: Receita vs Investimento
        campanhas  = [c["campanha"] for c in por_campanha]
        receitas   = [c["receita"] for c in por_campanha]
        investimentos = [c["investimento"] for c in por_campanha]

        fig = go.Figure()
        fig.add_trace(go.Bar(
            name="Receita",
            x=campanhas,
            y=receitas,
            marker_color="#2ecc71",
            text=[brl(v) for v in receitas],
            textposition="outside",
        ))
        fig.add_trace(go.Bar(
            name="Investimento",
            x=campanhas,
            y=investimentos,
            marker_color="#e74c3c",
            text=[brl(v) for v in investimentos],
            textposition="outside",
        ))
        fig.update_layout(
            barmode="group",
            title="Receita vs Investimento",
            height=380,
            yaxis_title="R$",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig, use_container_width=True)

    with right:
        # Tabela de métricas por campanha
        df_camp = pd.DataFrame(por_campanha)
        df_camp_display = df_camp[[
            "campanha", "total_anuncios", "impressoes", "cliques",
            "vendas", "receita", "investimento", "roas", "acos", "ctr"
        ]].copy()
        df_camp_display.columns = [
            "Campanha", "Anúncios", "Impressões", "Cliques",
            "Vendas", "Receita (R$)", "Investimento (R$)", "ROAS", "ACOS (%)", "CTR (%)"
        ]
        df_camp_display["Receita (R$)"]      = df_camp_display["Receita (R$)"].apply(lambda x: f"{x:,.2f}")
        df_camp_display["Investimento (R$)"] = df_camp_display["Investimento (R$)"].apply(lambda x: f"{x:,.2f}")
        st.dataframe(df_camp_display, use_container_width=True, hide_index=True)

        # ROAS por campanha — gauge visual
        st.markdown("**ROAS por Campanha**")
        for c in por_campanha:
            roas = c["roas"]
            cor = "#2ecc71" if roas >= 5 else ("#f39c12" if roas >= 3 else "#e74c3c")
            st.markdown(
                f"<div style='display:flex;justify-content:space-between;padding:4px 0;'>"
                f"<span style='font-size:0.85rem'>{c['campanha']}</span>"
                f"<span style='font-weight:700;color:{cor}'>{roas:.2f}x</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

    st.divider()

# ════════════════════════════════════════════════════════════
# 3. STATUS DOS ANÚNCIOS
# ════════════════════════════════════════════════════════════
if por_status:
    st.subheader("🏷️ Distribuição por Status")

    left, right = st.columns([1, 2])

    with left:
        # Pizza de quantidade
        labels = [s["status"] for s in por_status]
        values = [s["quantidade"] for s in por_status]
        cores = {
            "Ativo": "#2ecc71",
            "Desativada": "#e74c3c",
            "Movido": "#f39c12",
            "Sem status": "#95a5a6",
        }
        fig_pie = go.Figure(go.Pie(
            labels=labels,
            values=values,
            hole=0.45,
            marker_colors=[cores.get(l, "#bdc3c7") for l in labels],
            textinfo="label+percent",
        ))
        fig_pie.update_layout(title="Quantidade de anúncios", height=300, showlegend=False)
        st.plotly_chart(fig_pie, use_container_width=True)

    with right:
        df_status = pd.DataFrame(por_status)
        df_status_display = df_status[[
            "status", "quantidade", "impressoes", "cliques", "vendas", "receita", "investimento", "roas", "acos"
        ]].copy()
        df_status_display.columns = [
            "Status", "Qtd", "Impressões", "Cliques", "Vendas",
            "Receita (R$)", "Investimento (R$)", "ROAS", "ACOS (%)"
        ]
        df_status_display["Receita (R$)"]      = df_status_display["Receita (R$)"].apply(lambda x: f"{x:,.2f}")
        df_status_display["Investimento (R$)"] = df_status_display["Investimento (R$)"].apply(lambda x: f"{x:,.2f}")
        st.dataframe(df_status_display, use_container_width=True, hide_index=True)

    st.divider()

# ════════════════════════════════════════════════════════════
# 4. TOP 10 ANÚNCIOS — por receita
# ════════════════════════════════════════════════════════════
if top_anuncios:
    st.subheader("🏆 Top Anúncios por Receita")

    # Gráfico de barras horizontais
    titulos_curtos = [t["titulo"][:45] + "…" if len(t["titulo"]) > 45 else t["titulo"] for t in top_anuncios]
    receitas_top   = [t["receita"] for t in top_anuncios]

    fig_top = go.Figure(go.Bar(
        x=receitas_top,
        y=titulos_curtos,
        orientation="h",
        marker_color="#3498db",
        text=[brl(v) for v in receitas_top],
        textposition="outside",
    ))
    fig_top.update_layout(
        height=420,
        xaxis_title="Receita (R$)",
        yaxis=dict(autorange="reversed"),
        margin=dict(l=0),
    )
    st.plotly_chart(fig_top, use_container_width=True)

    # Tabela detalhada expansível
    with st.expander("📋 Ver tabela completa dos top anúncios"):
        df_top = pd.DataFrame(top_anuncios)
        df_top_display = df_top[[
            "titulo", "campanha", "status", "impressoes", "cliques",
            "vendas", "receita", "investimento", "roas", "acos", "ctr", "cvr", "cpc"
        ]].copy()
        df_top_display["titulo"] = df_top_display["titulo"].str[:60]
        df_top_display.columns = [
            "Título", "Campanha", "Status", "Impressões", "Cliques",
            "Vendas", "Receita (R$)", "Investimento (R$)", "ROAS", "ACOS (%)", "CTR (%)", "CVR (%)", "CPC"
        ]
        df_top_display["Receita (R$)"]      = df_top_display["Receita (R$)"].apply(lambda x: f"{x:,.2f}")
        df_top_display["Investimento (R$)"] = df_top_display["Investimento (R$)"].apply(lambda x: f"{x:,.2f}")
        st.dataframe(df_top_display, use_container_width=True, hide_index=True)

    st.divider()

# ════════════════════════════════════════════════════════════
# 5. PIORES ACOS — anúncios para otimizar
# ════════════════════════════════════════════════════════════
if piores_acos:
    st.subheader("⚠️ Anúncios com Maior ACOS — Oportunidades de Otimização")
    st.caption("Anúncios ativos com maior custo relativo sobre a receita (somente os que tiveram cliques)")

    fig_acos = go.Figure()
    titulos_acos = [t["titulo"][:40] + "…" if len(t["titulo"]) > 40 else t["titulo"] for t in piores_acos]
    acos_vals    = [t["acos"] for t in piores_acos]
    cores_acos   = ["#e74c3c" if v > 15 else "#f39c12" for v in acos_vals]

    fig_acos.add_trace(go.Bar(
        x=acos_vals,
        y=titulos_acos,
        orientation="h",
        marker_color=cores_acos,
        text=[f"{v:.1f}%" for v in acos_vals],
        textposition="outside",
    ))
    fig_acos.add_vline(x=15, line_dash="dash", line_color="#95a5a6", annotation_text="Meta 15%")
    fig_acos.update_layout(
        height=380,
        xaxis_title="ACOS (%)",
        yaxis=dict(autorange="reversed"),
        margin=dict(l=0),
    )
    st.plotly_chart(fig_acos, use_container_width=True)

    with st.expander("📋 Ver tabela dos piores ACOS"):
        df_acos = pd.DataFrame(piores_acos)
        df_acos_display = df_acos[[
            "titulo", "campanha", "status", "acos", "roas",
            "receita", "investimento", "cliques", "vendas"
        ]].copy()
        df_acos_display["titulo"] = df_acos_display["titulo"].str[:60]
        df_acos_display.columns = [
            "Título", "Campanha", "Status", "ACOS (%)", "ROAS",
            "Receita (R$)", "Investimento (R$)", "Cliques", "Vendas"
        ]
        df_acos_display["Receita (R$)"]      = df_acos_display["Receita (R$)"].apply(lambda x: f"{x:,.2f}")
        df_acos_display["Investimento (R$)"] = df_acos_display["Investimento (R$)"].apply(lambda x: f"{x:,.2f}")
        st.dataframe(df_acos_display, use_container_width=True, hide_index=True)

    st.divider()

# ── Scatter: Investimento vs Receita por anúncio ──────────
if top_anuncios:
    st.subheader("🔵 Investimento × Receita por Anúncio")
    st.caption("Bolhas maiores = mais cliques. Linha diagonal = break-even (ROAS 1x)")

    todos = top_anuncios + piores_acos
    df_scatter = pd.DataFrame(todos).drop_duplicates(subset=["codigo"])
    df_scatter = df_scatter[df_scatter["investimento"] > 0]

    if not df_scatter.empty:
        df_scatter["titulo_curto"] = df_scatter["titulo"].str[:40]
        fig_sc = px.scatter(
            df_scatter,
            x="investimento",
            y="receita",
            size="cliques",
            color="acos",
            hover_name="titulo_curto",
            hover_data={"investimento": ":.2f", "receita": ":.2f", "roas": ":.2f", "acos": ":.2f"},
            color_continuous_scale="RdYlGn_r",
            labels={
                "investimento": "Investimento (R$)",
                "receita": "Receita (R$)",
                "acos": "ACOS (%)",
            },
            title="Investimento vs Receita (cor = ACOS, tamanho = cliques)",
        )
        # Linha de break-even
        max_val = max(df_scatter["investimento"].max(), df_scatter["receita"].max()) * 1.1
        fig_sc.add_trace(go.Scatter(
            x=[0, max_val], y=[0, max_val],
            mode="lines",
            line=dict(dash="dot", color="#7f8c8d", width=1),
            name="Break-even (ROAS 1x)",
            showlegend=True,
        ))
        fig_sc.update_layout(height=450)
        st.plotly_chart(fig_sc, use_container_width=True)

st.divider()

# ── Rodapé / navegação ────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)
with col1:
    if st.button("📊 Dashboard Faturamento"):
        st.switch_page("pages/dashboard.py")
with col2:
    if st.button("📤 Upload"):
        st.switch_page("pages/upload.py")
with col3:
    if st.button("🔄 Resetar", type="secondary"):
        with st.spinner("Removendo dados..."):
            try:
                r = requests.delete(
                    f"{API_BASE_URL}/upload/reset/anuncios",
                    headers=headers,
                    timeout=15,
                )
                if r.status_code == 200:
                    st.success("✅ Dados removidos!")
                    st.switch_page("pages/upload.py")
                else:
                    st.error(f"Erro ao resetar: {r.json()}")
            except Exception as e:
                st.error(f"Erro: {e}")
with col4:
    if st.button("🚪 Logout"):
        st.session_state["token"] = None
        st.switch_page("app.py")