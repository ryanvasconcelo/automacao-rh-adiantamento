# src/business_logic.py (Versão Multi-Empresa)

import pandas as pd
import numpy as np
from datetime import date
import math
import calendar

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
        status = "Elegível"
        
        # Calcula dias reais do mês (28-31)
        dias_no_mes = calendar.monthrange(ano, mes)[1]
        
        # SEMPRE usa dias reais do mês como base
        dias_a_considerar = float(dias_no_mes)
        
        observacoes = []
        inicio_mes = date(ano, mes, 1)
        fim_mes = date(ano, mes, dias_no_mes)  # Último dia real do mês
        # usa o pay_day da regra específica
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
        elif row["FlagAdiantamento"] != "S":
            status = "Inelegível"
            observacoes.append("Flag adiantamento desabilitado")
        # REGRA 2.5: Admissão - agora usa o valor da regra específica
        # REGRA ESPECÍFICA CMD: permite admissão com 1 dia
        admission_limit = rule.base.admission_receive_until_day
        # Override para C.M. DISTRIBUIDORA (permite admissão com 1 dia)
        if rule.code == "CMD":
            admission_limit = 31  # Qualquer dia do mês
        
        # Verifica se foi admitido no mês de competência
        if admissao and admissao.year == ano and admissao.month == mes:
            # Se admitido APÓS o limite, é inelegível
            if admissao.day > admission_limit:
                status = "Inelegível"
                observacoes.append(f"Admissão em {admissao.strftime('%d/%m/%Y')}")
            # REGRA ESPECÍFICA REMBRAZ: Admissão 1-15 proporcional
            elif rule.code == "REMBRAZ" and admissao.day <= 15:
                dias_a_considerar = dias_no_mes - (admissao.day - 1)
                observacoes.append(f"Admissão proporcional em {admissao.strftime('%d/%m/%Y')}")
            # REGRA GERAL: Admissão no meio do mês = proporcional
            elif admissao.day > 1:
                # Calcula dias trabalhados desde a admissão até o fim do mês
                dias_a_considerar = dias_no_mes - (admissao.day - 1)
                observacoes.append(f"Admissão proporcional em {admissao.strftime('%d/%m/%Y')} ({dias_a_considerar} dias)")
        if status == "Inelegível":
            row["Status"] = status
            row["Observacoes"] = "; ".join(observacoes)
            row["DiasTrabalhados"] = 0
            return row
        if pd.notna(inicio_afast):
            # REGRA 1.1: Licença Maternidade
            if codigo_licenca in CODIGOS_LICENCA_MATERNIDADE:
                observacoes.append("Licença Maternidade (Elegível por regra)")
            
            # REGRAS 2.4, 2.7 e 2.8: FÉRIAS
            elif codigo_licenca == CODIGO_FERIAS:
                pay_day = rule.base.window.pay_day
                
                # ⚠️ REGRA PRIORITÁRIA: Férias iniciadas APÓS dia 15 = INELEGÍVEL
                # Esta regra tem mais pujança que todas as outras
                if (
                    inicio_afast
                    and inicio_afast.year == ano
                    and inicio_afast.month == mes
                    and inicio_afast.day > 15
                ):
                    status = "Inelegível"
                    observacoes.append(f"Férias iniciam dia {inicio_afast.day} - após dia 15 (não trabalhou primeira quinzena completa)")
                
                # CASO ESPECIAL: Férias começam e terminam no mesmo mês (ex: Vicente 6/10 a 10/10)
                elif (
                    inicio_afast
                    and fim_afast
                    and inicio_afast.year == ano
                    and inicio_afast.month == mes
                    and fim_afast.year == ano
                    and fim_afast.month == mes
                ):
                    # Calcula dias trabalhados: antes das férias + depois das férias
                    dias_antes_ferias = inicio_afast.day - 1  # dias 1 até dia antes das férias
                    dias_depois_ferias = dias_no_mes - fim_afast.day  # dias após retorno até fim do mês
                    dias_a_considerar = dias_antes_ferias + dias_depois_ferias
                    
                    # NOVA REGRA: Deve ter trabalhado pelo menos 1 dia na primeira quinzena (1-15)
                    # Verifica se trabalhou algum dia entre 1-15
                    dias_trabalhados_primeira_quinzena = 0
                    
                    # Dias antes das férias que caem na primeira quinzena
                    if inicio_afast.day > 1:
                        dias_trabalhados_primeira_quinzena += min(inicio_afast.day - 1, 15)
                    
                    # Dias depois das férias que caem na primeira quinzena
                    if fim_afast.day < 15:
                        dias_trabalhados_primeira_quinzena += (15 - fim_afast.day)
                    
                    if dias_trabalhados_primeira_quinzena == 0:
                        status = "Inelegível"
                        observacoes.append(f"Férias {inicio_afast.day}/{mes} a {fim_afast.day}/{mes} - não trabalhou na primeira quinzena")
                    else:
                        observacoes.append(
                            f"Férias {inicio_afast.day}/{mes} a {fim_afast.day}/{mes} "
                            f"({dias_a_considerar} dias trabalhados)"
                        )
                
                # REGRA 2.8: Retorno de férias dia 16+ não recebe
                elif (
                    fim_afast
                    and fim_afast.year == ano
                    and fim_afast.month == mes
                    and fim_afast.day >= pay_day
                ):
                    status = "Inelegível"
                    observacoes.append(f"Retorno de férias após dia {pay_day} ({fim_afast.strftime('%d/%m/%Y')})")
                
                # REGRA 2.4: Retorno de férias entre 1 e (pay_day-1) - proporcional
                elif (
                    fim_afast
                    and fim_afast.year == ano
                    and fim_afast.month == mes
                    and fim_afast.day < pay_day
                ):
                    # NOVA REGRA: Verifica se trabalhou na primeira quinzena
                    # Se retornou após dia 15, não trabalhou na primeira quinzena
                    if fim_afast.day >= 15:
                        status = "Inelegível"
                        observacoes.append(f"Retorno de férias dia {fim_afast.day + 1}/{mes} - não trabalhou na primeira quinzena")
                    else:
                        # Dias trabalhados após o retorno
                        dias_a_considerar = dias_no_mes - fim_afast.day
                        observacoes.append(f"Retorno de férias dia {fim_afast.day + 1}/{mes} ({dias_a_considerar} dias)")
                
                # REGRA 2.6: Início de férias entre 1 e (pay_day-1) - proporcional
                elif (
                    inicio_afast.year == ano
                    and inicio_afast.month == mes
                    and inicio_afast.day < pay_day
                ):
                    # NOVA REGRA: Deve ter trabalhado pelo menos 1 dia na primeira quinzena
                    # Se férias começam no dia 1, não trabalhou nenhum dia
                    if inicio_afast.day <= 1:
                        status = "Inelegível"
                        observacoes.append(f"Férias desde dia {inicio_afast.day} - não trabalhou na primeira quinzena")
                    # REGRA 1.4: Se tem consignado, recebe proporcional; se não tem, é inelegível
                    elif not tem_consignado:
                        status = "Inelegível"
                        observacoes.append(f"Férias iniciadas em {inicio_afast.strftime('%d/%m/%Y')} (sem consignado)")
                    else:
                        # Dias trabalhados antes das férias
                        dias_a_considerar = inicio_afast.day - 1
                        observacoes.append(f"Férias proporcional até {inicio_afast.strftime('%d/%m/%Y')} ({dias_a_considerar} dias)")
                
                # REGRA 2.7: Férias começam no dia do pagamento (dia 15)
                elif (
                    inicio_afast.year == ano
                    and inicio_afast.month == mes
                    and inicio_afast.day == pay_day
                ):
                    # Férias começam exatamente no dia 15 - recebe normal
                    observacoes.append(f"Férias iniciam dia {inicio_afast.day} (no dia do pagamento)")
                
                # REGRA ESPECÍFICA REMBRAZ: Alerta se férias não cobrem mês completo
                if rule.code == "REMBRAZ":
                    if inicio_afast and fim_afast:
                        if inicio_afast.day != 1 or fim_afast.day != 30:
                            observacoes.append(f"⚠️ ALERTA: Férias não cobrem período completo (1-30)")
            
            # REGRA 1.2: Afastamento médico
            elif codigo_licenca in CODIGOS_AFASTAMENTO_DOENCA:
                fim_efetivo_afastamento = fim_afast if pd.notna(fim_afast) else fim_mes
                dias_de_licenca_no_mes = (
                    min(fim_mes, fim_efetivo_afastamento)
                    - max(inicio_mes, inicio_afast)
                ).days + 1
                if dias_de_licenca_no_mes >= 16:
                    status = "Inelegível"
                    observacoes.append(f"{dias_de_licenca_no_mes} dias de licença médica no mês")
            
            # Outros afastamentos iniciados antes do mês
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
    
    # REGRA ESPECÍFICA PHYSIO VIDA: apenas "Maria" recebe
    if rule.code == "PHY":
        mask_maria = analise_df["Nome"].str.upper().str.contains("MARIA", na=False)
        analise_df.loc[~mask_maria, "Status"] = "Inelegível"
        analise_df.loc[~mask_maria, "Observacoes"] = "Empresa permite apenas funcionária Maria"
    
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

    # Calcula proporcionalidade:
    # - Divide salário por 30 (mês comercial)
    # - Multiplica pelos dias reais trabalhados
    dias_no_mes = calendar.monthrange(ano, mes)[1]
    mask_proporcional = analise_df["DiasTrabalhados"] < dias_no_mes
    # Fator: dias_trabalhados / 30 (sempre usa 30 como divisor)
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
# Em src/business_logic.py

# (O resto do arquivo, incluindo processar_regras, permanece o mesmo)


# --- FUNÇÃO MODIFICADA ---
def aplicar_descontos_consignado(
    df_calculado: pd.DataFrame, rule: CompanyRule
) -> pd.DataFrame:
    df_final = df_calculado.copy()
    df_final["ValorParcelaConsignado"] = df_final["ValorParcelaConsignado"].fillna(0.0)
    df_final["SalarioContratual"] = df_final["SalarioContratual"].fillna(0.0)
    df_final["ValorFixoAdiant"] = df_final["ValorFixoAdiant"].fillna(0.0)

    df_final["PercentualDescontoConsignado"] = rule.base.policy.consignado_provision_pct
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

    # NOVO: Adiciona uma coluna com o percentual formatado para a observação
    df_final["PercentualObservacao"] = (
        df_final["PercentualDescontoConsignado"] * 100
    ).map("{:,.0f}%".format)

    valor_desconto = (
        df_final["ValorParcelaConsignado"] * df_final["PercentualDescontoConsignado"]
    )

    # Modificação para lidar com a regra da BEL MICRO diretamente
    if rule.overrides.get("consignado_provision_pct") == 0.0:
        valor_desconto[:] = 0.0

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

    # --- MODIFICAÇÃO PRINCIPAL AQUI ---
    # Adiciona observação sobre o consignado com mais detalhes
    mask_consignado = df_final["ValorParcelaConsignado"] > 0

    def append_obs(row):
        obs = row["Observacoes"]
        parcela = row["ValorParcelaConsignado"]
        percentual_str = row["PercentualObservacao"]
        desconto = row["ValorDesconto"]

        # Gera a nova observação detalhada
        new_obs = f"Consignado (Parcela: R${parcela:,.2f} | Desc: R${desconto:,.2f} de {percentual_str})"

        if obs and obs != "N/A":
            return f"{obs}; {new_obs}"
        return new_obs

    df_final.loc[mask_consignado, "Observacoes"] = df_final[mask_consignado].apply(
        append_obs, axis=1
    )

    df_final.drop(
        columns=["PercentualDescontoConsignado", "PercentualObservacao"], inplace=True
    )  # Remove colunas auxiliares
    return df_final
