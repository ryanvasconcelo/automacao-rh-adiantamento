import io
import csv
from typing import List, Dict, Any

def generate_fortes_csv(cabecalho_empresa: str, registros: List[Dict[str, Any]]) -> str:
    """
    Gera uma string CSV no layout do Fortes para a empresa selecionada.
    Cód. Empregado | Cód. Evento | Referência | Valor do Evento
    """
    output = io.StringIO()
    writer = csv.writer(output, delimiter=',', lineterminator='\n')
    
    # 1. Escreve a linha do cabeçalho da empresa com as vírgulas vazias (ex: 01TC0006,,,)
    # Se o cabeçalho já não tiver as vírgulas, nós as adicionamos
    header_clean = cabecalho_empresa.split(",")[0].strip()
    output.write(f"{header_clean},,,\n")
    
    # 2. Escreve a linha de títulos (conforme modelo)
    output.write("Cód.Empregado,Cód. Evento,Referência,Valor do Evento\n")
    
    total_valor = 0.0
    total_linhas = 0
    
    # 3. Escreve os registros de cada empregado
    for reg in registros:
        # Garante matricula com 6 digitos (leading zeros)
        matricula_raw = str(reg.get("matricula", "")).strip()
        matricula = matricula_raw.zfill(6) if matricula_raw.isdigit() else matricula_raw
        
        evento = reg.get("evento_codigo", "030")
        referencia = ""
        
        try:
            valor_float = float(reg.get("valor", 0))
        except (ValueError, TypeError):
            valor_float = 0.0
            
        valor_str = f"{valor_float:.2f}".replace(".", ",")
        
        # O modelo Eventos_da_Folha_TC.csv mostra a linha toda entre aspas
        # Ex: "000029,030,,"300,6""
        # Para bater exatamente com o modelo, vamos formatar a string manualmente
        # Escapamos as aspas internas duplicando-as
        linha_interna = f"{matricula},{evento},{referencia},\"{valor_str}\""
        output.write(f"\"{linha_interna}\"\n")
        
        total_valor += valor_float
        total_linhas += 1
        
    # 4. Escreve a linha totalizadora (Z)
    soma_str = f"{total_valor:.2f}".replace(".", ",")
    total_interna = f"Z,{total_linhas},,\"{soma_str}\""
    output.write(f"\"{total_interna}\"\n")
    
    return output.getvalue()
