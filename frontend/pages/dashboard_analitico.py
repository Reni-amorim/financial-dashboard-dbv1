import streamlit as st
import requests
import os
import base64
import pandas as pd
import plotly.graph_objects as go
from utils.styles import aplicar_estilos
aplicar_estilos()

API_BASE_URL = os.getenv("API_BASE_URL", "http://backend:8000/api/v1")

st.set_page_config(page_title="Dashboard Analítico", layout="wide")

if "token" not in st.session_state or not st.session_state["token"]:
    st.warning("Você precisa fazer login.")
    st.switch_page("app.py")

headers = {"Authorization": f"Bearer {st.session_state['token']}"}

st.title("🔬 Dashboard Analítico — Faturamento × Anúncios × ICMS")

if "pagina_vendas" not in st.session_state:
    st.session_state["pagina_vendas"] = 1

PAGE_SIZE = 100

with st.spinner("Cruzando faturamento com anúncios..."):
    try:
        response = requests.get(
            f"{API_BASE_URL}/dashboard/analitico",
            headers=headers,
            timeout=60,
            params={"page": st.session_state["pagina_vendas"], "page_size": PAGE_SIZE},
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

s         = data["summary"]
acumulado = data["acumulado"]
vendas    = data["vendas"]


def brl(val: float) -> str:
    return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


st.caption(f"📅 Período analisado: **{s['periodo_inicio']}** até **{s['periodo_fim']}**")

# ════════════════════════════════════════════════════════════
# RESUMO FINANCEIRO
# Linha 1: 4 cards — Créditos | Débitos Op. | ICMS | Anúncios
# Linha 2: 2 cards — Líquido sem Rebate | Líquido Real
# Linha 3: 1 card  — Líquido Real com Rebate
# ════════════════════════════════════════════════════════════
st.subheader("💰 Resumo Financeiro")

# Linha 1: Créditos | Líquido da Operação | Débitos da Operação | ICMS
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("✅ Créditos", brl(s["total_creditos"]),
              help="Receitas por produtos + acréscimos + envio")
with col2:
    st.metric("🏦 Líquido da Operação", brl(s.get("total_brl_acumulado", 0)),
              help="Total (BRL) acumulado — resultado líquido calculado pelo Mercado Livre por venda")
with col3:
    st.metric("❌ Débitos da Operação", brl(s["total_debitos_op"]),
              help="Taxas + impostos + custos de envio + cancelamentos")
with col4:
    st.metric("🧾 ICMS Estimado", brl(s["total_icms"]),
              help="ICMS + DIFAL estimado sobre as vendas")

st.write("")

# Linha 2: Gasto com Anúncios | Líquido sem Rebate | Líquido Real | Líquido Real com Rebate
col5, col6, col7, col8 = st.columns(4)
with col5:
    st.metric("📢 Gasto com Anúncios", brl(s["total_anuncios"]),
              help="Total investido em anúncios patrocinados no período")
with col6:
    st.metric("💵 Líquido sem Rebate", brl(s["total_liquido_sem_rebate"]),
              delta=f"{s['margem_original']:.1f}%",
              help="Créditos − Débitos da Operação − ICMS")
with col7:
    st.metric("🏆 Líquido Real", brl(s["liquido_real"]),
              delta=f"{s['margem_real']:.1f}%",
              help="Líquido sem Rebate − Gasto com Anúncios")
with col8:
    st.metric("💎 Líquido Real com Rebate", brl(s.get("liquido_real_com_rebate", 0)),
              delta=f"{s.get('margem_real_com_rebate', 0):.1f}%",
              help="Total operação + rebate − ICMS Total − Gasto com Anúncios")

st.write("")

# Linha 3: Cancelamentos
col9, _, _, _ = st.columns(4)
with col9:
    st.metric("↩️ Cancelamentos", brl(s.get("total_cancelamentos", 0)),
              help="Total acumulado de cancelamentos e reembolsos no período")

st.divider()

# ── Comparativo visual ────────────────────────────────────
col_a, col_b = st.columns([2, 1])

with col_a:
    categorias = [
        "Créditos", "Débitos Op.", "ICMS",
        "Líquido sem Rebate", "Anúncios",
        "Líquido Real", "Líq. Real c/ Rebate"
    ]
    valores = [
        s["total_creditos"],
        -s["total_debitos_op"],
        -s["total_icms"],
        s["total_liquido_sem_rebate"],
        -s["total_anuncios"],
        s["liquido_real"],
        s.get("liquido_real_com_rebate", 0),
    ]
    cores = ["#2ecc71", "#e74c3c", "#f39c12", "#3498db", "#e67e22", "#27ae60", "#1abc9c"]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=categorias, y=valores,
        marker_color=cores,
        text=[brl(abs(v)) for v in valores],
        textposition="outside",
    ))
    fig.update_layout(title="Composição do Resultado", height=420,
                      yaxis_title="R$", showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

with col_b:
    st.markdown("**📊 Impacto dos Anúncios**")
    impacto        = s["total_liquido_sem_rebate"] - s["liquido_real"]
    margem_perdida = s["margem_original"] - s["margem_real"]
    st.metric("Redução no Líquido",   brl(impacto),                           delta_color="inverse")
    st.metric("Margem sem Rebate",    f"{s['margem_original']:.1f}%")
    st.metric("Margem Real",          f"{s['margem_real']:.1f}%")
    st.metric("Queda na Margem",      f"{margem_perdida:.1f}pp",              delta_color="inverse")
    st.metric("Margem c/ Rebate",     f"{s.get('margem_real_com_rebate', 0):.1f}%")
    st.metric("Total de Vendas",      s["total_vendas"])

st.divider()

# ════════════════════════════════════════════════════════════
# ACUMULADO POR ANÚNCIO
# ════════════════════════════════════════════════════════════
if acumulado:
    st.subheader("📢 Investimento Acumulado por Anúncio no Período")
    df_ac = pd.DataFrame(acumulado)
    titulos = [
        (r["titulo"][:45] + "…" if len(r["titulo"]) > 45 else r["titulo"]) or r["mlb"]
        for _, r in df_ac.iterrows()
    ]
    # Altura fixa mostrando ~20 registros; scroll interno para ver os demais
    ALTURA_VISIVEL = 800  # ~20 registros × 40px
    altura_total   = max(ALTURA_VISIVEL, len(acumulado) * 40)

    fig_ac = go.Figure(go.Bar(
        x=df_ac["investimento_total"], y=titulos,
        orientation="h", marker_color="#e67e22",
        text=[brl(v) for v in df_ac["investimento_total"]],
        textposition="outside",
    ))
    fig_ac.update_layout(
        height=altura_total,
        xaxis_title="Investimento Acumulado (R$)",
        yaxis=dict(autorange="reversed", range=[len(acumulado) - 0.5, len(acumulado) - 20.5]),
        margin=dict(l=0),
    )

    # Container com scroll — mostra ~20 registros e permite rolar para ver todos
    with st.container(height=820):
        st.plotly_chart(fig_ac, use_container_width=True)

    with st.expander("📋 Tabela: Investimento acumulado por anúncio", expanded=True):
        df_ac_display = df_ac.copy()
        df_ac_display["titulo"] = df_ac_display["titulo"].str[:60].fillna(df_ac_display["mlb"])
        df_ac_display.columns = ["Código MLB", "Título", "Investimento Total (R$)", "Vendas Diretas", "Custo por Venda (R$)"]
        df_ac_display["Investimento Total (R$)"] = df_ac_display["Investimento Total (R$)"].apply(lambda x: f"{x:,.2f}")
        df_ac_display["Custo por Venda (R$)"]    = df_ac_display["Custo por Venda (R$)"].apply(lambda x: f"{x:,.2f}")
        st.dataframe(df_ac_display, use_container_width=True, hide_index=True)

    st.divider()

# ════════════════════════════════════════════════════════════
# TABELA DE VENDAS DETALHADA
# ════════════════════════════════════════════════════════════
if vendas:
    pagination  = data.get("paginacao", {})
    total       = pagination.get("total", len(vendas))
    total_pages = pagination.get("total_pages", 1)
    page_atual  = pagination.get("page", 1)

    st.subheader(f"🧾 Vendas Detalhadas com Custo de Anúncio e ICMS Rateado ({total:,} vendas)")
    st.caption(
        "💡 **Líquido ML** = valor após taxas do ML + rebate. "
        "**ICMS** = estimado pelo calculador. "
        "**Líquido Real** = Líquido ML − ICMS − Custo Anúncio Rateado."
    )

    df_v         = pd.DataFrame(vendas)
    df_v_display = df_v.copy()

    for col in ["Receita por produtos (BRL)", "Total (BRL)", "icms_total_venda", "custo_por_venda", "liquido_operacao_sem_rebate_icms", "liquido_real_com_rebate"]:
        if col in df_v_display.columns:
            df_v_display[col] = pd.to_numeric(df_v_display[col], errors="coerce").apply(
                lambda x: brl(x) if pd.notna(x) else ""
            )

    rename = {
        "N.º de venda":                    "N.º Venda",
        "Data da venda":                   "Data",
        "mlb":                             "Código MLB",
        "Título do anúncio":               "Título",
        "Variação":                        "Variação",
        "Unidades":                        "Unid.",
        "Receita por produtos (BRL)":      "Receita Produto",
        "Total (BRL)":                     "Líquido ML + rebate",
        "icms_total_venda":                "ICMS",
        "custo_por_venda":                 "Custo Anúncio Rateado",
        "liquido_operacao_sem_rebate_icms": "Líquido Real Sem Rebate",
        "liquido_real_com_rebate":         "Líquido Real com Rebate",
    }
    # Ordem das colunas: ... | Custo Anúncio | Líquido Real Sem Rebate | Líquido Real com Rebate
    col_order = [
        "N.º de venda", "Data da venda", "mlb", "Título do anúncio",
        "Variação", "Unidades", "Receita por produtos (BRL)", "Total (BRL)",
        "icms_total_venda", "custo_por_venda",
        "liquido_operacao_sem_rebate_icms", "liquido_real_com_rebate",
    ]
    cols_show    = [c for c in col_order if c in df_v_display.columns]
    df_v_display = df_v_display[cols_show].rename(columns=rename)
    st.dataframe(
        df_v_display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Título":       st.column_config.TextColumn("Título",    width="small"),
            "Variação":     st.column_config.TextColumn("Variação",  width="small"),
            "Código MLB":   st.column_config.TextColumn("Código MLB", width="small"),
        }
    )

    st.divider()
    col_p1, col_p2, col_p3 = st.columns([1, 3, 1])
    with col_p1:
        if page_atual > 1:
            if st.button("◀ Anterior"):
                st.session_state["pagina_vendas"] -= 1
                st.rerun()
    with col_p2:
        st.caption(f"Página {page_atual} de {total_pages} — exibindo {len(vendas)} de {total:,} vendas")
    with col_p3:
        if page_atual < total_pages:
            if st.button("Próxima ▶"):
                st.session_state["pagina_vendas"] += 1
                st.rerun()

st.divider()

# ════════════════════════════════════════════════════════════
# DOWNLOAD XLSX
# ════════════════════════════════════════════════════════════
st.subheader("📥 Exportar Relatório")

if st.button("⬇️ Gerar e Baixar XLSX", type="primary"):
    with st.spinner("Gerando planilha..."):
        try:
            r = requests.get(f"{API_BASE_URL}/dashboard/analitico/exportar",
                             headers=headers, timeout=30)
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

col1, col2, col3, col4 = st.columns(4)
with col1:
    if st.button("📊 Faturamento"):
        st.switch_page("pages/dashboard_faturamento.py")
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