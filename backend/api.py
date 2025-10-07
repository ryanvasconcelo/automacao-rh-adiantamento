import pandas as pd
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict

import main
from src.rules_catalog import CATALOG, get_company_rule
from src.data_extraction import fetch_all_companies

app = FastAPI(title="RH Tools API - Auditor de Adiantamento", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AuditRequest(BaseModel):
    catalog_code: str
    month: int
    year: int


class Company(BaseModel):
    catalog_code: str
    db_code: str
    name: str


@app.get("/companies/grouped")
def get_companies_grouped():
    """
    Retorna um dicionário de empresas agrupadas por dia de pagamento (15 ou 20).
    """
    grouped_companies: Dict[str, List[Dict[str, str]]] = {"15": [], "20": []}
    for code, rule in CATALOG.items():
        pay_day = str(rule.base.window.pay_day)
        if pay_day in grouped_companies:
            grouped_companies[pay_day].append({"code": code, "name": rule.name})

    # Ordena as listas de empresas por nome
    grouped_companies["15"] = sorted(grouped_companies["15"], key=lambda c: c["name"])
    grouped_companies["20"] = sorted(grouped_companies["20"], key=lambda c: c["name"])

    return grouped_companies


@app.get("/companies", response_model=List[Company])
def get_companies():
    """
    Retorna a lista de todas as empresas disponíveis, garantindo que não há duplicatas.
    """
    try:
        db_companies = fetch_all_companies()
        company_list = []
        added_codes = (
            set()
        )  # --- CORREÇÃO: Conjunto para controlar códigos já adicionados

        for name, db_code in db_companies.items():
            for catalog_code, rule in CATALOG.items():
                if catalog_code in added_codes:
                    continue  # Já adicionamos esta regra, pular

                if (
                    name.upper() in rule.name.upper()
                    or rule.name.upper() in name.upper()
                ):
                    company_list.append(
                        {"catalog_code": catalog_code, "db_code": db_code, "name": name}
                    )
                    added_codes.add(catalog_code)  # Marca o código como adicionado
                    break

        return sorted(company_list, key=lambda c: c["name"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar empresas: {e}")


@app.post("/audit")
def run_audit(request: AuditRequest):
    # (O restante desta função permanece o mesmo)
    try:
        rule = get_company_rule(request.catalog_code)
        if not rule.emp_id:
            raise HTTPException(
                status_code=404,
                detail=f"Empresa '{request.catalog_code}' não tem um ID de base de dados mapeado.",
            )

        df_result = main.run(
            empresa_codigo=str(rule.emp_id),
            empresa_id_catalogo=request.catalog_code,
            ano=request.year,
            mes=request.month,
        )

        df_result.rename(
            columns={
                "Matricula": "matricula",
                "Nome": "nome",
                "Cargo": "cargo",
                "Analise": "analise",
                "Status": "status",
                "Observacoes": "observacoes",
                "ValorBrutoFortes": "valorBruto",
                "ValorLiquidoAdiantamento": "valorFinal",
                "ValorDesconto": "desconto",
            },
            inplace=True,
        )

        df_result["empresa"] = rule.name

        df_result_filled = df_result.replace({pd.NaT: None, np.nan: None})
        json_result = df_result_filled.to_dict(orient="records")

        return json_result
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail=f"Erro interno no processamento da auditoria: {e}"
        )
