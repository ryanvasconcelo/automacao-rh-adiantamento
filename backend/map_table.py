import sys
import os
import pandas as pd

sys.path.append(os.getcwd())
try:
    from src.database import get_connection
except ImportError:
    sys.path.append(os.path.join(os.getcwd(), "backend"))
    from src.database import get_connection


def verificar_tabela_dep():
    print("🔍 Procurando tabela DEP (Dependentes)...")
    try:
        with get_connection() as conn:
            # Verifica se DEP existe e lista colunas
            query = """
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'DEP'
            """
            df = pd.read_sql(query, conn)

            if df.empty:
                print("❌ Tabela DEP não encontrada.")
            else:
                print(f"✅ Tabela DEP encontrada com {len(df)} colunas.")
                print(df["COLUMN_NAME"].tolist())

                # Tenta contar dependentes de um empregado teste
                print("\n📊 Tentando contar dependentes para validação...")
                count_query = """
                    SELECT TOP 5 EMP_Codigo, EPG_Codigo, COUNT(*) as Qtd
                    FROM DEP
                    GROUP BY EMP_Codigo, EPG_Codigo
                    ORDER BY Qtd DESC
                """
                sample = pd.read_sql(count_query, conn)
                print(sample.to_string(index=False))

    except Exception as e:
        print(f"❌ Erro: {e}")


if __name__ == "__main__":
    verificar_tabela_dep()
