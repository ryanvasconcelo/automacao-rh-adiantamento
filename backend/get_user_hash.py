# get_user_hash.py
"""
Script para descobrir o hash da senha do usuário no Fortes.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.database import get_connection

def get_user_hash(username: str):
    """Busca o hash da senha do usuário."""
    print("="*60)
    print("BUSCANDO HASH DA SENHA")
    print("="*60)
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT Codigo, Senha, NOME, Bloqueado, UltimoAcesso
            FROM USU
            WHERE Codigo = %s
        """
        
        cursor.execute(query, [username])
        result = cursor.fetchone()
        
        if result:
            codigo, senha_hash, nome, bloqueado, ultimo_acesso = result
            
            print(f"\n✅ Usuário encontrado: {codigo}")
            print(f"   Nome: {nome or 'N/A'}")
            print(f"   Hash da senha: {senha_hash}")
            print(f"   Status: {'BLOQUEADO' if bloqueado == 1 else 'ATIVO'}")
            print(f"   Último acesso: {ultimo_acesso}")
            
            print("\n" + "="*60)
            print("INSTRUÇÕES:")
            print("="*60)
            print(f"\nAdicione ao seu arquivo .env:")
            print(f"\nFORTES_USER=\"{codigo}\"")
            print(f"FORTES_PASSWORD_HASH={senha_hash}")
            print("\nO sistema usará o hash para autenticação.")
            
        else:
            print(f"\n❌ Usuário {username} não encontrado!")
        
        conn.close()
        
    except Exception as e:
        print(f"\n❌ Erro: {e}")

if __name__ == "__main__":
    username = input("Digite o código do usuário (ex: RYAN): ").strip().upper()
    get_user_hash(username)