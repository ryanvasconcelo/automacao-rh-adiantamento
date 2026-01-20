# backend/src/fopag/router.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

# Imports locais
from . import fopag_auditor
from . import data_fetcher
from src.database import get_connection  # Importa a conexão segura

# Importa mapa de IDs se existir
try:
    from src.emp_ids import CODE_TO_EMP_ID
except ImportError:
    CODE_TO_EMP_ID = {}

# --- DEFINIÇÃO DA ROTA (PREFIXO NOVO) ---
router = APIRouter(prefix="/audit/fopag", tags=["FOPAG - Auditoria"])


# --- MODELOS ---
class FopagRealAuditRequest(BaseModel):
    empresa_id: str
    month: int
    year: int
    pension_rule: Optional[str] = "2"


# --- ENDPOINTS ---


@router.get("/companies")
def get_active_companies():
    """Busca lista de empresas (Compatível com Pyodbc e Pymssql)"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT Codigo, Nome FROM EMP (NOLOCK) WHERE DESATIVADA = 0 ORDER BY Nome"
            )

            # Recupera nomes das colunas para montar o dicionário manualmente
            # Isso resolve o problema do 'as_dict=True' não existir no Windows
            columns = [column[0] for column in cursor.description]

            lista = []
            for row in cursor.fetchall():
                # Converte a tupla em dicionário
                data = dict(zip(columns, row))

                try:
                    c_id = str(data["Codigo"]).strip()
                    # Remove decimais de código se existirem (ex: 10.0 -> 10)
                    if "." in c_id:
                        c_id = str(int(float(c_id)))

                    lista.append({"id": c_id, "name": str(data["Nome"]).strip()})
                except Exception:
                    continue

            return lista

    except Exception as e:
        print(f"Erro ao listar empresas: {e}")
        # Retorna lista vazia para não quebrar o front com erro 500
        return []


@router.post("/audit/database")
def run_database_audit(request: FopagRealAuditRequest):
    """Executa a auditoria"""
    company_code = request.empresa_id

    # 1. Mapeamento de ID
    fortes_id = CODE_TO_EMP_ID.get(company_code.upper(), company_code)

    # 2. Busca ID da Folha
    try:
        folha_seq = data_fetcher.get_folha_id(
            empresa_codigo=str(fortes_id), mes=request.month, ano=request.year
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro de conexão SQL: {str(e)}")

    if not folha_seq:
        raise HTTPException(
            status_code=404,
            detail=f"Folha Mensal não encontrada para {request.month}/{request.year} (Empresa {fortes_id}).",
        )

    # 3. Busca Dados
    try:
        dados_folha = data_fetcher.fetch_payroll_data(
            empresa_codigo=str(fortes_id), folha_seq=folha_seq
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Erro ao buscar dados da folha: {str(e)}"
        )

    if not dados_folha:
        return {"metadata": {"total_funcionarios": 0}, "divergencias": []}

    # 4. Auditoria
    try:
        caso_pensao_int = int(request.pension_rule) if request.pension_rule else 2

        resultados = fopag_auditor.run_fopag_audit(
            company_code=company_code,
            employee_payroll_data=dados_folha,
            ano=request.year,
            mes=request.month,
            caso_pensao=caso_pensao_int,
        )

        return {
            "metadata": {
                "empresa": company_code,
                "total_funcionarios": len(dados_folha),
                "total_divergencias": len(
                    [r for r in resultados if r["tem_divergencia"]]
                ),
            },
            "divergencias": resultados,
        }

    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail=f"Erro interno na auditoria: {str(e)}"
        )
