import pandas as pd
import numpy as np
from src.data_extraction import (
    fetch_employee_base_data,
    fetch_employee_leaves,
    fetch_employee_loans,
)
from src.business_logic import (
    processar_regras_e_calculos_jr,
    aplicar_descontos_consignado,
)


def run(empresa_codigo: str, ano: int, mes: int):
    """
    Função principal que orquestra a extração e processamento dos dados.
    """
    print(
        f"--- INICIANDO AUTOMAÇÃO PARA EMPRESA {empresa_codigo} | COMPETÊNCIA: {ano}-{mes:02d} ---"
    )

    base_df = fetch_employee_base_data(emp_codigo=empresa_codigo, ano=ano, mes=mes)
    if base_df is None or base_df.empty:
        print(f"Nenhum funcionário ativo encontrado para a empresa {empresa_codigo}.")
        return pd.DataFrame()

    employee_ids = base_df["Matricula"].tolist()
    leaves_df = fetch_employee_leaves(
        emp_codigo=empresa_codigo, employee_ids=employee_ids, ano=ano, mes=mes
    )
    loans_df = fetch_employee_loans(
        emp_codigo=empresa_codigo, employee_ids=employee_ids, ano=ano, mes=mes
    )

    merged_df = pd.merge(base_df, leaves_df, on="Matricula", how="left")

    if loans_df is not None and not loans_df.empty:
        final_df = pd.merge(merged_df, loans_df, on="Matricula", how="left")
    else:
        final_df = merged_df
        final_df["ValorParcelaConsignado"] = 0.0

    final_df = final_df.replace({np.nan: None, pd.NaT: None})
    final_df["ValorParcelaConsignado"].fillna(0, inplace=True)

    analise_df = processar_regras_e_calculos_jr(final_df, ano=ano, mes=mes)

    elegiveis_mask = analise_df["Status"] == "Elegível"
    df_elegiveis_com_desconto = aplicar_descontos_consignado(
        analise_df[elegiveis_mask].copy()
    )

    df_inelegiveis = analise_df[~elegiveis_mask].copy()

    # --- CORREÇÃO APLICADA AQUI ---
    # Garante que o DataFrame de inelegíveis tenha as mesmas colunas de valores que o de elegíveis.
    df_inelegiveis["ValorDesconto"] = 0.0
    df_inelegiveis["ValorLiquidoAdiantamento"] = 0.0

    resultado_completo = pd.concat(
        [df_elegiveis_com_desconto, df_inelegiveis], ignore_index=True
    )

    print("--- PROCESSO CONCLUÍDO ---")
    return resultado_completo


def build_summary(df_resultado: pd.DataFrame, codigo_empresa: str) -> pd.DataFrame:
    """Cria um DataFrame de resumo a partir do resultado completo."""
    if df_resultado is None or df_resultado.empty:
        summary_data = {
            "EmpresaCodigo": [codigo_empresa],
            "Elegiveis": [0],
            "Inelegiveis": [0],
            "Total": [0],
            "ValorTotalPagar": [0.0],
        }
        return pd.DataFrame(summary_data)

    elegiveis_df = df_resultado[df_resultado["Status"] == "Elegível"]
    total_elegiveis = len(elegiveis_df)
    total_geral = len(df_resultado)
    total_inelegiveis = total_geral - total_elegiveis
    # Agora a coluna 'ValorLiquidoAdiantamento' existirá
    valor_total = elegiveis_df["ValorLiquidoAdiantamento"].sum()

    summary_data = {
        "EmpresaCodigo": [codigo_empresa],
        "Elegiveis": [total_elegiveis],
        "Inelegiveis": [total_inelegiveis],
        "Total": [total_geral],
        "ValorTotalPagar": round(valor_total, 2),
    }
    return pd.DataFrame(summary_data)
