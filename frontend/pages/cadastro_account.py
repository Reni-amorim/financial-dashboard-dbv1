"""
Página de Cadastro de Accounts (sellers do Mercado Livre)
"""
import streamlit as st
import requests
import os
from utils.styles import aplicar_estilos
aplicar_estilos()

API_BASE_URL = os.getenv("API_BASE_URL", "http://backend:8000/api/v1")

st.set_page_config(page_title="Accounts", layout="wide")

if "token" not in st.session_state or not st.session_state["token"]:
    st.warning("Faça login primeiro.")
    st.switch_page("app.py")

headers = {"Authorization": f"Bearer {st.session_state['token']}"}


def listar_businesses():
    try:
        r = requests.get(f"{API_BASE_URL}/business/", headers=headers, timeout=10)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        st.error(f"Erro ao carregar businesses: {e}")
    return []


def listar_accounts():
    try:
        r = requests.get(f"{API_BASE_URL}/account/", headers=headers, timeout=10)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        st.error(f"Erro ao carregar accounts: {e}")
    return []


def criar_account(business_id, name, marketplace_id):
    try:
        payload = {
            "business_id": int(business_id),
            "name": name,
            "marketplace_id": int(marketplace_id) if marketplace_id else None,
            "status": "active",
        }
        r = requests.post(
            f"{API_BASE_URL}/account/",
            json=payload,
            headers=headers,
            timeout=10,
        )
        return r
    except Exception as e:
        st.error(f"Erro: {e}")
        return None


def deletar_account(account_id):
    try:
        return requests.delete(
            f"{API_BASE_URL}/account/{account_id}",
            headers=headers,
            timeout=10,
        )
    except Exception as e:
        st.error(f"Erro: {e}")
        return None


st.title("🛒 Cadastro de Accounts")
st.caption("Contas (sellers) do Mercado Livre vinculadas a cada Business.")
st.divider()

businesses = listar_businesses()
if not businesses:
    st.warning("Você precisa cadastrar um Business antes de criar Accounts.")
    if st.button("Ir para Cadastro de Business"):
        st.switch_page("pages/cadastro_business.py")
    st.stop()

with st.expander("➕ Adicionar novo account", expanded=True):
    with st.form("form_account"):
        business_sel = st.selectbox(
            "Business *",
            options=businesses,
            format_func=lambda b: f"{b['name']} (id {b['id']})",
        )
        nome = st.text_input(
            "Nome do Account *", placeholder="Ex: Loja oficial Mercado Livre"
        )
        marketplace_id = st.text_input(
            "Marketplace ID (seller ID do ML) *",
            placeholder="Ex: 123456789",
            help="ID numérico do seller no Mercado Livre. Usado no JOIN com a tabela orders.",
        )
        submitted = st.form_submit_button(
            "💾 Cadastrar Account", type="primary", use_container_width=True
        )
        if submitted:
            if not nome or not marketplace_id:
                st.error("Nome e Marketplace ID são obrigatórios.")
            elif not marketplace_id.strip().isdigit():
                st.error("Marketplace ID precisa ser numérico.")
            else:
                r = criar_account(business_sel["id"], nome, marketplace_id.strip())
                if r and r.status_code in (200, 201):
                    st.success(f"✅ Account **{nome}** cadastrado!")
                    st.rerun()
                elif r:
                    try:
                        detail = r.json().get("detail", r.text)
                    except Exception:
                        detail = r.text
                    st.error(f"❌ Erro {r.status_code}: {detail}")

st.subheader("📋 Accounts Cadastrados")
accounts = listar_accounts()
if not accounts:
    st.info("Nenhum account cadastrado ainda.")
else:
    biz_map = {b["id"]: b["name"] for b in businesses}
    for a in accounts:
        with st.container(border=True):
            col1, col2, col3, col4 = st.columns([4, 3, 2, 1])
            with col1:
                st.markdown(f"**🛒 {a.get('name') or '(sem nome)'}**")
                st.caption(f"ID: {a['id']} | Status: {a.get('status', '-')}")
            with col2:
                st.caption(f"Business: {biz_map.get(a['business_id'], a['business_id'])}")
            with col3:
                st.caption(f"Seller ML: **{a.get('marketplace_id') or '-'}**")
            with col4:
                if st.button("🗑️", key=f"del_a_{a['id']}", help="Remover account"):
                    r = deletar_account(a["id"])
                    if r and r.status_code in (200, 204):
                        st.success("Account removido!")
                        st.rerun()
                    elif r:
                        st.error(f"Erro: {r.status_code}")