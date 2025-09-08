# src/business_logic.py

import pandas as pd
from datetime import date, timedelta

def aplicar_regras_elegibilidade_jr(df: pd.DataFrame) -> pd.DataFrame:
    log.info
    ("Analisando elegibilidade dos funcionários...")
    
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

    # Função para calcular dias efetivos
    def calcular_dias_efetivos(row):
        # Ignora licença maternidade ('LM') desta regra
        if row['CodigoTipoLicenca'] == 'LM':
            return 20 # Considera o período cheio

        dias_potenciais = 0
        if pd.notna(row['AdmissaoData']):
            if row['AdmissaoData'].year < hoje.year or row['AdmissaoData'].month < hoje.month:
                dias_potenciais = 20
            elif row['AdmissaoData'].day <= fim_periodo.day:
                dias_potenciais = fim_periodo.day - row['AdmissaoData'].day + 1
        
        dias_afastado = 0
        if pd.notna(row['DataInicioAfastamento']):
            # Calcula a sobreposição do afastamento com o período de 1-20
            inicio_afast = max(row['DataInicioAfastamento'].date(), inicio_periodo)
            fim_afast = min(row['DataFimAfastamento'].date(), fim_periodo)
            if fim_afast >= inicio_afast:
                dias_afastado = (fim_afast - inicio_afast).days + 1
        
        return dias_potenciais - dias_afastado

    df['DiasEfetivos'] = df.apply(calcular_dias_efetivos, axis=1)

    # Aplica a regra dos 15 dias
    dias_insuficientes = df['DiasEfetivos'] < 15
    df.loc[dias_insuficientes, 'Status'] = 'Inelegível'
    df.loc[dias_insuficientes, 'Observacoes'] += f"Dias efetivos ({df['DiasEfetivos'].astype(int)}) < 15; "
    
    # Regra 4 (NOVA): Auditoria de Flag - Identificar quem deveria receber mas está com flag 'N'
    # Condições: A pessoa passaria em todas as regras (Observacoes está vazia), mas o flag original era 'N'
    necessita_correcao = (df['Observacoes'] == '') & (df['FlagAdiantamento'] == 'N')
    df.loc[necessita_correcao, 'Status'] = 'Requer Correção'
    df.loc[necessita_correcao, 'Observacoes'] = 'Este funcionário é elegível mas está sem o flag de adiantamento no sistema.'

    # --- FIM DAS REGRAS ---

    # A coluna 'Elegivel' agora é baseada no Status final
    df['Elegivel'] = df['Status'] == 'Elegível'

    log.info("Análise de elegibilidade concluída.")
    return df