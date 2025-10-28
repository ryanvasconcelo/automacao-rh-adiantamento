# test_fortes_auth.py
"""
Script para testar autenticação no Fortes.
"""

import os
import sys
from dotenv import load_dotenv

# Adiciona o diretório src ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src.fortes_auto_recalc import FortesAutoRecalc

# Carrega variáveis de ambiente
load_dotenv()

FORTES_USER = os.getenv("FORTES_USER", "RYAN")
FORTES_PASSWORD_HASH = os.getenv("FORTES_PASSWORD_HASH")


def test_auth():
    """Testa autenticação no Fortes."""
    print("=" * 60)
    print("TESTE DE AUTENTICAÇÃO NO FORTES")
    print("=" * 60)
    print(f"\nUsuário: {FORTES_USER}")
    
    if not FORTES_PASSWORD_HASH:
        print("\n❌ ERRO: FORTES_PASSWORD_HASH não encontrado no .env")
        print("\nPara configurar:")
        print("1. Execute: python get_user_hash.py")
        print("2. Adicione FORTES_PASSWORD_HASH ao arquivo .env")
        return False
    
    try:
        senha_hash = int(FORTES_PASSWORD_HASH)
        print(f"Hash da senha: {senha_hash}")
    except ValueError:
        print(f"\n❌ ERRO: FORTES_PASSWORD_HASH deve ser um número inteiro")
        print(f"Valor recebido: {FORTES_PASSWORD_HASH}")
        return False

    # Cria instância (empresa teste)
    recalc = FortesAutoRecalc("9224", FORTES_USER, senha_hash)

    print("\n🔐 Validando credenciais...")

    if recalc.validar_credenciais():
        print("\n✅ SUCESSO: Credenciais válidas!")
        print("O usuário está autenticado no Fortes.")
        return True
    else:
        print("\n❌ ERRO: Credenciais inválidas!")
        print("\nPossíveis causas:")
        print("1. Hash de senha incorreto")
        print("2. Usuário inativo no Fortes")
        print("3. Tabela USU não acessível")
        print("\nVerifique:")
        print("- Execute: python get_user_hash.py")
        print("- Confirme que o hash no .env está correto")
        print("- Menu Fortes > Cadastros > Usuários")
        return False


if __name__ == "__main__":
    test_auth()
