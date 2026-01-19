from typing import Dict, Optional

# Mapeia o código que vem do Front-end -> Para o código real no Banco de Dados (EMP_Codigo)
# Geralmente é igual, mas serve como uma "Whitelist" de segurança.

COMPANY_DB_MAP: Dict[str, str] = {
    "JR": "JR",
    "CMD": "CMD",
    "2056": "2056",  # A CICLISTA
}


def get_db_company_code(frontend_code: str) -> str:

    return str(frontend_code).upper()
