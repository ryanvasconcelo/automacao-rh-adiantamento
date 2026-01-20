# backend/src/adiantamento/runner.py
import pandas as pd
import numpy as np
from types import SimpleNamespace

# Imports locais
from .data_extraction import (
    fetch_employee_base_data,
    fetch_employee_leaves,
    fetch_employee_loans,
    fetch_employee_events,
    fetch_raw_advance_payroll,
)
from .business_logic import processar_regras, aplicar_descontos_consignado
from src.rules_catalog import get_company_rule


def dict_to_obj(d):
    """Converte dicionário em objeto SimpleNamespace recursivamente."""
    if isinstance(d, dict):
        return SimpleNamespace(**{k: dict_to_obj(v) for k, v in d.items()})
    return d


def run(
    empresa_codigo: str, empresa_id_catalogo: str, ano: int, mes: int
) -> pd.DataFrame:
    print(f"--- INICIANDO AUDITORIA PARA EMPRESA {empresa_codigo} ...")

    # 1. Busca e Prepara a Regra
    raw_rule = get_company_rule(empresa_id_catalogo)
    regra_empresa = dict_to_obj(raw_rule) if isinstance(raw_rule, dict) else raw_rule

    # 2. Busca Folha Bruta (Fortes)
    print("Buscando folha bruta do Fortes...")
    df_bruto_fortes = fetch_raw_advance_payroll(empresa_codigo, ano, mes)

    # --- SANITIZAÇÃO DE DADOS (CRÍTICO) ---
    # Converte 'ValorBrutoFortes' para numérico, forçando erros a virar NaN e depois 0.0
    if not df_bruto_fortes.empty:
        if "ValorBrutoFortes" in df_bruto_fortes.columns:
            df_bruto_fortes["ValorBrutoFortes"] = pd.to_numeric(
                df_bruto_fortes["ValorBrutoFortes"], errors="coerce"
            ).fillna(0.0)
        else:
            df_bruto_fortes["ValorBrutoFortes"] = 0.0
    else:
        # Se vazio, cria estrutura mínima para não quebrar o merge
        df_bruto_fortes = pd.DataFrame(columns=["Matricula", "ValorBrutoFortes"])
    # --------------------------------------

    # 3. Busca Dados para Cálculo
    print("Processando folha com regras de negócio...")
    base_df = fetch_employee_base_data(emp_codigo=empresa_codigo, ano=ano, mes=mes)

    if base_df.empty:
        print(f"AVISO: Nenhum funcionário encontrado na base.")
        return pd.DataFrame()

    employee_ids = base_df["Matricula"].tolist()
    leaves_df = fetch_employee_leaves(empresa_codigo, employee_ids, ano, mes)
    loans_df = fetch_employee_loans(empresa_codigo, employee_ids, ano, mes)
    events_df = fetch_employee_events(empresa_codigo, employee_ids, ano, mes, [])

    # Merges
    final_df = pd.merge(base_df, leaves_df, on="Matricula", how="left")
    if not events_df.empty:
        final_df = pd.merge(final_df, events_df, on="Matricula", how="left")
    if not loans_df.empty:
        final_df = pd.merge(final_df, loans_df, on="Matricula", how="left")

    final_df = final_df.replace({np.nan: None, pd.NaT: None})

    # Processamento Lógico
    df_com_regras = processar_regras(final_df, rule=regra_empresa, ano=ano, mes=mes)

    elegiveis_mask = df_com_regras["Status"] == "Elegível"
    df_elegiveis_com_desconto = aplicar_descontos_consignado(
        df_com_regras[elegiveis_mask].copy(), rule=regra_empresa
    )

    df_com_regras_final = pd.concat(
        [df_elegiveis_com_desconto, df_com_regras[~elegiveis_mask]], ignore_index=True
    )

    # 4. Comparação
    print("Comparando resultados e gerando relatório de auditoria...")
    df_auditoria = pd.merge(
        df_com_regras_final,
        df_bruto_fortes[["Matricula", "ValorBrutoFortes"]],
        on="Matricula",
        how="outer",
        indicator=True,
    )

    # Preenchimento de Nulos
    cols_numericas = [
        "ValorLiquidoAdiantamento",
        "ValorBrutoFortes",
        "ValorDesconto",
        "SalarioContratual",
        "PercentualAdiant",
    ]
    for col in cols_numericas:
        if col in df_auditoria.columns:
            df_auditoria[col] = pd.to_numeric(
                df_auditoria[col], errors="coerce"
            ).fillna(0.0)

    cols_texto = df_auditoria.select_dtypes(include="object").columns
    df_auditoria[cols_texto] = df_auditoria[cols_texto].fillna("")

    # Análise de Divergência
    def analisar_divergencia(row):
        # Agora seguro pois garantimos que são floats
        valor_regras = float(row.get("ValorLiquidoAdiantamento", 0))
        valor_fortes = float(row.get("ValorBrutoFortes", 0))

        if row["_merge"] == "left_only":
            return (
                "Removido pelas regras (Correto)"
                if row.get("Status") == "Inelegível"
                else "Calculado pelo sistema, ausente no Fortes"
            )
        elif row["_merge"] == "right_only":
            return "No Fortes, mas não calculado pelo sistema"
        elif abs(valor_regras - valor_fortes) > 0.01:
            return (
                f"Divergência: Calc R${valor_regras:.2f} vs Fortes R${valor_fortes:.2f}"
            )
        else:
            return "OK"

    if "_merge" in df_auditoria.columns:
        df_auditoria["Analise"] = df_auditoria.apply(analisar_divergencia, axis=1)
        df_auditoria.drop(columns=["_merge"], inplace=True)
    else:
        df_auditoria["Analise"] = "OK"

    # Ordenação e Seleção Final
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
    print(f"--- FIM: {len(df_auditoria)} registros processados ---")

    return df_auditoria
