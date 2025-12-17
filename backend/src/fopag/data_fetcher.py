import logging
from typing import List, Dict, Optional
from src.database import get_connection  # Reutilizamos sua conexão existente

logger = logging.getLogger(__name__)


def get_folha_id(empresa_codigo: str, mes: int, ano: int) -> Optional[int]:
    """
    Busca o ID (Sequencial) da Folha Mensal (Tipo 2) para a competência.
    """
    conn = get_connection()
    cursor = conn.cursor(as_dict=True)

    # Formato AAAAMM para o campo AnoMes
    ano_mes = f"{ano}{mes:02d}"

    try:
        sql = """
            SELECT TOP 1 FOL.Seq
            FROM FOL (NOLOCK)
            INNER JOIN FPG (NOLOCK) 
                ON FOL.EMP_Codigo = FPG.EMP_Codigo 
                AND FOL.Seq = FPG.FOL_Seq
            WHERE 
                FOL.EMP_Codigo = %s
                AND FPG.AnoMes = %s
                AND FOL.Folha = 2          -- 2 = Folha Mensal
                AND FPG.Tipo IN (1, 4)     -- 1 = Obra/Tomador Normal
            ORDER BY FOL.Seq DESC
        """
        cursor.execute(sql, (empresa_codigo, ano_mes))
        row = cursor.fetchone()

        if row:
            return row["Seq"]
        return None

    except Exception as e:
        logger.error(f"Erro ao buscar ID da folha: {e}")
        raise
    finally:
        conn.close()


def fetch_payroll_data(empresa_codigo: str, folha_seq: int) -> List[Dict]:
    """
    Busca todos os funcionários e seus eventos da tabela EFP (Calculada).
    """
    conn = get_connection()
    cursor = conn.cursor(as_dict=True)

    try:
        # A Query Unificada (CORRIGIDA - REMOVIDO INCIDÊNCIAS)
        sql = """
            SELECT 
                -- Dados do Funcionário
                EPG.Codigo AS Matricula,
                EPG.Nome AS Nome,
                
                -- Dados do Evento
                EFP.EVE_Codigo AS Codigo,
                EVE.NomeApr AS Descricao,
                EVE.ProvDesc AS Tipo, -- 1=Provento, 2=Desconto
                EFP.Valor AS Valor,
                EFP.Referencia AS Referencia

                -- REMOVI AS COLUNAS 'IncideINSS', ETC. QUE DAVAM ERRO

            FROM EFO (NOLOCK)
            INNER JOIN EPG (NOLOCK) 
                ON EFO.EMP_Codigo = EPG.EMP_Codigo 
                AND EFO.EPG_Codigo = EPG.Codigo
            LEFT JOIN EFP (NOLOCK) 
                ON EFO.EMP_Codigo = EFP.EMP_Codigo 
                AND EFO.FOL_Seq = EFP.EFO_FOL_Seq 
                AND EFO.EPG_Codigo = EFP.EFO_EPG_Codigo
            LEFT JOIN EVE (NOLOCK) 
                ON EFP.EMP_Codigo = EVE.EMP_Codigo 
                AND EFP.EVE_CODIGO = EVE.CODIGO -- Ajuste de join por precaução

            WHERE 
                EFO.EMP_Codigo = %s
                AND EFO.FOL_Seq = %s
                AND EFP.Valor > 0
            
            ORDER BY EPG.Nome, EFP.EVE_Codigo
        """

        cursor.execute(sql, (empresa_codigo, folha_seq))
        rows = cursor.fetchall()

        # --- PROCESSAMENTO ---

        funcionarios_map = {}

        for row in rows:
            matricula = str(row["Matricula"]).strip()  # Garante string limpa

            if matricula not in funcionarios_map:
                funcionarios_map[matricula] = {
                    "matricula": matricula,
                    "nome": str(row["Nome"]).strip(),
                    "dependentes": 0,
                    "proventos_base": [],
                    "eventos_variaveis_referencia": [],
                    "eventos_calculados_fortes": {},
                }

            func_data = funcionarios_map[matricula]

            # --- NORMALIZAÇÃO CRÍTICA ---
            # 1. Converte para int para matar zeros a esquerda (011 -> 11)
            # 2. Converte para string para bater com o catálogo ("11")
            try:
                codigo_limpo = str(int(row["Codigo"]))
            except ValueError:
                # Caso o código tenha letras, usa apenas o strip
                codigo_limpo = str(row["Codigo"]).strip()

            valor = float(row["Valor"])
            referencia = (
                float(row["Referencia"]) if row["Referencia"] is not None else 0.0
            )

            # 1. Popula o dicionário de "Resultados Reais"
            func_data["eventos_calculados_fortes"][codigo_limpo] = valor

            # 2. Classifica para as listas de cálculo

            # Salário Base (11) ou Periculosidade (13) -> Base Fixa
            if codigo_limpo in ["11", "13"]:
                func_data["proventos_base"].append(
                    {"codigo": codigo_limpo, "valor": valor}
                )

            # Se tem referência > 0, geralmente é variável (HE, Faltas)
            # MAS ignoramos se já foi classificado como base (para não duplicar)
            elif referencia > 0:
                func_data["eventos_variaveis_referencia"].append(
                    {"codigo": codigo_limpo, "referencia": referencia}
                )

        return list(funcionarios_map.values())

    except Exception as e:
        logger.error(f"Erro ao buscar dados da folha: {e}")
        raise
    finally:
        conn.close()
