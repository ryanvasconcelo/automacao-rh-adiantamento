# backend/src/database.py
import contextlib
import logging
from typing import Generator
from src.config import settings

logger = logging.getLogger("projecont.database")

# Imports condicionais
pymssql = None
pyodbc = None

try:
    import pymssql
except ImportError:
    pass

try:
    import pyodbc
except ImportError:
    pass


class DatabaseFactory:
    @staticmethod
    def get_connection():
        driver_type = settings.DB_DRIVER.lower()

        # --- ESTRATÉGIA 1: FreeTDS / Pymssql (Mac/Linux) ---
        if "freetds" in driver_type or "pymssql" in driver_type:
            if not pymssql:
                raise ImportError("Driver 'pymssql' não instalado.")

            return pymssql.connect(
                server=settings.DB_HOST,
                port=settings.DB_PORT,
                user=settings.DB_USER,
                password=settings.DB_PASSWORD,
                database=settings.DB_DATABASE,
                timeout=settings.DB_TIMEOUT,
                # REMOVIDO: as_dict=True (Isso quebrava o Pandas read_sql)
            )

        # --- ESTRATÉGIA 2: ODBC / Pyodbc (Windows) ---
        else:
            if not pyodbc:
                raise ImportError("Driver 'pyodbc' não instalado.")

            conn_str = (
                f"DRIVER={settings.DB_DRIVER};"
                f"SERVER={settings.DB_HOST},{settings.DB_PORT};"
                f"DATABASE={settings.DB_DATABASE};"
                f"UID={settings.DB_USER};"
                f"PWD={settings.DB_PASSWORD};"
                "TrustServerCertificate=yes;"
            )
            return pyodbc.connect(conn_str, timeout=settings.DB_TIMEOUT)


@contextlib.contextmanager
def get_connection():
    conn = None
    try:
        conn = DatabaseFactory.get_connection()
        yield conn
    except Exception as e:
        logger.error(f"❌ Erro Crítico de Banco de Dados: {str(e)}")
        raise e
    finally:
        if conn:
            conn.close()


def ping() -> bool:
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            return True
    except Exception:
        return False
