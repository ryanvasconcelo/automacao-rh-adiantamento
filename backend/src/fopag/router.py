# No arquivo: backend/src/fopag/router.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

# Importa nossos componentes
from . import fopag_rules_catalog
from . import fopag_auditor
from . import data_fetcher

# Importa o mapa de IDs atualizado
from src.emp_ids import CODE_TO_EMP_ID

router = APIRouter(prefix="/api/v1/fopag", tags=["FOPAG - Auditoria"])

# --- MODELOS ---


class FopagManualAuditRequest(BaseModel):
    company_code: str
    employee_data: list


# Modelo para auditoria REAL (Automática)
class FopagRealAuditRequest(BaseModel):
    company_code: str  # Ex: "JR" ou "2056"
    month: int
    year: int
    caso_pensao: Optional[int] = 2  # <--- NOVO CAMPO (Padrão 2)


# --- ENDPOINTS ---


@router.get("/catalog/events")
async def get_event_catalog():
    return fopag_rules_catalog.EVENT_CATALOG


@router.get("/catalog/rules/{company_code}")
async def get_company_rules(company_code: str):
    return fopag_rules_catalog.get_company_rule(company_code)


@router.post("/audit/manual")
async def run_manual_audit(request: FopagManualAuditRequest):
    from datetime import date

    hoje = date.today()
    divergencias = fopag_auditor.run_fopag_audit(
        company_code=request.company_code,
        employee_payroll_data=request.employee_data,
        ano=hoje.year,
        mes=hoje.month,
    )
    return {"divergencias": divergencias}


@router.post("/audit/database")
async def run_database_audit(request: FopagRealAuditRequest):
    """
    Auditoria Real Conectada ao Banco de Dados.
    """
    print(
        f"[Router] Iniciando auditoria via DB para {request.company_code} - {request.month}/{request.year}"
    )

    # Passo A: Traduzir Código (JR -> 9098, 2056 -> 2056)
    # Pega do arquivo src/emp_ids.py
    fortes_empresa_id = CODE_TO_EMP_ID.get(str(request.company_code))

    if not fortes_empresa_id:
        # Se não achou no map, tenta usar o próprio código se for numérico (fallback)
        if str(request.company_code).isdigit():
            fortes_empresa_id = str(request.company_code)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Empresa '{request.company_code}' não encontrada no mapeamento (emp_ids.py).",
            )

    # Passo B: Descobrir qual é a folha (Seq)
    folha_seq = data_fetcher.get_folha_id(
        empresa_codigo=str(fortes_empresa_id), mes=request.month, ano=request.year
    )

    if not folha_seq:
        raise HTTPException(
            status_code=404,
            detail=f"Nenhuma folha mensal encontrada para {request.company_code} em {request.month}/{request.year}.",
        )

    print(f"[Router] Folha encontrada. Seq: {folha_seq}")

    # Passo C: Buscar os dados (A Mágica do SQL)
    try:
        dados_reais = data_fetcher.fetch_payroll_data(
            empresa_codigo=str(fortes_empresa_id), folha_seq=folha_seq
        )
    except Exception as e:
        print(f"Erro no fetch: {e}")
        # Retorna o erro detalhado para o front entender o que houve no banco
        raise HTTPException(
            status_code=500, detail=f"Erro ao buscar dados do SQL: {str(e)}"
        )

    if not dados_reais:
        return {
            "message": "Folha encontrada, mas nenhum funcionário com eventos calculados.",
            "divergencias": [],
        }

    print(f"[Router] Dados recuperados. Auditando {len(dados_reais)} funcionários...")

    # Passo D: Rodar o Auditor
    divergencias = fopag_auditor.run_fopag_audit(
        company_code=request.company_code,
        employee_payroll_data=dados_reais,
        ano=request.year,
        mes=request.month,
        caso_pensao=request.caso_pensao,  # <--- Passando o parâmetro da tela
    )

    return {
        "metadata": {
            "empresa": request.company_code,
            "fortes_id": fortes_empresa_id,
            "folha_seq": folha_seq,
            "total_funcionarios": len(dados_reais),
            "total_divergencias": len(divergencias),
        },
        "divergencias": divergencias,
    }
