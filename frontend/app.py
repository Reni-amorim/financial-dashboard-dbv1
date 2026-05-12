import streamlit as st
import requests
import os

API_BASE_URL = os.getenv("API_BASE_URL", "http://backend:8000/api/v1")

st.set_page_config(layout="centered")

# ==============================
# TESTE DE CONEXÃO
# ==============================

st.title("📊 Financial Dashboard")

try:
    health_url = API_BASE_URL.replace("/api/v1", "") + "/health"
    response = requests.get(health_url)
    st.success("✅ Backend conectado")
except Exception as e:
    st.error("❌ Erro ao conectar no backend")
    st.stop()


# ==============================
# SESSION STATE
# ==============================

if "token" not in st.session_state:
    st.session_state["token"] = None


# ==============================
# FUNÇÕES
# ==============================

def login(username, password):
    data = {
        "username": username,
        "password": password
    }

    response = requests.post(
        f"{API_BASE_URL}/auth/login",
        data=data
    )

    if response.status_code == 200:
        token = response.json()["access_token"]
        st.session_state["token"] = token
        st.success("Login realizado com sucesso!")
        st.switch_page("pages/dashboard_faturamento.py")
    else:
        st.error("Usuário ou senha inválidos")


def register(username, name, email, password):
    data = {
        "username": username,
        "name": name,
        "email": email,
        "password": password
    }

    response = requests.post(
        f"{API_BASE_URL}/auth/register",
        json=data
    )

    if response.status_code == 201:
        st.success("Usuário registrado com sucesso! Faça login.")
    else:
        try:
            detail = response.json().get("detail")
        except Exception:
            detail = response.text
        st.error(f"Erro ao registrar usuário: {detail}")

def logout():
    st.session_state["token"] = None
    st.rerun()


# ==============================
# SE NÃO ESTIVER LOGADO
# ==============================

if not st.session_state["token"]:

    tab1, tab2 = st.tabs(["Login", "Registrar"])

    with tab1:
        st.subheader("🔐 Login")

        username = st.text_input("Usuário")
        password = st.text_input("Senha", type="password")

        if st.button("Entrar"):
            login(username, password)

    with tab2:
        st.subheader("📝 Registrar")

        new_username = st.text_input("Novo Usuário")
        new_name = st.text_input("Nome completo")
        new_email = st.text_input("Email")
        new_password = st.text_input("Nova Senha", type="password")

        if st.button("Registrar"):
            register(new_username, new_name, new_email, new_password)

# ==============================
# SE ESTIVER LOGADO
# ==============================

else:
    st.success("🔓 Usuário autenticado!")

    st.write("Token JWT ativo.")
    st.code(st.session_state["token"])

    if st.button("Logout"):
        logout()

    st.divider()
    st.header("📊 Dashboard (em construção)")