import streamlit as st
import requests
import os

API_BASE_URL = os.getenv("API_BASE_URL", "http://backend:8000/api/v1")

st.set_page_config(page_title="Upload", layout="wide")

# ── Proteção de rota ──────────────────────────────────────
if "token" not in st.session_state or not st.session_state["token"]:
    st.warning("Faça login primeiro")
    st.switch_page("app.py")

headers = {"Authorization": f"Bearer {st.session_state['token']}"}

st.title("📤 Upload de Planilhas")

tab1, tab2 = st.tabs(["💰 Faturamento", "📢 Anúncios Patrocinados"])

# ════════════════════════════════════════════════════════════
# ABA 1 — FATURAMENTO
# ════════════════════════════════════════════════════════════
with tab1:
    st.subheader("📊 Planilha de Faturamento")
    st.warning("⚠️ **Atenção:** Novo upload **substitui** os dados anteriores de faturamento no dashboard.")
    st.info("Planilha de vendas exportada do Mercado Livre.")

    file_fat = st.file_uploader("Arquivo XLSX (Faturamento)", type=["xlsx"], key="fat")

    if file_fat:
        st.success(f"✅ {file_fat.name}")
        st.write(f"📦 {file_fat.size / 1024:.2f} KB")

        if st.button("🚀 Processar Faturamento", type="primary", use_container_width=True):
            with st.spinner("Processando..."):
                try:
                    response = requests.post(
                        f"{API_BASE_URL}/upload/faturamento",
                        files={"file": file_fat},
                        headers=headers,
                        timeout=60,
                    )
                    if response.status_code == 200:
                        data = response.json()
                        st.success(f"✅ {data['message']}")
                        if "info" in data:
                            st.info(f"ℹ️ {data['info']}")
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Linhas Processadas", data.get("rows", 0))
                        with col2:
                            st.metric("Status", data.get("status", ""))
                        st.balloons()
                        if st.button("📊 Ver Dashboard de Faturamento", type="primary"):
                            st.switch_page("pages/dashboard.py")
                    else:
                        st.error(f"❌ Erro: {response.json()}")
                except Exception as e:
                    st.error(f"❌ {e}")

    # Histórico de faturamento
    st.divider()
    st.subheader("📜 Últimos uploads de faturamento")
    try:
        r = requests.get(f"{API_BASE_URL}/upload/list/faturamento", headers=headers, timeout=10)
        if r.status_code == 200:
            uploads = r.json()
            if uploads:
                for u in uploads:
                    emoji = "✅" if u["status"] == "completed" else "⏳"
                    data_upload = u.get("uploaded_at", "")[:10] if u.get("uploaded_at") else "N/A"
                    st.write(f"{emoji} {u['filename']} — {u.get('rows', 0)} linhas — {data_upload}")
            else:
                st.info("Nenhum upload ainda.")
    except Exception:
        pass

# ════════════════════════════════════════════════════════════
# ABA 2 — ANÚNCIOS PATROCINADOS
# ════════════════════════════════════════════════════════════
with tab2:
    st.subheader("📢 Planilha de Anúncios Patrocinados")
    st.info("Relatório de anúncios exportado do Mercado Livre Ads. O histórico de uploads é preservado.")

    file_anun = st.file_uploader("Arquivo XLSX (Anúncios)", type=["xlsx"], key="anun")

    if file_anun:
        st.success(f"✅ {file_anun.name}")
        st.write(f"📦 {file_anun.size / 1024:.2f} KB")

        if st.button("🚀 Processar Anúncios", type="primary", use_container_width=True):
            with st.spinner("Processando anúncios..."):
                try:
                    response = requests.post(
                        f"{API_BASE_URL}/upload/anuncios",
                        files={"file": file_anun},
                        headers=headers,
                        timeout=60,
                    )
                    if response.status_code == 200:
                        data = response.json()
                        st.success(f"✅ {data['message']}")

                        # Métricas do processamento
                        metrics = data.get("metrics", {})
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("Anúncios", data.get("rows", 0))
                        with col2:
                            st.metric("Ativos", metrics.get("anuncios_ativos", 0))
                        with col3:
                            receita = metrics.get("total_receita", 0)
                            st.metric("Receita", f"R$ {receita:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                        with col4:
                            roas = metrics.get("roas_global", 0)
                            st.metric("ROAS Global", f"{roas:.2f}x")

                        st.balloons()

                        if st.button("📢 Ver Dashboard de Anúncios", type="primary"):
                            st.switch_page("pages/dashboard_anuncios.py")
                    else:
                        st.error(f"❌ Erro: {response.json()}")
                except Exception as e:
                    st.error(f"❌ {e}")

    # Histórico de anúncios
    st.divider()
    st.subheader("📜 Histórico de uploads de anúncios")
    try:
        r = requests.get(f"{API_BASE_URL}/upload/list/anuncios", headers=headers, timeout=10)
        if r.status_code == 200:
            uploads = r.json()
            if uploads:
                for u in uploads:
                    emoji = "✅" if u["status"] == "completed" else "⏳"
                    data_upload = u.get("uploaded_at", "")[:10] if u.get("uploaded_at") else "N/A"
                    st.write(f"{emoji} {u['filename']} — {u.get('rows', 0)} anúncios — {data_upload}")
            else:
                st.info("Nenhum upload ainda.")
    except Exception:
        pass