# src/business_logic.py (Versão Multi-Empresa)

import pandas as pd
import numpy as np
from datetime import date
import math

# ATUALIZAÇÃO: Importa o objeto de regra para type hinting
from .rules_catalog import CompanyRule


def arredondar_especial_rh(valor: float) -> float:
    if valor is None or pd.isna(valor):
        return 0.0
    if (valor - int(valor)) > 0.500001:
        return float(math.ceil(valor))
    else:
        return float(math.floor(valor))


def arredondar_fortes(valor: float) -> float:
    return round(valor or 0.0, 2)


# ATUALIZAÇÃO: Função renomeada e agora recebe 'rule'
def processar_regras(
    df: pd.DataFrame, rule: CompanyRule, ano: int, mes: int
) -> pd.DataFrame:
    analise_df = df.copy()

    for col in ["AdmissaoData", "DtRescisao", "DtInicio", "DtFim"]:
        if col in analise_df.columns:
            analise_df[col] = pd.to_datetime(analise_df[col], errors="coerce")
    for col in [
        "ValorParcelaConsignado",
        "ValorQuebraCaixa",
        "ValorGratificacao",
        "ValorFixoAdiant",
    ]:
        if col not in analise_df.columns:
            analise_df[col] = 0.0
    fill_values = {
        "ValorParcelaConsignado": 0.0,
        "ValorQuebraCaixa": 0.0,
        "ValorGratificacao": 0.0,
        "ValorFixoAdiant": 0.0,
    }
    analise_df.fillna(value=fill_values, inplace=True)

    def analisar_funcionario(row):
        # ... (Esta função interna permanece a mesma) ...
        status = "Elegível"
        dias_a_considerar = 30.0
        observacoes = []
        inicio_mes = date(ano, mes, 1)
        fim_mes = date(ano, mes, 30)
        data_pagamento = date(ano, mes, 20)
        admissao = row["AdmissaoData"].date() if pd.notna(row["AdmissaoData"]) else None
        rescisao = row["DtRescisao"].date() if pd.notna(row["DtRescisao"]) else None
        inicio_afast = row["DtInicio"].date() if pd.notna(row["DtInicio"]) else None
        fim_afast = row["DtFim"].date() if pd.notna(row["DtFim"]) else None
        codigo_licenca = row["CodigoTipoLicenca"]
        tem_consignado = row["ValorParcelaConsignado"] > 0
        CODIGO_FERIAS = "01"
        CODIGOS_LICENCA_MATERNIDADE = ["02", "07", "09", "10", "11", "22"]
        CODIGOS_AFASTAMENTO_DOENCA = ["03", "04", "12", "13", "14", "15"]
        if rescisao and rescisao <= data_pagamento:
            status = "Inelegível"
            observacoes.append(f"Rescisão em {rescisao.strftime('%d/%m/%Y')}")
        elif row["FlagAdiantamento"] != "S":
            status = "Inelegível"
            observacoes.append("Flag adiantamento desabilitado")
        elif (
            admissao
            and admissao.year == ano
            and admissao.month == mes
            and admissao.day > 10
        ):
            status = "Inelegível"
            observacoes.append(f"Admissão em {admissao.strftime('%d/%m/%Y')}")
        if status == "Inelegível":
            row["Status"] = status
            row["Observacoes"] = "; ".join(observacoes)
            row["DiasTrabalhados"] = 0
            return row
        if pd.notna(inicio_afast):
            if codigo_licenca in CODIGOS_LICENCA_MATERNIDADE:
                observacoes.append("Licença Maternidade (Elegível por regra)")
            elif (
                codigo_licenca == CODIGO_FERIAS
                and fim_afast
                and fim_afast.year == ano
                and fim_afast.month == mes
                and fim_afast.day < 15
            ):
                observacoes.append(f"Retorno de férias em {fim_afast.day + 1}/{mes}")
                dias_a_considerar = 30 - fim_afast.day
            elif codigo_licenca in CODIGOS_AFASTAMENTO_DOENCA:
                fim_efetivo_afastamento = fim_afast if pd.notna(fim_afast) else fim_mes
                dias_de_licenca_no_mes = (
                    min(fim_mes, fim_efetivo_afastamento)
                    - max(inicio_mes, inicio_afast)
                ).days + 1
                if dias_de_licenca_no_mes >= 16:
                    status = "Inelegível"
                    observacoes.append(
                        f"{dias_de_licenca_no_mes} dias de licença médica no mês"
                    )
            elif (
                codigo_licenca == CODIGO_FERIAS
                and inicio_afast.year == ano
                and inicio_afast.month == mes
                and inicio_afast.day < 16
                and not tem_consignado
            ):
                status = "Inelegível"
                observacoes.append("Férias iniciadas antes do dia 16 (sem consignado)")
            elif inicio_afast < inicio_mes:
                status = "Inelegível"
                observacoes.append(
                    f"Afastamento (Outros/Cód: {codigo_licenca}) desde {inicio_afast.strftime('%d/%m/%Y')}"
                )
        row["Status"] = status
        row["Observacoes"] = "; ".join(observacoes) if observacoes else "N/A"
        row["DiasTrabalhados"] = max(0, dias_a_considerar)
        return row

    analise_df = analise_df.apply(analisar_funcionario, axis=1)
    elegiveis = analise_df["Status"] == "Elegível"
    analise_df["ValorAdiantamentoBruto"] = 0.0

    # ATUALIZAÇÃO: Lógica de Gerente/Subgerente agora é lida do objeto 'rule'
    if rule.special:
        mask_gerente_loja = (
            analise_df["Cargo"].str.upper().str.strip() == "GERENTE DE LOJA"
        )
        mask_sub_loja = (
            analise_df["Cargo"].str.upper().str.strip() == "SUB GERENTE DE LOJA"
        )
        analise_df.loc[elegiveis & mask_gerente_loja, "ValorAdiantamentoBruto"] = (
            rule.special.gerente_loja_value
        )
        analise_df.loc[elegiveis & mask_sub_loja, "ValorAdiantamentoBruto"] = (
            rule.special.subgerente_loja_value
        )

    mask_cargo_especial_calculado = analise_df["ValorAdiantamentoBruto"] > 0
    mask_valor_fixo = analise_df["ValorFixoAdiant"] > 0
    analise_df.loc[
        elegiveis & ~mask_cargo_especial_calculado & mask_valor_fixo,
        "ValorAdiantamentoBruto",
    ] = analise_df["ValorFixoAdiant"]

    mask_calculo_percentual = (
        elegiveis & ~mask_cargo_especial_calculado & ~mask_valor_fixo
    )
    salario = analise_df.loc[mask_calculo_percentual, "SalarioContratual"]
    percentual = analise_df.loc[mask_calculo_percentual, "PercentualAdiant"] / 100.0
    base_calculo = salario.copy()
    mask_qcaixa = analise_df.loc[mask_calculo_percentual, "ValorQuebraCaixa"] > 0
    mask_grat = analise_df.loc[mask_calculo_percentual, "ValorGratificacao"] > 0
    base_calculo.loc[mask_qcaixa] = base_calculo.loc[mask_qcaixa] * 1.10
    base_calculo.loc[mask_grat] = base_calculo.loc[mask_grat] * 1.40
    analise_df.loc[mask_calculo_percentual, "ValorAdiantamentoBruto"] = (
        base_calculo * percentual
    )

    mask_proporcional = analise_df["DiasTrabalhados"] < 30
    fator_proporcional = analise_df["DiasTrabalhados"] / 30.0
    analise_df.loc[
        elegiveis & mask_proporcional, "ValorAdiantamentoBruto"
    ] *= fator_proporcional

    # ATUALIZAÇÃO: Arredondamento agora é condicional
    if not rule.overrides.get("no_rounding", False):
        analise_df.loc[elegiveis, "ValorAdiantamentoBruto"] = analise_df.loc[
            elegiveis, "ValorAdiantamentoBruto"
        ].apply(arredondar_especial_rh)

    analise_df["ValorAdiantamentoBruto"].fillna(0, inplace=True)
    return analise_df


# ATUALIZAÇÃO: Função agora recebe 'rule'
def aplicar_descontos_consignado(
    df_calculado: pd.DataFrame, rule: CompanyRule
) -> pd.DataFrame:
    df_final = df_calculado.copy()
    df_final["ValorParcelaConsignado"] = df_final["ValorParcelaConsignado"].fillna(0.0)
    df_final["SalarioContratual"] = df_final["SalarioContratual"].fillna(0.0)
    df_final["ValorFixoAdiant"] = df_final["ValorFixoAdiant"].fillna(0.0)

    df_final["PercentualDescontoConsignado"] = 0.40
    mask_valor_fixo = df_final["ValorFixoAdiant"] > 0
    salario_base = df_final.loc[mask_valor_fixo, "SalarioContratual"]
    adiantamento_fixo = df_final.loc[mask_valor_fixo, "ValorFixoAdiant"]

    percentual_bruto = adiantamento_fixo.divide(salario_base.replace(0, pd.NA)).fillna(
        0
    )
    percentual_arredondado = (np.floor(percentual_bruto * 100)) / 100
    df_final.loc[mask_valor_fixo, "PercentualDescontoConsignado"] = (
        percentual_arredondado
    )

    valor_desconto = (
        df_final["ValorParcelaConsignado"] * df_final["PercentualDescontoConsignado"]
    )

    # ATUALIZAÇÃO: Arredondamento agora é condicional
    if not rule.overrides.get("no_rounding", False):
        df_final["ValorDesconto"] = valor_desconto.apply(arredondar_fortes)
    else:
        df_final["ValorDesconto"] = valor_desconto

    df_final["ValorLiquidoAdiantamento"] = (
        df_final["ValorAdiantamentoBruto"] - df_final["ValorDesconto"]
    )
    df_final.loc[
        df_final["ValorLiquidoAdiantamento"] < 0, "ValorLiquidoAdiantamento"
    ] = 0

    # Adiciona observação sobre o consignado
    mask_consignado = df_final["ValorParcelaConsignado"] > 0

    def append_obs(row):
        obs = row["Observacoes"]
        parcela = row["ValorParcelaConsignado"]
        new_obs = f"Consignado Parcela: R${parcela:.2f}"
        if obs and obs != "N/A":
            return f"{obs}; {new_obs}"
        return new_obs

    df_final.loc[mask_consignado, "Observacoes"] = df_final[mask_consignado].apply(
        append_obs, axis=1
    )

    df_final.drop(columns=["PercentualDescontoConsignado"], inplace=True)
    return df_final
