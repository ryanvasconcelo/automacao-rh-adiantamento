# src/business_logic.py

import pandas as pd
from datetime import date, timedelta
from config.logging_config import log

def aplicar_regras_elegibilidade_jr(df: pd.DataFrame) -> pd.DataFrame:
    log.info("Analisando elegibilidade dos funcionários...")
    
    df['AdmissaoData'] = pd.to_datetime(df['AdmissaoData'], errors='coerce')

    # Passo 1: Inicializar colunas de análise
    df['Observacoes'] = ''
    df['Status'] = 'Elegível' # Começamos otimistas

    # --- INÍCIO DA APLICAÇÃO DAS REGRAS ---

    # Regra 1: Flag de Adiantamento (Agora como um passo de auditoria)
    flag_desabilitado = df['FlagAdiantamento'] != 'S'
    df.loc[flag_desabilitado, 'Status'] = 'Inelegível'
    df.loc[flag_desabilitado, 'Observacoes'] += 'Flag de adiantamento desabilitado; '

      # Regra 2 e 3 combinadas: Dias Trabalhados e Afastamentos
    hoje = date.today()
    inicio_periodo = date(hoje.year, hoje.month, 1)
    fim_periodo = date(hoje.year, hoje.month, 20)

    def calcular_dias_efetivos(row):
        if row['CodigoTipoLicenca'] == 'LM':
            return 20 

        dias_potenciais = 0
        if pd.notna(row['AdmissaoData']):
            if row['AdmissaoData'].year < hoje.year or row['AdmissaoData'].month < hoje.month:
                dias_potenciais = 20
            elif row['AdmissaoData'].day <= fim_periodo.day:
                dias_potenciais = fim_periodo.day - row['AdmissaoData'].day + 1
        
        dias_afastado = 0
        if pd.notna(row['DataInicioAfastamento']):
            inicio_afast = max(row['DataInicioAfastamento'].date(), inicio_periodo)
            fim_afast = min(row['DataFimAfastamento'].date(), fim_periodo)
            if fim_afast >= inicio_afast:
                dias_afastado = (fim_afast - inicio_afast).days + 1
        
        return dias_potenciais - dias_afastado

    df['DiasEfetivos'] = df.apply(calcular_dias_efetivos, axis=1)
    
    # --- CORREÇÃO DA MENSAGEM DE LOG ---
    # Primeiro, identificamos quem é inelegível por esta regra.
    dias_insuficientes_mask = df['DiasEfetivos'] < 15
    
    # Agora, para cada um deles, criamos a mensagem de erro personalizada.
    # O .apply() garante que usamos o valor da 'DiasEfetivos' de cada linha.
    df.loc[dias_insuficientes_mask, 'Observacoes'] += df[dias_insuficientes_mask].apply(
        lambda row: f"Dias efetivos ({row['DiasEfetivos']}) < 15; ", axis=1
    )
    df.loc[dias_insuficientes_mask, 'Status'] = 'Inelegível'
    
    # Regra 4 (NOVA): Auditoria de Flag - Identificar quem deveria receber mas está com flag 'N'
    # Condições: A pessoa passaria em todas as regras (Observacoes está vazia), mas o flag original era 'N'
    necessita_correcao = (df['Observacoes'] == '') & (df['FlagAdiantamento'] == 'N')
    df.loc[necessita_correcao, 'Status'] = 'Requer Correção'
    df.loc[necessita_correcao, 'Observacoes'] = 'Este funcionário é elegível mas está sem o flag de adiantamento no sistema.'

    # A coluna 'Elegivel' agora é baseada no Status final
    df['Elegivel'] = df['Status'] == 'Elegível'

    log.info("Análise de elegibilidade concluída.")
    return df