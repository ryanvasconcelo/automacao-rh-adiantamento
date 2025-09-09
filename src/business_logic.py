# src/business_logic.py

import pandas as pd
from datetime import date, timedelta
from config.logging_config import log

def processar_regras_e_calculos_jr(df: pd.DataFrame, ano: int, mes: int) -> pd.DataFrame:
    """
    Função principal que aplica todas as regras de elegibilidade e calcula os valores
    de adiantamento para a empresa JR Rodrigues, seguindo a hierarquia definida.
    """
    log.info("Iniciando processamento de regras de negócio e cálculos...")
    
    # --- 1. PREPARAÇÃO ---
    analise_df = df.copy()
    for col in ['AdmissaoData', 'DataInicioAfastamento', 'DataFimAfastamento']:
        if col in analise_df.columns:
            analise_df[col] = pd.to_datetime(analise_df[col], errors='coerce')

    analise_df['Status'] = 'Elegível'
    analise_df['Observacoes'] = ''
    analise_df['DiasEfetivos'] = 0
    analise_df['ValorAdiantamentoBruto'] = 0.0

    inicio_periodo = date(ano, mes, 1)
    fim_periodo = date(ano, mes, 20)

    # --- 2. APLICAÇÃO DAS REGRAS DE ELEGIBILIDADE (POR LINHA) ---
    def analisar_elegibilidade(row):
        # Regra 1: Admissão (maior prioridade)
        if pd.notna(row['AdmissaoData']) and row['AdmissaoData'].month == mes and row['AdmissaoData'].year == ano:
            if row['AdmissaoData'].day > 10:
                return 'Inelegível', 'Admitido após o dia 10; ', 0

        # Regra 2: Licença Maternidade (segunda maior prioridade)
        if row['CodigoTipoLicenca'] == 'LM':
            dias_efetivos_lm = 20
            return 'Elegível', 'Licença Maternidade; ', dias_efetivos_lm

        # Regra 3: Afastamento Médico >= 16 dias
        if pd.notna(row['DataInicioAfastamento']) and row['CodigoTipoLicenca'] != '01': # Ignora Férias
            duracao = (row['DataFimAfastamento'] - row['DataInicioAfastamento']).days + 1
            if duracao >= 16:
                return 'Inelegível', f'Afastamento de {duracao} dias (>= 16); ', 0
        
        # Regra 4: Férias (usando o código '01')
        if row['CodigoTipoLicenca'] == '01':
            data_retorno = row['DataFimAfastamento'].date() + timedelta(days=1)
            if data_retorno.day > 15:
                 return 'Inelegível', f'Retorno de férias no dia {data_retorno.day} (> 15); ', 0
            if row['DataInicioAfastamento'].day <= 15:
                return 'Inelegível', 'Início de férias antes do dia 16 (já recebeu); ', 0

        # Cálculo de dias efetivos
        dias_potenciais = 20
        if pd.notna(row['AdmissaoData']) and row['AdmissaoData'].month == mes and row['AdmissaoData'].year == ano:
             if row['AdmissaoData'].day <= fim_periodo.day:
                dias_potenciais = fim_periodo.day - row['AdmissaoData'].day + 1
             else:
                dias_potenciais = 0
        
        dias_afastado_no_periodo = 0
        if pd.notna(row['DataInicioAfastamento']):
            inicio_evento = max(row['DataInicioAfastamento'].date(), inicio_periodo)
            fim_evento = min(row['DataFimAfastamento'].date(), fim_periodo)
            if fim_evento >= inicio_evento:
                dias_afastado_no_periodo = (fim_evento - inicio_evento).days + 1
        
        dias_efetivos = dias_potenciais - dias_afastado_no_periodo
        
        return row['Status'], row['Observacoes'], dias_efetivos

    resultados = analise_df.apply(analisar_elegibilidade, axis=1, result_type='expand')
    analise_df[['Status', 'Observacoes', 'DiasEfetivos']] = resultados

    # --- 3. AUDITORIA FINAL DE FLAG ---
    analise_df.loc[analise_df['FlagAdiantamento'] != 'S', 'Status'] = 'Inelegível'
    analise_df.loc[analise_df['FlagAdiantamento'] != 'S', 'Observacoes'] += 'Flag de adiantamento desabilitado; '

    # --- 4. CÁLCULO DE VALORES (APENAS PARA OS ELEGÍVEIS) ---
    mask_elegiveis = analise_df['Status'] == 'Elegível'
    
    mask_gerente = analise_df['Cargo'].str.contains('GERENTE', case=False, na=False) & ~analise_df['Cargo'].str.contains('SUB', case=False, na=False)
    mask_final_gerente = mask_elegiveis & mask_gerente
    analise_df.loc[mask_final_gerente, 'ValorAdiantamentoBruto'] = (analise_df.loc[mask_final_gerente, 'DiasEfetivos'] / 20.0) * 1500.00

    mask_subgerente = analise_df['Cargo'].str.contains('SUBGERENTE', case=False, na=False)
    mask_final_subgerente = mask_elegiveis & mask_subgerente
    analise_df.loc[mask_final_subgerente, 'ValorAdiantamentoBruto'] = (analise_df.loc[mask_final_subgerente, 'DiasEfetivos'] / 20.0) * 900.00

    mask_comum = mask_elegiveis & ~mask_gerente & ~mask_subgerente
    percentual = analise_df.loc[mask_comum, 'PercentualAdiant'] / 100.0
    salario = analise_df.loc[mask_comum, 'SalarioContratual']
    dias = analise_df.loc[mask_comum, 'DiasEfetivos']
    analise_df.loc[mask_comum, 'ValorAdiantamentoBruto'] = (dias / 20.0) * (salario * percentual)
    
    analise_df['ValorAdiantamentoBruto'] = analise_df['ValorAdiantamentoBruto'].round(2)

    log.success("Processamento de regras e cálculos concluído.")
    return analise_df

def aplicar_descontos_consignado(df_calculado: pd.DataFrame) -> pd.DataFrame:
    log.info("Aplicando descontos de empréstimo consignado...")
    if df_calculado.empty: return df_calculado

    df_final = df_calculado.copy()
    
    if 'ValorParcelaConsignado' not in df_final.columns:
        df_final['ValorParcelaConsignado'] = 0.0

    df_final['ValorParcelaConsignado'] = df_final['ValorParcelaConsignado'].fillna(0.0)
    df_final['ValorDesconto'] = (df_final['ValorParcelaConsignado'] * 0.40).round(2)
    df_final['ValorLiquidoAdiantamento'] = df_final['ValorAdiantamentoBruto'] - df_final['ValorDesconto']
    df_final.loc[df_final['ValorLiquidoAdiantamento'] < 0, 'ValorLiquidoAdiantamento'] = 0
    
    log.success("Descontos aplicados com sucesso.")
    return df_final