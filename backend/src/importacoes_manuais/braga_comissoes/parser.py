import io
import pandas as pd
from typing import List, Dict, Any

def extract_comissoes_from_excel(file_bytes: bytes) -> List[Dict[str, Any]]:
    """
    Abre o arquivo XLSX extraindo valores de 'sums' computados (padrão pandas read_excel para engine openpyxl).
    Lê a aba VENDEDOR e percorre identificando a linha do vendedor e as respectivas somas.
    """
    # Lendo sem header para não perder nenhuma linha e ter acesso as posições diretas
    df = pd.read_excel(io.BytesIO(file_bytes), sheet_name='VENDEDOR', header=None)
    
    col_data = df.iloc[:, 0].astype(str)
    col_vend = df.iloc[:, 1]
    col_valor = df.iloc[:, 6]
    
    # 1. Pegar cabeçalho da empresa (que comeca com 01TC)
    cabecalhos = col_data[col_data.str.contains('01TC', na=False)]
    empresa_header = cabecalhos.iloc[0].strip() if not cabecalhos.empty else "01TC0006 - HEADER PADRAO"
    
    # 2. Localizar linhas de subtotal
    val_num = pd.to_numeric(col_valor, errors='coerce')
    totais_mask = col_vend.isna() & val_num.notna()
    totais = df[totais_mask]
    
    resultados = []
    
    # Lista de apelidos/termos para ignorar (ruído na planilha)
    IGNORAR = ['DIRETORIA', 'TOTAL', 'RESUMO', 'VENDEDOR', 'SUBTOTAL']
    
    for idx, row in totais.iterrows():
        valor = float(val_num.iloc[idx])
        
        # Procurar o vendedor logo acima da linha de subtotal
        vendedor_nome = None
        for i in range(idx-1, -1, -1):
            v = col_vend.iloc[i]
            if pd.notna(v):
                v_clean = str(v).strip().upper()
                if v_clean not in IGNORAR:
                    vendedor_nome = str(v).strip()
                    break
                
        if vendedor_nome:
            resultados.append({
                "apelido": vendedor_nome,
                "valor": valor,
                "cabecalho_empresa": empresa_header
            })
            
    return resultados
