# backend/src/adiantamento/data_extraction.py
import pandas as pd
from src.database import get_connection
from typing import Optional
import warnings

warnings.filterwarnings("ignore", category=UserWarning, module="pandas")
# -------------------------------
from ..database import get_connection


def audit_advance_flags(emp_codigo: str) -> pd.DataFrame:
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
            AND E.DtRescisao IS NULL
            AND (S.Adiantamento IS NULL OR S.Adiantamento != 'S')
        ORDER BY E.Nome;
    """
    # Uso do Context Manager para segurança
    with get_connection() as conn:
        return pd.read_sql(query, conn, params=[emp_codigo])


def fetch_raw_advance_payroll(emp_codigo: str, ano: int, mes: int) -> pd.DataFrame:
    """Busca a folha bruta (ADIANTAMENTO) no Fortes."""
    fim_do_mes = pd.Timestamp(ano, mes, 1) + pd.offsets.MonthEnd(0)
    inicio_mes_ref = f"{ano}-{mes:02d}-01"

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
    params = [fim_do_mes, int(emp_codigo), inicio_mes_ref]

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
        LEFT JOIN SEP AS S ON E.EMP_Codigo = S.EMP_Codigo AND E.Codigo = S.EPG_Codigo
        AND S.DATA = (
            SELECT MAX(S2.DATA) FROM SEP AS S2
            WHERE S2.EMP_Codigo = S.EMP_Codigo AND S2.EPG_Codigo = S.EPG_Codigo AND S2.DATA <= %s
        )
        LEFT JOIN CAR AS C ON S.CAR_Codigo = C.CODIGO AND S.EMP_Codigo = C.EMP_Codigo
        WHERE
            E.EMP_Codigo = %s
            AND (E.DtRescisao IS NULL OR E.DtRescisao >= %s)
    """
    fim_do_mes = pd.Timestamp(ano, mes, 1) + pd.offsets.MonthEnd(0)
    params = [fim_do_mes, int(emp_codigo), inicio_mes_ref]

    with get_connection() as conn:
        return pd.read_sql(query, conn, params=params)


def fetch_employee_leaves(
    emp_codigo: str, employee_ids: list, ano: int, mes: int
) -> pd.DataFrame:
    if not employee_ids:
        return pd.DataFrame()

    inicio_mes = f"{ano}-{mes:02d}-01"
    # Lógica simples para próximo mês
    if mes == 12:
        inicio_proximo_mes = f"{ano + 1}-01-01"
    else:
        inicio_proximo_mes = f"{ano}-{mes + 1:02d}-01"

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
    params = [int(emp_codigo)] + employee_ids + [inicio_proximo_mes, inicio_mes]

    with get_connection() as conn:
        df = pd.read_sql(query, conn, params=params)
        if df.empty:
            return df

        # Tratamento de datas
        df["DtInicio"] = pd.to_datetime(df["DtInicio"], errors="coerce")
        df["DtFim"] = pd.to_datetime(df["DtFim"], errors="coerce")

        return (
            df.groupby("Matricula")
            .agg(
                {
                    "DtInicio": "min",
                    "DtFim": "max",
                    "CodigoTipoLicenca": "first",
                    "Tipo": "first",
                }
            )
            .reset_index()
        )


def fetch_employee_loans(
    emp_codigo: str, employee_ids: list, ano: int, mes: int
) -> pd.DataFrame:
    if not employee_ids:
        return pd.DataFrame()

    ano_mes = f"{ano}{mes:02d}"
    placeholders = ", ".join(["%s"] * len(employee_ids))
    query = f"""
        SELECT COT_EPG_Codigo AS Matricula, SUM(ValorParcela) AS ValorParcelaConsignado
        FROM COE
        WHERE EMP_Codigo = %s AND COT_EPG_Codigo IN ({placeholders})
          AND AnoMesDesconto = %s
        GROUP BY COT_EPG_Codigo
    """
    params = [int(emp_codigo)] + employee_ids + [ano_mes]
    with get_connection() as conn:
        return pd.read_sql(query, conn, params=params)


def fetch_employee_events(
    emp_codigo: str, employee_ids: list, ano: int, mes: int, event_codes: list
) -> pd.DataFrame:
    # Mantido vazio conforme lógica anterior
    return pd.DataFrame()


def fetch_all_companies():
    query = "SELECT Codigo, Nome FROM EMP WHERE DESATIVADA = 0 ORDER BY Nome"
    try:
        with get_connection() as conn:
            # Se for pymssql (dev), cursor pode ser iterado ou read_sql
            df = pd.read_sql(query, conn)
            # Retorna dict {Nome: Codigo} para o sidebar do Streamlit (se ainda usado)
            return pd.Series(df.Codigo.values, index=df.Nome).to_dict()
    except Exception as e:
        print(f"Erro ao buscar empresas: {e}")
        return {}


def fetch_real_advance_values(emp_codigo: str, ano: int, mes: int) -> pd.DataFrame:
    """
    Busca o Valor Líquido REAL calculado pelo Fortes.
    ATUALIZAÇÃO: Agora considera ProvDesc = -1 como Desconto.
    """
    ano_mes = f"{ano}{mes:02d}"

    query = """
        SELECT 
            EFO.EPG_CODIGO as Matricula,
            SUM(
                CASE 
                    -- Proventos (Soma)
                    WHEN EVE.ProvDesc = 1 THEN EFP.VALOR   
                    
                    -- Descontos Padrão (Subtrai)
                    WHEN EVE.ProvDesc = 2 THEN -EFP.VALOR
                    
                    -- Descontos Especiais/Provisão (Subtrai) - CORREÇÃO AQUI
                    WHEN EVE.ProvDesc = -1 THEN -EFP.VALOR
                    
                    -- Bases e Informativos (Ignora)
                    ELSE 0 
                END
            ) as ValorRealFortes
        FROM FOL (NOLOCK)
        INNER JOIN FPG (NOLOCK) 
            ON FOL.EMP_Codigo = FPG.EMP_Codigo 
            AND FOL.Seq = FPG.FOL_Seq
        INNER JOIN EFO (NOLOCK) 
            ON FOL.EMP_Codigo = EFO.EMP_Codigo 
            AND FOL.Seq = EFO.FOL_Seq
        INNER JOIN EFP (NOLOCK) 
            ON EFO.EMP_Codigo = EFP.EMP_Codigo 
            AND EFO.FOL_Seq = EFP.EFO_FOL_Seq 
            AND EFO.EPG_Codigo = EFP.EFO_EPG_Codigo
        INNER JOIN EVE (NOLOCK) 
            ON EFP.EMP_Codigo = EVE.EMP_Codigo 
            AND EFP.EVE_Codigo = EVE.Codigo
        WHERE 
            FOL.EMP_Codigo = %s
            AND FPG.AnoMes = %s
            AND FOL.Folha = 1  -- 1 = Adiantamento
            
            -- Pega apenas a última versão da folha
            AND FOL.Seq = (
                SELECT TOP 1 F2.Seq 
                FROM FOL F2 (NOLOCK)
                INNER JOIN FPG G2 (NOLOCK) ON F2.EMP_Codigo = G2.EMP_Codigo AND F2.Seq = G2.FOL_Seq
                WHERE F2.EMP_Codigo = FOL.EMP_Codigo AND G2.AnoMes = FPG.AnoMes AND F2.Folha = 1
                ORDER BY F2.Seq DESC
            )
        GROUP BY EFO.EPG_CODIGO
    """

    params = [int(emp_codigo), ano_mes]

    with get_connection() as conn:
        return pd.read_sql(query, conn, params=params)
