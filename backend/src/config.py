# backend/src/config.py
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # --- Identificação do Ambiente ---
    APP_NAME: str = "Projecont Auditor Unified"

    # --- Banco de Dados Principal (Fortes AC) ---
    # Se DB_DRIVER for 'FreeTDS', usa pymssql (Mac/Linux)
    # Se DB_DRIVER for '{ODBC Driver 17...}', usa pyodbc (Windows)
    DB_DRIVER: str = "FreeTDS"
    DB_HOST: str
    DB_PORT: int = 1433
    DB_DATABASE: str = "AC"
    DB_USER: str
    DB_PASSWORD: str
    DB_TIMEOUT: int = 30

    # --- Credenciais Legadas (Para procedures do Fortes) ---
    FORTES_USER: str = "RYAN"
    FORTES_PASSWORD_HASH: str = "50619"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignora variáveis extras (como as antigas QUEUE_*)


@lru_cache()
def get_settings():
    return Settings()


# Instância global
settings = get_settings()
