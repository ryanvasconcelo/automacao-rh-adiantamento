# src/data_extraction.py (Versão com correção no JOIN da folha bruta)
import pandas as pd
from .database import get_connection


# NOVA FUNÇÃO DE AUDITORIA
def audit_advance_flags(emp_codigo: str) -> pd.DataFrame:
    """
    Audita funcionários ativos para verificar se a flag de adiantamento está desmarcada.
    Retorna um DataFrame com os funcionários inconsistentes.
    """
    query = """
        SELECT
            E.Codigo AS Matricula,
            E.Nome,
            E.AdmissaoData,
            S.Adiantamento AS FlagAdiantamento,
            C.NOME AS Cargo
        FROM EPG AS E
        INNER JOIN SEP AS S ON E.EMP_Codigo = S.EMP_Codigo AND E.Codigo = S.EPG_Codigo
        LEFT JOIN CAR AS C ON S.CAR_Codigo = C.CODIGO AND S.EMP_Codigo = C.EMP_Codigo
        WHERE
            S.DATA = (
                SELECT MAX(S2.DATA) FROM SEP AS S2
                WHERE S2.EMP_Codigo = S.EMP_Codigo AND S2.EPG_Codigo = S.EPG_Codigo
            )
            AND E.EMP_Codigo = %s
            AND E.DtRescisao IS NULL -- Apenas funcionários ativos
            AND (S.Adiantamento IS NULL OR S.Adiantamento != 'S') -- Onde a flag não é 'S'
        ORDER BY
            E.Nome;
    """
    params = [emp_codigo]
    with get_connection() as conn:
        return pd.read_sql(query, conn, params=params)


def fetch_employee_base_data(emp_codigo: str, ano: int, mes: int) -> pd.DataFrame:
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
                WHERE S2.EMP_Codigo = S.EMP_Codigo AND S2.EPG_Codigo = S.EPG_Codigo AND S2.DATA <= %s
            )
            AND E.EMP_Codigo = %s
            AND (E.DtRescisao IS NULL OR E.DtRescisao >= %s)
    """
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
    placeholders = ", ".join(["%s"] * len(employee_ids))
    query = f"""
        SELECT EPG_CODIGO AS Matricula, DTINICIAL AS DtInicio, DTFINAL AS DtFim, 
               TLI_CODIGO AS CodigoTipoLicenca, T.NOME AS Tipo
        FROM LIC L JOIN TLI T ON L.TLI_CODIGO = T.CODIGO
        WHERE L.EMP_Codigo = %s 
          AND L.EPG_CODIGO IN ({placeholders})
          AND L.DTINICIAL < %s
          AND (L.DTFINAL >= %s OR L.DTFINAL IS NULL)
    """
    params = [emp_codigo] + employee_ids + [inicio_proximo_mes, inicio_mes]
    with get_connection() as conn:
        df = pd.read_sql(query, conn, params=params)
        if df.empty:
            return df
        df["DtInicio"] = pd.to_datetime(df["DtInicio"], errors="coerce")
        df["DtFim"] = pd.to_datetime(df["DtFim"], errors="coerce")
        df_aggregated = (
            df.groupby("Matricula")
            .agg(
                DtInicio=("DtInicio", "min"),
                DtFim=("DtFim", "max"),
                CodigoTipoLicenca=("CodigoTipoLicenca", "first"),
                Tipo=("Tipo", "first"),
            )
            .reset_index()
        )
        return df_aggregated


def fetch_employee_loans(
    emp_codigo: str, employee_ids: list, ano: int, mes: int
) -> pd.DataFrame:
    if not employee_ids:
        return pd.DataFrame()
    ano_mes_competencia = f"{ano}{mes:02d}"
    placeholders = ", ".join(["%s"] * len(employee_ids))
    query = f"""
        SELECT COT_EPG_Codigo AS Matricula, SUM(ValorParcela) AS ValorParcelaConsignado
        FROM COE
        WHERE EMP_Codigo = %s AND COT_EPG_Codigo IN ({placeholders})
          AND AnoMesDesconto = %s
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
    except Exception:
        return {"JR Rodrigues (Fallback)": "9098"}


# src/data_extraction.py (Versão com desativação temporária de eventos)
def fetch_employee_events(
    emp_codigo: str, employee_ids: list, ano: int, mes: int, event_codes: list
) -> pd.DataFrame:
    """
    Busca eventos específicos. TEMPORARIAMENTE DESATIVADA até descobrirmos
    o nome correto da tabela de movimento financeiro.
    """
    print("AVISO: A busca por eventos (Quebra de Caixa, Gratificação) está desativada.")
    # Retorna um DataFrame vazio para não quebrar o fluxo principal
    return pd.DataFrame(columns=["Matricula", "ValorQuebraCaixa", "ValorGratificacao"])


# --- FUNÇÃO CORRIGIDA ---
def fetch_raw_advance_payroll(emp_codigo: str, ano: int, mes: int) -> pd.DataFrame:
    """
    Busca a folha de adiantamento 'bruta' pré-calculada pelo Fortes.
    Esta query foi simplificada para usar apenas os JOINs essenciais e validados.
    """
    fim_do_mes = pd.Timestamp(ano, mes, 1) + pd.offsets.MonthEnd(0)

    # CORREÇÃO: A query foi simplificada para remover JOINs não essenciais (FUN, SIT)
    # que estavam a causar o erro. O JOIN com a tabela CAR foi validado.
    query = """
        SELECT
            E.CODIGO AS Matricula,
            E.NOME AS Nome,
            C.NOME AS Cargo,
            S.VALOR AS SalarioContratual,
            S.PERCENTUALADIANT AS PercentualAdiant,
            convert(numeric(15,2), isnull(S.VALOR,0) * (isnull(S.PERCENTUALADIANT,0)/100)) as ValorBrutoFortes
        FROM EPG E
        JOIN SEP S ON S.EMP_CODIGO = E.EMP_CODIGO AND S.EPG_CODIGO = E.CODIGO
        LEFT JOIN CAR C ON S.CAR_Codigo = C.CODIGO AND S.EMP_Codigo = C.EMP_Codigo
        WHERE
            S.DATA = (
                SELECT MAX(S2.DATA) FROM SEP S2
                WHERE S2.EMP_CODIGO = S.EMP_CODIGO AND S2.EPG_CODIGO = S.EPG_CODIGO AND S2.DATA <= %s
            )
            AND E.EMP_CODIGO = %s
            AND (E.DTRESCISAO IS NULL OR E.DTRESCISAO >= %s)
            AND S.ADIANTAMENTO = 'S'
            AND convert(numeric(15,2),isnull(S.VALOR,0) * (isnull(S.PERCENTUALADIANT,0)/100)) > 0
    """
    inicio_mes_ref = f"{ano}-{mes:02d}-01"
    params = [fim_do_mes, emp_codigo, inicio_mes_ref]

    with get_connection() as conn:
        df = pd.read_sql(query, conn, params=params)
        return df
