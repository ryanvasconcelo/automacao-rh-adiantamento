# main.py

from src.data_extraction import fetch_employee_base_data, fetch_employee_leaves
from src.business_logic import aplicar_regras_elegibilidade_jr
from config.logging_config import log
import pandas as pd

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 120)

CODIGO_EMPRESA = '9098'

def run():
    log.info(f"--- INICIANDO AUTOMAÇÃO DE ADIANTAMENTO PARA EMPRESA {CODIGO_EMPRESA} ---")
    
    base_df = fetch_employee_base_data(emp_codigo=CODIGO_EMPRESA)
    if base_df is None or base_df.empty:
        log.warning("Nenhum dado encontrado para processar. Encerrando.")
        return

    log.info(f"Encontrados {len(base_df)} funcionários ativos na base.")

    employee_ids = base_df['Matricula'].tolist()
    leaves_df = fetch_employee_leaves(emp_codigo=CODIGO_EMPRESA, employee_ids=employee_ids)
    log.info(f"Encontrados {len(leaves_df)} registros de afastamento para o período.")
    
    merged_df = pd.merge(base_df, leaves_df, on='Matricula', how='left')
    
    analise_df = aplicar_regras_elegibilidade_jr(merged_df)
    
    elegiveis_df = analise_df[analise_df['Status'] == 'Elegível']
    inelegiveis_df = analise_df[analise_df['Status'] == 'Inelegível']
    correcao_df = analise_df[analise_df['Status'] == 'Requer Correção']
    
    log.info("--- RELATÓRIO DE ANÁLISE DE ELEGIBILIDADE ---")
    log.info(f"Total de funcionários analisados: {len(analise_df)}")
    log.info(f"Funcionários Elegíveis: {len(elegiveis_df)}")
    log.info(f"Funcionários Inelegíveis: {len(inelegiveis_df)}")
    log.info(f"Funcionários Requerendo Correção Cadastral: {len(correcao_df)}")
    
    colunas_display = ['Matricula', 'Nome', 'AdmissaoData', 'FlagAdiantamento', 'DiasEfetivos', 'Observacoes']
    
    if not inelegiveis_df.empty:
        log.warning("--- Detalhamento de Funcionários Inelegíveis ---")
        # Usamos o método to_string() para garantir que o DataFrame seja logado corretamente.
        log.warning(f"\n{inelegiveis_df[colunas_display].to_string()}")
        
    if not correcao_df.empty:
        log.warning("--- Detalhamento de Funcionários para Correção Cadastral ---")
        log.warning(f"\n{correcao_df[colunas_display].to_string()}")
        
    log.success("--- PROCESSO CONCLUÍDO ---")

if __name__ == "__main__":
    run()