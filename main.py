# main.py (Versão Final com Pré-Limpeza)

from src.data_extraction import fetch_employee_base_data, fetch_employee_leaves
from src.data_validation import validate_employee_data
from src.business_logic import aplicar_regras_elegibilidade_jr
from config.logging_config import log
import pandas as pd
import numpy as np  # Importamos o numpy

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 120) 

CODIGO_EMPRESA = '9098'

def run():
    log.info(f"--- INICIANDO AUTOMAÇÃO DE ADIANTAMENTO PARA EMPRESA {CODIGO_EMPRESA} ---")
    
    # ETAPA 1: EXTRAÇÃO
    base_df = fetch_employee_base_data(emp_codigo=CODIGO_EMPRESA)
    if base_df is None or base_df.empty:
        log.warning("Nenhum funcionário ativo encontrado para processar. Encerrando.")
        return
    log.info(f"Encontrados {len(base_df)} funcionários ativos na base.")

    employee_ids = base_df['Matricula'].tolist()
    leaves_df = fetch_employee_leaves(emp_codigo=CODIGO_EMPRESA, employee_ids=employee_ids)
    log.info(f"Encontrados {len(leaves_df)} registros de afastamento/licenças para o período.")
    
    # ETAPA 2: CONSOLIDAÇÃO
    final_df = pd.merge(base_df, leaves_df, on='Matricula', how='left')
    
    # ETAPA 3 (NOVA): PRÉ-LIMPEZA UNIVERSAL DOS DADOS
    # Substituímos todos os NaN (float) do pandas pelo None (NoneType) do Python.
    # Isso resolve o conflito de tipos antes de chegar no Pydantic.
    final_df = final_df.replace({np.nan: None})
    
    # ETAPA 4: VALIDAÇÃO
    validated_df = validate_employee_data(final_df)
    
    # ETAPA 5: LÓGICA DE NEGÓCIO
    analise_df = aplicar_regras_elegibilidade_jr(validated_df)
    
    # ... (o resto do arquivo para gerar o relatório permanece o mesmo)
    # ... (copie o final do seu main.py anterior aqui)
    log.success("--- PROCESSO CONCLUÍDO ---")

if __name__ == "__main__":
    run()