import streamlit as st
import requests
import os

API_BASE_URL = os.getenv("API_BASE_URL", "http://backend:8000/api/v1")

st.set_page_config(page_title="Upload", layout="wide")

# Proteção
if "token" not in st.session_state or not st.session_state["token"]:
    st.warning("Faça login primeiro")
    st.switch_page("app.py")

headers = {"Authorization": f"Bearer {st.session_state['token']}"}

st.title("📤 Upload de Planilhas")

# 🔥 ABAS
tab1, tab2 = st.tabs(["💰 Faturamento", "📢 Anúncios"])

# ============= FATURAMENTO =============
with tab1:
    st.subheader("📊 Planilha de Faturamento")
    
    # 🔥 Aviso sobre substituição
    st.warning("⚠️ **Atenção:** Fazer novo upload irá **substituir** os dados anteriores de faturamento no dashboard.")
    
    st.info("Upload da planilha de vendas do Mercado Livre")
    
    file_fat = st.file_uploader(
        "Arquivo XLSX (Faturamento)",
        type=["xlsx"],
        key="fat",
    )
    
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
                        timeout=60
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Mensagem de sucesso
                        st.success(f"✅ {data['message']}")
                        
                        # Info sobre substituição
                        if "info" in data:
                            st.info(f"ℹ️ {data['info']}")
                        
                        # Mostra dados
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Linhas Processadas", data.get('rows', 0))
                        with col2:
                            st.metric("Status", data.get('status', ''))
                        
                        st.balloons()
                        
                        # Botão para ir ao dashboard
                        if st.button("📊 Ver Dashboard Atualizado", type="primary"):
                            st.switch_page("pages/dashboard.py")
                            
                    else:
                        st.error(f"❌ {response.json()}")
                except Exception as e:
                    st.error(f"❌ {e}")
    
    # Histórico
    st.divider()
    st.subheader("📜 Últimos uploads")
    
    try:
        r = requests.get(f"{API_BASE_URL}/upload/list/faturamento", headers=headers, timeout=10)
        if r.status_code == 200:
            uploads = r.json()
            if uploads:
                for u in uploads:
                    emoji = "✅" if u["status"] == "completed" else "⏳"
                    st.write(f"{emoji} {u['filename']} - {u.get('rows', 0)} linhas")
            else:
                st.info("Nenhum upload ainda")
    except:
        pass

# ============= ANÚNCIOS =============
with tab2:
    st.subheader("📢 Planilha de Anúncios")
    st.info("Upload da planilha de anúncios")
    
    file_anun = st.file_uploader(
        "Arquivo XLSX (Anúncios)",
        type=["xlsx"],
        key="anun",
    )
    
    if file_anun:
        st.success(f"✅ {file_anun.name}")
        st.write(f"📦 {file_anun.size / 1024:.2f} KB")