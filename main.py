# main.py (Versão Final e Robusta)

from src.data_extraction import fetch_employee_base_data, fetch_employee_leaves, fetch_employee_loans, fetch_all_companies
from src.data_validation import validate_employee_data
from src.business_logic import processar_regras_e_calculos_jr, aplicar_descontos_consignado
from src.file_generator import gerar_arquivo_final
from config.logging_config import log
import pandas as pd
import numpy as np

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 150)

def run(empresa_codigo: str, ano: int, mes: int):
    """
    Função principal que orquestra o fluxo para um período específico.
    """
    log.info(f"--- INICIANDO AUTOMAÇÃO PARA EMPRESA {empresa_codigo} | COMPETÊNCIA: {ano}-{mes:02d} ---")
    
    base_df = fetch_employee_base_data(emp_codigo=empresa_codigo, ano=ano, mes=mes)
    if base_df is None or base_df.empty:
        log.warning(f"Nenhum funcionário ativo encontrado para a empresa {empresa_codigo}. Encerrando.")
        return pd.DataFrame(), pd.DataFrame()
    
    employee_ids = base_df['Matricula'].tolist()
    leaves_df = fetch_employee_leaves(emp_codigo=empresa_codigo, employee_ids=employee_ids, ano=ano, mes=mes)
    loans_df = fetch_employee_loans(emp_codigo=empresa_codigo, employee_ids=employee_ids, ano=ano, mes=mes)
    
    merged_df = pd.merge(base_df, leaves_df, on='Matricula', how='left')
    
    # Verificação para juntar os empréstimos apenas se houver dados
    if loans_df is not None and not loans_df.empty:
        final_df = pd.merge(merged_df, loans_df, on='Matricula', how='left')
    else:
        final_df = merged_df

    final_df = final_df.replace({np.nan: None})
    validated_df = validate_employee_data(final_df)
    
    analise_df = processar_regras_e_calculos_jr(validated_df, ano=ano, mes=mes)
    
    elegiveis_df = analise_df[analise_df['Status'] == 'Elegível'].copy()
    inelegiveis_df = analise_df[analise_df['Status'] == 'Inelegível'].copy()
    
    elegiveis_final_df = aplicar_descontos_consignado(elegiveis_df)
    
    gerar_arquivo_final(elegiveis_final_df, empresa_codigo=empresa_codigo)
    
    log.success("--- PROCESSO CONCLUÍDO ---")
    
    return elegiveis_final_df, inelegiveis_df

if __name__ == "__main__":
    run(empresa_codigo='9098', ano=2025, mes=8)
