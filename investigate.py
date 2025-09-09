# investigate.py
# Ferramenta para explorar tabelas do banco de dados.

import pandas as pd
from src.database import get_db_connection
from config.logging_config import log

# Altere a query para a tabela que você quer investigar.
# Vamos começar pela TLI (Tipos de Licença).
QUERY = "SELECT TOP 10 * FROM COE"

def run_investigation():
    log.info(f"Executando query de investigação: {QUERY}")
    connection = get_db_connection()
    if connection:
        try:
            df = pd.read_sql(QUERY, connection)
            log.info(f"\n--- Conteúdo da Tabela: {QUERY.split()[-1]} ---")
            # O .to_string() garante que veremos todas as linhas e colunas.
            print(df.to_string())
        except Exception as e:
            log.error(f"Erro ao investigar a tabela: {e}")
        finally:
            connection.close()
            log.info("Conexão de investigação fechada.")

if __name__ == "__main__":
    run_investigation()