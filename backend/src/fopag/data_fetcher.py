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
          AND FOL.Folha = 2 AND FPG.Tipo IN (1, 4) -- Folha Mensal
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
    Busca TODOS os eventos da folha para auditoria completa (Confiar + Verificar).
    """
    sql = """
        SELECT 
            -- Dados do Funcionário
            EPG.Codigo AS Matricula,
            EPG.Nome AS Nome,
            EPG.AdmissaoData AS DataAdmissao,
            EPG.Categoria AS CodigoVinculo,
            
            -- Dados do Evento Financeiro (Real)
            EFP.EVE_Codigo AS Codigo,
            EVE.NomeApr AS Descricao,
            EVE.ProvDesc AS Tipo, -- 1=Prov, 2=Desc, 0=Base
            EFP.Valor AS Valor,
            EFP.Referencia AS Referencia

        FROM EFO (NOLOCK)
        INNER JOIN EPG (NOLOCK) 
            ON EFO.EMP_Codigo = EPG.EMP_Codigo AND EFO.EPG_Codigo = EPG.Codigo
        
        -- Join com Eventos Financeiros (Valores calculados)
        LEFT JOIN EFP (NOLOCK) 
            ON EFO.EMP_Codigo = EFP.EMP_Codigo 
            AND EFO.FOL_Seq = EFP.EFO_FOL_Seq 
            AND EFO.EPG_Codigo = EFP.EFO_EPG_Codigo
            
        -- Join com Cadastro de Eventos (Para pegar nomes e tipos)
        LEFT JOIN EVE (NOLOCK) 
            ON EFP.EMP_Codigo = EVE.EMP_Codigo 
            AND EFP.EVE_CODIGO = EVE.CODIGO

        WHERE 
            EFO.EMP_Codigo = %s
            AND EFO.FOL_Seq = %s
            AND EFP.Valor > 0 -- Traz apenas o que tem valor financeiro
            
        ORDER BY EPG.Nome, EVE.ProvDesc, EFP.EVE_Codigo
    """

    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (empresa_codigo, folha_seq))
            rows = [dict_factory(cursor, row) for row in cursor.fetchall()]

            # --- PROCESSAMENTO E AGRUPAMENTO ---
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
                        "tipo_contrato": vinculo,
                        "dependentes": 0,  # Poderia buscar na tabela DEP se necessário
                        "eventos": [],  # Lista plana com tudo (Salário, HE, Bases, Impostos)
                    }

                # Normalização de dados do evento
                try:
                    codigo_limpo = str(int(row["Codigo"]))
                except:
                    codigo_limpo = str(row["Codigo"]).strip()

                evento = {
                    "codigo": codigo_limpo,
                    "descricao": str(row["Descricao"]).strip(),
                    "tipo": row["Tipo"],  # 1, 2 ou 0
                    "valor": float(row["Valor"]),
                    "referencia": (
                        float(row["Referencia"]) if row["Referencia"] else 0.0
                    ),
                }

                funcionarios_map[matricula]["eventos"].append(evento)

            return list(funcionarios_map.values())

    except Exception as e:
        logger.error(f"Erro fetch_payroll_data: {e}")
        raise
