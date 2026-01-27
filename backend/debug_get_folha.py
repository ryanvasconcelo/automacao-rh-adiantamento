#!/usr/bin/env python3
"""
Debug: Testar qual Seq é retornada pela query
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
    empresa = "9189"
    ano_mes = "202509"
    
    print(f"\n🔍 Testando query get_folha_id para {ano_mes}\n")
    
    # Query original (com MAX)
    sql_max = """
        SELECT MAX(FOL.Seq) as Seq
        FROM FOL (NOLOCK)
        INNER JOIN FPG (NOLOCK) ON FOL.EMP_Codigo = FPG.EMP_Codigo AND FOL.Seq = FPG.FOL_Seq
        WHERE FOL.EMP_Codigo = %s 
          AND FPG.AnoMes = %s
          AND FOL.Folha = 2
    """
    
    # Query simples (sem MAX)
    sql_simple = """
        SELECT FOL.Seq
        FROM FOL (NOLOCK)
        INNER JOIN FPG (NOLOCK) ON FOL.EMP_Codigo = FPG.EMP_Codigo AND FOL.Seq = FPG.FOL_Seq
        WHERE FOL.EMP_Codigo = %s 
          AND FPG.AnoMes = %s
          AND FOL.Folha = 2
        ORDER BY FOL.Seq DESC
    """
    
    try:
        with get_connection() as conn:
            # Teste 1: MAX
            print("📌 Teste 1: Usando MAX(FOL.Seq)")
            cursor = conn.cursor()
            cursor.execute(sql_max, (empresa, ano_mes))
            row = cursor.fetchone()
            if row:
                data = dict_factory(cursor, row)
                print(f"   Resultado: Seq = {data['Seq']}")
            else:
                print("   Nenhum resultado")
            
            # Teste 2: TOP 1 ORDER BY DESC
            print("\n📌 Teste 2: Usando TOP 1 ORDER BY FOL.Seq DESC")
            cursor = conn.cursor()
            cursor.execute(sql_simple, (empresa, ano_mes))
            row = cursor.fetchone()
            if row:
                data = dict_factory(cursor, row)
                print(f"   Resultado: Seq = {data['Seq']}")
            else:
                print("   Nenhum resultado")
            
            # Teste 3: Listar TODAS as Seq para este AnoMes e Folha
            print(f"\n📌 Teste 3: TODAS as Seq para {ano_mes} + Folha = 2")
            sql_all = """
                SELECT DISTINCT FOL.Seq, COUNT(*) as QtdEventos
                FROM FOL (NOLOCK)
                INNER JOIN FPG (NOLOCK) ON FOL.EMP_Codigo = FPG.EMP_Codigo AND FOL.Seq = FPG.FOL_Seq
                INNER JOIN EFO (NOLOCK) ON FOL.EMP_Codigo = EFO.EMP_Codigo AND FOL.Seq = EFO.FOL_Seq
                WHERE FOL.EMP_Codigo = %s 
                  AND FPG.AnoMes = %s
                  AND FOL.Folha = 2
                GROUP BY FOL.Seq
                ORDER BY FOL.Seq DESC
            """
            cursor = conn.cursor()
            cursor.execute(sql_all, (empresa, ano_mes))
            rows = [dict_factory(cursor, row) for row in cursor.fetchall()]
            if rows:
                for row in rows:
                    print(f"   Seq: {row['Seq']} - QtdEventos: {row['QtdEventos']}")
            else:
                print("   Nenhum resultado")
    
    except Exception as e:
        print(f"❌ Erro: {e}")


if __name__ == "__main__":
    main()
