# teste unitario com pytest, é um pedaco de codigo que testa outro pedaco de codigo, funciona como um controle de qualidade garantindo que o codigo principal esta funcionando corretamente atraves do resultado do teste

# arrange - preparar: aqui é criado um dataframe fake com dados da funcao real

# act - agir: aqui é executada a funcao real com o dataframe fake

# assert - afirmar: aqui é verificado se o resultado da funcao real é o mesmo que o esperado

# tests/test_business_logic.py

import pandas as pd
import pytest
from src.business_logic import aplicar_regras_elegibilidade_jr
from datetime import date, timedelta

# Esta é a nossa primeira função de teste. O nome também deve começar com 'test_'.
def test_regra_flag_adiantamento():
    # 1. Arrange (Preparar)
    # Criamos um DataFrame "fake" com dois funcionários para o nosso cenário de teste.
    # Um tem o flag 'S' (deve passar), o outro tem 'N' (deve falhar).
    # Adicionamos as outras colunas que a função espera, com valores válidos.
    dados_teste = {
        'Matricula': ['001', '002'],
        'Nome': ['Funcionario Elegivel', 'Funcionario Inelegivel'],
        'AdmissaoData': [pd.to_datetime('2020-01-01'), pd.to_datetime('2020-01-01')],
        'FlagAdiantamento': ['S', 'N'],
        # Adicionamos colunas de afastamento vazias, pois este teste foca apenas no flag.
        'DataInicioAfastamento': [pd.NaT, pd.NaT],
        'DataFimAfastamento': [pd.NaT, pd.NaT],
        'CodigoTipoLicenca': [None, None]
    }
    df_teste = pd.DataFrame(dados_teste)

    # 2. Act (Agir)
    # Executamos a função que estamos testando com nossos dados de exemplo.
    df_resultado = aplicar_regras_elegibilidade_jr(df_teste)

    # 3. Assert (Verificar)
    # Verificamos se o resultado é exatamente o que esperamos.
    # Se qualquer uma dessas verificações falhar, o pytest nos avisará.
    
    # A função deve retornar o mesmo número de funcionários que entrou.
    assert len(df_resultado) == 2
    
    # O primeiro funcionário (índice 0) deve ter o Status 'Elegível'.
    assert df_resultado.loc[0, 'Status'] == 'Elegível'
    assert df_resultado.loc[0, 'Observacoes'] == '' # E nenhuma observação de erro.
    
    # O segundo funcionário (índice 1) deve ter o Status 'Inelegível'.
    assert df_resultado.loc[1, 'Status'] == 'Inelegível'
    # E a observação deve conter a justificativa correta.
    assert 'Flag de adiantamento desabilitado' in df_resultado.loc[1, 'Observacoes']