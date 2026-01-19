import pandas as pd
import numpy as np
from types import SimpleNamespace  # <--- Importante para criar a regra fake

# Importações dos seus módulos (mantivemos igual)
from src.data_extraction import (
    fetch_employee_base_data,
    fetch_employee_leaves,
    fetch_employee_loans,
    fetch_employee_events,
    fetch_raw_advance_payroll,
)

# Tentamos importar o catálogo, mas vamos proteger o uso dele
try:
    from src.rules_catalog import get_company_rule
except ImportError:
    get_company_rule = None

from src.business_logic import processar_regras, aplicar_descontos_consignado


# --- REGRA DE EMERGÊNCIA (FALLBACK) ---
# Se o catálogo falhar ou a empresa não existir, usaremos isso aqui.
def criar_regra_padrao():
    return SimpleNamespace(
        percentual_vt=0.06,
        dia_limite_beneficio=20,
        valor_cota_salario_familia=65.00,
        calcula_periculosidade=True,
        calcula_insalubridade=True,
        usa_calc_inss=True,
        usa_calc_irrf=True,
        usa_calc_fgts=True,
        # Códigos padrões do Fortes
        cod_salario_base="11",
        cod_inss="310",
        cod_irrf="311",
        cod_he_50="60",
        cod_he_100="61",
        cod_dsr_he="49",
        cod_adic_noturno="12",
        cod_periculosidade="13",
        cod_desconto_adiantamento="300",
        cod_faltas="321",
        cod_faltas_em_horas="319",
        cod_dsr_desconto="349",
        cod_vale_transporte="320",
        cod_vale_refeicao="319",
        cod_salario_familia="10",
        cod_salario_maternidade="8",
        cod_reembolso_salarial=None,
    )


def run(
    empresa_codigo: str, empresa_id_catalogo: str, ano: int, mes: int
) -> pd.DataFrame:
    print(f"--- INICIANDO AUDITORIA (ADIANTAMENTO) PARA {empresa_codigo} ---")

    # --- BLINDAGEM: Tenta pegar a regra, se falhar, usa a padrão ---
    try:
        if get_company_rule:
            print(f"Buscando regra para catálogo ID: {empresa_id_catalogo}")
            regra_empresa = get_company_rule(empresa_id_catalogo)
        else:
            raise Exception("Função get_company_rule não importada.")
    except Exception as e:
        print(f">>> AVISO: Erro ao buscar regra específica ({e}).")
        print(">>> USANDO REGRA PADRÃO DE EMERGÊNCIA (Para não travar).")
        regra_empresa = criar_regra_padrao()
    # -------------------------------------------------------------

    # --- ETAPA 1: BUSCAR FOLHA BRUTA DO FORTES ---
    print("Buscando folha bruta do Fortes...")
    # ATENÇÃO: Essa função busca dados de ADIANTAMENTO
    df_bruto_fortes = fetch_raw_advance_payroll(empresa_codigo, ano, mes)

    # --- ETAPA 2: GERAR FOLHA COM NOSSAS REGRAS ---
    print("Processando cálculo lógico...")
    base_df = fetch_employee_base_data(emp_codigo=empresa_codigo, ano=ano, mes=mes)

    if base_df.empty:
        print(">>> ALERTA: Nenhum funcionário ativo encontrado na base.")
        return pd.DataFrame()

    employee_ids = base_df["Matricula"].tolist()

    # Buscas auxiliares
    leaves_df = fetch_employee_leaves(empresa_codigo, employee_ids, ano, mes)
    loans_df = fetch_employee_loans(empresa_codigo, employee_ids, ano, mes)
    events_df = fetch_employee_events(empresa_codigo, employee_ids, ano, mes, [])

    # Merges (Juntar tabelas)
    final_df = pd.merge(base_df, leaves_df, on="Matricula", how="left")
    if not events_df.empty:
        final_df = pd.merge(final_df, events_df, on="Matricula", how="left")
    if not loans_df.empty:
        final_df = pd.merge(final_df, loans_df, on="Matricula", how="left")

    # Limpeza de nulos
    final_df = final_df.replace({np.nan: None, pd.NaT: None})

    # Processamento Lógico (Cálculo)
    df_com_regras = processar_regras(final_df, rule=regra_empresa, ano=ano, mes=mes)

    # Aplicação de Descontos (Consignado)
    elegiveis_mask = df_com_regras["Status"] == "Elegível"
    df_elegiveis_com_desconto = aplicar_descontos_consignado(
        df_com_regras[elegiveis_mask].copy(), rule=regra_empresa
    )

    # Reunião dos dados
    df_com_regras_final = pd.concat(
        [df_elegiveis_com_desconto, df_com_regras[~elegiveis_mask]], ignore_index=True
    )

    # --- ETAPA 3: COMPARAÇÃO E RELATÓRIO ---
    print("Comparando Calculado vs Fortes...")

    # Garante que a coluna existe no bruto para não dar erro de Key
    if "ValorBrutoFortes" not in df_bruto_fortes.columns:
        df_bruto_fortes["ValorBrutoFortes"] = 0.0

    df_auditoria = pd.merge(
        df_com_regras_final,
        df_bruto_fortes[["Matricula", "ValorBrutoFortes"]],
        on="Matricula",
        how="outer",
        indicator=True,
    )

    # Preenchimento de Nulos (Segurança)
    numeric_cols = [
        "ValorLiquidoAdiantamento",
        "ValorBrutoFortes",
        "ValorDesconto",
        "SalarioContratual",
        "PercentualAdiant",
    ]
    for col in numeric_cols:
        if col in df_auditoria.columns:
            df_auditoria[col] = df_auditoria[col].fillna(0.0)

    object_cols = df_auditoria.select_dtypes(include="object").columns
    df_auditoria[object_cols] = df_auditoria[object_cols].fillna("")

    # Análise de Divergência
    def analisar_divergencia(row):
        valor_calc = row.get("ValorLiquidoAdiantamento", 0.0)
        valor_real = row.get("ValorBrutoFortes", 0.0)

        # Se só existe no nosso cálculo e não no Fortes
        if row["_merge"] == "left_only":
            if row.get("Status") == "Inelegível":
                return "Removido pelas regras (Correto)"
            return "Calculado pelo sistema, mas não está na folha do Fortes"

        # Se só existe no Fortes e não no nosso cálculo
        elif row["_merge"] == "right_only":
            return (
                "Está no Fortes, mas o sistema não calculou (Verificar admissão/cargo)"
            )

        # Se existe nos dois, compara valores
        elif abs(valor_calc - valor_real) > 0.01:
            return f"Divergência: Calc R${valor_calc:.2f} vs Fortes R${valor_real:.2f}"

        else:
            return "OK"

    df_auditoria["Analise"] = df_auditoria.apply(analisar_divergencia, axis=1)

    # Padronização final das colunas
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

    # Ordenação e Retorno
    df_auditoria = df_auditoria[colunas_finais].sort_values(by="Nome")
    print("--- FIM DA AUDITORIA ---")
    return df_auditoria


# (Função build_summary mantida igual, apenas para compatibilidade)
def build_summary(df_resultado: pd.DataFrame, codigo_empresa: str) -> pd.DataFrame:
    if df_resultado is None or df_resultado.empty:
        return pd.DataFrame(
            {
                "EmpresaCodigo": [codigo_empresa],
                "Elegiveis": [0],
                "Inelegiveis": [0],
                "Total": [0],
                "ValorTotalPagar": [0.0],
            }
        )

    elegiveis = df_resultado[df_resultado["Status"] == "Elegível"]
    valor_total = (
        elegiveis["ValorLiquidoAdiantamento"].sum()
        if "ValorLiquidoAdiantamento" in elegiveis.columns
        else 0.0
    )

    return pd.DataFrame(
        {
            "EmpresaCodigo": [codigo_empresa],
            "Elegiveis": [len(elegiveis)],
            "Inelegiveis": [len(df_resultado) - len(elegiveis)],
            "Total": [len(df_resultado)],
            "ValorTotalPagar": [round(valor_total, 2)],
        }
    )
