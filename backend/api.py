# api.py (Versão 3.2 - Enviando Data da Última Importação)

import os
import io
import pandas as pd
import numpy as np
import json
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional, Tuple
import logging
import time

logger = logging.getLogger(__name__)

# --- Imports do Nosso Projeto ---
import main
from src.rules_catalog import CATALOG, get_company_rule
from src.data_extraction import fetch_all_companies
from src.emp_ids import CODE_TO_EMP_ID
import queue_db
import pyodbc  # Import para o tipo de cursor

app = FastAPI(title="RH Tools API - Auditor de Adiantamento", version="3.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- MODELOS Pydantic (sem alterações) ---
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


# --- ENDPOINTS DE AUDITORIA (Com Ajuste 3) ---


@app.get("/companies/grouped")
def get_companies_grouped():
    # ... (código original sem alterações)
    grouped_companies: Dict[str, List[Dict[str, str]]] = {"15": [], "20": []}
    for code, rule in CATALOG.items():
        if not rule.base or not hasattr(rule.base, "window"):
            continue
        pay_day = str(rule.base.window.pay_day)
        if pay_day in grouped_companies:
            grouped_companies[pay_day].append({"code": code, "name": rule.name})
    grouped_companies["15"] = sorted(grouped_companies["15"], key=lambda c: c["name"])
    grouped_companies["20"] = sorted(grouped_companies["20"], key=lambda c: c["name"])
    return grouped_companies


@app.post("/audit/day")
async def run_day_audit(request: DayAuditRequest):

    target_day = str(request.day)
    companies_to_audit = [
        (code, rule)
        for code, rule in CATALOG.items()
        if rule.base
        and hasattr(rule.base, "window")
        and str(rule.base.window.pay_day) == target_day
        and rule.emp_id
    ]

    # --- INÍCIO DA ALTERAÇÃO (AJUSTE 3 - BACKEND) ---
    # Busca os status de importação (agora um dicionário: {codigo: data})
    import_status_map = get_imported_status_from_db(request.year, request.month)
    # --- FIM DA ALTERAÇÃO ---

    all_results = []
    for code, rule in companies_to_audit:
        try:
            print(
                f"--- INICIANDO AUDITORIA PARA EMPRESA {rule.emp_id} ({rule.name}) ..."
            )
            df_company_result = main.run(
                empresa_codigo=str(rule.emp_id),
                empresa_id_catalogo=code,
                ano=request.year,
                mes=request.month,
            )
            df_company_result["empresaNome"] = rule.name
            df_company_result["empresaCodigo"] = rule.emp_id
            df_company_result["empresaCode"] = rule.code

            # --- INÍCIO DA ALTERAÇÃO (AJUSTE 3 - BACKEND) ---
            # O status agora é se existe um job 'CONCLUIDO' para este código
            last_import_date = import_status_map.get(str(rule.emp_id))
            df_company_result["consignadoImportado"] = bool(last_import_date)
            # Adiciona a nova coluna com a data
            df_company_result["ultimaImportacao"] = last_import_date
            # --- FIM DA ALTERAÇÃO ---

            all_results.append(df_company_result)
        except Exception as e:
            logger.error(f"Erro ao auditar {rule.name}: {e}", exc_info=True)
            continue

    if not all_results:
        return []

    df_final = pd.concat(all_results, ignore_index=True)
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
    # Garante que a nova coluna exista mesmo se tudo falhar
    if "ultimaImportacao" not in df_final.columns:
        df_final["ultimaImportacao"] = None

    df_final_filled = df_final.replace({pd.NaT: None, np.nan: None})
    return df_final_filled.to_dict(orient="records")


# --- ENDPOINTS DE RPA (Corrigidos para pyodbc) ---


@app.post("/rpa/import-consignments", status_code=status.HTTP_202_ACCEPTED)
async def trigger_rpa_import_consignments(request: RPAImportRequest):
    """
    (Fase 3) Recebe o pedido do React e ENFILEIRA os jobs
    na tabela TB_RPA_JOBS. Não executa o RPA.
    """
    print(f"Recebida solicitação de importação para {request.month}/{request.year}")

    competencia = f"{request.month:02d}/{request.year}"

    codes_to_queue = []
    if request.company_codes:
        codes_to_queue = request.company_codes
        print(f"Empresas especificadas: {codes_to_queue}")
    else:
        # TODO: Esta lógica ainda é "importar todos", não "importar pendentes"
        codes_to_queue = list(CODE_TO_EMP_ID.keys())
        print(f"Enfileirando todas as empresas do catálogo.")

    if not codes_to_queue:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "noop", "message": "Nenhuma empresa para enfileirar."},
        )

    jobs_para_inserir = []
    for catalog_code in codes_to_queue:
        fortes_code = CODE_TO_EMP_ID.get(catalog_code)
        if not fortes_code:
            logger.warning(
                f"Código de catálogo não encontrado no emp_ids.py: {catalog_code}"
            )
            continue
        jobs_para_inserir.append((str(fortes_code), competencia))

    if not jobs_para_inserir:
        raise HTTPException(status_code=400, detail="Códigos de catálogo inválidos.")

    conn = None
    try:
        conn = queue_db.get_queue_connection()
        cursor = conn.cursor()

        # --- CORREÇÃO (Dialeto pyodbc) ---
        sql_insert = """
            IF NOT EXISTS (
                SELECT 1 FROM TB_RPA_JOBS
                WHERE empresa_codigo = ? AND competencia = ?
                AND status IN ('PENDENTE', 'EM_PROCESSAMENTO')
            )
            BEGIN
                INSERT INTO TB_RPA_JOBS (empresa_codigo, competencia, status, updated_at)
                VALUES (?, ?, 'PENDENTE', GETDATE())
            END
        """

        jobs_enfileirados = 0
        for fortes_code, comp in jobs_para_inserir:
            params = (fortes_code, comp, fortes_code, comp)
            cursor.execute(sql_insert, params)
            if cursor.rowcount > 0:
                jobs_enfileirados += 1

        # conn.commit() é desnecessário se autocommit=True no pyodbc

        print(f"Jobs inseridos/atualizados na fila: {jobs_enfileirados}")
        return {
            "status": "queued",
            "message": f"{jobs_enfileirados} job(s) foram enfileirados para processamento.",
        }

    except Exception as e:
        logger.error(f"Erro ao enfileirar jobs na TB_RPA_JOBS: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Erro interno ao acessar a fila de jobs."
        )
    finally:
        if conn:
            conn.close()


@app.get("/rpa/status")
async def get_rpa_status():
    """
    (NOVO) Lê a tabela TB_RPA_JOBS e retorna um resumo
    para o React atualizar a UI.
    """
    conn = None
    try:
        conn = queue_db.get_queue_connection()
        cursor = conn.cursor()  # pyodbc não usa as_dict=True

        # 1. Contagem de Status
        sql_count = "SELECT status, COUNT(*) as count FROM TB_RPA_JOBS GROUP BY status"
        cursor.execute(sql_count)
        # Converte tuplas (status, count) em dicionário
        status_counts = {row[0]: row[1] for row in cursor.fetchall()}

        # 2. Últimos 5 Erros
        sql_errors = """
            SELECT TOP 5 id, empresa_codigo, competencia, error_message, updated_at
            FROM TB_RPA_JOBS
            WHERE status = 'ERRO'
            ORDER BY updated_at DESC
        """
        cursor.execute(sql_errors)
        # Converte tuplas em dicionários manualmente
        errors = [
            {
                "id": row[0],
                "empresa_codigo": row[1],
                "competencia": row[2],
                "error_message": row[3],
                "updated_at": row[4],
            }
            for row in cursor.fetchall()
        ]

        return {
            "pending": status_counts.get("PENDENTE", 0),
            "processing": status_counts.get("EM_PROCESSAMENTO", 0),
            "completed": status_counts.get("CONCLUIDO", 0),
            "errors": errors,
        }

    except Exception as e:
        logger.error(f"Erro ao ler status da TB_RPA_JOBS: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Erro interno ao ler o status da fila."
        )
    finally:
        if conn:
            conn.close()


@app.post("/reports/generate")
async def trigger_rpa_generate_reports(request: ReportGenerationRequest):
    # Esta é uma simulação (Fase 3), podemos conectar na fila também
    print(f"Recebida solicitação de GERAÇÃO DE RELATÓRIOS (Simulado)...")
    # TODO: Enfileirar este job também
    time.sleep(3)  # Simulação
    return {
        "status": "success",
        "message": f"Geração de relatórios (simulada) iniciada.",
    }


# --- Funções Auxiliares (Com Ajuste 3) ---


# --- INÍCIO DA ALTERAÇÃO (AJUSTE 3 - BACKEND) ---
def get_imported_status_from_db(year: int, month: int) -> Dict[str, object]:
    """
    Busca na TB_RPA_JOBS todos os códigos de empresa
    que têm um job 'CONCLUIDO' para a competência, e retorna a ÚLTIMA data.
    """
    conn = None
    try:
        conn = queue_db.get_queue_connection()
        cursor = conn.cursor()

        sql = """
            SELECT 
                empresa_codigo, 
                MAX(updated_at) as last_import_date
            FROM TB_RPA_JOBS
            WHERE 
                competencia = ? 
                AND status = 'CONCLUIDO'
            GROUP BY 
                empresa_codigo
        """
        competencia = f"{month:02d}/{year}"
        cursor.execute(sql, (competencia,))

        # Retorna um dicionário (ex: {'9098': '2025-11-06 13:00:00', ...})
        return {row[0]: row[1] for row in cursor.fetchall()}

    except Exception as e:
        logger.error(f"Erro ao buscar status de 'CONCLUIDO': {e}", exc_info=True)
        return {}  # Retorna um dicionário vazio em caso de erro
    finally:
        if conn:
            conn.close()


# --- FIM DA ALTERAÇÃO ---
