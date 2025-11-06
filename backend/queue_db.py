# queue_db.py (Versão 2.0 - Usando pyodbc)
# Esta versão usa pyodbc, que é mais estável com Autenticação do Windows.

import os
import pyodbc  # <--- MUDANÇA DE BIBLIOTECA
from dotenv import load_dotenv

load_dotenv(override=True)

# Lendo as novas variáveis de ambiente
SERVER = os.getenv("QUEUE_DB_SERVER", "localhost,1433").strip()
DATABASE = os.getenv("QUEUE_DB_DATABASE", "RPA_JOBS_DB").strip()
DRIVER = os.getenv("QUEUE_DB_DRIVER", "{ODBC Driver 17 for SQL Server}").strip()
TO = int(os.getenv("DB_TIMEOUT", "30"))

# String de conexão Mágica para pyodbc + Autenticação Windows
# "Trusted_Connection=yes" é o que diz "use Autenticação do Windows"
CONNECTION_STRING = (
    f"DRIVER={DRIVER};SERVER={SERVER};DATABASE={DATABASE};Trusted_Connection=yes;"
)


def get_queue_connection():
    """Cria e retorna uma conexão pyodbc para a FILA DE JOBS."""
    try:
        print(f"Conectando à Fila (RPA_JOBS_DB) com pyodbc (Auth Windows)...")
        # pyodbc usa 'autocommit=True' para evitar problemas de lock
        return pyodbc.connect(CONNECTION_STRING, timeout=TO, autocommit=True)

    except Exception as e:
        print(f"!!! FALHA AO CONECTAR NA FILA (pyodbc): {e}")
        print("Verifique se o 'ODBC Driver 17 for SQL Server' está instalado.")
        raise
