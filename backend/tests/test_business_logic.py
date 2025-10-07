# tests/test_business_logic.py

import pandas as pd
import pytest
from src.business_logic import processar_regras_e_calculos_jr
from datetime import date, timedelta

# Helper para criar DataFrames de teste mais completos
def criar_df_teste(dados: dict) -> pd.DataFrame:
    colunas_padrao = {
        'Matricula': '001', 'Nome': 'Teste', 'FlagAdiantamento': 'S',
        'DataInicioAfastamento': pd.NaT, 'DataFimAfastamento': pd.NaT,
        'CodigoTipoLicenca': None, 'AdmissaoData': pd.to_datetime('2020-01-01'),
        'SalarioContratual': 2000.0, 'PercentualAdiant': 40.0,
        'ValorFixoAdiant': 0.0, 'Cargo': 'TESTE'
    }
    colunas_padrao.update(dados)
    return pd.DataFrame([colunas_padrao])

def test_admissao_tardia_torna_inelegivel():
    # Arrange
    hoje = date.today()
    df_teste = criar_df_teste({'AdmissaoData': pd.to_datetime(f'{hoje.year}-{hoje.month}-11')})
    # Act
    df_resultado = processar_regras_e_calculos_jr(df_teste)
    # Assert
    assert df_resultado.loc[0, 'Status'] == 'Inelegível'
    assert 'Admitido após o dia 10' in df_resultado.loc[0, 'Observacoes']# src/business_logic.py (Substitua a função inteira por esta)

import pandas as pd
from datetime import date
import calendar
from config.logging_config import log

# --- Funções Auxiliares (permanecem as mesmas) ---
def get_total_dias_mes(ano: int, mes: int) -> int:
    return calendar.monthrange(ano, mes)[1]

def arredondar_fortes(valor: float) -> float:
    return round(valor, 0)

# --- Motor Principal de Regras (VERSÃO CORRIGIDA) ---
def processar_regras_e_calculos_jr(df: pd.DataFrame, ano: int, mes: int) -> pd.DataFrame:
    log.info("Iniciando processamento de regras de negócio (v2.2 - CORRIGIDO)...")

    analise_df = df.copy()
    total_dias_mes = get_total_dias_mes(ano, mes)
    log.info(f"Mês de competência tem {total_dias_mes} dias.")

    for col in ['AdmissaoData', 'DataInicioAfastamento', 'DataFimAfastamento']:
        if col in analise_df.columns:
            analise_df[col] = pd.to_datetime(analise_df[col], errors='coerce')

    analise_df['StatusDetalhado'] = 'Elegível'
    analise_df['Observacoes'] = ''
    analise_df['DiasEfetivos'] = total_dias_mes
    analise_df['ValorAdiantamentoBruto'] = 0.0

    def analisar_funcionario(row):
        observacoes = []
        status_detalhado = 'Elegível'
        dias_efetivos = row['DiasEfetivos']

        # REGRA 1: ADMISSÃO (Mantida)
        if pd.notna(row['AdmissaoData']) and row['AdmissaoData'].year == ano and row['AdmissaoData'].month == mes:
            dias_trabalhados = total_dias_mes - row['AdmissaoData'].day + 1
            primeira_quinzena_trabalhada = row['AdmissaoData'].day <= 15
            if dias_trabalhados < 15 or not primeira_quinzena_trabalhada:
                status_detalhado = 'Inelegível_Omitir'
                observacoes.append(f"Admissão recente ({row['AdmissaoData'].strftime('%d/%m/%Y')}) sem dias mínimos.")
            dias_efetivos = dias_trabalhados

        # REGRA 2: AFASTAMENTOS E FÉRIAS
        if pd.notna(row['DataInicioAfastamento']):
            tipo_licenca = row['CodigoTipoLicenca']
            inicio_afastamento = row['DataInicioAfastamento']

            # ======================= MUDANÇA 1: PRIORIDADE LICENÇA MATERNIDADE =======================
            # Esta verificação agora vem PRIMEIRO para garantir sua prioridade.
            if tipo_licenca == 'LM': # Adapte o código real de Licença Maternidade se for diferente
                # Já é elegível, nenhuma ação negativa é necessária.
                # Apenas garantimos que o loop de verificação pare aqui para este tema.
                pass
            
            # Afastamentos que zeram o pagamento e são reportados
            elif tipo_licenca in ['INSS', 'INVALIDADE']: # Adapte os códigos reais aqui
                if inicio_afastamento.date() < date(ano, mes, 20):
                    status_detalhado = 'Inelegível_Reportar'
                    observacoes.append(f"Afastado por {tipo_licenca} desde {inicio_afastamento.strftime('%d/%m/%Y')}.")
            
            # Afastamento médico > 15 dias
            elif tipo_licenca == 'ATESTADO': # Adapte o código real aqui
                duracao = (row['DataFimAfastamento'] - inicio_afastamento).days + 1
                if duracao > 15:
                    status_detalhado = 'Inelegível_Reportar'
                    observacoes.append(f"Atestado superior a 15 dias ({duracao} dias).")
            
            # ======================= MUDANÇA 2: REGRA DE FÉRIAS CORRIGIDA =======================
            elif tipo_licenca == '01': # Código de Férias
                if inicio_afastamento.day >= 16:
                    # ELEGÍVEL, mas proporcional. Dias efetivos são os dias antes das férias.
                    dias_efetivos = inicio_afastamento.day - 1
                else: # Férias iniciam ANTES do dia 16
                    status_detalhado = 'Inelegível_Omitir'
                    observacoes.append(f"Início de férias em {inicio_afastamento.day}, antes do dia 16.")

        # REGRA 3: FLAG DE ADIANTAMENTO (Mantida)
        if row['FlagAdiantamento'] != 'S' and status_detalhado != 'Inelegível_Reportar':
            status_detalhado = 'Inelegível_Omitir'
            observacoes.append("Flag de adiantamento desabilitado no cadastro.")
        
        row['StatusDetalhado'] = status_detalhado
        row['Observacoes'] = "; ".join(observacoes)
        row['DiasEfetivos'] = dias_efetivos
        
        return row

    analise_df = analise_df.apply(analisar_funcionario, axis=1)

    # Bloco de cálculo (sem alterações na lógica, apenas receberá os dados corretos)
    mask_elegiveis = analise_df['StatusDetalhado'] == 'Elegível'
    
    mask_gerente = analise_df['Cargo'].str.contains('GERENTE', case=False, na=False) & ~analise_df['Cargo'].str.contains('SUB', case=False, na=False)
    idx_gerente = analise_df[mask_elegiveis & mask_gerente].index
    proporcao = analise_df.loc[idx_gerente, 'DiasEfetivos'] / total_dias_mes
    analise_df.loc[idx_gerente, 'ValorAdiantamentoBruto'] = proporcao * 1500.00

    mask_subgerente = analise_df['Cargo'].str.contains('SUBGERENTE', case=False, na=False)
    idx_subgerente = analise_df[mask_elegiveis & mask_subgerente].index
    proporcao = analise_df.loc[idx_subgerente, 'DiasEfetivos'] / total_dias_mes
    analise_df.loc[idx_subgerente, 'ValorAdiantamentoBruto'] = proporcao * 900.00
    
    mask_comum = mask_elegiveis & ~mask_gerente & ~mask_subgerente
    idx_comum = analise_df[mask_comum].index
    proporcao = analise_df.loc[idx_comum, 'DiasEfetivos'] / total_dias_mes
    base_valor = analise_df.loc[idx_comum, 'SalarioContratual'] * (analise_df.loc[idx_comum, 'PercentualAdiant'] / 100.0)
    analise_df.loc[idx_comum, 'ValorAdiantamentoBruto'] = proporcao * base_valor
    
    analise_df['ValorAdiantamentoBruto'] = analise_df['ValorAdiantamentoBruto'].apply(arredondar_fortes)
    analise_df.loc[~mask_elegiveis, 'ValorAdiantamentoBruto'] = 0.0
    
    status_map = {'Elegível': 'Elegível', 'Inelegível_Reportar': 'Inelegível', 'Inelegível_Omitir': 'Inelegível'}
    analise_df['Status'] = analise_df['StatusDetalhado'].map(status_map)

    log.success("Processamento de regras e cálculos (v2.2) concluído.")
    return analise_df# src/business_logic.py (Substitua a função inteira por esta)

import pandas as pd
from datetime import date
import calendar
from config.logging_config import log

# --- Funções Auxiliares (permanecem as mesmas) ---
def get_total_dias_mes(ano: int, mes: int) -> int:
    return calendar.monthrange(ano, mes)[1]

def arredondar_fortes(valor: float) -> float:
    return round(valor, 0)

# --- Motor Principal de Regras (VERSÃO CORRIGIDA) ---
def processar_regras_e_calculos_jr(df: pd.DataFrame, ano: int, mes: int) -> pd.DataFrame:
    log.info("Iniciando processamento de regras de negócio (v2.2 - CORRIGIDO)...")

    analise_df = df.copy()
    total_dias_mes = get_total_dias_mes(ano, mes)
    log.info(f"Mês de competência tem {total_dias_mes} dias.")

    for col in ['AdmissaoData', 'DataInicioAfastamento', 'DataFimAfastamento']:
        if col in analise_df.columns:
            analise_df[col] = pd.to_datetime(analise_df[col], errors='coerce')

    analise_df['StatusDetalhado'] = 'Elegível'
    analise_df['Observacoes'] = ''
    analise_df['DiasEfetivos'] = total_dias_mes
    analise_df['ValorAdiantamentoBruto'] = 0.0

    def analisar_funcionario(row):
        observacoes = []
        status_detalhado = 'Elegível'
        dias_efetivos = row['DiasEfetivos']

        # REGRA 1: ADMISSÃO (Mantida)
        if pd.notna(row['AdmissaoData']) and row['AdmissaoData'].year == ano and row['AdmissaoData'].month == mes:
            dias_trabalhados = total_dias_mes - row['AdmissaoData'].day + 1
            primeira_quinzena_trabalhada = row['AdmissaoData'].day <= 15
            if dias_trabalhados < 15 or not primeira_quinzena_trabalhada:
                status_detalhado = 'Inelegível_Omitir'
                observacoes.append(f"Admissão recente ({row['AdmissaoData'].strftime('%d/%m/%Y')}) sem dias mínimos.")
            dias_efetivos = dias_trabalhados

        # REGRA 2: AFASTAMENTOS E FÉRIAS
        if pd.notna(row['DataInicioAfastamento']):
            tipo_licenca = row['CodigoTipoLicenca']
            inicio_afastamento = row['DataInicioAfastamento']

            # ======================= MUDANÇA 1: PRIORIDADE LICENÇA MATERNIDADE =======================
            # Esta verificação agora vem PRIMEIRO para garantir sua prioridade.
            if tipo_licenca == 'LM': # Adapte o código real de Licença Maternidade se for diferente
                # Já é elegível, nenhuma ação negativa é necessária.
                # Apenas garantimos que o loop de verificação pare aqui para este tema.
                pass
            
            # Afastamentos que zeram o pagamento e são reportados
            elif tipo_licenca in ['INSS', 'INVALIDADE']: # Adapte os códigos reais aqui
                if inicio_afastamento.date() < date(ano, mes, 20):
                    status_detalhado = 'Inelegível_Reportar'
                    observacoes.append(f"Afastado por {tipo_licenca} desde {inicio_afastamento.strftime('%d/%m/%Y')}.")
            
            # Afastamento médico > 15 dias
            elif tipo_licenca == 'ATESTADO': # Adapte o código real aqui
                duracao = (row['DataFimAfastamento'] - inicio_afastamento).days + 1
                if duracao > 15:
                    status_detalhado = 'Inelegível_Reportar'
                    observacoes.append(f"Atestado superior a 15 dias ({duracao} dias).")
            
            # ======================= MUDANÇA 2: REGRA DE FÉRIAS CORRIGIDA =======================
            elif tipo_licenca == '01': # Código de Férias
                if inicio_afastamento.day >= 16:
                    # ELEGÍVEL, mas proporcional. Dias efetivos são os dias antes das férias.
                    dias_efetivos = inicio_afastamento.day - 1
                else: # Férias iniciam ANTES do dia 16
                    status_detalhado = 'Inelegível_Omitir'
                    observacoes.append(f"Início de férias em {inicio_afastamento.day}, antes do dia 16.")

        # REGRA 3: FLAG DE ADIANTAMENTO (Mantida)
        if row['FlagAdiantamento'] != 'S' and status_detalhado != 'Inelegível_Reportar':
            status_detalhado = 'Inelegível_Omitir'
            observacoes.append("Flag de adiantamento desabilitado no cadastro.")
        
        row['StatusDetalhado'] = status_detalhado
        row['Observacoes'] = "; ".join(observacoes)
        row['DiasEfetivos'] = dias_efetivos
        
        return row

    analise_df = analise_df.apply(analisar_funcionario, axis=1)

    # Bloco de cálculo (sem alterações na lógica, apenas receberá os dados corretos)
    mask_elegiveis = analise_df['StatusDetalhado'] == 'Elegível'
    
    mask_gerente = analise_df['Cargo'].str.contains('GERENTE', case=False, na=False) & ~analise_df['Cargo'].str.contains('SUB', case=False, na=False)
    idx_gerente = analise_df[mask_elegiveis & mask_gerente].index
    proporcao = analise_df.loc[idx_gerente, 'DiasEfetivos'] / total_dias_mes
    analise_df.loc[idx_gerente, 'ValorAdiantamentoBruto'] = proporcao * 1500.00

    mask_subgerente = analise_df['Cargo'].str.contains('SUBGERENTE', case=False, na=False)
    idx_subgerente = analise_df[mask_elegiveis & mask_subgerente].index
    proporcao = analise_df.loc[idx_subgerente, 'DiasEfetivos'] / total_dias_mes
    analise_df.loc[idx_subgerente, 'ValorAdiantamentoBruto'] = proporcao * 900.00
    
    mask_comum = mask_elegiveis & ~mask_gerente & ~mask_subgerente
    idx_comum = analise_df[mask_comum].index
    proporcao = analise_df.loc[idx_comum, 'DiasEfetivos'] / total_dias_mes
    base_valor = analise_df.loc[idx_comum, 'SalarioContratual'] * (analise_df.loc[idx_comum, 'PercentualAdiant'] / 100.0)
    analise_df.loc[idx_comum, 'ValorAdiantamentoBruto'] = proporcao * base_valor
    
    analise_df['ValorAdiantamentoBruto'] = analise_df['ValorAdiantamentoBruto'].apply(arredondar_fortes)
    analise_df.loc[~mask_elegiveis, 'ValorAdiantamentoBruto'] = 0.0
    
    status_map = {'Elegível': 'Elegível', 'Inelegível_Reportar': 'Inelegível', 'Inelegível_Omitir': 'Inelegível'}
    analise_df['Status'] = analise_df['StatusDetalhado'].map(status_map)

    log.success("Processamento de regras e cálculos (v2.2) concluído.")
    return analise_df

def test_licenca_maternidade_e_elegivel():
    # Arrange
    df_teste = criar_df_teste({'CodigoTipoLicenca': 'LM'})
    # Act
    df_resultado = processar_regras_e_calculos_jr(df_teste)
    # Assert
    assert df_resultado.loc[0, 'Status'] == 'Elegível'

def test_retorno_ferias_tardio_torna_inelegivel():
    # Arrange: Fim das férias dia 15 -> retorno dia 16
    hoje = date.today()
    df_teste = criar_df_teste({
        'DataInicioAfastamento': pd.to_datetime(f'{hoje.year}-{hoje.month}-01'),
        'DataFimAfastamento': pd.to_datetime(f'{hoje.year}-{hoje.month}-15'),
        'CodigoTipoLicenca': '01' # Férias
    })
    # Act
    df_resultado = processar_regras_e_calculos_jr(df_teste)
    # Assert
    assert df_resultado.loc[0, 'Status'] == 'Inelegível'
    assert 'Retorno de férias no dia 16' in df_resultado.loc[0, 'Observacoes']

def test_calculo_valor_proporcional_admissao_dia_6():
    """Testa o cálculo para um funcionário comum admitido no dia 6."""
    # Arrange: Admitido dia 6 -> 15 dias efetivos (de 6 a 20)
    df_teste = criar_df_teste({'SalarioContratual': 2000.0, 'AdmissaoData': pd.to_datetime(f'{date.today().year}-{date.today().month}-06')})
    # Act
    df_resultado = processar_regras_e_calculos_jr(df_teste)
    # Assert: (15 dias / 20) * (2000 * 0.40) = 0.75 * 800 = 600
    assert df_resultado.loc[0, 'Status'] == 'Elegível'
    assert df_resultado.loc[0, 'ValorAdiantamentoBruto'] == pytest.approx(600.0)

def test_calculo_valor_gerente_integral():
    """Testa o cálculo para um gerente com período cheio."""
    # Arrange
    df_teste = criar_df_teste({'Cargo': 'Gerente de Loja'})
    # Act
    df_resultado = processar_regras_e_calculos_jr(df_teste)
    # Assert: (20 dias / 20) * 1500 = 1500
    assert df_resultado.loc[0, 'Status'] == 'Elegível'
    assert df_resultado.loc[0, 'ValorAdiantamentoBruto'] == pytest.approx(1500.0)