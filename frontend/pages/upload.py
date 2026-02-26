import streamlit as st
import requests
import os

API_BASE_URL = os.getenv("API_BASE_URL", "http://backend:8000/api/v1")

st.set_page_config(page_title="Upload", layout="centered")

if "token" not in st.session_state or not st.session_state["token"]:
    st.warning("Você precisa fazer login.")
    st.switch_page("app.py")

st.title("Upload de planilha XLSX")

file = st.file_uploader("Selecione um arquivo XLSX", type=["xlsx"])

if file and st.button("Processar upload"):
    headers = {"Authorization": f"Bearer {st.session_state['token']}"}
    files = {"file": (file.name, file.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}

    resp = requests.post(f"{API_BASE_URL}/upload/", headers=headers, files=files, timeout=180)

    if resp.ok:
        st.success("Upload processado com sucesso!")
        st.json(resp.json())
        st.switch_page("pages/dashboard.py")
    else:
        st.error(f"Erro no upload: {resp.status_code}")
        try:
            st.json(resp.json())
        except Exception:
            st.write(resp.text)