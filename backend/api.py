# api.py (Versão com Persistência JSON para Status do Consignado)

import os
import io
import shutil
import zipfile
import pandas as pd
import numpy as np
import json  # <--- ADICIONADO
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional, Tuple  # <--- ADICIONADO Tuple
import logging
import time

logger = logging.getLogger(__name__)

import main
from src.rules_catalog import CATALOG, get_company_rule
from src.data_extraction import (
    fetch_all_companies,
    fetch_filters_for_company,
    get_latest_fol_seq,
    fetch_listagem_adiantamento_data,
    fetch_recibo_pagamento_data,
    fetch_folha_sintetica_data,
)
from src.file_generator import generate_and_zip_reports

app = FastAPI(
    title="RH Tools API - Auditor de Adiantamento", version="2.1.0"
)  # Versão incrementada

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- ARMAZENAMENTO DE STATUS (Agora com JSON) ---
STATUS_FILE_PATH = "consignado_status.json"

# Tipo para a chave do dicionário (Ano, Mês, EmpID_str)
StatusKey = Tuple[int, int, str]
# Tipo para o dicionário de status
ConsignadoStatusDict = Dict[str, bool]  # Chave será string no JSON: "ano_mes_empId"


def _make_status_key_str(year: int, month: int, emp_id: str) -> str:
    """Cria a chave string para o JSON."""
    return f"{year}_{month:02d}_{emp_id}"


def load_status() -> ConsignadoStatusDict:
    """Carrega o status do arquivo JSON."""
    if not os.path.exists(STATUS_FILE_PATH):
        return {}
    try:
        with open(STATUS_FILE_PATH, "r") as f:
            # Carrega diretamente como Dict[str, bool]
            data = json.load(f)
            # Validação simples (opcional, mas bom ter)
            if not isinstance(data, dict):
                logger.warning(f"Arquivo {STATUS_FILE_PATH} corrompido. Ignorando.")
                return {}
            return data
    except (json.JSONDecodeError, IOError) as e:
        logger.error(
            f"Erro ao carregar {STATUS_FILE_PATH}: {e}. Retornando status vazio."
        )
        return {}


def save_status(status_dict: ConsignadoStatusDict):
    """Salva o status no arquivo JSON."""
    try:
        with open(STATUS_FILE_PATH, "w") as f:
            json.dump(status_dict, f, indent=4)
    except IOError as e:
        logger.error(f"Erro ao salvar {STATUS_FILE_PATH}: {e}")


# Carrega o status inicial ao iniciar a aplicação
consignado_import_status = load_status()


# --- MODELOS Pydantic (sem alterações) ---
# ... (AuditRequest, DayAuditRequest, etc.) ...
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


@app.get("/companies/grouped")
def get_companies_grouped():
    # ... (sem alterações)
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


@app.post("/audit")
def run_single_audit(request: AuditRequest):
    # ... (sem alterações)
    try:
        rule = get_company_rule(request.catalog_code)
        if not rule.emp_id:
            raise HTTPException(
                status_code=404,
                detail=f"Empresa '{request.catalog_code}' não tem um ID mapeado.",
            )
        df_result = main.run(
            empresa_codigo=str(rule.emp_id),
            empresa_id_catalogo=request.catalog_code,
            ano=request.year,
            mes=request.month,
        )
        df_result.rename(
            columns={
                "ValorBrutoFortes": "valorBruto",
                "ValorLiquidoAdiantamento": "valorFinal",
                "ValorAdiantamentoBruto": "valorBrutoAuditado",
            },
            inplace=True,
        )
        df_result_filled = df_result.replace({pd.NaT: None, np.nan: None})
        return df_result_filled.to_dict(orient="records")
    except Exception as e:
        logger.error(f"Erro em /audit para {request.catalog_code}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro interno: {e}")


@app.post("/audit/day")
async def run_day_audit(request: DayAuditRequest):
    """Executa a auditoria e inclui o status de importação do consignado (lido do JSON)."""
    target_day = str(request.day)
    companies_to_audit = [  # ... (lógica de filtro sem alterações)
        (code, rule)
        for code, rule in CATALOG.items()
        if rule.base
        and hasattr(rule.base, "window")
        and str(rule.base.window.pay_day) == target_day
        and rule.emp_id
    ]
    all_results = []

    # Recarrega o status do arquivo caso tenha sido modificado por outra requisição
    current_status = load_status()

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

            # --- MODIFICAÇÃO AQUI: Usa a chave string e o status carregado ---
            status_key_str = _make_status_key_str(
                request.year, request.month, str(rule.emp_id)
            )
            df_company_result["consignadoImportado"] = current_status.get(
                status_key_str, False
            )
            # -----------------------------------------------------------------

            all_results.append(df_company_result)
            print(f"--- PROCESSO DE AUDITORIA CONCLUÍDO PARA {rule.name} ---")
        except Exception as e:
            logger.error(f"Erro ao auditar a empresa {rule.name}: {e}", exc_info=True)
            print(f"Erro ao auditar a empresa {rule.name}: {e}")
            continue

    if not all_results:
        return []
    # ... (concatenação, rename e retorno sem alterações)
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
    df_final_filled = df_final.replace({pd.NaT: None, np.nan: None})
    return df_final_filled.to_dict(orient="records")


@app.post("/rpa/import-consignments")
async def trigger_rpa_import_consignments(request: RPAImportRequest):
    """Aciona (simula) o RPA e atualiza o status no arquivo JSON."""
    print(
        f"Recebida solicitação de importação de consignados para {request.month}/{request.year}"
    )

    # Carrega o status mais recente do arquivo
    current_status = load_status()
    empresas_para_importar = []

    if request.company_codes:
        empresas_para_importar = [
            code for code in request.company_codes if CATALOG.get(code)
        ]
        print(f"Empresas especificadas: {empresas_para_importar}")
    else:
        print("Buscando empresas com consignado pendente...")
        for code, rule in CATALOG.items():
            if not rule.emp_id:
                continue
            status_key_str = _make_status_key_str(
                request.year, request.month, str(rule.emp_id)
            )
            if not current_status.get(
                status_key_str, False
            ):  # Verifica no status carregado
                empresas_para_importar.append(code)
        print(f"Empresas pendentes encontradas: {empresas_para_importar}")

    if not empresas_para_importar:
        return {
            "status": "success",
            "message": "Nenhuma empresa encontrada para importação.",
        }

    # --- SIMULAÇÃO DA EXECUÇÃO DO RPA ---
    print(">>> Iniciando SIMULAÇÃO do RPA de importação...")
    time.sleep(5)
    print(">>> SIMULAÇÃO do RPA concluída com sucesso.")
    # ------------------------------------

    empresas_com_sucesso = empresas_para_importar  # Simulação assume sucesso

    # Atualiza o status no dicionário carregado
    for code in empresas_com_sucesso:
        rule = CATALOG.get(code)
        if rule and rule.emp_id:
            status_key_str = _make_status_key_str(
                request.year, request.month, str(rule.emp_id)
            )
            current_status[status_key_str] = True  # Atualiza o dicionário
            print(f"Status atualizado para importado: {rule.name}")

    # Salva o dicionário atualizado de volta no arquivo JSON
    save_status(current_status)  # <--- SALVA NO ARQUIVO

    return {
        "status": "success",
        "message": f"Importação de consignados (simulada) concluída com sucesso para {len(empresas_com_sucesso)} empresa(s).",
    }


@app.post("/reports/generate")
async def generate_reports_endpoint(request: ReportGenerationRequest):
    # ... (este endpoint permanece como estava, chamando generate_and_zip_reports)
    try:
        empresas_a_processar = {}
        for row in request.data:
            if row.empresaCodigo not in empresas_a_processar:
                empresas_a_processar[row.empresaCodigo] = {
                    "nome": row.empresaNome,
                    "funcionarios": [],
                }
            empresas_a_processar[row.empresaCodigo]["funcionarios"].append(row)

        zip_buffer = generate_and_zip_reports(
            empresas_a_processar, request.month, request.year
        )

        if zip_buffer is None:
            raise HTTPException(
                status_code=404,
                detail="Nenhum dado de relatório encontrado para as empresas e período selecionados.",
            )

        return StreamingResponse(
            zip_buffer,
            media_type="application/x-zip-compressed",
            headers={
                "Content-Disposition": f"attachment; filename=Relatorios_Adiantamento_{request.month}-{request.year}.zip"
            },
        )
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Erro crítico em /reports/generate: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Erro interno ao gerar relatórios: {e}"
        )


# (Adicione aqui o if __name__ == "__main__": uvicorn.run(...) se você o utiliza)


# --- Modelos Pydantic Adicionais (se não existirem) ---
class RPAImportRequest(BaseModel):
    year: int
    month: int
    company_codes: Optional[List[str]] = (
        None  # Lista de códigos do catálogo ou None para "todos pendentes"
    )


# --- Novo Endpoint ---
@app.post("/rpa/import-consignments")
async def trigger_rpa_import_consignments(request: RPAImportRequest):
    """
    Aciona (atualmente simula) o RPA para importar consignados e atualiza o status.
    """
    print(
        f"Recebida solicitação de importação de consignados para {request.month}/{request.year}"
    )

    empresas_para_importar = []

    if request.company_codes:  # Se uma lista específica foi enviada
        empresas_para_importar = [
            code for code in request.company_codes if CATALOG.get(code)
        ]
        print(f"Empresas especificadas: {empresas_para_importar}")
    else:  # Se for para importar "todos pendentes"
        print("Buscando empresas com consignado pendente...")
        for code, rule in CATALOG.items():
            if not rule.emp_id:
                continue  # Pula empresas sem ID mapeado
            status_key = (request.year, request.month, str(rule.emp_id))
            if not consignado_import_status.get(status_key, False):
                empresas_para_importar.append(code)
        print(f"Empresas pendentes encontradas: {empresas_para_importar}")

    if not empresas_para_importar:
        return {
            "status": "success",
            "message": "Nenhuma empresa encontrada para importação.",
        }

    # --- SIMULAÇÃO DA EXECUÇÃO DO RPA ---
    print(">>> Iniciando SIMULAÇÃO do RPA de importação...")
    import time

    time.sleep(5)  # Simula o tempo que o RPA levaria
    print(">>> SIMULAÇÃO do RPA concluída com sucesso.")
    # ------------------------------------

    # --- Em um cenário real, o script RPA retornaria quais empresas tiveram sucesso ---
    # Para a simulação, vamos assumir que todas tiveram sucesso
    empresas_com_sucesso = empresas_para_importar

    # Atualiza o status no dicionário em memória
    for code in empresas_com_sucesso:
        rule = CATALOG.get(code)
        if rule and rule.emp_id:
            status_key = (request.year, request.month, str(rule.emp_id))
            consignado_import_status[status_key] = True
            print(f"Status atualizado para importado: {rule.name}")

    return {
        "status": "success",
        "message": f"Importação de consignados (simulada) concluída com sucesso para {len(empresas_com_sucesso)} empresa(s).",
    }
