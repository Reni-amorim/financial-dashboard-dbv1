import streamlit as st
import requests
import os

API_BASE_URL = os.getenv("API_BASE_URL", "http://backend:8000/api/v1")

st.set_page_config(page_title="Dashboard", layout="wide")

# =========================
# PROTEÇÃO DE ROTA
# =========================
if "token" not in st.session_state or not st.session_state["token"]:
    st.warning("Você precisa fazer login.")
    st.switch_page("app.py")

headers = {"Authorization": f"Bearer {st.session_state['token']}"}

st.title("Dashboard")

# =========================
# BUSCAR DADOS DO BACKEND
# =========================
try:
    response = requests.get(
        f"{API_BASE_URL}/dashboard/",
        headers=headers,
        timeout=10
    )

    if response.status_code != 200:
        st.error("Erro ao carregar dados")
        st.json(response.json())
        st.stop()

    data = response.json()

except Exception as e:
    st.error("Erro ao conectar no backend")
    st.write(e)
    st.stop()

# =========================
# MÉTRICAS
# =========================

col1, col2, col3, col4 = st.columns(4)

col1.metric("Faturamento", f"R$ {data['total_revenue']:.2f}")
col2.metric("Débitos", f"R$ {data['total_debits']:.2f}")
col3.metric("Líquido", f"R$ {data['net_amount']:.2f}")
col4.metric("Transações", data["transactions"])

st.divider()

if st.button("Logout"):
    st.session_state["token"] = None
    st.switch_page("app.py")
