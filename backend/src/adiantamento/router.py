import pandas as pd
import numpy as np
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Optional

# --- IMPORTS LOCAIS CORRIGIDOS ---
# Importamos o runner que está na mesma pasta (adiantamento)
from . import runner
from src.rules_catalog import CATALOG
from src.emp_ids import CODE_TO_EMP_ID

# Configuração de Logs
logger = logging.getLogger(__name__)

# --- DEFINIÇÃO DO ROUTER ---
# Atenção: Aqui usamos APIRouter, não FastAPI
router = APIRouter(prefix="/audit/adiantamento", tags=["Adiantamento"])


# --- MODELOS PYDANTIC ---
class AuditRequest(BaseModel):
    catalog_code: str
    month: int
    year: int


class DayAuditRequest(BaseModel):
    day: int
    month: int
    year: int


class CorrectedAuditRow(BaseModel):
    matricula: str
    nome: str
    empresaCodigo: int
    empresaNome: str


class ReportGenerationRequest(BaseModel):
    month: int
    year: int
    data: List[CorrectedAuditRow]


class RPAImportRequest(BaseModel):
    year: int
    month: int
    company_codes: Optional[List[str]] = None


# --- ENDPOINTS ---


@router.get("/companies/grouped")
def get_companies_grouped():
    """
    Retorna as empresas agrupadas por dia de pagamento (15 ou 20).
    """
    grouped_companies: Dict[str, List[Dict[str, str]]] = {"15": [], "20": []}

    for code, rule in CATALOG.items():
        if not rule.base or not hasattr(rule.base, "window"):
            continue

        pay_day = str(rule.base.window.pay_day)

        if pay_day not in grouped_companies:
            grouped_companies[pay_day] = []

        grouped_companies[pay_day].append({"code": code, "name": rule.name})

    # Ordenação
    for day in grouped_companies:
        grouped_companies[day] = sorted(grouped_companies[day], key=lambda c: c["name"])

    return grouped_companies


@router.post("/day")
async def run_day_audit(request: DayAuditRequest):
    """
    Executa a auditoria de Adiantamento (Código Legado Migrado).
    """
    target_day = str(request.day)

    companies_to_audit = [
        (code, rule)
        for code, rule in CATALOG.items()
        if rule.base
        and hasattr(rule.base, "window")
        and str(rule.base.window.pay_day) == target_day
        and rule.emp_id
    ]

    all_results = []

    for code, rule in companies_to_audit:
        try:
            # Chama o runner.py (antigo main.py)
            df_company_result = runner.run(
                empresa_codigo=str(rule.emp_id),
                empresa_id_catalogo=code,
                ano=request.year,
                mes=request.month,
            )

            df_company_result["empresaNome"] = rule.name
            df_company_result["empresaCodigo"] = rule.emp_id
            df_company_result["empresaCode"] = rule.code

            all_results.append(df_company_result)
        except Exception as e:
            logger.error(f"Erro ao auditar {rule.name}: {e}", exc_info=True)
            continue

    if not all_results:
        return []

    df_final = pd.concat(all_results, ignore_index=True)

    # Renomeia para CamelCase (Padrão JS/React)
    df_final.rename(
        columns={
            "Matricula": "matricula",
            "Nome": "nome",
            "Cargo": "cargo",
            "Analise": "analise",
            "Status": "status",
            "Observacoes": "observacoes",
            "ValorBrutoFortes": "valorBruto",
            "ValorLiquidoAdiantamento": "valorFinal",
            "ValorAdiantamentoBruto": "valorBrutoAuditado",
            "ValorDesconto": "desconto",
        },
        inplace=True,
    )

    if "ultimaImportacao" not in df_final.columns:
        df_final["ultimaImportacao"] = None

    df_final_filled = df_final.replace({pd.NaT: None, np.nan: None})
    return df_final_filled.to_dict(orient="records")


# FIM DO ARQUIVO - Não adicione app.include_router aqui!
