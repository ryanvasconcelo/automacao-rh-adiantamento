# src/data_extraction.py

import pandas as pd
from datetime import date, timedelta
from .database import get_db_connection
from config.logging_config import log

def fetch_employee_base_data(emp_codigo: str, ano: int, mes: int):
    log.info(f"Iniciando a busca de dados para a empresa: {emp_codigo} | Competência: {ano}-{mes:02d}")
    data_ref = f"{ano}-{mes:02d}-20"
    query = f"""
        SELECT
            E.Codigo AS Matricula, E.Nome, E.AdmissaoData, E.DtRescisao,
            S.Valor AS SalarioContratual, S.Adiantamento AS FlagAdiantamento,
            S.PercentualAdiant, S.ValorAdiant AS ValorFixoAdiant, C.NOME AS Cargo
        FROM EPG AS E
        INNER JOIN SEP AS S ON E.EMP_Codigo = S.EMP_Codigo AND E.Codigo = S.EPG_Codigo
        LEFT JOIN CAR AS C ON S.CAR_Codigo = C.CODIGO AND S.EMP_Codigo = C.EMP_Codigo
        WHERE
            S.DATA = (
                SELECT MAX(S2.DATA) FROM SEP AS S2
                WHERE S2.EMP_Codigo = S.EMP_Codigo AND S2.EPG_Codigo = S.EPG_Codigo AND S2.DATA <= '{data_ref}'
            )
            AND (E.DtRescisao IS NULL OR E.DtRescisao > '{data_ref}')
            AND E.EMP_Codigo = '{emp_codigo}'
    """
    connection = None
    try:
        connection = get_db_connection()
        return pd.read_sql(query, connection) if connection else None
    except Exception as e:
        log.error(f"Ocorreu um erro ao executar a consulta base: {e}")
        return None
    finally:
        if connection: connection.close()

def fetch_employee_leaves(emp_codigo: str, employee_ids: list, ano: int, mes: int):
    log.info("Buscando dados de afastamentos (licenças)...")
    if not employee_ids: return pd.DataFrame()
    ids_string = ", ".join([f"'{eid}'" for eid in employee_ids])
    inicio_mes = f"{ano}-{mes:02d}-01"
    proximo_mes_ano = ano + 1 if mes == 12 else ano
    proximo_mes_mes = 1 if mes == 12 else mes + 1
    inicio_proximo_mes = f"{proximo_mes_ano}-{proximo_mes_mes:02d}-01"
    query = f"""
        SELECT EPG_CODIGO AS Matricula, DTINICIAL AS DataInicioAfastamento,
               DTFINAL AS DataFimAfastamento, TLI_CODIGO AS CodigoTipoLicenca
        FROM LIC
        WHERE EMP_Codigo = '{emp_codigo}' AND EPG_CODIGO IN ({ids_string})
          AND DTFINAL >= '{inicio_mes}' AND DTINICIAL < '{inicio_proximo_mes}'
    """
    connection = None
    try:
        connection = get_db_connection()
        if connection:
            leaves_df = pd.read_sql(query, connection)
            leaves_df['DataInicioAfastamento'] = pd.to_datetime(leaves_df['DataInicioAfastamento'], errors='coerce')
            leaves_df['DataFimAfastamento'] = pd.to_datetime(leaves_df['DataFimAfastamento'], errors='coerce')
            return leaves_df
        return pd.DataFrame()
    except Exception as e:
        log.error(f"Ocorreu um erro ao buscar afastamentos: {e}")
        return pd.DataFrame()
    finally:
        if connection: connection.close()

def fetch_employee_loans(emp_codigo: str, employee_ids: list, ano: int, mes: int):
    log.info("Buscando dados de empréstimos consignados...")
    if not employee_ids: return pd.DataFrame()
    ids_string = ", ".join([f"'{eid}'" for eid in employee_ids])
    ano_mes_competencia = f"{ano}{mes:02d}"
    query = f"""
        SELECT COT_EPG_Codigo AS Matricula, SUM(ValorParcela) AS ValorParcelaConsignado
        FROM COE
        WHERE EMP_Codigo = '{emp_codigo}' AND COT_EPG_Codigo IN ({ids_string})
          AND AnoMesDesconto = '{ano_mes_competencia}'
        GROUP BY COT_EPG_Codigo
    """
    connection = None
    try:
        connection = get_db_connection()
        return pd.read_sql(query, connection) if connection else pd.DataFrame()
    except Exception as e:
        log.error(f"Ocorreu um erro ao buscar empréstimos: {e}")
        return pd.DataFrame()
    finally:
        if connection: connection.close()

def fetch_all_companies():
    log.info("Buscando lista de todas as empresas ativas...")
    query = "SELECT Codigo, Nome FROM EMP WHERE DESATIVADA = 0 ORDER BY Nome"
    connection = None
    try:
        connection = get_db_connection()
        if connection:
            companies_df = pd.read_sql(query, connection)
            return pd.Series(companies_df.Codigo.values, index=companies_df.Nome).to_dict()
        return {}
    except Exception as e:
        log.error(f"Não foi possível buscar a lista de empresas. A tabela 'EMP' existe? Erro: {e}")
        return {"JR Rodrigues (Fallback)": "9098"}
    finally:
        if connection: connection.close()