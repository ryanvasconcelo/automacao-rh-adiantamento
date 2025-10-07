# check_columns.py (Modo Diagnóstico)
import os
import pymssql
from dotenv import load_dotenv


def run_diagnostic_query():
    load_dotenv(override=True)
    HOST = os.getenv("DB_HOST", "").strip()
    PORT = int(os.getenv("DB_PORT", "1433").strip())
    DB = os.getenv("DB_DATABASE", "").strip()
    USR = os.getenv("DB_USER", "").strip()
    PWD = os.getenv("DB_PASSWORD", "").strip()

    # Esta query tenta fazer a conversão que está falhando em toda a tabela.
    # Se ela falhar, confirma nossa teoria.
    query = (
        "SELECT COUNT(*) FROM EPG WHERE CAST(EMP_CODIGO AS VARCHAR(20)) IS NOT NULL;"
    )

    conn = None
    try:
        print("--- INICIANDO TESTE DE DIAGNÓSTICO ---")
        conn = pymssql.connect(
            server=HOST, port=PORT, user=USR, password=PWD, database=DB, timeout=30
        )
        print("✅ Conexão bem-sucedida.")

        print(f"Executando query de diagnóstico: {query}")
        cursor = conn.cursor()
        cursor.execute(query)
        result = cursor.fetchone()

        print(f"✅ Query executada! Total de registros: {result[0]}")
        print("Nenhuma linha causou o erro de overflow.")

    except pymssql.Error as e:
        # Se o erro de 'Arithmetic overflow' acontecer aqui, encontramos o culpado.
        print("\n❌ ERRO CONFIRMADO!")
        print(
            "O erro 'Arithmetic overflow' aconteceu durante a conversão direta no SQL."
        )
        print(
            "Isso prova que existe um dado inválido na coluna 'EMP_CODIGO' da tabela 'EPG'."
        )
        print(f"Detalhe do erro: {e}")

    finally:
        if conn:
            conn.close()
        print("\n--- TESTE FINALIZADO ---")


if __name__ == "__main__":
    run_diagnostic_query()
