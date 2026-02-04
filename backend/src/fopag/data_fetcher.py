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
    Busca TODOS os eventos da folha com informações completas.
    """
    sql = """
        SELECT 
            EPG.Codigo AS Matricula,
            EPG.Nome AS Nome,
            EPG.AdmissaoData AS DataAdmissao,
            EPG.Categoria AS CodigoVinculo,
            
            -- Carga horária real
            ISNULL(SEP.HorasMes, 220) AS CargaHoraria,
            
            (SELECT COUNT(*) 
             FROM DEP (NOLOCK) 
             WHERE DEP.EMP_Codigo = EPG.EMP_Codigo 
               AND DEP.EPG_Codigo = EPG.Codigo
               AND DEP.TB_TIP_DEP_CODIGO IN ('03', '04')) AS DependentesIRRF,
            
            (SELECT COUNT(*) 
             FROM DEP (NOLOCK) 
             WHERE DEP.EMP_Codigo = EPG.EMP_Codigo 
               AND DEP.EPG_Codigo = EPG.Codigo 
               AND DEP.TB_TIP_DEP_CODIGO IN ('03', '04')
               AND (
                   DATEDIFF(year, DEP.NascData, GETDATE()) < 14 
                   OR DEP.IncapazTrabalho = 'S'
               )) AS DependentesSalarioFamilia,
            
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
        
        LEFT JOIN SEP (NOLOCK) ON EFO.EMP_Codigo = SEP.EMP_Codigo 
                              AND EFO.EPG_Codigo = SEP.EPG_Codigo 
                              AND EFO.SEP_Data = SEP.Data

        -- Usando Join Composto Correto
        LEFT JOIN EFP (NOLOCK) ON EFO.EMP_Codigo = EFP.EMP_Codigo 
                              AND EFO.FOL_Seq = EFP.EFO_FOL_Seq 
                              AND EFO.EPG_Codigo = EFP.EFO_EPG_Codigo
        LEFT JOIN EVE (NOLOCK) ON EFP.EMP_Codigo = EVE.EMP_Codigo 
                              AND EFP.EVE_CODIGO = EVE.CODIGO
        
        WHERE EFO.EMP_Codigo = %s 
          AND EFO.FOL_Seq = %s
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
                        "dependentes": int(row["DependentesIRRF"] or 0),
                        "dependentes_salario_familia": int(
                            row["DependentesSalarioFamilia"] or 0
                        ),
                        "eventos": [],
                        "proventos_base": [],
                        "eventos_variaveis_referencia": [],
                        "eventos_calculados_fortes": {},
                    }

                if not row.get("Codigo"):
                    continue

                try:
                    codigo_limpo = str(int(row["Codigo"]))
                except:
                    codigo_limpo = str(row["Codigo"]).strip()

                valor = float(row["Valor"]) if row["Valor"] else 0.0
                referencia = float(row["Referencia"]) if row["Referencia"] else 0.0
                tipo_evento = row["Tipo"]

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


def get_ferias_details(empresa_codigo: str, ano: int, mes: int) -> Dict[str, List[Dict]]:
    """
    Busca eventos de Férias via tabela FER.
    Critério: Férias gozadas no mês de referência (Inicio ou Fim no mês).
    Usa joins explícitos via chaves compostas (EFO_FOL_SEQ, EFO_EPG_CODIGO).
    """
    # Ajuste Fino conforme Logs: LEFT JOINs + EVE.InfProvDesc + Filtros Robustos
    sql = """
        SELECT 
            FER.EFO_EPG_Codigo AS Matricula, 
            EVE.Codigo AS EveCodigo,
            EVE.NomeApr AS Descricao,
            EVE.InfProvDesc AS Tipo, 
            EFP.Valor AS Valor,
            EFP.Referencia AS Referencia,
            EVE.IndicativoCPMensalFerias AS IncideINSS,
            EVE.IndicativoIRRFMensal AS IncideIRRF,
            EVE.IndicativoFGTSMensalFerias AS IncideFGTS,
            
            -- Identificação Semântica do INSS (Base vs Desconto)
            CASE 
                WHEN EVE.Codigo = '602' THEN 'BASE_INSS'
                -- Se for Desconto (2) e tiver INSS no nome (mas não for o 310 da folha normal, que aqui seria outro código)
                WHEN EVE.InfProvDesc = '2' AND (EVE.Nome LIKE '%INSS%' OR EVE.NomeApr LIKE '%INSS%') 
                    THEN 'DESCONTO_INSS'
                ELSE 'OUTRO'
            END AS TipoEventoINSS,
            
            FER.DtGozoInicial,
            FER.DtGozoFinal
        FROM FER (NOLOCK)
        
        LEFT JOIN EFO (NOLOCK) ON FER.EMP_CODIGO = EFO.EMP_CODIGO 
                                AND FER.EFO_FOL_SEQ = EFO.FOL_SEQ 
                                AND FER.EFO_EPG_CODIGO = EFO.EPG_CODIGO
        
        LEFT JOIN FOL (NOLOCK) ON EFO.EMP_CODIGO = FOL.EMP_CODIGO 
                                AND EFO.FOL_SEQ = FOL.SEQ
        
        LEFT JOIN EFP (NOLOCK) ON EFO.EMP_CODIGO = EFP.EMP_CODIGO 
                                AND EFO.EPG_CODIGO = EFP.EFO_EPG_CODIGO 
                                AND EFO.FOL_SEQ = EFP.EFO_FOL_SEQ
        
        LEFT JOIN EVE (NOLOCK) ON EFP.EMP_CODIGO = EVE.EMP_CODIGO 
                                AND EFP.EVE_CODIGO = EVE.CODIGO
        
        WHERE FER.EMP_CODIGO = %s
          -- Lógica de Overlap: Pega qualquer férias que toque no mês de referência
          AND FER.DtGozoInicial <= %s 
          AND FER.DtGozoFinal >= %s
          
          -- Garante que pegamos dados de FOLHA válida (4=Férias, 5=Compl, 20=RescComp)
          AND (FOL.FOLHA = 4 OR FOL.FOLHA = 5 OR FOL.FOLHA = 20)
          
          -- Filtra apenas Proventos (1) e Descontos (2) para evitar lixo
          AND EVE.InfProvDesc IN (1, 2)
          AND EFP.Valor > 0
          
        ORDER BY FER.EFO_EPG_CODIGO, EVE.CODIGO
    """
    
    import calendar
    from datetime import date
    last_day_val = calendar.monthrange(ano, mes)[1]
    dt_ini_mes = date(ano, mes, 1)
    dt_fim_mes = date(ano, mes, last_day_val)

    try:
        data_map = {}
        with get_connection() as conn:
            cursor = conn.cursor()
            print(f"[DEBUG SQL] Buscando Férias (v3 - InfProvDesc): Emp={empresa_codigo} Overlap [{dt_ini_mes} a {dt_fim_mes}]")
            cursor.execute(sql, (str(empresa_codigo), dt_fim_mes, dt_ini_mes))
            rows = cursor.fetchall()
            print(f"[DEBUG SQL] Rows encontradas: {len(rows)}")
            
            for row in rows:
                d = dict_factory(cursor, row)
                mat = str(d["Matricula"]).strip()
                
                evt = {
                    "codigo": str(d["EveCodigo"]),
                    "descricao": str(d["Descricao"]).strip() + " (Férias)",
                    "tipo": d["Tipo"],
                    "valor": float(d["Valor"]),
                    "referencia": float(d["Referencia"]) if d["Referencia"] else 0.0,
                    "tipo_inss": d["TipoEventoINSS"], # Novo Campo
                    "incidencias": {
                        "inss": int(d["IncideINSS"] or 0) > 0,
                        "irrf": int(d["IncideIRRF"] or 0) > 0,
                        "fgts": int(d["IncideFGTS"] or 0) > 0
                    },
                    "origem": "FERIAS",
                    "data_ferias": f"{d['DtGozoInicial']} a {d['DtGozoFinal']}",
                    "dt_inicio": d['DtGozoInicial'],
                    "dt_fim": d['DtGozoFinal']
                }
                
                if mat not in data_map:
                    data_map[mat] = []
                data_map[mat].append(evt)
                
        return data_map
    except Exception as e:
        logger.error(f"Erro get_ferias_details: {e}")
        return {}
