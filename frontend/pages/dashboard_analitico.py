import streamlit as st
import requests
import os
import base64
import pandas as pd
import plotly.graph_objects as go

API_BASE_URL = os.getenv("API_BASE_URL", "http://backend:8000/api/v1")

st.set_page_config(page_title="Dashboard Analítico", layout="wide")

if "token" not in st.session_state or not st.session_state["token"]:
    st.warning("Você precisa fazer login.")
    st.switch_page("app.py")

headers = {"Authorization": f"Bearer {st.session_state['token']}"}

st.markdown("""
<style>
    div[data-testid="stMetric"] {
        background-color: #000000 !important;
        border-radius: 8px;
        padding: 12px;
    }
    div[data-testid="stMetric"] label,
    div[data-testid="stMetricValue"] > div,
    div[data-testid="stMetricDelta"] > div,
    div[data-testid="stMetricLabel"] > div {
        color: #ffffff !important;
    }
</style>
""", unsafe_allow_html=True)

st.title("🔬 Dashboard Analítico — Faturamento × Anúncios")

# ── Busca dados ───────────────────────────────────────────
with st.spinner("Cruzando faturamento com anúncios..."):
    try:
        response = requests.get(
            f"{API_BASE_URL}/dashboard/analitico",
            headers=headers,
            timeout=30,
        )
        if response.status_code != 200:
            st.error(f"Erro {response.status_code}")
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

summary   = data["summary"]
acumulado = data["acumulado"]
vendas    = data["vendas"]

# ── Período ───────────────────────────────────────────────
st.caption(f"📅 Período analisado: **{summary['periodo_inicio']}** até **{summary['periodo_fim']}**")

def brl(val):
    return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# ════════════════════════════════════════════════════════════
# 1. CARDS FINANCEIROS
# ════════════════════════════════════════════════════════════
st.subheader("💰 Resumo Financeiro")

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric(
        "✅ Créditos",
        brl(summary["total_creditos"]),
        help="Receitas por produtos + acréscimos + envio",
    )
with col2:
    st.metric(
        "❌ Débitos",
        brl(summary["total_debitos"]),
        help="Taxas + impostos + custos de envio + cancelamentos",
    )
with col3:
    st.metric(
        "💵 Líquido Original",
        brl(summary["total_liquido"]),
        delta=f"{summary['margem_original']:.1f}%",
        help="Créditos − Débitos (sem descontar anúncios)",
    )
with col4:
    st.metric(
        "📢 Gasto com Anúncios",
        brl(summary["total_anuncios"]),
        delta=f"-{summary['total_anuncios']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
        delta_color="inverse",
        help="Total investido em anúncios patrocinados no período",
    )
with col5:
    st.metric(
        "🏆 Líquido Real",
        brl(summary["liquido_real"]),
        delta=f"{summary['margem_real']:.1f}%",
        help="Líquido Original − Gasto com Anúncios",
    )

st.divider()

# ── Comparativo visual: Líquido Original vs Líquido Real ──
col_a, col_b = st.columns([2, 1])

with col_a:
    fig = go.Figure()
    categorias = ["Créditos", "Débitos", "Líquido Original", "Gasto Anúncios", "Líquido Real"]
    valores    = [
        summary["total_creditos"],
        -summary["total_debitos"],
        summary["total_liquido"],
        -summary["total_anuncios"],
        summary["liquido_real"],
    ]
    cores = ["#2ecc71", "#e74c3c", "#3498db", "#e67e22", "#27ae60"]
    fig.add_trace(go.Bar(
        x=categorias, y=valores,
        marker_color=cores,
        text=[brl(abs(v)) for v in valores],
        textposition="outside",
    ))
    fig.update_layout(
        title="Composição do Resultado",
        height=380,
        yaxis_title="R$",
        showlegend=False,
    )
    st.plotly_chart(fig, width="stretch")

with col_b:
    st.markdown("**📊 Impacto dos Anúncios**")
    impacto = summary["total_liquido"] - summary["liquido_real"]
    margem_perdida = summary["margem_original"] - summary["margem_real"]
    st.metric("Redução no Líquido", brl(impacto), delta_color="inverse")
    st.metric("Margem Original", f"{summary['margem_original']:.1f}%")
    st.metric("Margem Real",     f"{summary['margem_real']:.1f}%")
    st.metric("Queda na Margem", f"{margem_perdida:.1f}pp", delta_color="inverse")
    st.metric("Total de Vendas", summary["total_vendas"])

st.divider()

# ════════════════════════════════════════════════════════════
# 2. ACUMULADO POR ANÚNCIO
# ════════════════════════════════════════════════════════════
if acumulado:
    st.subheader("📢 Investimento Acumulado por Anúncio no Período")

    df_ac = pd.DataFrame(acumulado)

    # Gráfico horizontal
    titulos = [
        (r["titulo"][:45] + "…" if len(r["titulo"]) > 45 else r["titulo"])
        or r["mlb"]
        for _, r in df_ac.iterrows()
    ]
    fig_ac = go.Figure(go.Bar(
        x=df_ac["investimento_total"],
        y=titulos,
        orientation="h",
        marker_color="#e67e22",
        text=[brl(v) for v in df_ac["investimento_total"]],
        textposition="outside",
    ))
    fig_ac.update_layout(
        height=max(300, len(acumulado) * 40),
        xaxis_title="Investimento Acumulado (R$)",
        yaxis=dict(autorange="reversed"),
        margin=dict(l=0),
    )
    st.plotly_chart(fig_ac, width="stretch")

    # Tabela detalhada
    with st.expander("📋 Tabela: Investimento acumulado por anúncio"):
        df_ac_display = df_ac.copy()
        df_ac_display["titulo"] = df_ac_display["titulo"].str[:60].fillna(df_ac_display["mlb"])
        df_ac_display.columns = ["Código MLB", "Título", "Investimento Total (R$)", "Qtd Vendas", "Custo por Venda (R$)"]
        df_ac_display["Investimento Total (R$)"] = df_ac_display["Investimento Total (R$)"].apply(lambda x: f"{x:,.2f}")
        df_ac_display["Custo por Venda (R$)"]    = df_ac_display["Custo por Venda (R$)"].apply(lambda x: f"{x:,.2f}")
        st.dataframe(df_ac_display, width="stretch", hide_index=True)

    st.divider()

# ════════════════════════════════════════════════════════════
# 3. TABELA DE VENDAS DETALHADA
# ════════════════════════════════════════════════════════════
if vendas:
    st.subheader("🧾 Vendas Detalhadas com Custo de Anúncio Rateado")
    st.caption(
        "💡 **Líquido ML (sem anúncios)** = valor líquido calculado pelo Mercado Livre após taxas de venda, "
        "frete e impostos — mas **não desconta** o custo de anúncios patrocinados. "
        "O **Líquido Real** = Receita Produto − Custo Anúncio Rateado."
    )

    df_v = pd.DataFrame(vendas)

    # Formata colunas monetárias para exibição
    money_display = ["Receita por produtos (BRL)", "Total (BRL)", "custo_por_venda", "liquido_real"]
    df_v_display = df_v.copy()
    for col in money_display:
        if col in df_v_display.columns:
            df_v_display[col] = pd.to_numeric(df_v_display[col], errors="coerce").apply(
                lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if pd.notna(x) else ""
            )

    # Renomeia para exibição
    rename = {
        "N.º de venda":               "N.º Venda",
        "Data da venda":              "Data",
        "mlb":                        "Código MLB",
        "Título do anúncio":          "Título",
        "Variação":                   "Variação",
        "Unidades":                   "Unid.",
        "Receita por produtos (BRL)": "Receita Produto",
        "Total (BRL)":                "Líquido ML (sem anúncios)",
        "custo_por_venda":            "Custo Anúncio Rateado",
        "liquido_real":               "Líquido Real",
    }
    cols_show = [c for c in rename.keys() if c in df_v_display.columns]
    df_v_display = df_v_display[cols_show].rename(columns=rename)

    st.dataframe(df_v_display, width="stretch", hide_index=True)

st.divider()

# ════════════════════════════════════════════════════════════
# 4. DOWNLOAD XLSX
# ════════════════════════════════════════════════════════════
st.subheader("📥 Exportar Relatório")

if st.button("⬇️ Gerar e Baixar XLSX", type="primary"):
    with st.spinner("Gerando planilha..."):
        try:
            r = requests.get(
                f"{API_BASE_URL}/dashboard/analitico/exportar",
                headers=headers,
                timeout=30,
            )
            if r.status_code == 200:
                payload = r.json()
                if "erro" in payload:
                    st.error(f"Erro ao gerar planilha: {payload['erro']}")
                else:
                    xlsx_bytes = base64.b64decode(payload["data"])
                    st.download_button(
                        label="📄 Clique aqui para baixar",
                        data=xlsx_bytes,
                        file_name=payload["filename"],
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
            else:
                st.error(f"Erro {r.status_code}")
        except Exception as e:
            st.error(f"Erro: {e}")

st.divider()

# ── Navegação ─────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)
with col1:
    if st.button("📊 Faturamento"):
        st.switch_page("pages/dashboard.py")
with col2:
    if st.button("📢 Anúncios"):
        st.switch_page("pages/dashboard_anuncios.py")
with col3:
    if st.button("📤 Upload"):
        st.switch_page("pages/upload.py")
with col4:
    if st.button("🚪 Logout"):
        st.session_state["token"] = None
        st.switch_page("app.py")