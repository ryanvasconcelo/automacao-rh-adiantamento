# backend/map_hours_tables.py
import sys
import os
import pandas as pd

# Ajuste de path para importar o módulo src corretamente
sys.path.append(os.getcwd())
try:
    from src.database import get_connection
except ImportError:
    sys.path.append(os.path.join(os.getcwd(), "backend"))
    from src.database import get_connection


def investigar_tabelas_horas():
    print("🕵️‍♂️ Investigando tabelas em busca da Carga Horária...")

    tabelas_alvo = ["SEP", "CAR", "ESC", "EPG"]

    try:
        with get_connection() as conn:
            for tabela in tabelas_alvo:
                print(f"\n--- Analisando Tabela: {tabela} ---")

                query = f"""
                    SELECT COLUMN_NAME 
                    FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_NAME = '{tabela}'
                    ORDER BY COLUMN_NAME
                """

                df = pd.read_sql(query, conn)

                if df.empty:
                    print("   (Tabela não encontrada ou sem permissão)")
                    continue

                colunas = df["COLUMN_NAME"].tolist()

                # Filtra colunas que podem ser de horas
                candidatas = [
                    c
                    for c in colunas
                    if any(
                        x in c.upper()
                        for x in ["HORA", "CARGA", "JORNADA", "QTD", "MENSAL"]
                    )
                ]

                if candidatas:
                    for c in candidatas:
                        print(f"   👉 {c}")
                else:
                    print("   (Nenhuma coluna suspeita encontrada)")

                # Se for a tabela SEP ou CAR, vamos tentar pegar uma amostra de dados
                # para ver se os valores fazem sentido (ex: 220, 180)
                if tabela in ["SEP", "CAR"] and candidatas:
                    col_str = ", ".join(candidatas[:3])  # Pega as 3 primeiras suspeitas
                    try:
                        sample_query = f"SELECT TOP 3 {col_str} FROM {tabela}"
                        sample = pd.read_sql(sample_query, conn)
                        print(
                            f"   📊 Amostra de dados:\n{sample.to_string(index=False)}"
                        )
                    except:
                        print("   (Não foi possível ler amostra de dados)")

    except Exception as e:
        print(f"❌ Erro fatal: {e}")


if __name__ == "__main__":
    investigar_tabelas_horas()
