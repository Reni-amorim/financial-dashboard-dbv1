"""
Página de Cadastro de Businesses (filiais/marcas da Company)
"""
import streamlit as st
import requests
import os
from utils.styles import aplicar_estilos
aplicar_estilos()

API_BASE_URL = os.getenv("API_BASE_URL", "http://backend:8000/api/v1")

st.set_page_config(page_title="Businesses", layout="wide")

if "token" not in st.session_state or not st.session_state["token"]:
    st.warning("Faça login primeiro.")
    st.switch_page("app.py")

headers = {"Authorization": f"Bearer {st.session_state['token']}"}


def listar_companies():
    try:
        r = requests.get(f"{API_BASE_URL}/company/", headers=headers, timeout=10)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        st.error(f"Erro ao carregar companies: {e}")
    return []


def listar_businesses():
    try:
        r = requests.get(f"{API_BASE_URL}/business/", headers=headers, timeout=10)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        st.error(f"Erro ao carregar businesses: {e}")
    return []


def criar_business(name, document):
    try:
        payload = {"name": name}
        if document:
            payload["document"] = document
        r = requests.post(
            f"{API_BASE_URL}/business/",
            json=payload,
            headers=headers,
            timeout=10,
        )
        return r
    except Exception as e:
        st.error(f"Erro: {e}")
        return None


def deletar_business(business_id):
    try:
        return requests.delete(
            f"{API_BASE_URL}/business/{business_id}",
            headers=headers,
            timeout=10,
        )
    except Exception as e:
        st.error(f"Erro: {e}")
        return None


st.title("🏬 Cadastro de Businesses")
st.caption("Businesses (filiais/marcas) vinculados à sua Company.")
st.divider()

companies = listar_companies()
if not companies:
    st.warning("Você precisa cadastrar uma Company antes de criar Businesses.")
    if st.button("Ir para Cadastro de Empresa"):
        st.switch_page("pages/cadastro_company.py")
    st.stop()

company = companies[0]
st.info(f"🏢 Company atual: **{company['name']}** (UF: {company.get('state_origin', '-')})")

with st.expander("➕ Adicionar novo business", expanded=True):
    with st.form("form_business"):
        nome = st.text_input("Nome do Business *", placeholder="Ex: Loja Matriz SP")
        documento = st.text_input(
            "Documento (opcional)",
            placeholder="CNPJ ou identificador interno",
            max_chars=20,
        )
        submitted = st.form_submit_button(
            "💾 Cadastrar Business", type="primary", use_container_width=True
        )
        if submitted:
            if not nome:
                st.error("Nome é obrigatório.")
            else:
                r = criar_business(nome, documento)
                if r and r.status_code in (200, 201):
                    st.success(f"✅ Business **{nome}** cadastrado!")
                    st.rerun()
                elif r:
                    try:
                        detail = r.json().get("detail", r.text)
                    except Exception:
                        detail = r.text
                    st.error(f"❌ Erro {r.status_code}: {detail}")

st.subheader("📋 Businesses Cadastrados")
businesses = listar_businesses()
if not businesses:
    st.info("Nenhum business cadastrado ainda.")
else:
    for b in businesses:
        with st.container(border=True):
            col1, col2, col3 = st.columns([5, 3, 1])
            with col1:
                st.markdown(f"**🏬 {b['name']}**")
                st.caption(f"ID: {b['id']}")
            with col2:
                st.caption(f"Documento: {b.get('document') or '-'}")
            with col3:
                if st.button("🗑️", key=f"del_b_{b['id']}", help="Remover business"):
                    r = deletar_business(b["id"])
                    if r and r.status_code in (200, 204):
                        st.success("Business removido!")
                        st.rerun()
                    elif r:
                        st.error(f"Erro: {r.status_code}")