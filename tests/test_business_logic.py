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
    assert 'Admitido após o dia 10' in df_resultado.loc[0, 'Observacoes']

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