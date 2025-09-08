import pandas as pd
from .database import get_db_connection
from config.logging_config import log

# A função agora recebe 'emp_codigo' como um argumento dinâmico
def fetch_employee_base_data(emp_codigo: str):
    """
    Busca os dados base dos funcionários ativos de uma empresa específica.
    """
    log.info(f"Iniciando a busca de dados para a empresa: {emp_codigo}")
    
    # A query agora usa o argumento 'emp_codigo' para filtrar a empresa correta.
    query = f"""
        SELECT
            E.Codigo AS Matricula,
            E.Nome,
            E.AdmissaoData,
            E.DtRescisao,
            S.Valor AS SalarioContratual,
            S.Adiantamento AS FlagAdiantamento,
            S.PercentualAdiant,
            S.ValorAdiant AS ValorFixoAdiant,
            C.NOME AS Cargo
        FROM
            EPG AS E
        INNER JOIN
            SEP AS S ON E.EMP_Codigo = S.EMP_Codigo AND E.Codigo = S.EPG_Codigo
        LEFT JOIN
            CAR AS C ON S.CAR_Codigo = C.CODIGO AND S.EMP_Codigo = C.EMP_Codigo
        WHERE
            S.DATA = (
                SELECT MAX(S2.DATA)
                FROM SEP AS S2
                WHERE S2.EMP_Codigo = S.EMP_Codigo
                  AND S2.EPG_Codigo = S.EPG_Codigo
                  AND S2.DATA <= GETDATE()
            )
            AND (E.DtRescisao IS NULL OR E.DtRescisao > GETDATE())
            AND E.EMP_Codigo = '{emp_codigo}' -- Filtro dinâmico da empresa
    """
    
    connection = None
    try:
        connection = get_db_connection()
        if connection:
            employees_df = pd.read_sql(query, connection)
            log.info("Dados extraídos com sucesso!")
            return employees_df
        else:
            log.info("Não foi possível extrair dados, a conexão com o banco falhou.")
            return None
    except Exception as e:
        log.info(f"Ocorreu um erro ao executar a consulta: {e}")
        return None
    finally:
        if connection:
            connection.close()
            log.info("Conexão com o banco de dados fechada.")

# busca a lista de afastamentos (licenças) do mês corrente para os funcionários fornecidos
def fetch_employee_leaves(emp_codigo: str, employee_ids: list):
    """
    Busca os afastamentos (licenças) do mês corrente para uma lista específica de funcionários.
    """
    log.info("Buscando dados de afastamentos (licenças)...")
    if not employee_ids:
        return pd.DataFrame() # Retorna um DataFrame vazio se não houver funcionários para buscar

    # Converte a lista de matrículas em uma string formatada para a cláusula IN do SQL
    ids_string = ", ".join([f"'{eid}'" for eid in employee_ids])

    # Query para buscar licenças que estão ativas em qualquer parte do mês corrente
    query = f"""
        SELECT 
            EPG_CODIGO AS Matricula,
            DTINICIAL AS DataInicioAfastamento,
            DTFINAL AS DataFimAfastamento,
            TLI_CODIGO AS CodigoTipoLicenca
        FROM LIC
        WHERE 
            EMP_Codigo = '{emp_codigo}'
            AND EPG_CODIGO IN ({ids_string})
            AND DTFINAL >= DATEFROMPARTS(YEAR(GETDATE()), MONTH(GETDATE()), 1) -- O afastamento termina neste mês ou depois
            AND DTINICIAL < DATEADD(month, 1, DATEFROMPARTS(YEAR(GETDATE()), MONTH(GETDATE()), 1)) -- E começa antes do próximo mês
    """
    
    connection = None
    try:
        connection = get_db_connection()
        if connection:
            leaves_df = pd.read_sql(query, connection)
            # Converte as colunas de data para o formato datetime
            leaves_df['DataInicioAfastamento'] = pd.to_datetime(leaves_df['DataInicioAfastamento'], errors='coerce')
            leaves_df['DataFimAfastamento'] = pd.to_datetime(leaves_df['DataFimAfastamento'], errors='coerce')
            return leaves_df
        return pd.DataFrame() # Retorna DF vazio em caso de falha na conexão
    except Exception as e:
        log.info(f"Ocorreu um erro ao buscar afastamentos: {e}")
        return pd.DataFrame() # Retorna DF vazio em caso de erro
    finally:
        if connection:
            connection.close()

# Este bloco pode ser removido ou deixado para testes rápidos.
if __name__ == "__main__":
    
    CODIGO_EMPRESA_TESTE = '9098' # Código da JR Rodrigues para nosso teste 
    
    df = fetch_employee_base_data(emp_codigo=CODIGO_EMPRESA_TESTE)
    
    if df is not None:
        log.info(df.head())