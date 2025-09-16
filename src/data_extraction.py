# src/data_extraction.py
import pandas as pd
from .database import get_connection


def fetch_employee_base_data(emp_codigo: str, ano: int, mes: int) -> pd.DataFrame:
    """Busca dados base dos funcionários usando queries parametrizadas e seguras."""
    inicio_mes_ref = f"{ano}-{mes:02d}-01"

    query = """
        SELECT
            E.Codigo AS Matricula, E.Nome, E.AdmissaoData, E.DtRescisao,
            CAST(E.EMP_Codigo AS BIGINT) AS EmpresaCodigo,
            S.Valor AS SalarioContratual, S.Adiantamento AS FlagAdiantamento,
            S.PercentualAdiant, S.ValorAdiant AS ValorFixoAdiant, C.NOME AS Cargo
        FROM EPG AS E
        INNER JOIN SEP AS S ON E.EMP_Codigo = S.EMP_Codigo AND E.Codigo = S.EPG_Codigo
        LEFT JOIN CAR AS C ON S.CAR_Codigo = C.CODIGO AND S.EMP_Codigo = C.EMP_Codigo
        WHERE
            S.DATA = (
                SELECT MAX(S2.DATA) FROM SEP AS S2
                WHERE S2.EMP_Codigo = S.EMP_Codigo AND S2.EPG_Codigo = S.EPG_Codigo AND S2.DATA <= ?
            )
            AND E.EMP_Codigo = ?
            AND (E.DtRescisao IS NULL OR E.DtRescisao >= ?)
    """
    # CORREÇÃO: Usando 'ano' e 'mes' em vez de 'year' e 'month'
    fim_do_mes = pd.Timestamp(ano, mes, 1) + pd.offsets.MonthEnd(0)
    params = [fim_do_mes, emp_codigo, inicio_mes_ref]

    with get_connection() as conn:
        return pd.read_sql(query, conn, params=params)


def fetch_employee_leaves(
    emp_codigo: str, employee_ids: list, ano: int, mes: int
) -> pd.DataFrame:
    if not employee_ids:
        return pd.DataFrame()

    inicio_mes = f"{ano}-{mes:02d}-01"
    proximo_mes_ano = ano + 1 if mes == 12 else ano
    proximo_mes_mes = 1 if mes == 12 else mes + 1
    inicio_proximo_mes = f"{proximo_mes_ano}-{proximo_mes_mes:02d}-01"

    placeholders = ", ".join("?" * len(employee_ids))
    query = f"""
        SELECT EPG_CODIGO AS Matricula, DTINICIAL AS DtInicio, DTFINAL AS DtFim, 
               TLI_CODIGO AS CodigoTipoLicenca, T.NOME AS Tipo
        FROM LIC L JOIN TLI T ON L.TLI_CODIGO = T.CODIGO
        WHERE L.EMP_Codigo = ? 
          AND L.EPG_CODIGO IN ({placeholders})
          AND L.DTFINAL >= ? AND L.DTINICIAL < ?
    """
    params = [emp_codigo] + employee_ids + [inicio_mes, inicio_proximo_mes]

    with get_connection() as conn:
        df = pd.read_sql(query, conn, params=params)
        df["DtInicio"] = pd.to_datetime(df["DtInicio"], errors="coerce")
        df["DtFim"] = pd.to_datetime(df["DtFim"], errors="coerce")
        return df


def fetch_employee_loans(
    emp_codigo: str, employee_ids: list, ano: int, mes: int
) -> pd.DataFrame:
    if not employee_ids:
        return pd.DataFrame()

    ano_mes_competencia = f"{ano}{mes:02d}"
    placeholders = ", ".join("?" * len(employee_ids))
    query = f"""
        SELECT COT_EPG_Codigo AS Matricula, SUM(ValorParcela) AS ValorParcelaConsignado
        FROM COE
        WHERE EMP_Codigo = ? AND COT_EPG_Codigo IN ({placeholders})
          AND AnoMesDesconto = ?
        GROUP BY COT_EPG_Codigo
    """
    params = [emp_codigo] + employee_ids + [ano_mes_competencia]

    with get_connection() as conn:
        return pd.read_sql(query, conn, params=params)


def fetch_all_companies():
    query = "SELECT Codigo, Nome FROM EMP WHERE DESATIVADA = 0 ORDER BY Nome"
    try:
        with get_connection() as conn:
            companies_df = pd.read_sql(query, conn)
            return pd.Series(
                companies_df.Codigo.values, index=companies_df.Nome
            ).to_dict()
    except Exception as e:
        return {"JR Rodrigues (Fallback)": "9098"}
