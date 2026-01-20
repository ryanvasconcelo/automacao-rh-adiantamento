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
    fetch_real_advance_values,  # <--- IMPORT NOVO
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

    # 2. Busca Dados Fortes
    # A) Cadastro (Teórico base) - Mantemos para referência de cadastro
    print("Buscando dados de cadastro (Teórico)...")
    df_bruto_fortes = fetch_raw_advance_payroll(empresa_codigo, ano, mes)

    # B) Eventos Reais (O que foi calculado de verdade na folha)
    print("Buscando valores reais da folha (Eventos)...")
    df_real_fortes = fetch_real_advance_values(empresa_codigo, ano, mes)

    # --- SANITIZAÇÃO DE DADOS ---
    if not df_bruto_fortes.empty:
        if "ValorBrutoFortes" in df_bruto_fortes.columns:
            df_bruto_fortes["ValorBrutoFortes"] = pd.to_numeric(
                df_bruto_fortes["ValorBrutoFortes"], errors="coerce"
            ).fillna(0.0)
    else:
        df_bruto_fortes = pd.DataFrame(columns=["Matricula", "ValorBrutoFortes"])

    if not df_real_fortes.empty:
        df_real_fortes["ValorRealFortes"] = pd.to_numeric(
            df_real_fortes["ValorRealFortes"], errors="coerce"
        ).fillna(0.0)
    else:
        df_real_fortes = pd.DataFrame(columns=["Matricula", "ValorRealFortes"])
    # ---------------------------

    # 3. Busca Dados para Cálculo Próprio (Regras de Negócio)
    print("Processando cálculo paralelo...")
    base_df = fetch_employee_base_data(emp_codigo=empresa_codigo, ano=ano, mes=mes)

    if base_df.empty:
        print(f"AVISO: Nenhum funcionário encontrado na base.")
        return pd.DataFrame()

    employee_ids = base_df["Matricula"].tolist()
    leaves_df = fetch_employee_leaves(empresa_codigo, employee_ids, ano, mes)
    loans_df = fetch_employee_loans(empresa_codigo, employee_ids, ano, mes)
    events_df = fetch_employee_events(empresa_codigo, employee_ids, ano, mes, [])

    # Merges Cálculo Próprio
    final_df = pd.merge(base_df, leaves_df, on="Matricula", how="left")
    if not events_df.empty:
        final_df = pd.merge(final_df, events_df, on="Matricula", how="left")
    if not loans_df.empty:
        final_df = pd.merge(final_df, loans_df, on="Matricula", how="left")

    final_df = final_df.replace({np.nan: None, pd.NaT: None})

    # Processamento Lógico (Engine Python)
    df_com_regras = processar_regras(final_df, rule=regra_empresa, ano=ano, mes=mes)

    elegiveis_mask = df_com_regras["Status"] == "Elegível"
    df_elegiveis_com_desconto = aplicar_descontos_consignado(
        df_com_regras[elegiveis_mask].copy(), rule=regra_empresa
    )

    df_com_regras_final = pd.concat(
        [df_elegiveis_com_desconto, df_com_regras[~elegiveis_mask]], ignore_index=True
    )

    # 4. Consolidação Final (Merge de Tudo)
    print("Consolidando dados...")

    # Merge 1: Nossos Cálculos + Cadastro Fortes (Teórico)
    df_step1 = pd.merge(
        df_com_regras_final,
        df_bruto_fortes[["Matricula", "ValorBrutoFortes"]],
        on="Matricula",
        how="outer",
        indicator=False,
    )

    # Merge 2: Resultado + Valores Reais (Eventos)
    df_auditoria = pd.merge(
        df_step1,
        df_real_fortes[["Matricula", "ValorRealFortes"]],
        on="Matricula",
        how="outer",
        indicator=True,
    )

    # Preenchimento de Nulos e Tipagem
    cols_numericas = [
        "ValorLiquidoAdiantamento",
        "ValorBrutoFortes",
        "ValorRealFortes",
        "ValorDesconto",
        "SalarioContratual",
        "PercentualAdiant",
    ]
    for col in cols_numericas:
        if col not in df_auditoria.columns:
            df_auditoria[col] = 0.0
        df_auditoria[col] = pd.to_numeric(df_auditoria[col], errors="coerce").fillna(
            0.0
        )

    cols_texto = df_auditoria.select_dtypes(include="object").columns
    df_auditoria[cols_texto] = df_auditoria[cols_texto].fillna("")

    # Análise de Divergência Atualizada (O CORAÇÃO DA MUDANÇA)
    def analisar_divergencia(row):
        valor_nosso = float(row.get("ValorLiquidoAdiantamento", 0))
        valor_real_fortes = float(row.get("ValorRealFortes", 0))
        valor_teorico_fortes = float(row.get("ValorBrutoFortes", 0))
        status = row.get("Status", "Desconhecido")

        # Cenário 1: Só existe na nossa regra (Provavelmente demitido ou erro de filtro)
        if row["_merge"] == "left_only":
            return (
                "Removido pelas regras (Correto)"
                if status == "Inelegível"
                else "Calculado pelo sistema, mas não encontrado na folha (EFP)"
            )

        # Cenário 2: Só existe no Fortes (Não calculamos)
        if row["_merge"] == "right_only":
            return "No Fortes, mas não calculado pelo sistema (Verificar regras)"

        # Cenário 3: Folha não calculada (Valor Real é zero, mas deveria ter algo)
        if valor_real_fortes == 0 and valor_teorico_fortes > 0:
            return "Folha não calculada no Fortes (Sem eventos gerados)"

        # Cenário 4: Comparação Financeira (Nosso x Real)
        # Tolerância de 5 centavos para arredondamentos
        if abs(valor_nosso - valor_real_fortes) > 0.05:
            return f"Divergência: Sistema R${valor_nosso:.2f} vs Folha R${valor_real_fortes:.2f}"

        return "OK"

    if "_merge" in df_auditoria.columns:
        df_auditoria["Analise"] = df_auditoria.apply(analisar_divergencia, axis=1)
        df_auditoria.drop(columns=["_merge"], inplace=True)
    else:
        df_auditoria["Analise"] = "OK"

    # Seleção Final de Colunas
    colunas_finais = [
        "Matricula",
        "Nome",
        "Cargo",
        "Analise",
        "Status",
        "Observacoes",
        "ValorBrutoFortes",
        "ValorRealFortes",
        "ValorLiquidoAdiantamento",
        "ValorDesconto",
        "SalarioContratual",
        "PercentualAdiant",
    ]

    # Garante estrutura
    for col in colunas_finais:
        if col not in df_auditoria.columns:
            df_auditoria[col] = ""

    df_auditoria = df_auditoria[colunas_finais].sort_values(by="Nome")
    print(f"--- FIM: {len(df_auditoria)} registros processados ---")

    return df_auditoria
