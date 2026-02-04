
import sys
import os

# Adiciona o diretório raiz ao path para poder importar módulos
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.database import get_connection

def inspect_dep_columns():
    query = "SELECT TOP 1 * FROM DEP"
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            columns = [column[0] for column in cursor.description]
            print("Colunas da tabela DEP:")
            for col in columns:
                print(f"- {col}")
    except Exception as e:
        print(f"Erro ao inspecionar DEP: {e}")

if __name__ == "__main__":
    inspect_dep_columns()
