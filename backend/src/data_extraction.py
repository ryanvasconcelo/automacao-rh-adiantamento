# src/data_extraction.py (Versão com correção no JOIN da folha bruta)
import pandas as pd
from .database import get_connection
from typing import Optional


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


def fetch_payroll_report_data(
    emp_codigo: str,
    fol_seq: int,
    filtro_estabelecimento: str = None,
    filtro_lotacao: str = None,
    filtro_obra: str = None,
) -> pd.DataFrame:
    """
    Busca os dados de uma folha de adiantamento já calculada no Fortes,
    agora com a lógica de filtros completa baseada nos logs.
    """

    params = []

    # --- CONSTRUÇÃO DINÂMICA DA QUERY BASEADA NOS LOGS ---

    # Cláusula para Estabelecimento
    filtro_est_sql = " AND (%s = '' OR SEP.EST_CODIGO = %s)"
    params.extend([filtro_estabelecimento or "", filtro_estabelecimento or ""])

    # Cláusula para Obra/Tomador (baseado no log da NEWEN)
    filtro_obra_sql = ""
    if filtro_obra:
        filtro_obra_sql = " AND SEP.TOM_Codigo = %s"
        params.append(filtro_obra)

    # Cláusula para Lotação (baseado no log da NEWEN)
    # Em um sistema real, teríamos que gerenciar o ID da sessão para a tabela mLOT.
    # Para nossa automação, podemos simplificar e filtrar diretamente, o que é mais eficiente.
    filtro_lotacao_sql = ""
    if filtro_lotacao:
        filtro_lotacao_sql = " AND SEP.LOT_CODIGO = %s"
        params.append(filtro_lotacao)

    # Adiciona os parâmetros principais no início da lista
    params.insert(0, fol_seq)
    params.insert(0, int(emp_codigo))

    query_principal = f"""
        SELECT 
            EFO.EPG_CODIGO AS Matricula,
            EPG.NOME AS Nome,
            SCAR1.NOME AS Cargo,
            SEP.VALOR AS SalarioContratual,
            EFPADIANT.VALOR AS ValorAdiantamento,
            EFPBASE.VALOR AS BaseCalculo,
            LOT.NOME AS Lotacao,
            SEP.EST_CODIGO AS EstabelecimentoCodigo,
            SEP.TOM_CODIGO AS ObraCodigo,
            SEP.LOT_CODIGO AS LotacaoCodigo
        FROM FOL
        LEFT JOIN EFO ON FOL.EMP_CODIGO = EFO.EMP_CODIGO AND FOL.SEQ = EFO.FOL_SEQ
        LEFT JOIN EPG ON EFO.EMP_CODIGO = EPG.EMP_CODIGO AND EFO.EPG_CODIGO = EPG.CODIGO
        LEFT JOIN EFP EFPADIANT ON EFO.EMP_CODIGO = EFPADIANT.EMP_CODIGO AND EFO.FOL_SEQ = EFPADIANT.EFO_FOL_SEQ AND EFO.EPG_CODIGO = EFPADIANT.EFO_EPG_CODIGO AND EFPADIANT.EVE_CODIGO = '001'
        LEFT JOIN EFP EFPBASE ON EFO.EMP_CODIGO = EFPBASE.EMP_CODIGO AND EFO.FOL_SEQ = EFPBASE.EFO_FOL_SEQ AND EFO.EPG_CODIGO = EFPBASE.EFO_EPG_CODIGO AND EFPBASE.EVE_CODIGO = '608'
        LEFT JOIN SEP ON EFO.EMP_CODIGO = SEP.EMP_CODIGO AND EFO.EPG_CODIGO = SEP.EPG_CODIGO AND EFO.SEP_DATA = SEP.DATA
        LEFT JOIN CAR ON CAR.EMP_CODIGO = SEP.EMP_CODIGO AND CAR.CODIGO = SEP.CAR_CODIGO
        LEFT JOIN SCAR SCAR1 ON CAR.EMP_CODIGO = SCAR1.EMP_CODIGO AND SCAR1.CAR_CODIGO = CAR.CODIGO AND SCAR1.DATA = (
            SELECT MAX(SCAR2.DATA) FROM SCAR SCAR2
            WHERE SCAR2.EMP_CODIGO = SCAR1.EMP_CODIGO AND SCAR2.CAR_CODIGO = SCAR1.CAR_CODIGO AND SCAR2.DATA <= FOL.DTCALCULO
        )
        LEFT JOIN LOT ON SEP.EMP_CODIGO = LOT.EMP_CODIGO AND SEP.LOT_CODIGO = LOT.CODIGO
        WHERE FOL.EMP_CODIGO = %s AND FOL.SEQ = %s
        {filtro_est_sql}
        {filtro_obra_sql}
        {filtro_lotacao_sql}
        ORDER BY EPG.NOME
    """

    # A query de eventos precisa dos mesmos filtros
    query_eventos = f"""
        SELECT 
            EFO.EPG_CODIGO AS Matricula,
            EVE.CODIGO AS EventoCodigo,
            EVE.NOMEAPR AS EventoNome,
            EFP.REFERENCIA AS EventoReferencia,
            EFP.VALOR * EVE.PROVDESC AS EventoValor
        FROM FOL
        LEFT JOIN EFO ON FOL.EMP_CODIGO = EFO.EMP_CODIGO AND FOL.SEQ = EFO.FOL_SEQ
        LEFT JOIN EFP ON EFO.EMP_CODIGO = EFP.EMP_CODIGO AND EFO.FOL_SEQ = EFP.EFO_FOL_SEQ AND EFO.EPG_CODIGO = EFP.EFO_EPG_CODIGO
        LEFT JOIN EVE ON EFP.EVE_CODIGO = EVE.CODIGO AND EFP.EMP_CODIGO = EVE.EMP_CODIGO
        LEFT JOIN SEP ON EFO.EMP_CODIGO = SEP.EMP_CODIGO AND EFO.EPG_CODIGO = SEP.EPG_CODIGO AND EFO.SEP_DATA = SEP.DATA
        WHERE FOL.EMP_CODIGO = %s AND FOL.SEQ = %s
        AND EFP.EVE_CODIGO <> '001'
        AND EVE.INFPROVDESC IN ('1', '2')
        {filtro_est_sql}
        {filtro_obra_sql}
        {filtro_lotacao_sql}
        ORDER BY EFO.EPG_CODIGO, EVE.CODIGO
    """

    with get_connection() as conn:
        df_principal = pd.read_sql(query_principal, conn, params=params)
        if df_principal.empty:
            return pd.DataFrame()

        df_eventos = pd.read_sql(query_eventos, conn, params=params)

        if not df_eventos.empty:
            eventos_agrupados = (
                df_eventos.groupby("Matricula")
                .apply(lambda x: x.to_dict(orient="records"))
                .rename("Eventos")
            )
            df_final = pd.merge(
                df_principal, eventos_agrupados, on="Matricula", how="left"
            )
        else:
            df_final = df_principal
            df_final["Eventos"] = None

    return df_final


def debug_fetch_active_employee_count(emp_codigo: str, ano: int, mes: int) -> int:
    """
    DEBUG: Conta o número de funcionários ativos em EPG para um dado período.
    """
    inicio_mes_ref = f"{ano}-{mes:02d}-01"
    query = """
        SELECT COUNT(*) as count
        FROM EPG AS E
        WHERE
            E.EMP_Codigo = %s
            AND (E.DtRescisao IS NULL OR E.DtRescisao >= %s)
    """
    params = [emp_codigo, inicio_mes_ref]
    with get_connection() as conn:
        count_df = pd.read_sql(query, conn, params=params)
        return count_df["count"].iloc[0] if not count_df.empty else 0


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
    params = [int(emp_codigo)] + employee_ids + [inicio_proximo_mes, inicio_mes]
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
    params = [int(emp_codigo)] + employee_ids + [ano_mes_competencia]
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
    params = [fim_do_mes, int(emp_codigo), inicio_mes_ref]

    with get_connection() as conn:
        df = pd.read_sql(query, conn, params=params)
        return df


def get_latest_fol_seq(emp_codigo: str, ano: int, mes: int) -> Optional[int]:
    """Busca o 'Seq' da folha de pagamento (FOL) mais recente para uma competência."""
    ano_mes = f"{ano}{mes:02d}"
    query = """
        SELECT TOP 1 FOL.Seq
        FROM FPG
        LEFT JOIN FOL ON FPG.EMP_Codigo = FOL.EMP_Codigo AND FPG.FOL_Seq = FOL.Seq
        WHERE FPG.EMP_Codigo = %s
          AND FPG.AnoMes = %s
          AND FOL.Folha = 1
        ORDER BY FOL.ENCERRADA ASC, FPG.Sequencial DESC, FOL.Seq DESC
    """
    params = [emp_codigo, ano_mes]
    with get_connection() as conn:
        df = pd.read_sql(query, conn, params=params)
    return int(df["Seq"].iloc[0]) if not df.empty else None


def fetch_filters_for_company(emp_codigo: str) -> dict:
    """Busca todas as listas de filtros para uma empresa."""
    filters = {"estabelecimentos": [], "obras": [], "lotacoes": []}
    with get_connection() as conn:
        df_est = pd.read_sql(
            "SELECT CODIGO, NOME FROM EST WHERE EMP_CODIGO = %s ORDER BY NOME",
            conn,
            params=[emp_codigo],
        )
        if not df_est.empty:
            filters["estabelecimentos"] = df_est.to_dict(orient="records")
        df_obr = pd.read_sql(
            "SELECT CODIGO, NOME FROM TOM WHERE EMP_CODIGO = %s ORDER BY NOME",
            conn,
            params=[emp_codigo],
        )
        if not df_obr.empty:
            filters["obras"] = df_obr.to_dict(orient="records")
        df_lot = pd.read_sql(
            "SELECT CODIGO, NOME FROM LOT WHERE EMP_CODIGO = %s ORDER BY NOME",
            conn,
            params=[emp_codigo],
        )
        if not df_lot.empty:
            filters["lotacoes"] = df_lot.to_dict(orient="records")
    return filters


# --- NOVAS FUNÇÕES DE BUSCA DE DADOS PARA CADA RELATÓRIO ---
def fetch_listagem_adiantamento_data(
    emp_codigo: str, fol_seq: int, **kwargs
) -> pd.DataFrame:
    """Busca dados para o relatório 'Listagem de Adiantamento'."""
    params = [int(emp_codigo), fol_seq]
    filtro_est_sql = " AND (%s = '' OR SEP.EST_CODIGO = %s)"
    params.extend(
        [
            kwargs.get("filtro_estabelecimento") or "",
            kwargs.get("filtro_estabelecimento") or "",
        ]
    )
    # Adicione outros filtros conforme necessário

    query = f"""
        SELECT 
            EFO.EPG_CODIGO AS Matricula, EPG.NOME AS Nome, SCAR1.NOME AS Cargo,
            SEP.VALOR AS SalarioContratual, EFPADIANT.VALOR AS ValorAdiantamento,
            EFPBASE.VALOR AS BaseCalculo, LOT.NOME AS Lotacao, SEP.EST_CODIGO AS EstabelecimentoCodigo,
            SEP.TOM_CODIGO AS ObraCodigo, SEP.LOT_CODIGO AS LotacaoCodigo
        FROM FOL
        LEFT JOIN EFO ON FOL.EMP_CODIGO = EFO.EMP_CODIGO AND FOL.SEQ = EFO.FOL_SEQ
        LEFT JOIN EPG ON EFO.EMP_CODIGO = EPG.EMP_CODIGO AND EFO.EPG_CODIGO = EPG.CODIGO
        LEFT JOIN EFP EFPADIANT ON EFO.EMP_CODIGO = EFPADIANT.EMP_CODIGO AND EFO.FOL_SEQ = EFPADIANT.EFO_FOL_SEQ AND EFO.EPG_CODIGO = EFPADIANT.EFO_EPG_CODIGO AND EFPADIANT.EVE_CODIGO = '001'
        LEFT JOIN EFP EFPBASE ON EFO.EMP_CODIGO = EFPBASE.EMP_CODIGO AND EFO.FOL_SEQ = EFPBASE.EFO_FOL_SEQ AND EFO.EPG_CODIGO = EFPBASE.EFO_EPG_CODIGO AND EFPBASE.EVE_CODIGO = '608'
        LEFT JOIN SEP ON EFO.EMP_CODIGO = SEP.EMP_CODIGO AND EFO.EPG_CODIGO = SEP.EPG_CODIGO AND EFO.SEP_DATA = SEP.DATA
        LEFT JOIN CAR ON CAR.EMP_CODIGO = SEP.EMP_CODIGO AND CAR.CODIGO = SEP.CAR_CODIGO
        LEFT JOIN SCAR SCAR1 ON CAR.EMP_CODIGO = SCAR1.EMP_CODIGO AND SCAR1.CAR_CODIGO = CAR.CODIGO AND SCAR1.DATA = (
            SELECT MAX(SCAR2.DATA) FROM SCAR SCAR2
            WHERE SCAR2.EMP_CODIGO = SCAR1.EMP_CODIGO AND SCAR2.CAR_CODIGO = SCAR1.CAR_CODIGO AND SCAR2.DATA <= FOL.DTCALCULO
        )
        LEFT JOIN LOT ON SEP.EMP_CODIGO = LOT.EMP_CODIGO AND SEP.LOT_CODIGO = LOT.CODIGO
        WHERE FOL.EMP_CODIGO = %s AND FOL.SEQ = %s
        {filtro_est_sql}
        ORDER BY EPG.NOME
    """
    with get_connection() as conn:
        return pd.read_sql(query, conn, params=params)


def fetch_recibo_pagamento_data(
    emp_codigo: str, fol_seq: int, **kwargs
) -> pd.DataFrame:
    """Busca dados para o 'Recibo de Pagamento', incluindo dados bancários."""
    params = [int(emp_codigo), fol_seq]
    filtro_est_sql = " AND (%s = '' OR SEP.EST_CODIGO = %s)"
    params.extend(
        [
            kwargs.get("filtro_estabelecimento") or "",
            kwargs.get("filtro_estabelecimento") or "",
        ]
    )

    query = f"""
        SELECT 
            BAN.NOME AS Banco, AGB.NOME AS Agencia, EPG.CONTACORRENTE AS ContaCorrente,
            EFO.EPG_CODIGO AS Matricula, EPG.NOME AS Nome, EPG.ADMISSAODATA AS Admissao,
            SCAR1.NOME AS Cargo, SEP.VALOR AS Salario, EFP.VALOR AS ValorReceber,
            EFP.REFERENCIA AS Referencia, LOT.NOME AS Lotacao, EST.NOME AS Estabelecimento
        FROM FOL
        LEFT JOIN EFO ON FOL.EMP_CODIGO = EFO.EMP_CODIGO AND FOL.SEQ = EFO.FOL_SEQ
        LEFT JOIN EPG ON EFO.EMP_CODIGO = EPG.EMP_CODIGO AND EFO.EPG_CODIGO = EPG.CODIGO
        LEFT JOIN SEP ON EFO.EMP_CODIGO = SEP.EMP_CODIGO AND EFO.EPG_CODIGO = SEP.EPG_CODIGO AND EFO.SEP_DATA = SEP.DATA
        LEFT JOIN EST ON SEP.EMP_CODIGO = EST.EMP_CODIGO AND SEP.EST_CODIGO = EST.CODIGO
        LEFT JOIN CAR ON CAR.EMP_CODIGO = SEP.EMP_CODIGO AND CAR.CODIGO = SEP.CAR_CODIGO
        LEFT JOIN SCAR SCAR1 ON CAR.EMP_CODIGO = SCAR1.EMP_CODIGO AND SCAR1.CAR_CODIGO = CAR.CODIGO AND SCAR1.DATA = (
            SELECT MAX(SCAR2.DATA) FROM SCAR SCAR2 WHERE SCAR2.EMP_CODIGO = SCAR1.EMP_CODIGO AND SCAR2.CAR_CODIGO = SCAR1.CAR_CODIGO AND SCAR2.DATA <= FOL.DTCALCULO
        )
        LEFT JOIN LOT ON SEP.EMP_CODIGO = LOT.EMP_CODIGO AND SEP.LOT_CODIGO = LOT.CODIGO
        LEFT JOIN BAN ON EPG.BAN_CODIGO = BAN.CODIGO
        LEFT JOIN AGB ON EPG.BAN_CODIGO = AGB.BAN_CODIGO AND EPG.AGB_CODIGO = AGB.CODIGO
        LEFT JOIN EFP ON EFO.EMP_CODIGO = EFP.EMP_CODIGO AND EFO.FOL_SEQ = EFP.EFO_FOL_SEQ AND EFO.EPG_CODIGO = EFP.EFO_EPG_CODIGO
        WHERE FOL.EMP_CODIGO = %s AND FOL.SEQ = %s AND EFP.EVE_CODIGO = '001'
        {filtro_est_sql}
        ORDER BY EPG.NOME
    """
    with get_connection() as conn:
        return pd.read_sql(query, conn, params=params)


def fetch_folha_sintetica_data(emp_codigo: str, fol_seq: int, **kwargs) -> pd.DataFrame:
    """Busca dados agregados para a 'Folha Sintética'."""
    params = [int(emp_codigo), fol_seq]
    filtro_est_sql = " AND (%s = '' OR SEP.EST_CODIGO = %s)"
    params.extend(
        [
            kwargs.get("filtro_estabelecimento") or "",
            kwargs.get("filtro_estabelecimento") or "",
        ]
    )

    query = f"""
        SELECT 
            EST.NOME AS Estabelecimento, LOT.NOME AS Lotacao,
            EVE.CODIGO AS EventoCodigo, EVE.NOMEAPR AS EventoNome,
            SUM(EFP.VALOR * EVE.PROVDESC) AS ValorTotal
        FROM FOL
        LEFT JOIN EFO ON FOL.EMP_CODIGO = EFO.EMP_CODIGO AND FOL.SEQ = EFO.FOL_SEQ
        LEFT JOIN EFP ON EFO.EMP_CODIGO = EFP.EMP_CODIGO AND EFO.FOL_SEQ = EFP.EFO_FOL_SEQ AND EFO.EPG_CODIGO = EFP.EFO_EPG_CODIGO
        LEFT JOIN EVE ON EFP.EMP_CODIGO = EVE.EMP_CODIGO AND EFP.EVE_CODIGO = EVE.CODIGO
        LEFT JOIN SEP ON EFO.EMP_CODIGO = SEP.EMP_CODIGO AND EFO.EPG_CODIGO = SEP.EPG_CODIGO AND EFO.SEP_DATA = SEP.DATA
        LEFT JOIN EST ON SEP.EMP_CODIGO = EST.EMP_CODIGO AND SEP.EST_CODIGO = EST.CODIGO
        LEFT JOIN LOT ON SEP.EMP_CODIGO = LOT.EMP_CODIGO AND SEP.LOT_CODIGO = LOT.CODIGO
        WHERE FOL.EMP_CODIGO = %s AND FOL.SEQ = %s
        {filtro_est_sql}
        GROUP BY EST.NOME, LOT.NOME, EVE.CODIGO, EVE.NOMEAPR
        ORDER BY EST.NOME, LOT.NOME, EVE.CODIGO
    """
    with get_connection() as conn:
        return pd.read_sql(query, conn, params=params)
