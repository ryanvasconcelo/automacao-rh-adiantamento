from typing import Tuple, Dict, List
from src.database import get_connection
import logging

logger = logging.getLogger(__name__)

def map_apelidos_to_matriculas(apelidos: List[str]) -> Dict[str, Tuple[str, str]]:
    """
    Busca uma lista de apelidos no banco de dados do Fortes (tabela EPG) usando uma única conexão.
    Puxa todos os empregados das duas empresas e faz o match em memória usando lógica de prefixo sem espaços.
    Isso permite que "ALEXM" dê match em "ALEX MARQUES" (ALEXMARQUES.startswith(ALEXM)).
    Retorna um dicionário: { 'APELIDO': ('MATRICULA', 'EMPRESA_ID') }
    """
    if not apelidos:
        return {}
        
    resultado = {}
    
    sql = """
        SELECT Codigo, EMP_Codigo, Nome
        FROM EPG (NOLOCK)
        WHERE EMP_Codigo IN ('9274', '9275')
          AND DtRescisao IS NULL
    """
    
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql)
            rows = cursor.fetchall()
            
            # Prepara a lista em memória
            db_employees = []
            for row in rows:
                matricula = str(row[0]).strip()
                emp = str(row[1]).strip()
                nome_original = str(row[2]).strip().upper() if row[2] else ""
                
                # Partes do nome para lógica de iniciais
                partes = [p for p in nome_original.split() if len(p) > 1] # ignora 'de', 'da', etc curtos
                first_name = partes[0] if partes else ""
                others = partes[1:] if len(partes) > 1 else []
                
                # Possíveis combinações de match
                matches_possiveis = set()
                nome_clean = nome_original.replace(" ", "")
                matches_possiveis.add(nome_clean)
                
                # Padrão: PrimeiroNome + Inicial de qualquer outro (ex: ALEXM de ALEX MARQUES)
                if first_name:
                    for o in others:
                        matches_possiveis.add(first_name + o[0]) # ALEX + M
                        matches_possiveis.add(first_name + o)    # ALEX + MARQUES (concatenado)
                
                # Padrão: Inicial do Primeiro + Qualquer outro nome (ex: ASEGUNDO de ANA SEGUNDO)
                if first_name and others:
                    initial = first_name[0]
                    for o in others:
                        matches_possiveis.add(initial + o) # A + SEGUNDO
                
                db_employees.append({
                    "matricula": matricula,
                    "empresa": emp,
                    "nome_clean": nome_clean,
                    "nome_original": nome_original,
                    "matches_possiveis": matches_possiveis
                })
                
            for apelido in set(apelidos):
                if not apelido:
                    continue
                    
                apelido_clean = str(apelido).strip().upper().replace(" ", "")
                
                match_matricula, match_empresa, match_nome = None, None, None
                
                # Tenta match em uma das combinações possíveis ou startswith
                for db_emp in db_employees:
                    # 1. Match exato ou concatenado ou inicial (AUGUSTOM, ASEGUNDO, ALEXM)
                    if apelido_clean in db_emp["matches_possiveis"]:
                        match_matricula, match_empresa, match_nome = db_emp["matricula"], db_emp["empresa"], db_emp["nome_original"]
                        break
                    
                    # 2. Match por prefixo (ex: ALEXMARQUES começa com ALEXM)
                    if db_emp["nome_clean"].startswith(apelido_clean):
                        match_matricula, match_empresa, match_nome = db_emp["matricula"], db_emp["empresa"], db_emp["nome_original"]
                        break
                            
                resultado[apelido] = (match_matricula, match_empresa, match_nome)
                    
    except Exception as e:
        logger.error(f"Erro no mapeamento em lote de apelidos: {e}")
        raise RuntimeError(f"Falha ao conectar ou buscar dados no Fortes (Verifique VPN/Banco): {str(e)}")
        
    return resultado
