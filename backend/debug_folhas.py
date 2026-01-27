#!/usr/bin/env python3
"""
Listar todas as folhas disponíveis para setembro/2025
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
    print("\n📋 TODAS AS FOLHAS DE SETEMBRO/2025\n")
    
    sql = """
        SELECT 
            FOL.Seq,
            FOL.Folha,
            COUNT(DISTINCT EPG.Codigo) as QtdFuncionarios,
            COUNT(DISTINCT EFP.EVE_CODIGO) as QtdEventosDiferentes,
            COUNT(*) as TotalEventos
        FROM FOL (NOLOCK)
        INNER JOIN EFO (NOLOCK) ON FOL.EMP_Codigo = EFO.EMP_Codigo AND FOL.Seq = EFO.FOL_Seq
        INNER JOIN EPG (NOLOCK) ON EFO.EMP_Codigo = EPG.EMP_Codigo AND EFO.EPG_Codigo = EPG.Codigo
        LEFT JOIN EFP (NOLOCK) ON EFO.EMP_Codigo = EFP.EMP_Codigo AND EFO.FOL_Seq = EFP.EFO_FOL_Seq AND EFO.EPG_Codigo = EFP.EFO_EPG_Codigo
        WHERE FOL.EMP_Codigo = '9189'
        GROUP BY FOL.Seq, FOL.Folha
        ORDER BY FOL.Seq DESC
    """
    
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql)
            rows = [dict_factory(cursor, row) for row in cursor.fetchall()]
            
            if not rows:
                print("❌ Nenhuma folha encontrada!")
                return
            
            print(f"{'Seq':<6} {'Folha':<6} {'Funcionários':<15} {'Eventos Diff':<15} {'Total Eventos':<15}")
            print("-" * 75)
            
            for row in rows:
                print(f"{row['Seq']:<6} {row['Folha']:<6} {row['QtdFuncionarios']:<15} {row['QtdEventosDiferentes']:<15} {row['TotalEventos']:<15}")
    
    except Exception as e:
        print(f"Erro: {e}")


if __name__ == "__main__":
    main()
