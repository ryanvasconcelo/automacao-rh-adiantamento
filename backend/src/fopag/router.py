# backend/src/fopag/router.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

# --- IMPORTAÇÕES CERTAS ---
# O ponto (.) significa "desta mesma pasta"
from . import fopag_auditor
from . import data_fetcher
from . import fopag_rules_catalog

# Importa o mapa de IDs da pasta src (nível acima)
try:
    from src.emp_ids import CODE_TO_EMP_ID
except ImportError:
    CODE_TO_EMP_ID = {}

# CORREÇÃO AQUI: Removemos o prefixo porque o server.py já coloca ele
router = APIRouter(tags=["FOPAG - Auditoria"])


# --- MODELOS DE DADOS ---
class CompanySchema(BaseModel):
    codigo: str
    nome: str


class FopagRealAuditRequest(BaseModel):
    empresa_id: str
    month: int
    year: int
    pension_rule: Optional[str] = "2"


# --- ENDPOINTS ---


@router.get("/companies")
def get_active_companies():
    """Busca lista de empresas direto do SQL para o Dropdown"""
    print(">>> Buscando empresas no banco...")
    conn = data_fetcher.get_connection()
    if not conn:
        return []

    try:
        cursor = conn.cursor(as_dict=True)
        cursor.execute("SELECT Codigo, Nome FROM EMP (NOLOCK) ORDER BY Nome")
        rows = cursor.fetchall()

        lista = []
        for row in rows:
            try:
                c_id = str(row["Codigo"]).strip()
                if "." in c_id:
                    c_id = str(int(float(c_id)))

                lista.append({"id": c_id, "name": str(row["Nome"]).strip()})
            except:
                continue

        print(f">>> {len(lista)} empresas carregadas.")
        return lista
    except Exception as e:
        print(f"Erro ao listar empresas: {e}")
        return []
    finally:
        conn.close()


@router.post("/audit/database")
def run_database_audit(request: FopagRealAuditRequest):
    """
    Executa a auditoria usando o FOPAG_AUDITOR (O arquivo correto)
    """
    company_code = request.empresa_id
    print(
        f"\n>>> INICIANDO AUDITORIA PARA: {company_code} - {request.month}/{request.year}"
    )

    # 1. Tenta achar ID mapeado ou usa o próprio
    fortes_id = CODE_TO_EMP_ID.get(company_code.upper(), company_code)

    # 2. Busca o ID Sequencial da Folha (SQL)
    folha_seq = data_fetcher.get_folha_id(
        empresa_codigo=str(fortes_id), mes=request.month, ano=request.year
    )

    if not folha_seq:
        raise HTTPException(
            status_code=404,
            detail=f"Folha Mensal não encontrada no Fortes para {request.month}/{request.year}.",
        )

    # 3. Busca os dados dos funcionários (SQL)
    try:
        dados_folha = data_fetcher.fetch_payroll_data(
            empresa_codigo=str(fortes_id), folha_seq=folha_seq
        )
    except Exception as e:
        print(f"Erro SQL: {e}")
        raise HTTPException(status_code=500, detail=f"Erro no Banco de Dados: {str(e)}")

    if not dados_folha:
        return {"metadata": {"total_funcionarios": 0}, "divergencias": []}

    # 4. Roda a Auditoria
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
        raise HTTPException(status_code=500, detail=f"Erro na Auditoria: {str(e)}")
