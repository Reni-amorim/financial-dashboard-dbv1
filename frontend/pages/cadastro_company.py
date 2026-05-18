"""
Página de Cadastro de Empresas (Company)
"""
import streamlit as st
import requests
import os
from utils.styles import aplicar_estilos
aplicar_estilos()

API_BASE_URL = os.getenv("API_BASE_URL", "http://backend:8000/api/v1")

st.set_page_config(page_title="Empresas", layout="wide")

if "token" not in st.session_state or not st.session_state["token"]:
    st.warning("Faça login primeiro.")
    st.switch_page("app.py")

headers = {"Authorization": f"Bearer {st.session_state['token']}"}

ESTADOS = [
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO",
    "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI",
    "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
]

REGIMES = ["Simples Nacional", "Lucro Presumido", "Lucro Real"]


def carregar_empresas():
    try:
        r = requests.get(f"{API_BASE_URL}/company/", headers=headers, timeout=10)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        st.error(f"Erro ao carregar empresas: {e}")
    return []


def criar_empresa(nome, cnpj, estado, regime):
    try:
        r = requests.post(
            f"{API_BASE_URL}/company/",
            json={
                "name": nome,
                "document": cnpj,
                "state_origin": estado,
                "regime_tributario": regime,
            },
            headers=headers,
            timeout=10,
        )
        return r
    except Exception as e:
        st.error(f"Erro: {e}")
        return None


def deletar_empresa(company_id):
    try:
        r = requests.delete(
            f"{API_BASE_URL}/company/{company_id}",
            headers=headers,
            timeout=10,
        )
        return r
    except Exception as e:
        st.error(f"Erro: {e}")
        return None


st.title("🏢 Cadastro de Empresas")
st.caption("Gerencie as empresas vinculadas à sua conta.")

st.divider()

with st.expander("➕ Adicionar nova empresa", expanded=True):
    with st.form("form_empresa"):
        col1, col2 = st.columns(2)

        with col1:
            nome = st.text_input(
                "Nome da Empresa *",
                placeholder="Ex: Carroussel Auto Peças Ltda",
            )
            cnpj = st.text_input(
                "CNPJ *",
                placeholder="XX.XXX.XXX/XXXX-XX",
                max_chars=18,
            )

        with col2:
            estado = st.selectbox(
                "Estado (UF) *",
                options=ESTADOS,
                index=ESTADOS.index("SP"),
            )
            regime = st.selectbox(
                "Regime Tributário *",
                options=REGIMES,
            )

        submitted = st.form_submit_button("💾 Cadastrar Empresa", type="primary", use_container_width=True)

        if submitted:
            if not nome or not cnpj:
                st.error("Nome e CNPJ são obrigatórios.")
            else:
                response = criar_empresa(nome, cnpj, estado, regime)
                if response and response.status_code in (200, 201):
                    st.success(f"✅ Empresa **{nome}** cadastrada com sucesso!")
                    st.rerun()
                elif response:
                    try:
                        detail = response.json().get("detail", "Erro desconhecido")
                    except Exception:
                        detail = response.text
                    st.error(f"❌ Erro {response.status_code}: {detail}")

st.subheader("📋 Empresas Cadastradas")

empresas = carregar_empresas()

if not empresas:
    st.info("Nenhuma empresa cadastrada ainda.")
else:
    for empresa in empresas:
        with st.container(border=True):
            col1, col2, col3 = st.columns([4, 2, 1])

            with col1:
                st.markdown(f"**🏢 {empresa['name']}**")
                st.caption(f"CNPJ: {empresa.get('document', '-')}")

            with col2:
                st.markdown(f"📍 **{empresa.get('state_origin', '-')}**")
                st.caption(empresa.get('regime_tributario', '-'))

            with col3:
                if st.button("🗑️", key=f"del_{empresa['id']}", help="Remover empresa"):
                    r = deletar_empresa(empresa['id'])
                    if r and r.status_code in (200, 204):
                        st.success("Empresa removida!")
                        st.rerun()