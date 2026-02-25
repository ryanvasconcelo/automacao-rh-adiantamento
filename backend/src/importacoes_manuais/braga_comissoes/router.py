from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional
from src.importacoes_manuais.braga_comissoes.parser import extract_comissoes_from_excel
from src.importacoes_manuais.braga_comissoes.mapper import map_apelidos_to_matriculas
from src.importacoes_manuais.braga_comissoes.generator import generate_fortes_csv

router = APIRouter(prefix="/braga-comissoes", tags=["Braga Comissões"])

@router.post("/processar")
async def processar_planilha_braga(
    file: UploadFile = File(...),
    evento_padrao: str = Form("030")
):
    """
    Recebe a planilha XLSX, faz o parser, pesquisa EPG via DB e gera os arquivos Fortes (separados por empresa).
    """
    if not file.filename.endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Arquivo deve ser .xlsx")
        
    contents = await file.read()
    
    try:
        dados_extraidos = extract_comissoes_from_excel(contents)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao processar planilha: {str(e)}")
        
    registros_por_empresa = {}
    erros_mapeamento = []
    
    # 1. Extrair mapa de apelidos em BATCH da base
    apelidos_unicos = list(set([item.get("apelido") for item in dados_extraidos if item.get("apelido")]))
    
    try:
        mapeamento = map_apelidos_to_matriculas(apelidos_unicos)
    except RuntimeError as db_err:
        raise HTTPException(status_code=503, detail=str(db_err))
        
    
    # 2. Iterar itens e associar matriculas e empresas já baixadas da memoria
    for item in dados_extraidos:
        apelido = item.get("apelido")
        valor = item.get("valor")
        cabecalho_empresa = item.get("cabecalho_empresa")
        
        matricula, empresa_id, match_nome = mapeamento.get(apelido, (None, None, None))
        
        if not matricula or not empresa_id:
            erros_mapeamento.append(apelido)
            continue
            
            
        if empresa_id not in registros_por_empresa:
            registros_por_empresa[empresa_id] = {
                "cabecalho_bruto": cabecalho_empresa,
                "registros": []
            }
            
        registros_por_empresa[empresa_id]["registros"].append({
            "matricula": matricula,
            "nome_match": match_nome,
            "apelido_original": apelido,
            "evento_codigo": evento_padrao,
            "valor": valor
        })
        
    # Gera os CSVs
    arquivos_gerados = {}
    arquivos_detalhes = {}
    for emp_id, emp_data in registros_por_empresa.items():
        csv_content = generate_fortes_csv(emp_data["cabecalho_bruto"], emp_data["registros"])
        arquivos_gerados[emp_id] = csv_content
        arquivos_detalhes[emp_id] = emp_data["registros"]
        
    status = "warning" if erros_mapeamento else "success"
    message = "Arquivos processados com avisos. Alguns apelidos não foram encontrados." if erros_mapeamento else "Arquivos processados com sucesso."
    
    return {
        "status": status,
        "message": message,
        "arquivos": arquivos_gerados,
        "arquivos_detalhes": arquivos_detalhes,
        "apelidos_nao_encontrados": list(set(erros_mapeamento))
    }
