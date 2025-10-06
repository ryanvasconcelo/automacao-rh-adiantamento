import pandas as pd
import numpy as np
from src.data_extraction import (
    fetch_employee_base_data,
    fetch_employee_leaves,
    fetch_employee_loans,
    fetch_employee_events,
    fetch_raw_advance_payroll,
)
from src.rules_catalog import get_company_rule
from src.business_logic import processar_regras, aplicar_descontos_consignado


def run(
    empresa_codigo: str, empresa_id_catalogo: str, ano: int, mes: int
) -> pd.DataFrame:
    print(f"--- INICIANDO AUDITORIA PARA EMPRESA {empresa_codigo} ...")
    regra_empresa = get_company_rule(empresa_id_catalogo)

    # --- ETAPA 1: BUSCAR FOLHA BRUTA DO FORTES ---
    print("Buscando folha bruta do Fortes...")
    df_bruto_fortes = fetch_raw_advance_payroll(empresa_codigo, ano, mes)

    # --- ETAPA 2: GERAR FOLHA COM NOSSAS REGRAS ---
    print("Processando folha com regras de negócio...")
    base_df = fetch_employee_base_data(emp_codigo=empresa_codigo, ano=ano, mes=mes)
    if base_df.empty:
        return pd.DataFrame()

    employee_ids = base_df["Matricula"].tolist()
    leaves_df = fetch_employee_leaves(empresa_codigo, employee_ids, ano, mes)
    loans_df = fetch_employee_loans(empresa_codigo, employee_ids, ano, mes)
    events_df = fetch_employee_events(empresa_codigo, employee_ids, ano, mes, [])

    final_df = pd.merge(base_df, leaves_df, on="Matricula", how="left")
    if not events_df.empty:
        final_df = pd.merge(final_df, events_df, on="Matricula", how="left")
    if not loans_df.empty:
        final_df = pd.merge(final_df, loans_df, on="Matricula", how="left")
    final_df = final_df.replace({np.nan: None, pd.NaT: None})

    df_com_regras = processar_regras(final_df, rule=regra_empresa, ano=ano, mes=mes)
    elegiveis_mask = df_com_regras["Status"] == "Elegível"
    df_elegiveis_com_desconto = aplicar_descontos_consignado(
        df_com_regras[elegiveis_mask].copy(), rule=regra_empresa
    )
    df_com_regras_final = pd.concat(
        [df_elegiveis_com_desconto, df_com_regras[~elegiveis_mask]], ignore_index=True
    )

    # --- ETAPA 3: COMPARAÇÃO E GERAÇÃO DO RELATÓRIO DE AUDITORIA ---
    print("Comparando resultados e gerando relatório de auditoria...")
    df_auditoria = pd.merge(
        df_com_regras_final,
        df_bruto_fortes[["Matricula", "ValorBrutoFortes"]],
        on="Matricula",
        how="outer",
        indicator=True,
    )

    # --- CORREÇÃO DEFINITIVA DO FILLNA ---
    # Primeiro, preenche colunas numéricas específicas com 0.0
    numeric_cols_to_fill = [
        "ValorLiquidoAdiantamento",
        "ValorBrutoFortes",
        "ValorDesconto",
        "SalarioContratual",
        "PercentualAdiant",
    ]
    for col in numeric_cols_to_fill:
        if col in df_auditoria.columns:
            df_auditoria[col] = df_auditoria[col].fillna(0.0)

    # Depois, preenche as colunas de texto (object) com string vazia
    object_cols = df_auditoria.select_dtypes(include="object").columns
    df_auditoria[object_cols] = df_auditoria[object_cols].fillna("")

    def analisar_divergencia(row):
        valor_regras = row["ValorLiquidoAdiantamento"]
        valor_fortes = row["ValorBrutoFortes"]

        if row["_merge"] == "left_only":
            return (
                "Removido pelas regras (Correto)"
                if row["Status"] == "Inelegível"
                else "Na folha de regras, mas não na do Fortes (INCONSISTÊNCIA GRAVE)"
            )
        elif row["_merge"] == "right_only":
            return "Na folha do Fortes, mas removido pelas nossas regras"
        elif abs(valor_regras - valor_fortes) > 0.01:
            return f"Divergência de valor (Regras: R${valor_regras:.2f} vs Fortes: R${valor_fortes:.2f})"
        else:
            return "OK"

    df_auditoria["Analise"] = df_auditoria.apply(analisar_divergencia, axis=1)

    colunas_finais = [
        "Matricula",
        "Nome",
        "Cargo",
        "Analise",
        "Status",
        "Observacoes",
        "ValorBrutoFortes",
        "ValorLiquidoAdiantamento",
        "ValorDesconto",
        "SalarioContratual",
        "PercentualAdiant",
    ]
    for col in colunas_finais:
        if col not in df_auditoria.columns:
            df_auditoria[col] = ""

    df_auditoria = df_auditoria[colunas_finais].sort_values(by="Nome")

    print("--- PROCESSO DE AUDITORIA CONCLUÍDO ---")
    return df_auditoria


# (A função build_summary permanece a mesma)
def build_summary(
    df_resultado: pd.DataFrame, codigo_empresa: str
) -> pd.DataFrame:  # ...
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
