# api.py (Versão Final com todos os endpoints)

import os
import io
import shutil
import zipfile
import pandas as pd
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

import main
from src.rules_catalog import CATALOG, get_company_rule
from src.data_extraction import (
    fetch_all_companies,
    fetch_filters_for_company,
    fetch_payroll_report_data,
    get_latest_fol_seq,
    fetch_listagem_adiantamento_data,
    fetch_recibo_pagamento_data,
    fetch_folha_sintetica_data,
)

app = FastAPI(title="RH Tools API - Auditor de Adiantamento", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- MODELOS Pydantic ---


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


class ApplyCorrectionsRequest(BaseModel):
    empresaCodigo: int  # Mudou de str para int
    month: int
    year: int
    selectedMatriculas: List[str]
    fortes_user: Optional[str] = None
    fortes_password_hash: Optional[int] = None
    auto_recalc: bool = False


class ReportGenerationRequest(BaseModel):
    month: int
    year: int
    data: List[CorrectedAuditRow]


# --- ENDPOINTS ANTIGOS (Mantidos para referência ou uso futuro) ---


@app.get("/companies/grouped")
def get_companies_grouped():
    grouped_companies: Dict[str, List[Dict[str, str]]] = {"15": [], "20": []}
    for code, rule in CATALOG.items():
        pay_day = str(rule.base.window.pay_day)
        if pay_day in grouped_companies:
            grouped_companies[pay_day].append({"code": code, "name": rule.name})
    grouped_companies["15"] = sorted(grouped_companies["15"], key=lambda c: c["name"])
    grouped_companies["20"] = sorted(grouped_companies["20"], key=lambda c: c["name"])
    return grouped_companies


@app.post("/audit")
def run_single_audit(request: AuditRequest):
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

        # ... (formatação do resultado como antes)
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
        raise HTTPException(status_code=500, detail=f"Erro interno: {e}")


# --- NOVOS ENDPOINTS DO FLUXO ---


@app.post("/audit/day")
async def run_day_audit(request: DayAuditRequest):
    """Executa a auditoria para todas as empresas de um dia de pagamento específico."""
    target_day = str(request.day)
    companies_to_audit = [
        (code, rule)
        for code, rule in CATALOG.items()
        if str(rule.base.window.pay_day) == target_day and rule.emp_id
    ]

    all_results = []
    for code, rule in companies_to_audit:
        try:
            df_company_result = main.run(
                empresa_codigo=str(rule.emp_id),
                empresa_id_catalogo=code,
                ano=request.year,
                mes=request.month,
            )

            # Adiciona informações da empresa a cada linha
            df_company_result["empresaNome"] = rule.name
            df_company_result["empresaCodigo"] = rule.emp_id
            df_company_result["empresaCode"] = rule.code

            all_results.append(df_company_result)
        except Exception as e:
            print(f"Erro ao auditar a empresa {rule.name}: {e}")
            # Pular empresa com erro, mas continuar o lote
            continue

    if not all_results:
        return []

    df_final = pd.concat(all_results, ignore_index=True)

    # Renomeia colunas para o frontend
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


@app.post("/corrections/apply")
async def apply_corrections(request: ApplyCorrectionsRequest):
    """
    Aplica correções REAIS na tabela SEP do Fortes.

    ⚠️ ATENÇÃO: Esta operação modifica o banco de dados do Fortes!
    """
    try:
        from src.workflow_manager import AdiantamentoWorkflow

        # Converte para string para usar no workflow
        empresa_codigo_str = str(request.empresaCodigo)

        # Busca o código do catálogo pela empresa
        catalog_code = None
        for code, rule in CATALOG.items():
            if rule.emp_id and str(rule.emp_id) == empresa_codigo_str:
                catalog_code = code
                break

        if not catalog_code:
            # Lista empresas disponíveis para debug
            available_companies = {
                code: rule.emp_id for code, rule in CATALOG.items() if rule.emp_id
            }
            raise HTTPException(
                status_code=404,
                detail=f"Empresa {request.empresaCodigo} não encontrada no catálogo. Disponíveis: {available_companies}",
            )

        # Cria workflow usando o código do catálogo
        workflow = AdiantamentoWorkflow(
            catalog_code,
            request.year,
            request.month,
        )

        # Executa o fluxo completo com correções
        result = workflow.executar_fluxo_completo(
            aplicar_correcoes=True,
            confirmado=True,
            fortes_user=request.fortes_user or os.getenv("FORTES_USER"),
            fortes_password_hash=request.fortes_password_hash
            or int(os.getenv("FORTES_PASSWORD_HASH", "0")),
            auto_recalc=request.auto_recalc,
        )

        # Verifica o tipo de erro
        if result.status.value == "erro":
            # Verifica se é erro de permissão
            if result.falhas_correcao and all(
                "permiss" in str(f.get("erro", "")).lower()
                for f in result.falhas_correcao
            ):
                # Todas as falhas são de permissão
                raise HTTPException(
                    status_code=403,  # Forbidden
                    detail={
                        "error": "Permissão negada para UPDATE na tabela SEP",
                        "message": "O usuário do banco de dados não tem permissão para modificar a tabela SEP.",
                        "solution": [
                            "Execute no SQL Server (como DBA):",
                            "",
                            "USE AC;",
                            "GO",
                            "GRANT UPDATE ON dbo.SEP TO [seu_usuario];",
                            "GO",
                            "",
                            "Ou configure um usuário com permissões adequadas no arquivo .env",
                        ],
                        "affected_employees": len(result.falhas_correcao),
                        "technical_details": result.mensagem,
                    },
                )
            else:
                # Outros tipos de erro
                raise HTTPException(
                    status_code=500,
                    detail={
                        "error": result.mensagem,
                        "failures": result.falhas_correcao,
                    },
                )

        # Verifica sucesso parcial (algumas correções aplicadas, outras não)
        if result.correcoes_aplicadas == 0 and result.falhas_correcao:
            # Nenhuma correção aplicada
            erros_permissao = [
                f
                for f in result.falhas_correcao
                if "permiss" in str(f.get("erro", "")).lower()
            ]

            if len(erros_permissao) == len(result.falhas_correcao):
                raise HTTPException(
                    status_code=403,
                    detail={
                        "error": "Permissão negada para UPDATE na tabela SEP",
                        "solution": [
                            "USE AC;",
                            "GRANT UPDATE ON dbo.SEP TO [seu_usuario];",
                        ],
                        "affected_employees": len(result.falhas_correcao),
                    },
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail={
                        "error": "Nenhuma correção aplicada",
                        "failures": result.falhas_correcao,
                    },
                )

        # Sucesso (total ou parcial)
        response_data = {
            "success": True,
            "message": result.mensagem,
            "correcoes_aplicadas": result.correcoes_aplicadas,
            "caminho_pdf": result.caminho_pdf,
            "caminho_csv": result.caminho_csv,
        }

        # Adiciona avisos se houve falhas parciais
        if result.falhas_correcao:
            response_data["warning"] = (
                f"{len(result.falhas_correcao)} funcionários falharam"
            )
            response_data["falhas"] = result.falhas_correcao

        return response_data

    except HTTPException:
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()

        # Verifica se é erro de permissão na exceção genérica
        error_msg = str(e).lower()
        if "permission" in error_msg or "permiss" in error_msg:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "Permissão negada",
                    "message": str(e),
                    "solution": [
                        "USE AC;",
                        "GRANT UPDATE ON dbo.SEP TO [seu_usuario];",
                    ],
                },
            )

        raise HTTPException(
            status_code=500, detail=f"Erro ao aplicar correções: {str(e)}"
        )


@app.post("/reports/generate")
async def generate_reports(request: ReportGenerationRequest):
    """Gera os relatórios, chamando a função de busca de dados correta para cada tipo."""

    empresas_a_processar = {}
    for row in request.data:
        if row.empresaCodigo not in empresas_a_processar:
            empresas_a_processar[row.empresaCodigo] = {
                "nome": row.empresaNome,
                "funcionarios": [],
            }
        empresas_a_processar[row.empresaCodigo]["funcionarios"].append(row)

    output_path = "relatorios_gerados"
    if os.path.exists(output_path):
        shutil.rmtree(output_path)
    os.makedirs(output_path)

    for emp_codigo, info in empresas_a_processar.items():
        try:
            print(f"Gerando relatórios para: {info['nome']}")
            fol_seq = get_latest_fol_seq(str(emp_codigo), request.year, request.month)

            if not fol_seq:
                print(
                    f"AVISO: Nenhuma folha de adiantamento processada encontrada para {info['nome']}. Pulando."
                )
                continue

            print(f"  - Usando Folha ID (FOL.Seq): {fol_seq}")
            empresa_path = os.path.join(
                output_path,
                f"Adiantamento {info['nome']} {request.month}-{request.year}",
            )
            os.makedirs(empresa_path, exist_ok=True)
            filtros = fetch_filters_for_company(str(emp_codigo))

            # --- LÓGICA DE SELEÇÃO DE FUNÇÃO ATUALIZADA ---
            for tipo_relatorio in [
                "Listagem de Adiantamento",
                "Recibo de Pagamento",
                "Folha Sintetica",
            ]:
                print(f"    - Gerando: {tipo_relatorio}")

                # Seleciona a função de busca de dados correta
                if tipo_relatorio == "Listagem de Adiantamento":
                    func_busca = fetch_listagem_adiantamento_data
                elif tipo_relatorio == "Recibo de Pagamento":
                    func_busca = fetch_recibo_pagamento_data
                else:  # Folha Sintetica
                    func_busca = fetch_folha_sintetica_data

                # A lógica de loop de filtros agora usa a função selecionada
                if tipo_relatorio == "Folha Sintetica":
                    report_data = func_busca(str(emp_codigo), fol_seq)
                    if not report_data.empty:
                        report_data.to_csv(
                            os.path.join(
                                empresa_path, "Folha Sintetica de Adiantamento.csv"
                            ),
                            index=False,
                        )
                    continue

                for filtro_nome, filtro_lista in filtros.items():
                    if not filtro_lista:
                        continue

                    filtro_path = os.path.join(empresa_path, filtro_nome.capitalize())
                    os.makedirs(filtro_path, exist_ok=True)

                    df_geral = func_busca(str(emp_codigo), fol_seq)
                    if not df_geral.empty:
                        df_geral.to_csv(
                            os.path.join(filtro_path, f"{tipo_relatorio} - Geral.csv"),
                            index=False,
                        )

                    for item in filtro_lista:
                        filtro_kwargs = {
                            "filtro_estabelecimento": (
                                item["CODIGO"]
                                if filtro_nome == "estabelecimentos"
                                else None
                            )
                        }
                        df_especifico = func_busca(
                            str(emp_codigo), fol_seq, **filtro_kwargs
                        )
                        if not df_especifico.empty:
                            file_name = (
                                f"{tipo_relatorio} - {item['NOME']}.csv".replace(
                                    "/", "-"
                                )
                            )
                            df_especifico.to_csv(
                                os.path.join(filtro_path, file_name), index=False
                            )

        except Exception as e:
            print(f"ERRO CRÍTICO ao gerar relatório para a empresa {info['nome']}: {e}")
            import traceback

            traceback.print_exc()
            continue

    # --- CORREÇÃO 2: Verifica se algum arquivo foi realmente gerado ---
    # `os.listdir` em um diretório vazio retorna uma lista vazia, que é "falsy"
    if not os.listdir(output_path) or not any(os.scandir(output_path)):
        # Limpa a pasta de saída vazia
        shutil.rmtree(output_path)
        raise HTTPException(
            status_code=404,
            detail="Nenhum dado de relatório encontrado para as empresas e período selecionados.",
        )

    # Compacta a pasta de saída em um arquivo ZIP em memória
    zip_buffer = io.BytesIO()
    # --- CORREÇÃO 1: Modo 'w' (write) em vez de 'a' (append) ---
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED, False) as zip_file:
        for root, _, files in os.walk(output_path):
            for file in files:
                full_path = os.path.join(root, file)
                archive_path = os.path.relpath(full_path, output_path)
                zip_file.write(full_path, archive_path)

    shutil.rmtree(output_path)
    zip_buffer.seek(0)

    return StreamingResponse(
        zip_buffer,
        media_type="application/x-zip-compressed",
        headers={
            "Content-Disposition": f"attachment; filename=Relatorios_Adiantamento_{request.month}-{request.year}.zip"
        },
    )
