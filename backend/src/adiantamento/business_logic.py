# src/business_logic.py (Versão Blindada contra Strings)

import pandas as pd
import numpy as np
from datetime import date
import math
import calendar

# Importa o objeto de regra para type hinting
from src.rules_catalog import CompanyRule


def arredondar_especial_rh(valor: float) -> float:
    if valor is None or pd.isna(valor):
        return 0.0
    if (valor - int(valor)) > 0.500001:
        return float(math.ceil(valor))
    else:
        return float(math.floor(valor))


def arredondar_fortes(valor: float) -> float:
    return round(valor or 0.0, 2)


def processar_regras(
    df: pd.DataFrame, rule: CompanyRule, ano: int, mes: int
) -> pd.DataFrame:
    analise_df = df.copy()

    # --- 1. SANITIZAÇÃO DE DATAS ---
    for col in ["AdmissaoData", "DtRescisao", "DtInicio", "DtFim"]:
        if col in analise_df.columns:
            analise_df[col] = pd.to_datetime(analise_df[col], errors="coerce")

    # --- 2. SANITIZAÇÃO NUMÉRICA (A CORREÇÃO DO ERRO) ---
    # Forçamos essas colunas a serem números. Se for texto, vira número. Se falhar, vira 0.0.
    numeric_cols = [
        "ValorParcelaConsignado",
        "ValorQuebraCaixa",
        "ValorGratificacao",
        "ValorFixoAdiant",
        "SalarioContratual",
        "PercentualAdiant",
    ]

    for col in numeric_cols:
        if col not in analise_df.columns:
            analise_df[col] = 0.0
        else:
            # Converte para numérico, transformando erros (texto inválido) em NaN
            analise_df[col] = pd.to_numeric(analise_df[col], errors="coerce")

    # Preenche NaNs com 0.0
    analise_df.fillna(value={col: 0.0 for col in numeric_cols}, inplace=True)

    # --- FIM DA CORREÇÃO ---

    def analisar_funcionario(row):
        status = "Elegível"

        # Calcula dias reais do mês (28-31)
        dias_no_mes = calendar.monthrange(ano, mes)[1]
        dias_a_considerar = float(dias_no_mes)

        observacoes = []
        inicio_mes = date(ano, mes, 1)
        fim_mes = date(ano, mes, dias_no_mes)

        # Acessa a regra com segurança (agora garantido pelo runner.py)
        data_pagamento = date(ano, mes, rule.base.window.pay_day)

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
        elif row.get("FlagAdiantamento") != "S":
            status = "Inelegível"
            observacoes.append("Flag adiantamento desabilitado")

        admission_limit = rule.base.admission_receive_until_day
        if rule.code == "CMD":
            admission_limit = 31

        if admissao and admissao.year == ano and admissao.month == mes:
            if admissao.day > admission_limit:
                status = "Inelegível"
                observacoes.append(f"Admissão em {admissao.strftime('%d/%m/%Y')}")
            elif rule.code == "REMBRAZ" and admissao.day <= 15:
                dias_a_considerar = dias_no_mes - (admissao.day - 1)
                observacoes.append(
                    f"Admissão proporcional em {admissao.strftime('%d/%m/%Y')}"
                )
            elif admissao.day > 1:
                dias_a_considerar = dias_no_mes - (admissao.day - 1)
                observacoes.append(
                    f"Admissão proporcional em {admissao.strftime('%d/%m/%Y')} ({dias_a_considerar} dias)"
                )

        if status == "Inelegível":
            row["Status"] = status
            row["Observacoes"] = "; ".join(observacoes)
            row["DiasTrabalhados"] = 0
            return row

        if pd.notna(inicio_afast):
            if codigo_licenca in CODIGOS_LICENCA_MATERNIDADE:
                observacoes.append("Licença Maternidade (Elegível por regra)")
            elif codigo_licenca == CODIGO_FERIAS:
                pay_day = rule.base.window.pay_day
                if (
                    inicio_afast
                    and inicio_afast.year == ano
                    and inicio_afast.month == mes
                    and inicio_afast.day > 15
                ):
                    status = "Inelegível"
                    observacoes.append(
                        f"Férias iniciam dia {inicio_afast.day} - após dia 15"
                    )
                elif (
                    inicio_afast
                    and fim_afast
                    and inicio_afast.year == ano
                    and inicio_afast.month == mes
                    and fim_afast.year == ano
                    and fim_afast.month == mes
                ):
                    dias_antes_ferias = inicio_afast.day - 1
                    dias_depois_ferias = dias_no_mes - fim_afast.day
                    dias_a_considerar = dias_antes_ferias + dias_depois_ferias
                    dias_trabalhados_primeira_quinzena = 0
                    if inicio_afast.day > 1:
                        dias_trabalhados_primeira_quinzena += min(
                            inicio_afast.day - 1, 15
                        )
                    if fim_afast.day < 15:
                        dias_trabalhados_primeira_quinzena += 15 - fim_afast.day
                    if dias_trabalhados_primeira_quinzena == 0:
                        status = "Inelegível"
                        observacoes.append(
                            f"Férias {inicio_afast.day}-{fim_afast.day} - não trabalhou 1ª quinzena"
                        )
                    else:
                        observacoes.append(
                            f"Férias no mês ({dias_a_considerar} dias trabalhados)"
                        )
                elif (
                    fim_afast
                    and fim_afast.year == ano
                    and fim_afast.month == mes
                    and fim_afast.day >= pay_day
                ):
                    status = "Inelegível"
                    observacoes.append(f"Retorno de férias após dia {pay_day}")
                elif (
                    fim_afast
                    and fim_afast.year == ano
                    and fim_afast.month == mes
                    and fim_afast.day < pay_day
                ):
                    if fim_afast.day >= 15:
                        status = "Inelegível"
                        observacoes.append(
                            f"Retorno dia {fim_afast.day + 1} - não trabalhou 1ª quinzena"
                        )
                    else:
                        dias_a_considerar = dias_no_mes - fim_afast.day
                        observacoes.append(
                            f"Retorno dia {fim_afast.day + 1} ({dias_a_considerar} dias)"
                        )
                elif (
                    inicio_afast.year == ano
                    and inicio_afast.month == mes
                    and inicio_afast.day < pay_day
                ):
                    if inicio_afast.day <= 1:
                        status = "Inelegível"
                        observacoes.append(f"Férias desde dia {inicio_afast.day}")
                    elif not tem_consignado:
                        status = "Inelegível"
                        observacoes.append(
                            f"Férias iniciadas em {inicio_afast.strftime('%d/%m/%Y')} (sem consignado)"
                        )
                    else:
                        dias_a_considerar = inicio_afast.day - 1
                        observacoes.append(
                            f"Férias proporcional até {inicio_afast.strftime('%d/%m/%Y')}"
                        )
                elif (
                    inicio_afast.year == ano
                    and inicio_afast.month == mes
                    and inicio_afast.day == pay_day
                ):
                    observacoes.append(f"Férias iniciam no dia do pagamento")

            elif codigo_licenca in CODIGOS_AFASTAMENTO_DOENCA:
                fim_efetivo_afastamento = fim_afast if pd.notna(fim_afast) else fim_mes
                dias_de_licenca_no_mes = (
                    min(fim_mes, fim_efetivo_afastamento)
                    - max(inicio_mes, inicio_afast)
                ).days + 1
                if dias_de_licenca_no_mes >= 16:
                    status = "Inelegível"
                    observacoes.append(
                        f"{dias_de_licenca_no_mes} dias de licença médica"
                    )
            elif inicio_afast < inicio_mes:
                status = "Inelegível"
                observacoes.append(f"Afastamento anterior ao mês")

        row["Status"] = status
        row["Observacoes"] = "; ".join(observacoes) if observacoes else "N/A"
        row["DiasTrabalhados"] = max(0, dias_a_considerar)
        return row

    analise_df = analise_df.apply(analisar_funcionario, axis=1)

    if rule.code == "PHY":
        mask_maria = analise_df["Nome"].str.upper().str.contains("MARIA", na=False)
        analise_df.loc[~mask_maria, "Status"] = "Inelegível"
        analise_df.loc[~mask_maria, "Observacoes"] = (
            "Empresa permite apenas funcionária Maria"
        )

    elegiveis = analise_df["Status"] == "Elegível"
    analise_df["ValorAdiantamentoBruto"] = 0.0

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

    # AGORA SEGURO: Comparação numérica garantida
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

    dias_no_mes = calendar.monthrange(ano, mes)[1]
    mask_proporcional = analise_df["DiasTrabalhados"] < dias_no_mes
    fator_proporcional = analise_df["DiasTrabalhados"] / 30.0
    analise_df.loc[
        elegiveis & mask_proporcional, "ValorAdiantamentoBruto"
    ] *= fator_proporcional

    if not rule.overrides.get("no_rounding", False):
        analise_df.loc[elegiveis, "ValorAdiantamentoBruto"] = analise_df.loc[
            elegiveis, "ValorAdiantamentoBruto"
        ].apply(arredondar_especial_rh)

    analise_df["ValorAdiantamentoBruto"].fillna(0, inplace=True)
    return analise_df


# ... (Mantenha os imports e a função processar_regras como estão) ...


def aplicar_descontos_consignado(
    df_calculado: pd.DataFrame, rule: CompanyRule
) -> pd.DataFrame:
    df_final = df_calculado.copy()

    # 1. Sanitização de Segurança
    cols_check = [
        "ValorParcelaConsignado",
        "SalarioContratual",
        "ValorFixoAdiant",
        "PercentualAdiant",
    ]
    for col in cols_check:
        if col in df_final.columns:
            df_final[col] = pd.to_numeric(df_final[col], errors="coerce").fillna(0.0)

    # 2. Definição do Percentual de Desconto (Dinâmico)
    # Lógica: O desconto do consignado deve ser proporcional ao quanto o funcionário recebe de adiantamento.
    # Ex: Se recebe 40% do salário, desconta 40% da parcela.

    # Inicializa com o padrão da regra (fallback)
    percentual_padrao = rule.base.policy.consignado_provision_pct  # Geralmente 0.40
    df_final["PercentualDescontoConsignado"] = percentual_padrao

    # A) Para quem tem Percentual definido no cadastro (Maioria)
    mask_percentual = df_final["PercentualAdiant"] > 0
    # Divide por 100 pois vem 40.0 do banco
    df_final.loc[mask_percentual, "PercentualDescontoConsignado"] = (
        df_final.loc[mask_percentual, "PercentualAdiant"] / 100.0
    )

    # B) Para quem recebe Valor Fixo (SEP.ValorAdiant > 0)
    # Calculamos o percentual efetivo: (Valor Fixo / Salário)
    mask_valor_fixo = df_final["ValorFixoAdiant"] > 0

    # Evita divisão por zero
    salario_safe = df_final["SalarioContratual"].replace(0, np.nan)
    percentual_calculado = df_final["ValorFixoAdiant"] / salario_safe

    # Aplica onde tem valor fixo, preenchendo com 0 se der erro, e arredonda 2 casas
    pct_fixo = percentual_calculado.fillna(0).apply(
        lambda x: math.floor(x * 100) / 100.0
    )

    df_final.loc[mask_valor_fixo, "PercentualDescontoConsignado"] = pct_fixo

    # 3. Cálculo do Valor
    df_final["PercentualObservacao"] = (
        df_final["PercentualDescontoConsignado"] * 100
    ).map("{:,.0f}%".format)

    valor_desconto = (
        df_final["ValorParcelaConsignado"] * df_final["PercentualDescontoConsignado"]
    )

    # Regra Específica: BEL MICRO não desconta consignado no adiantamento
    if rule.overrides.get("consignado_provision_pct") == 0.0:
        valor_desconto[:] = 0.0

    # Arredondamento
    if not rule.overrides.get("no_rounding", False):
        df_final["ValorDesconto"] = valor_desconto.apply(arredondar_fortes)
    else:
        df_final["ValorDesconto"] = valor_desconto

    # 4. Cálculo do Líquido Final
    df_final["ValorLiquidoAdiantamento"] = (
        df_final["ValorAdiantamentoBruto"] - df_final["ValorDesconto"]
    )

    # Garante que não fique negativo
    df_final.loc[
        df_final["ValorLiquidoAdiantamento"] < 0, "ValorLiquidoAdiantamento"
    ] = 0

    # 5. Formatação da Observação
    mask_consignado = df_final["ValorParcelaConsignado"] > 0

    def append_obs(row):
        obs = row["Observacoes"]
        parcela = row["ValorParcelaConsignado"]
        percentual_str = row["PercentualObservacao"]
        desconto = row["ValorDesconto"]

        # Texto explicativo para auditoria
        new_obs = f"Consignado (Parcela: R${parcela:,.2f} | Desc: R${desconto:,.2f} aplicado {percentual_str})"

        if obs and obs != "N/A":
            return f"{obs}; {new_obs}"
        return new_obs

    df_final.loc[mask_consignado, "Observacoes"] = df_final[mask_consignado].apply(
        append_obs, axis=1
    )

    # Limpeza
    df_final.drop(
        columns=["PercentualDescontoConsignado", "PercentualObservacao"], inplace=True
    )

    return df_final
