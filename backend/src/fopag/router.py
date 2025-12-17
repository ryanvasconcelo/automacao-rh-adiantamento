# No arquivo: backend/src/fopag/router.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

# Importa nossos componentes
from . import fopag_rules_catalog
from . import fopag_auditor
from . import data_fetcher  # <--- O Conector SQL

# Importa o mapa de IDs (JR -> 9098)
# (Assumindo que src.emp_ids existe e tem o CODE_TO_EMP_ID)
from src.emp_ids import CODE_TO_EMP_ID

router = APIRouter(prefix="/api/v1/fopag", tags=["FOPAG - Auditoria"])

# --- MODELOS ---


# Modelo para teste manual (JSON injetado)
class FopagManualAuditRequest(BaseModel):
    company_code: str
    employee_data: list


# Modelo para auditoria REAL (Automática)
class FopagRealAuditRequest(BaseModel):
    company_code: str  # Ex: "JR"
    month: int  # Ex: 10
    year: int  # Ex: 2025


# --- ENDPOINTS ---


@router.get("/catalog/events")
async def get_event_catalog():
    return fopag_rules_catalog.EVENT_CATALOG


@router.get("/catalog/rules/{company_code}")
async def get_company_rules(company_code: str):
    return fopag_rules_catalog.get_company_rule(company_code)


# 1. Endpoint Manual (O que usávamos antes)
@router.post("/audit/manual")
async def run_manual_audit(request: FopagManualAuditRequest):
    # Como o teste manual não envia data, vamos assumir o mês atual ou fixo
    # Se quiser testar Fevereiro, mude manualmente aqui ou adicione no RequestModel
    from datetime import date

    hoje = date.today()

    divergencias = fopag_auditor.run_fopag_audit(
        company_code=request.company_code,
        employee_payroll_data=request.employee_data,
        ano=hoje.year,  # <--- Valor padrão para não quebrar
        mes=hoje.month,  # <--- Valor padrão para não quebrar
    )
    return {"divergencias": divergencias}


# 2. Endpoint REAL (Conectado ao SQL) - A GRANDE NOVIDADE
@router.post("/audit/database")
async def run_database_audit(request: FopagRealAuditRequest):
    """
    1. Traduz o código da empresa (JR -> 9098).
    2. Busca o ID da folha no SQL para o Mês/Ano.
    3. Busca os dados dos funcionários e eventos no SQL.
    4. Roda o Auditor.
    """
    print(
        f"[Router] Iniciando auditoria via DB para {request.company_code} - {request.month}/{request.year}"
    )

    # Passo A: Traduzir Código (JR -> 9098)
    fortes_empresa_id = CODE_TO_EMP_ID.get(request.company_code)
    if not fortes_empresa_id:
        raise HTTPException(
            status_code=400,
            detail=f"Empresa '{request.company_code}' não encontrada no mapeamento (emp_ids.py).",
        )

    # Passo B: Descobrir qual é a folha (Seq)
    # (Converte int para string pois sua função get_folha_id espera str no primeiro arg se for o caso,
    # mas nosso data_fetcher tipou como str, então vamos converter)
    folha_seq = data_fetcher.get_folha_id(
        empresa_codigo=str(fortes_empresa_id), mes=request.month, ano=request.year
    )

    if not folha_seq:
        raise HTTPException(
            status_code=404,
            detail=f"Nenhuma folha mensal (calculada e não encerrada) encontrada para {request.month}/{request.year}.",
        )

    print(f"[Router] Folha encontrada. Seq: {folha_seq}")

    # Passo C: Buscar os dados (A Mágica do SQL)
    try:
        dados_reais = data_fetcher.fetch_payroll_data(
            empresa_codigo=str(fortes_empresa_id), folha_seq=folha_seq
        )
    except Exception as e:
        print(f"Erro no fetch: {e}")
        raise HTTPException(
            status_code=500, detail="Erro ao buscar dados do SQL Server."
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
        ano=request.year,  # <--- NOVO
        mes=request.month,  # <--- NOVO
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
