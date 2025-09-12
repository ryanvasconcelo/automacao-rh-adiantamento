# main.py (VERSÃO DE PRODUÇÃO FINAL)

import pandas as pd
import numpy as np
from src.data_extraction import fetch_employee_base_data, fetch_employee_leaves, fetch_employee_loans
from src.business_logic import processar_regras_e_calculos_jr, aplicar_descontos_consignado
from src.file_generator import gerar_arquivo_final
from config.logging_config import log

def run(empresa_codigo: str, ano: int, mes: int):
    log.info(f"--- INICIANDO AUTOMAÇÃO PARA EMPRESA {empresa_codigo} | COMPETÊNCIA: {ano}-{mes:02d} ---")
    
    base_df = fetch_employee_base_data(emp_codigo=empresa_codigo, ano=ano, mes=mes)
    if base_df is None or base_df.empty:
        log.warning(f"Nenhum funcionário ativo encontrado para a empresa {empresa_codigo}. Encerrando.")
        return pd.DataFrame(), pd.DataFrame()
    
    employee_ids = base_df['Matricula'].tolist()
    leaves_df = fetch_employee_leaves(emp_codigo=empresa_codigo, employee_ids=employee_ids, ano=ano, mes=mes)
    loans_df = fetch_employee_loans(emp_codigo=empresa_codigo, employee_ids=employee_ids, ano=ano, mes=mes)
    
    merged_df = pd.merge(base_df, leaves_df, on='Matricula', how='left')
    
    if loans_df is not None and not loans_df.empty:
        final_df = pd.merge(merged_df, loans_df, on='Matricula', how='left')
    else:
        final_df = merged_df

    final_df = final_df.replace({np.nan: None, pd.NaT: None})
    
    analise_df = processar_regras_e_calculos_jr(final_df, ano=ano, mes=mes)
    
    status_para_relatorio_final = ['Elegível', 'Inelegível_Reportar']
    elegiveis_para_relatorio_df = analise_df[analise_df['StatusDetalhado'].isin(status_para_relatorio_final)].copy()

    inelegiveis_para_analise_df = analise_df[analise_df['StatusDetalhado'] == 'Inelegível_Omitir'].copy()
    
    elegiveis_final_df = aplicar_descontos_consignado(elegiveis_para_relatorio_df)
    
    gerar_arquivo_final(elegiveis_final_df, empresa_codigo=empresa_codigo)
    
    log.success("--- PROCESSO CONCLUÍDO ---")
    
    return elegiveis_final_df, inelegiveis_para_analise_df
    
if __name__ == "__main__":
    run(empresa_codigo='9098', ano=2025, mes=8)