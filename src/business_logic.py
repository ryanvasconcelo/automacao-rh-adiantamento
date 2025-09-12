# src/business_logic.py (VERSÃO FINAL E DEFINITIVA)

import pandas as pd
from datetime import date
from config.logging_config import log

def arredondar_fortes(valor: float) -> float:
    return round(valor, 0)

def processar_regras_e_calculos_jr(df: pd.DataFrame, ano: int, mes: int) -> pd.DataFrame:
    log.info("Iniciando processamento de regras de negócio (Versão Definitiva)...")
    analise_df = df.copy()

    for col in ['AdmissaoData', 'DataInicioAfastamento', 'DataFimAfastamento']:
        if col in analise_df.columns:
            analise_df[col] = pd.to_datetime(analise_df[col], errors='coerce')

    analise_df['BaseCalculo'] = 30.0
    analise_df['StatusDetalhado'] = 'Elegível'
    analise_df['Observacoes'] = ''
    analise_df['DiasTrabalhados'] = 30.0
    analise_df['ValorAdiantamentoBruto'] = 0.0

    def analisar_funcionario(row):
        observacoes, status_detalhado = [], 'Elegível'
        dias_trabalhados = 30.0
        inicio_mes = date(ano, mes, 1)

        # --- HIERARQUIA DE REGRAS DE ELEGIBILIDADE ---
        
        # 1. Licença Maternidade (PRIORIDADE MÁXIMA)
        if row['CodigoTipoLicenca'] == 'LM':
            status_detalhado = 'Elegível'
        # 2. Afastamentos de Longa Duração (iniciados ANTES do mês atual)
        elif pd.notna(row['DataInicioAfastamento']) and row['DataInicioAfastamento'].date() < inicio_mes:
            status_detalhado = 'Inelegível_Reportar'
            observacoes.append(f"Afast. longa duração desde {row['DataInicioAfastamento'].date().strftime('%d/%m/%Y')}.")
        # 3. Férias iniciadas antes do dia 16
        elif pd.notna(row['DataInicioAfastamento']) and row['CodigoTipoLicenca'] == '01' and row['DataInicioAfastamento'].day < 16:
            status_detalhado = 'Inelegível_Omitir'
            observacoes.append("Início de férias antes do dia 16.")
        # 4. Flag de adiantamento desabilitado
        elif row['FlagAdiantamento'] != 'S':
            status_detalhado = 'Inelegível_Omitir'
            observacoes.append("Flag de adiantamento desabilitado.")
        
        # 5. Se passou por todas as checagens acima, calcula os dias e a regra de mínimo
        if status_detalhado == 'Elegível':
            is_first_month = (row['AdmissaoData'].year == ano and row['AdmissaoData'].month == mes)
            if is_first_month:
                dias_trabalhados = 30 - row['AdmissaoData'].day + 1
            elif pd.notna(row['DataInicioAfastamento']) and row['CodigoTipoLicenca'] == '01': # Férias após dia 15
                dias_trabalhados = row['DataInicioAfastamento'].day - 1
            
            dias_trabalhados = max(0, dias_trabalhados)

            if dias_trabalhados < 15:
                status_detalhado = 'Inelegível_Omitir'
                observacoes.append(f"Menos de 15 dias trabalhados ({int(dias_trabalhados)}).")
        
        row['StatusDetalhado'], row['Observacoes'], row['DiasTrabalhados'] = status_detalhado, "; ".join(set(observacoes)), dias_trabalhados
        return row

    analise_df = analise_df.apply(analisar_funcionario, axis=1)
    
    # --- CÁLCULO DE VALORES ---
    mask_elegiveis = analise_df['StatusDetalhado'] == 'Elegível'
    base_adiantamento_proporcional = (analise_df['SalarioContratual'] / 30.0) * analise_df['DiasTrabalhados']
    mask_gerente_fixo = (analise_df['Cargo'].str.contains('GERENTE DE LOJA', case=False, na=False) | (analise_df['Cargo'].str.upper() == 'GERENTE') | (analise_df['Matricula'] == '000915'))
    mask_subgerente_loja = analise_df['Cargo'].str.contains('SUB GERENTE DE LOJA', case=False, na=False)
    idx_gerente_fixo = analise_df[mask_elegiveis & mask_gerente_fixo].index
    analise_df.loc[idx_gerente_fixo, 'ValorAdiantamentoBruto'] = ((analise_df.loc[idx_gerente_fixo, 'DiasTrabalhados'] / 30.0) * 1500.00)
    idx_subgerente_loja = analise_df[mask_elegiveis & mask_subgerente_loja].index
    analise_df.loc[idx_subgerente_loja, 'ValorAdiantamentoBruto'] = ((analise_df.loc[idx_subgerente_loja, 'DiasTrabalhados'] / 30.0) * 900.00)
    mask_comum = mask_elegiveis & ~mask_gerente_fixo & ~mask_subgerente_loja
    idx_comum = analise_df[mask_comum].index
    percentual = analise_df.loc[idx_comum, 'PercentualAdiant'] / 100.0
    analise_df.loc[idx_comum, 'ValorAdiantamentoBruto'] = base_adiantamento_proporcional.loc[idx_comum] * percentual
    analise_df['ValorAdiantamentoBruto'] = analise_df['ValorAdiantamentoBruto'].apply(arredondar_fortes)
    analise_df.loc[~mask_elegiveis, 'ValorAdiantamentoBruto'] = 0.0
    status_map = {'Elegível': 'Elegível', 'Inelegível_Reportar': 'Inelegível', 'Inelegível_Omitir': 'Inelegível'}
    analise_df['Status'] = analise_df['StatusDetalhado'].map(status_map)

    log.success("Processamento de regras de negócio (Definitivo) concluído.")
    return analise_df

def aplicar_descontos_consignado(df_calculado: pd.DataFrame) -> pd.DataFrame:
    """Aplica descontos de empréstimo consignado. Nenhuma mudança necessária aqui."""
    log.info("Aplicando descontos de empréstimo consignado...")
    if df_calculado.empty: return df_calculado

    df_final = df_calculado.copy()
    
    if 'ValorParcelaConsignado' not in df_final.columns:
        df_final['ValorParcelaConsignado'] = 0.0

    df_final['ValorParcelaConsignado'] = df_final['ValorParcelaConsignado'].fillna(0.0)
    df_final['ValorDesconto'] = (df_final['ValorParcelaConsignado'] * 0.40).round(2)
    df_final['ValorLiquidoAdiantamento'] = df_final['ValorAdiantamentoBruto'] - df_final['ValorDesconto']
    
    # Garante que o líquido não seja negativo
    df_final.loc[df_final['ValorLiquidoAdiantamento'] < 0, 'ValorLiquidoAdiantamento'] = 0
    
    log.success("Descontos aplicados com sucesso.")
    return df_final