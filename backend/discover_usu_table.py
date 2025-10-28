# discover_usu_table.py
"""
Script para descobrir a estrutura da tabela USU do Fortes.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.database import get_connection

def discover_table_structure():
    """Descobre a estrutura da tabela USU."""
    print("="*60)
    print("DESCOBRINDO ESTRUTURA DA TABELA USU")
    print("="*60)
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Lista todas as colunas da tabela USU
        query = """
            SELECT 
                COLUMN_NAME,
                DATA_TYPE,
                CHARACTER_MAXIMUM_LENGTH,
                IS_NULLABLE
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = 'USU'
            ORDER BY ORDINAL_POSITION
        """
        
        cursor.execute(query)
        columns = cursor.fetchall()
        
        if columns:
            print("\n✅ Tabela USU encontrada!")
            print("\nColunas disponíveis:")
            print("-" * 60)
            for col in columns:
                col_name, data_type, max_length, nullable = col
                length_str = f"({max_length})" if max_length else ""
                null_str = "NULL" if nullable == "YES" else "NOT NULL"
                print(f"  {col_name:<30} {data_type}{length_str:<15} {null_str}")
        else:
            print("\n❌ Tabela USU não encontrada!")
        
        # Tenta buscar alguns registros para ver o conteúdo
        print("\n" + "="*60)
        print("AMOSTRA DE DADOS (primeiros 3 registros)")
        print("="*60)
        
        cursor.execute("SELECT TOP 3 * FROM USU")
        rows = cursor.fetchall()
        
        if rows:
            # Pega os nomes das colunas
            col_names = [desc[0] for desc in cursor.description]
            
            for row in rows:
                print("\nRegistro:")
                for col_name, value in zip(col_names, row):
                    print(f"  {col_name}: {value}")
        
        conn.close()
        
    except Exception as e:
        print(f"\n❌ Erro: {e}")

if __name__ == "__main__":
    discover_table_structure()