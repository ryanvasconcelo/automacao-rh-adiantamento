# app.py (Versão Final Alinhada)
import streamlit as st
import pandas as pd
from datetime import date
from src.database import ping
from src.data_extraction import fetch_all_companies

# CORREÇÃO: Importando 'run' e 'build_summary'
from main import run, build_summary

st.set_page_config(page_title="Auditoria RH | Adiantamentos", layout="wide")


@st.cache_data(ttl=600)
def carregar_empresas():
    # Garante que a empresa de teste exista caso a busca falhe
    empresas = fetch_all_companies()
    if not empresas or not any("JR RODRIGUES DP" in s for s in empresas):
        empresas["JR RODRIGUES DP (Fallback)"] = "9098"
    return empresas


EMPRESAS = carregar_empresas()

with st.sidebar:
    st.title("Painel de Controle RH")
    page = st.radio(
        "Módulo de Execução",
        ["Gerar Adiantamento", "Dashboard Histórico", "Configurações"],
        label_visibility="collapsed",
    )
    st.divider()
    st.subheader("Status do Sistema")
    if ping():
        st.success("Conexão com Fortes: Ativa")
    else:
        st.error("Conexão com Fortes: Inativa")

if page == "Gerar Adiantamento":
    st.title("⚙️ Gerar Folha de Adiantamento")
    with st.container(border=True):
        st.subheader("Parâmetros de Geração")
        colA, colB, colC = st.columns([1, 1, 2])
        with colA:
            ano = st.number_input("Ano", min_value=2020, max_value=2100, value=2025)
        with colB:
            mes = st.number_input("Mês", min_value=1, max_value=12, value=8)

        # Lógica para encontrar o nome padrão da empresa
        nomes_empresas = list(EMPRESAS.keys())
        default_company_name = next(
            (name for name in nomes_empresas if "JR RODRIGUES DP" in name),
            nomes_empresas[0],
        )

        with colC:
            empresa_selecionada = st.selectbox(
                "Selecione a Empresa",
                nomes_empresas,
                index=nomes_empresas.index(default_company_name),
            )

    if st.button(
        "Executar Geração e Auditoria", type="primary", use_container_width=True
    ):
        if not empresa_selecionada:
            st.warning("Por favor, selecione uma empresa.")
        else:
            codigo_empresa = EMPRESAS[empresa_selecionada]
            with st.spinner(f"Processando {empresa_selecionada}..."):
                try:
                    # CORREÇÃO: Chamando a função 'run'
                    df_resultado = run(empresa_codigo=codigo_empresa, ano=ano, mes=mes)
                    st.session_state["last_run_result"] = df_resultado
                    st.session_state["last_run_code"] = codigo_empresa
                except Exception as e:
                    st.error(
                        f"Ocorreu um erro crítico durante o processamento: {e}",
                        icon="🚨",
                    )
                    st.exception(e)

    if "last_run_result" in st.session_state:
        st.divider()
        st.header("Resultados da Execução")

        df_resultado = st.session_state["last_run_result"]
        codigo_empresa_processado = st.session_state["last_run_code"]

        resumo_df = build_summary(df_resultado, codigo_empresa_processado)

        if not resumo_df.empty:
            resumo = resumo_df.iloc[0]
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Analisados", int(resumo["Total"]))
            c2.metric("Elegíveis", int(resumo["Elegiveis"]))
            c3.metric("Inelegíveis", int(resumo["Inelegiveis"]))
            valor_formatado = f"R$ {resumo['ValorTotalPagar']:_.2f}".replace(
                ".", ","
            ).replace("_", ".")
            c4.metric("Valor Total a Pagar", valor_formatado)
            st.dataframe(resumo_df, use_container_width=True, hide_index=True)

        elegiveis_df = df_resultado[df_resultado["Status"] == "Elegível"].copy()
        inelegiveis_df = df_resultado[df_resultado["Status"] == "Inelegível"].copy()

        if not inelegiveis_df.empty:
            with st.expander("Ver detalhes dos funcionários inelegíveis"):
                st.dataframe(
                    inelegiveis_df[["Matricula", "Nome", "Cargo", "Observacoes"]],
                    use_container_width=True,
                    hide_index=True,
                )

        if not elegiveis_df.empty:
            st.markdown("---")
            st.subheader("✅ Detalhes dos Funcionários Elegíveis")
            st.dataframe(elegiveis_df, use_container_width=True, hide_index=True)

elif page == "Dashboard Histórico":
    st.title("📊 Dashboard Histórico")
    st.info("Funcionalidade em desenvolvimento.")

elif page == "Configurações":
    st.title("🔧 Configurações")
    st.info("Funcionalidade em desenvolvimento.")
