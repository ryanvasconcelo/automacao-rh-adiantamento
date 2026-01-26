# backend/src/fopag/data_fetcher.py
import logging
from typing import List, Dict, Optional
from src.database import get_connection

logger = logging.getLogger(__name__)


def dict_factory(cursor, row):
    """Helper para converter Row de Tupla em Dicionário"""
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def get_folha_id(empresa_codigo: str, mes: int, ano: int) -> Optional[int]:
    """Busca o ID (Sequencial) da Folha Mensal."""
    ano_mes = f"{ano}{mes:02d}"
    sql = """
        SELECT TOP 1 FOL.Seq
        FROM FOL (NOLOCK)
        INNER JOIN FPG (NOLOCK) ON FOL.EMP_Codigo = FPG.EMP_Codigo AND FOL.Seq = FPG.FOL_Seq
        WHERE FOL.EMP_Codigo = %s AND FPG.AnoMes = %s
          AND FOL.Folha = 2 AND FPG.Tipo IN (1, 4)
        ORDER BY FOL.Seq DESC
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (empresa_codigo, ano_mes))
            row = cursor.fetchone()
            if row:
                data = dict_factory(cursor, row)
                return data["Seq"]
            return None
    except Exception as e:
        logger.error(f"Erro ao buscar ID da folha: {e}")
        raise


def fetch_payroll_data(empresa_codigo: str, folha_seq: int) -> List[Dict]:
    """
    Busca eventos da folha com TODAS as informações necessárias:
    - Carga horária real
    - Dependentes para salário família
    - Referências dinâmicas (insalubridade, faltas)
    """
    sql = """
        SELECT 
            EPG.Codigo AS Matricula,
            EPG.Nome AS Nome,
            EPG.AdmissaoData AS DataAdmissao,
            EPG.Categoria AS CodigoVinculo,
            
            -- Carga horária real
            ISNULL(SEP.HorasMes, 220) AS CargaHoraria,
            
            -- ✅ NOVO: Contagem de dependentes para salário família
            (SELECT COUNT(*) 
             FROM DEP (NOLOCK) 
             WHERE DEP.EMP_Codigo = EPG.EMP_Codigo 
               AND DEP.EPG_Codigo = EPG.Codigo 
               AND DEP.SalarioFamilia = 'S') AS DependentesSalarioFamilia,
            
            -- Eventos
            EFP.EVE_Codigo AS Codigo,
            EVE.NomeApr AS Descricao,
            EVE.ProvDesc AS Tipo, 
            EFP.Valor AS Valor,
            EFP.Referencia AS Referencia,
            
            -- Incidências (eSocial)
            EVE.IndicativoCPMensalFerias AS IncideINSS,
            EVE.IndicativoIRRFMensal AS IncideIRRF,
            EVE.IndicativoFGTSMensalFerias AS IncideFGTS

        FROM EFO (NOLOCK)
        INNER JOIN EPG (NOLOCK) ON EFO.EMP_Codigo = EPG.EMP_Codigo 
                                AND EFO.EPG_Codigo = EPG.Codigo
        
        -- Carga horária vigente
        LEFT JOIN SEP (NOLOCK) ON EFO.EMP_Codigo = SEP.EMP_Codigo 
                              AND EFO.EPG_Codigo = SEP.EPG_Codigo 
                              AND EFO.SEP_Data = SEP.Data

        -- Eventos da folha
        LEFT JOIN EFP (NOLOCK) ON EFO.EMP_Codigo = EFP.EMP_Codigo 
                              AND EFO.FOL_Seq = EFP.EFO_FOL_Seq 
                              AND EFO.EPG_Codigo = EFP.EFO_EPG_Codigo
        LEFT JOIN EVE (NOLOCK) ON EFP.EMP_Codigo = EVE.EMP_Codigo 
                              AND EFP.EVE_CODIGO = EVE.CODIGO
        
        WHERE EFO.EMP_Codigo = %s 
          AND EFO.FOL_Seq = %s 
          AND EFP.Valor > 0
        ORDER BY EPG.Nome, EFP.EVE_Codigo
    """

    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (empresa_codigo, folha_seq))
            rows = [dict_factory(cursor, row) for row in cursor.fetchall()]

            funcionarios_map = {}
            CODIGOS_APRENDIZ = ["103", "55", "56", "07"]

            for row in rows:
                matricula = str(row["Matricula"]).strip()

                if matricula not in funcionarios_map:
                    vinculo = (
                        str(row["CodigoVinculo"]).strip()
                        if row["CodigoVinculo"]
                        else ""
                    )
                    cargo_detectado = (
                        "Jovem Aprendiz"
                        if vinculo in CODIGOS_APRENDIZ
                        else "Funcionario Padrão"
                    )

                    funcionarios_map[matricula] = {
                        "matricula": matricula,
                        "nome": str(row["Nome"]).strip(),
                        "data_admissao": row["DataAdmissao"],
                        "cargo": cargo_detectado,
                        "carga_horaria": float(row["CargaHoraria"]),
                        "tipo_contrato": vinculo,
                        "dependentes": int(
                            row["DependentesSalarioFamilia"] or 0
                        ),  # ✅ NOVO
                        "eventos": [],
                        "proventos_base": [],
                        "eventos_variaveis_referencia": [],
                        "eventos_calculados_fortes": {},
                    }

                # Normalização do código
                try:
                    codigo_limpo = str(int(row["Codigo"]))
                except:
                    codigo_limpo = str(row["Codigo"]).strip()

                valor = float(row["Valor"])
                referencia = float(row["Referencia"]) if row["Referencia"] else 0.0
                tipo_evento = row["Tipo"]

                # Incidências
                def check_incidence(val):
                    try:
                        return int(val) > 0
                    except:
                        return False

                inc_inss = check_incidence(row.get("IncideINSS"))
                inc_irrf = check_incidence(row.get("IncideIRRF"))
                inc_fgts = check_incidence(row.get("IncideFGTS"))

                evento = {
                    "codigo": codigo_limpo,
                    "descricao": str(row["Descricao"]).strip(),
                    "tipo": tipo_evento,
                    "valor": valor,
                    "referencia": referencia,
                    "incidencias": {
                        "inss": inc_inss,
                        "irrf": inc_irrf,
                        "fgts": inc_fgts,
                    },
                }

                funcionarios_map[matricula]["eventos"].append(evento)
                funcionarios_map[matricula]["eventos_calculados_fortes"][
                    codigo_limpo
                ] = valor

                if codigo_limpo in ["11", "13", "31", "001"]:
                    funcionarios_map[matricula]["proventos_base"].append(
                        {"codigo": codigo_limpo, "valor": valor}
                    )
                else:
                    funcionarios_map[matricula]["eventos_variaveis_referencia"].append(
                        {
                            "codigo": codigo_limpo,
                            "referencia": referencia,
                            "valor": valor,
                            "descricao": evento["descricao"],
                        }
                    )

            return list(funcionarios_map.values())

    except Exception as e:
        logger.error(f"Erro fetch_payroll_data: {e}")
        raise
