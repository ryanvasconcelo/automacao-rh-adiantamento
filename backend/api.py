# api.py (Versão 3.3 - Lógica de Fila Corrigida)

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
import pyodbc

app = FastAPI(title="RH Tools API - Auditor de Adiantamento", version="3.3.0")

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


# --- ENDPOINTS DE AUDITORIA (Estável) ---
@app.get("/companies/grouped")
def get_companies_grouped():
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

    import_status_map = get_imported_status_from_db(request.year, request.month)

    all_results = []
    for code, rule in companies_to_audit:
        try:
            df_company_result = main.run(
                empresa_codigo=str(rule.emp_id),
                empresa_id_catalogo=code,
                ano=request.year,
                mes=request.month,
            )
            df_company_result["empresaNome"] = rule.name
            df_company_result["empresaCodigo"] = rule.emp_id
            df_company_result["empresaCode"] = rule.code

            last_import_date = import_status_map.get(str(rule.emp_id))
            df_company_result["consignadoImportado"] = bool(last_import_date)
            df_company_result["ultimaImportacao"] = last_import_date

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
    if "ultimaImportacao" not in df_final.columns:
        df_final["ultimaImportacao"] = None

    df_final_filled = df_final.replace({pd.NaT: None, np.nan: None})
    return df_final_filled.to_dict(orient="records")


# --- ENDPOINTS DE RPA (Com Ajuste 3 - Lógica de Fila) ---


@app.post("/rpa/import-consignments", status_code=status.HTTP_202_ACCEPTED)
async def trigger_rpa_import_consignments(request: RPAImportRequest):
    """
    (v3.3) Enfileira jobs na TB_RPA_JOBS.
    Agora é inteligente e sabe quais empresas já estão na fila.
    """
    print(f"Recebida solicitação de importação para {request.month}/{request.year}")
    competencia = f"{request.month:02d}/{request.year}"

    conn = None
    try:
        conn = queue_db.get_queue_connection()
        cursor = conn.cursor()

        # --- INÍCIO DA ALTERAÇÃO (Ajuste 3 - Lógica de Fila) ---
        # 1. Pega TODOS os códigos de catálogo (ex: 'JR', 'ACB')
        all_catalog_codes = set(CODE_TO_EMP_ID.keys())

        # 2. Pega todos os jobs que JÁ ESTÃO NA FILA (PENDENTE, PROCESSANDO, CONCLUIDO)
        #    para esta competência, e os "traduz" de volta para Código de Catálogo

        # (Cria um mapa reverso: {'9098': 'JR', '9234': 'ACB'})
        fortes_to_catalog_map = {v: k for k, v in CODE_TO_EMP_ID.items()}

        sql_get_existing = (
            "SELECT DISTINCT empresa_codigo FROM TB_RPA_JOBS WHERE competencia = ?"
        )
        cursor.execute(sql_get_existing, (competencia,))

        # Converte os códigos Fortes (ex: '9098') de volta para códigos de catálogo (ex: 'JR')
        existing_catalog_codes = {
            fortes_to_catalog_map.get(row[0])
            for row in cursor.fetchall()
            if fortes_to_catalog_map.get(row[0])
        }

        # 3. Determina quais códigos precisam ser enfileirados
        codes_to_queue = []
        if request.company_codes:
            # Botão Vermelho (Individual) ou Modal
            codes_to_queue = request.company_codes
            print(f"Empresas especificadas: {codes_to_queue}")
        else:
            # Botão Cinza (Global) - "Importar Todos os Pendentes"
            # Pendentes = Todos - Existentes
            codes_to_queue = list(all_catalog_codes - existing_catalog_codes)
            print(f"Empresas pendentes (não estão na fila): {codes_to_queue}")
        # --- FIM DA ALTERAÇÃO ---

        if not codes_to_queue:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status": "noop",
                    "message": "Nenhuma empresa nova para enfileirar.",
                },
            )

        # 4. Traduzir para códigos Fortes (ex: "9234") e preparar o SQL
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
            raise HTTPException(
                status_code=400, detail="Códigos de catálogo inválidos."
            )

        # 5. Inserir no Banco de Dados da Fila (TB_RPA_JOBS)
        # (Nós não precisamos mais do "IF NOT EXISTS" porque já filtramos)
        sql_insert = """
            INSERT INTO TB_RPA_JOBS (empresa_codigo, competencia, status, updated_at)
            VALUES (?, ?, 'PENDENTE', GETDATE())
        """

        jobs_enfileirados = 0
        for fortes_code, comp in jobs_para_inserir:
            params = (fortes_code, comp)
            cursor.execute(sql_insert, params)
            if cursor.rowcount > 0:
                jobs_enfileirados += 1

        print(f"Jobs inseridos na fila: {jobs_enfileirados}")
        return {
            "status": "queued",
            "message": f"{jobs_enfileirados} novo(s) job(s) foram enfileirados para processamento.",
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
    conn = None
    try:
        conn = queue_db.get_queue_connection()
        cursor = conn.cursor()

        sql_count = "SELECT status, COUNT(*) as count FROM TB_RPA_JOBS GROUP BY status"
        cursor.execute(sql_count)
        status_counts = {row[0]: row[1] for row in cursor.fetchall()}

        sql_errors = """
            SELECT TOP 5 id, empresa_codigo, competencia, error_message, updated_at
            FROM TB_RPA_JOBS
            WHERE status = 'ERRO'
            ORDER BY updated_at DESC
        """
        cursor.execute(sql_errors)
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
    # (Simulação)
    print(f"Recebida solicitação de GERAÇÃO DE RELATÓRIOS (Simulado)...")
    time.sleep(3)
    return {
        "status": "success",
        "message": f"Geração de relatórios (simulada) iniciada.",
    }


# --- Funções Auxiliares (Estável) ---
def get_imported_status_from_db(year: int, month: int) -> Dict[str, object]:
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

        return {row[0]: row[1] for row in cursor.fetchall()}

    except Exception as e:
        logger.error(f"Erro ao buscar status de 'CONCLUIDO': {e}", exc_info=True)
        return {}
    finally:
        if conn:
            conn.close()
