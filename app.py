import streamlit as st
import pandas as pd
from datetime import date
from src.database import ping
from src.data_extraction import fetch_all_companies, audit_advance_flags
from src.rules_catalog import get_code_by_name
from main import run, build_summary  # build_summary será usado novamente

st.set_page_config(page_title="Automação RH | Adiantamentos", layout="wide")


@st.cache_data(ttl=600)
def carregar_empresas():
    empresas = fetch_all_companies()
    if not empresas or not any("JR RODRIGUES DP" in s for s in empresas):
        empresas["JR RODRIGUES DP (Fallback)"] = "9098"
    return empresas


EMPRESAS = carregar_empresas()

with st.sidebar:
    st.title("Painel de Controle RH")
    page = st.radio(
        "Módulo de Execução",
        ["Gerar Adiantamento", "Auditoria de Flags"],
        label_visibility="collapsed",
    )
    st.divider()
    st.subheader("Status do Sistema")
    db_ok = ping()
    if db_ok:
        st.success("Conexão com Fortes: Ativa")
    else:
        st.error("Conexão com Fortes: Inativa")

if page == "Gerar Adiantamento":
    st.title("⚙️ Auditoria e Geração de Adiantamento")
    st.info(
        "Esta ferramenta compara a folha 'bruta' gerada pelo Fortes com a folha processada pelas nossas regras de negócio, destacando as divergências."
    )

    with st.container(border=True):
        colA, colB, colC = st.columns([1, 1, 2])
        with colA:
            ano = st.number_input(
                "Ano", min_value=2020, max_value=2100, value=date.today().year
            )
        with colB:
            mes = st.number_input(
                "Mês", min_value=1, max_value=12, value=date.today().month
            )
        nomes_empresas = list(EMPRESAS.keys())
        default_index = 0
        if nomes_empresas:
            try:
                default_index = next(
                    i
                    for i, name in enumerate(nomes_empresas)
                    if "JR RODRIGUES DP" in name
                )
            except StopIteration:
                default_index = 0
        with colC:
            empresa_selecionada = st.selectbox(
                "Selecione a Empresa", nomes_empresas, index=default_index
            )

    if st.button(
        "Executar Auditoria",
        type="primary",
        use_container_width=True,
        disabled=not db_ok,
    ):
        if not empresa_selecionada:
            st.warning("Por favor, selecione uma empresa.")
        else:
            codigo_empresa_db = EMPRESAS[empresa_selecionada]
            try:
                codigo_catalogo = get_code_by_name(empresa_selecionada)
                with st.spinner(f"Executando auditoria para {empresa_selecionada}..."):
                    df_resultado = run(
                        empresa_codigo=codigo_empresa_db,
                        empresa_id_catalogo=codigo_catalogo,
                        ano=ano,
                        mes=mes,
                    )
                    st.session_state["last_run_result"] = df_resultado
            except Exception as e:
                st.error(
                    f"Ocorreu um erro crítico durante o processamento: {e}", icon="🚨"
                )
                st.exception(e)

    # CORREÇÃO: Este bloco agora verifica se a chave existe antes de tentar usá-la.
    if "last_run_result" in st.session_state:
        st.divider()
        st.header("Relatório de Auditoria de Divergências")

        df_auditoria = st.session_state["last_run_result"]

        if df_auditoria.empty:
            st.success("Nenhuma divergência ou funcionário encontrado para o período.")
        else:
            st.dataframe(df_auditoria, use_container_width=True, hide_index=True)

        # --- NOVA PÁGINA DE AUDITORIA ---
    elif page == "Auditoria de Flags":
        st.title("🔎 Auditoria de Flags de Adiantamento")
        st.info(
            "Esta ferramenta verifica todos os funcionários **ativos** e lista aqueles que **não** estão com a flag 'Recebe Adiantamento' marcada como 'S' no Fortes."
        )

        with st.container(border=True):
            nomes_empresas_audit = list(EMPRESAS.keys())
            empresa_selecionada_audit = st.selectbox(
                "Selecione a Empresa para Auditar", nomes_empresas_audit, index=0
            )

        if st.button("Iniciar Auditoria", type="primary", use_container_width=True):
            if not empresa_selecionada_audit:
                st.warning("Por favor, selecione uma empresa.")
            else:
                codigo_empresa_db_audit = EMPRESAS[empresa_selecionada_audit]
                with st.spinner(f"A auditar {empresa_selecionada_audit}..."):
                    try:
                        inconsistent_df = audit_advance_flags(
                            emp_codigo=codigo_empresa_db_audit
                        )
                        st.session_state["audit_result"] = inconsistent_df
                        st.session_state["audited_company"] = empresa_selecionada_audit
                    except Exception as e:
                        st.error(f"Ocorreu um erro durante a auditoria: {e}", icon="🚨")
                        st.exception(e)

        if "audit_result" in st.session_state:
            st.divider()
            audited_company = st.session_state["audited_company"]
            result_df = st.session_state["audit_result"]

            if result_df.empty:
                st.success(
                    f"✅ Todos os funcionários ativos da empresa {audited_company} estão com a flag de adiantamento marcada corretamente."
                )
            else:
                st.warning(
                    f"🚨 Encontrados {len(result_df)} funcionários ativos com a flag de adiantamento desmarcada ou nula na empresa {audited_company}:"
                )
                st.dataframe(result_df, use_container_width=True, hide_index=True)

        elif page == "Dashboard Histórico":
            st.title("📊 Dashboard Histórico")
            st.info("Funcionalidade em desenvolvimento.")

        elif page == "Configurações":
            st.title("🔧 Configurações")
            st.info("Funcionalidade em desenvolvimento.")
