# src/database.py
import os
import pymssql
from dotenv import load_dotenv

load_dotenv(override=True)

HOST = os.getenv("DB_HOST", "").strip()
PORT = int(os.getenv("DB_PORT", "1433").strip())
DB = os.getenv("DB_DATABASE", "").strip()
USR = os.getenv("DB_USER", "").strip()
PWD = os.getenv("DB_PASSWORD", "").strip()
TO = int(os.getenv("DB_TIMEOUT", "30"))


def get_connection():
    """Cria e retorna uma conexão pymssql configurada."""
    if not all([HOST, DB, USR, PWD]):
        raise RuntimeError(
            "Verifique se todas as variáveis de banco de dados estão no arquivo .env"
        )

    try:
        return pymssql.connect(
            server=HOST, port=PORT, user=USR, password=PWD, database=DB, timeout=TO
        )
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
