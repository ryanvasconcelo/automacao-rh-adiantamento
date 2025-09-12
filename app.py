# app.py (VERSÃO FINAL COM COLUNA CARGO)

import streamlit as st
import pandas as pd
from main import run
from src.data_extraction import fetch_all_companies
from datetime import date
from config.logging_config import log

st.set_page_config(page_title="Projecont RH | Automações", page_icon="🤖", layout="wide")

@st.cache_data(ttl=600)
def carregar_empresas():
    empresas = fetch_all_companies()
    if not empresas or "JR Rodrigues (Salmo 91)" not in empresas:
         empresas["JR Rodrigues (Salmo 91)"] = "9098"
    return empresas

EMPRESAS = carregar_empresas()
if not EMPRESAS:
    st.error("Não foi possível carregar a lista de empresas do banco de dados.")
    st.stop()

with st.sidebar:
    st.title("Seleção")
    st.divider()
    st.subheader("Período de Competência")
    ano_atual = date.today().year
    ano_selecionado = st.number_input("Ano", min_value=2020, max_value=ano_atual + 5, value=2025)
    mes_selecionado = st.number_input("Mês", min_value=1, max_value=12, value=8)
    
    st.divider()
    st.subheader("Modo de Gestão")
    tipo_processamento = st.selectbox("Modo de Gestão", ("Gerar Folha de Adiantamento", "Gerar Folha de Pagamento", "Simular Férias", "Simular Rescisão"), label_visibility="collapsed")

    st.divider()
    st.subheader("Seleção de Empresa")
    
    empresas_selecionadas_nomes = st.multiselect(
        "Selecione uma ou mais empresas:",
        options=list(EMPRESAS.keys()),
        default=list(EMPRESAS.keys())[0] if EMPRESAS else []
    )

st.header(tipo_processamento)
st.caption("Selecione as empresas e o tipo de processamento, depois clique em 'Gerar Relatórios'.")

if st.button("Gerar Relatórios", type="primary", use_container_width=True):
    
    if not empresas_selecionadas_nomes:
        st.warning("Por favor, selecione pelo menos uma empresa na barra lateral.")
    elif tipo_processamento != "Gerar Folha de Adiantamento":
        st.info(f"A funcionalidade '{tipo_processamento}' será implementada em breve.")
    else:
        st.subheader("Resultados do Processamento")
        error_container = st.container()
        
        for nome_empresa in empresas_selecionadas_nomes:
            codigo_empresa = EMPRESAS.get(nome_empresa)
            
            with st.container(border=True):
                st.markdown(f"#### {nome_empresa}")
                try:
                    if codigo_empresa == "9098":
                        with st.spinner(f"Processando {nome_empresa} para {mes_selecionado:02d}/{ano_selecionado}..."):
                            elegiveis_df, inelegiveis_df = run(empresa_codigo=codigo_empresa, ano=ano_selecionado, mes=mes_selecionado)
                        
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("Elegíveis", len(elegiveis_df))
                        c2.metric("Inelegíveis", len(inelegiveis_df))
                        c3.metric("Total", len(elegiveis_df) + len(inelegiveis_df))
                        
                        valor_total_pago = elegiveis_df['ValorLiquidoAdiantamento'].sum()
                        valor_formatado = f"R$ {valor_total_pago:_.2f}".replace('.', ',').replace('_', '.')
                        c4.metric("Valor Total a Pagar", valor_formatado)

                        if not inelegiveis_df.empty:
                            with st.expander("Ver detalhes dos funcionários inelegíveis"):
                                # ADICIONADO 'Cargo'
                                st.dataframe(inelegiveis_df[['Matricula', 'Nome', 'Cargo', 'Observacoes']], use_container_width=True)
                        
                        if not elegiveis_df.empty:
                            st.markdown("---")
                            st.subheader("✅ Detalhes dos Funcionários Elegíveis")
                            
                            # ADICIONADO 'Cargo'
                            colunas_elegiveis = ['Matricula', 'Nome', 'Cargo', 'SalarioContratual', 'ValorAdiantamentoBruto', 'ValorDesconto', 'ValorLiquidoAdiantamento']
                            
                            df_display = elegiveis_df[colunas_elegiveis].copy()
                            for col in ['SalarioContratual', 'ValorAdiantamentoBruto', 'ValorDesconto', 'ValorLiquidoAdiantamento']:
                                if col in df_display.columns:
                                     df_display[col] = df_display[col].apply(lambda x: f"R$ {x:_.2f}".replace('.', ',').replace('_', '.') if pd.notna(x) else "R$ 0,00")

                            st.dataframe(df_display, use_container_width=True)

                            csv = elegiveis_df[colunas_elegiveis].to_csv(index=False, sep=';', decimal=',').encode('utf-8')
                            st.download_button(
                               label="Baixar Relatório de Elegíveis (CSV)",
                               data=csv,
                               file_name=f"adiantamento_elegiveis_{codigo_empresa}_{date.today().strftime('%Y-%m-%d')}.csv",
                               mime="text/csv",
                               key=f"download_elegiveis_{codigo_empresa}"
                            )
                    else:
                        st.info(f"As regras de negócio para a empresa {nome_empresa} ainda não foram implementadas.")

                except Exception as e:
                    log.error(f"Falha crítica ao processar {nome_empresa}: {e}")
                    with error_container:
                        st.error(f"**Erro de Execução em '{nome_empresa}':** {e}", icon="🚨")