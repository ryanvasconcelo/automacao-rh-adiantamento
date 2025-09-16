# src/database.py
import os
import pyodbc
from dotenv import load_dotenv

load_dotenv(override=True)

DRV = os.getenv("DB_DRIVER", "").strip()
HOST = os.getenv("DB_HOST", "").strip()
PORT = os.getenv("DB_PORT", "1433").strip()
DB = os.getenv("DB_DATABASE", "").strip()
USR = os.getenv("DB_USER", "").strip()
PWD = os.getenv("DB_PASSWORD", "").strip()
TO = int(os.getenv("DB_TIMEOUT", "30"))


def get_connection():
    """Cria e retorna uma conexão pyodbc pura e configurada."""
    if not all([DRV, HOST, DB, USR, PWD]):
        raise RuntimeError(
            "Verifique se todas as variáveis de banco de dados estão no arquivo .env"
        )

    connection_string = (
        f"Driver={{{DRV}}};"
        f"Server={HOST};"
        f"Port={PORT};"
        f"Database={DB};"
        f"UID={USR};"
        f"PWD={PWD};"
        f"TDS_Version=7.4;"
    )
    try:
        return pyodbc.connect(connection_string, timeout=TO, autocommit=True)
    except Exception as e:
        print(f"Falha ao conectar ao banco de dados: {e}")
        raise


def ping() -> bool:
    """Testa a conexão com o banco de dados."""
    try:
        conn = get_connection()
        conn.close()
        return True
    except Exception:
        return False
