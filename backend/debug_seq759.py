#!/usr/bin/env python3
"""
Debug: Descobrir qual AnoMes tem Seq 759
"""

import sys
import os

sys.path.append(os.getcwd())

try:
    from src.database import get_connection
except ImportError:
    sys.path.append(os.path.join(os.getcwd(), "backend"))
    from src.database import get_connection


def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def main():
    print("\n🔍 Descobrindo AnoMes para Seq 759\n")
    
    sql = """
        SELECT DISTINCT FOL.Seq, FOL.Folha, FPG.AnoMes
        FROM FOL (NOLOCK)
        INNER JOIN FPG (NOLOCK) ON FOL.EMP_Codigo = FPG.EMP_Codigo AND FOL.Seq = FPG.FOL_Seq
        WHERE FOL.EMP_Codigo = '9189'
          AND FOL.Seq = 759
    """
    
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql)
            rows = [dict_factory(cursor, row) for row in cursor.fetchall()]
            
            if rows:
                print("Seq 759:")
                for row in rows:
                    print(f"  Folha: {row['Folha']}, AnoMes: {row['AnoMes']}")
            else:
                print("❌ Seq 759 não encontrada com FPG")
    
    except Exception as e:
        print(f"❌ Erro: {e}")


if __name__ == "__main__":
    main()
