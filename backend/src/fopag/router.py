from fastapi import APIRouter
from pydantic import BaseModel
from . import fopag_rules_catalog
from . import fopag_auditor

router = APIRouter(
    prefix="/api/v1/fopag",  # <-- Mudei o prefixo para /fopag
    tags=["FOPAG - Auditoria"],
)


# --- MODELOS (Pydantic) ---
# (Precisamos definir os dados que a API espera)
class FopagAuditRequest(BaseModel):
    company_code: str
    # TODO: Definir como vamos receber os dados do funcionário
    # Por enquanto, vamos receber um dict "mágico"
    employee_data: list


# --- ENDPOINTS DA ARQUITETURA HÍBRIDA ---


@router.get("/catalog/events")
async def get_event_catalog():
    """
    Retorna o Catálogo de Eventos (a Matriz de Incidência)
    que o stakeholder nos deu.
    """
    return fopag_rules_catalog.EVENT_CATALOG


@router.get("/catalog/rules/{company_code}")
async def get_company_rules(company_code: str):
    """
    Retorna as regras/exceções "hardcoded" para uma empresa.
    """
    return fopag_rules_catalog.get_company_rule(company_code)


@router.post("/audit")
async def run_audit(request: FopagAuditRequest):
    """
    Endpoint Principal: Roda a auditoria da FOPAG.
    (O "Componente 3")
    """
    divergencias = fopag_auditor.run_fopag_audit(
        company_code=request.company_code, employee_payroll_data=request.employee_data
    )
    return {"divergencias": divergencias}
