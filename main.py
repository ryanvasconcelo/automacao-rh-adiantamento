# main.py (substitua o conteúdo)

from src.data_extraction import fetch_employee_base_data, fetch_employee_leaves
from src.business_logic import aplicar_regras_elegibilidade_jr
import pandas as pd

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 120) # Ajuste a largura para melhor visualização

CODIGO_EMPRESA = '9098'

def run():
    print(f"--- INICIANDO AUTOMAÇÃO DE ADIANTAMENTO PARA EMPRESA {CODIGO_EMPRESA} ---")
    
    base_df = fetch_employee_base_data(emp_codigo=CODIGO_EMPRESA)
    if base_df is None or base_df.empty:
        print("Nenhum dado encontrado para processar. Encerrando.")
        return
    print(f"\nEncontrados {len(base_df)} funcionários ativos na base.")

    employee_ids = base_df['Matricula'].tolist()
    leaves_df = fetch_employee_leaves(emp_codigo=CODIGO_EMPRESA, employee_ids=employee_ids)
    print(f"Encontrados {len(leaves_df)} registros de afastamento para o período.")
    
    merged_df = pd.merge(base_df, leaves_df, on='Matricula', how='left')
    
    analise_df = aplicar_regras_elegibilidade_jr(merged_df)
    
    # Separação dos resultados em grupos
    elegiveis_df = analise_df[analise_df['Status'] == 'Elegível']
    inelegiveis_df = analise_df[analise_df['Status'] == 'Inelegível']
    correcao_df = analise_df[analise_df['Status'] == 'Requer Correção']
    
    print(f"\n--- RELATÓRIO DE ANÁLISE DE ELEGIBILIDADE ---")
    print(f"Total de funcionários analisados: {len(analise_df)}")
    print(f"Funcionários Elegíveis: {len(elegiveis_df)}")
    print(f"Funcionários Inelegíveis: {len(inelegiveis_df)}")
    print(f"Funcionários Requerendo Correção Cadastral: {len(correcao_df)}")
    
    colunas_display = ['Matricula', 'Nome', 'AdmissaoData', 'FlagAdiantamento', 'DiasEfetivos', 'Observacoes']
    
    if not inelegiveis_df.empty:
        print("\n--- Detalhamento de Funcionários Inelegíveis ---")
        print(inelegiveis_df[colunas_display])
        
    if not correcao_df.empty:
        print("\n--- Detalhamento de Funcionários para Correção Cadastral ---")
        print(correcao_df[colunas_display])
        
    print("\n--- PROCESSO CONCLUÍDO ---")

if __name__ == "__main__":
    run()