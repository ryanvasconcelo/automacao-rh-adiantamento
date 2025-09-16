# src/business_logic.py (Versão com a função aninhada corrigida)

import pandas as pd
from datetime import date


def arredondar_fortes(valor: float) -> float:
    return round(valor or 0.0, 2)


def processar_regras_e_calculos_jr(
    df: pd.DataFrame, ano: int, mes: int
) -> pd.DataFrame:
    analise_df = df.copy()

    # Garante que as colunas de data são do tipo datetime
    for col in ["AdmissaoData", "DtRescisao", "DtInicio", "DtFim"]:
        if col in analise_df.columns:
            analise_df[col] = pd.to_datetime(analise_df[col], errors="coerce")

    # --- CORREÇÃO: A FUNÇÃO AUXILIAR AGORA ESTÁ AQUI DENTRO ---
    # Estando aqui, ela tem acesso a 'ano' e 'mes' da função principal.
    def analisar_funcionario(row):
        observacoes = []
        status = "Elegível"
        dias_a_considerar = 30.0
        base_de_dias = 30.0
        inicio_mes = date(ano, mes, 1)

        admissao = row["AdmissaoData"].date()
        inicio_afast = row["DtInicio"].date() if pd.notna(row["DtInicio"]) else None

        # HIERARQUIA DE VERIFICAÇÃO DE INELEGIBILIDADE
        if pd.notna(row["DtInicio"]) and inicio_afast < inicio_mes:
            status = "Inelegível"
            observacoes.append(
                f"Afastamento longa duração desde {inicio_afast.strftime('%d/%m/%Y')}"
            )

        elif row["FlagAdiantamento"] != "S":
            status = "Inelegível"
            observacoes.append("Flag adiantamento desabilitado")

        elif (
            pd.notna(row["CodigoTipoLicenca"])
            and row["CodigoTipoLicenca"] == "01"
            and inicio_afast
            and inicio_afast.day < 16
        ):
            status = "Inelegível"
            observacoes.append("Férias iniciadas antes do dia 16")

        elif admissao.year == ano and admissao.month == mes and admissao.day > 10:
            status = "Inelegível"
            observacoes.append(f"Admissão em {admissao.day}/{mes}")

        # Se passou, calcula os dias para proporcionalidade
        if status == "Elegível":
            is_first_month = admissao.year == ano and admissao.month == mes
            if is_first_month:
                # Usa a data de pagamento (dia 20) como referência para recém-admitidos
                dias_a_considerar = (date(ano, mes, 20) - admissao).days + 1
            elif (
                pd.notna(row["CodigoTipoLicenca"])
                and row["CodigoTipoLicenca"] == "01"
                and inicio_afast
            ):
                dias_a_considerar = inicio_afast.day - 1

            dias_a_considerar = max(0, dias_a_considerar)

        row["Status"] = status
        row["Observacoes"] = "; ".join(observacoes)
        row["DiasTrabalhados"] = dias_a_considerar
        return row

    # Aplica a função a cada linha
    analise_df = analise_df.apply(analisar_funcionario, axis=1)

    # --- CÁLCULO DE VALORES (VETORIZADO) ---
    elegiveis = analise_df["Status"] == "Elegível"

    # Inicia a coluna de valor bruto com zeros
    analise_df["ValorAdiantamentoBruto"] = 0.0

    # Cargos Especiais
    mask_gerente = analise_df["Cargo"].str.contains("GERENTE", na=False)
    mask_sub = analise_df["Cargo"].str.contains("SUBGERENTE", na=False)

    analise_df.loc[elegiveis & mask_gerente, "ValorAdiantamentoBruto"] = (
        1500.0 / 30.0
    ) * analise_df["DiasTrabalhados"]
    analise_df.loc[elegiveis & mask_sub, "ValorAdiantamentoBruto"] = (
        900.0 / 30.0
    ) * analise_df["DiasTrabalhados"]

    # Funcionários Comuns
    mask_comum = elegiveis & ~mask_gerente & ~mask_sub
    percentual = analise_df.loc[mask_comum, "PercentualAdiant"] / 100.0
    salario = analise_df.loc[mask_comum, "SalarioContratual"]
    dias = analise_df.loc[mask_comum, "DiasTrabalhados"]
    analise_df.loc[mask_comum, "ValorAdiantamentoBruto"] = (
        (salario / 30.0) * dias * percentual
    )

    analise_df["ValorAdiantamentoBruto"].fillna(0, inplace=True)

    return analise_df


def aplicar_descontos_consignado(df_calculado: pd.DataFrame) -> pd.DataFrame:
    df_final = df_calculado.copy()
    if "ValorParcelaConsignado" not in df_final.columns:
        df_final["ValorParcelaConsignado"] = 0.0

    df_final["ValorParcelaConsignado"] = df_final["ValorParcelaConsignado"].fillna(0.0)
    df_final["ValorDesconto"] = (df_final["ValorParcelaConsignado"] * 0.40).apply(
        arredondar_fortes
    )
    df_final["ValorLiquidoAdiantamento"] = (
        df_final["ValorAdiantamentoBruto"] - df_final["ValorDesconto"]
    )
    df_final.loc[
        df_final["ValorLiquidoAdiantamento"] < 0, "ValorLiquidoAdiantamento"
    ] = 0

    return df_final
