#!/usr/bin/env python3
import pymssql
import os
from dotenv import load_dotenv

load_dotenv(override=True)


def test_connection():
    """Testa a conexão ODBC com diferentes drivers"""

    # Listar drivers disponíveis
    print("🔍 Drivers ODBC disponíveis:")
    drivers = pyodbc.drivers()
    for i, driver in enumerate(drivers, 1):
        print(f"  {i}. {driver}")

    if not drivers:
        print("❌ Nenhum driver ODBC encontrado!")
        return False

    # Pegar configurações do .env
    HOST = os.getenv("DB_HOST", "").strip()
    PORT = os.getenv("DB_PORT", "1433").strip()
    DB = os.getenv("DB_DATABASE", "").strip()
    USR = os.getenv("DB_USER", "").strip()
    PWD = os.getenv("DB_PASSWORD", "").strip()

    if not all([HOST, DB, USR, PWD]):
        print("❌ Configurações de banco incompletas no .env")
        return False

    # Testar diferentes drivers
    drivers_to_test = ["FreeTDS", "TDS"]

    for driver_name in drivers_to_test:
        if driver_name in drivers:
            print(f"\n🧪 Testando driver: {driver_name}")

            connection_string = (
                f"Driver={{{driver_name}}};"
                f"Server={HOST};"
                f"Port={PORT};"
                f"Database={DB};"
                f"UID={USR};"
                f"PWD={PWD};"
                f"TDS_Version=7.3;"
            )

            try:
                print(f"   📡 Conectando ao servidor {HOST}:{PORT}...")
                conn = pymssql.connect(connection_string, timeout=10)

                # Testar uma query simples
                cursor = conn.cursor()
                cursor.execute("SELECT 1 as test")
                result = cursor.fetchone()

                print(f"   ✅ Conexão bem-sucedida com {driver_name}!")
                print(f"   📊 Teste de query: {result[0]}")

                conn.close()
                return True

            except Exception as e:
                print(f"   ❌ Falha com {driver_name}: {str(e)}")
                continue

    print("\n❌ Todos os drivers falharam!")
    return False


def show_env_config():
    """Mostra configuração atual do ambiente"""
    print("\n📋 Configuração atual:")
    print(f"   ODBCSYSINI: {os.environ.get('ODBCSYSINI', 'Não definido')}")
    print(f"   ODBCINI: {os.environ.get('ODBCINI', 'Não definido')}")
    print(f"   DB_HOST: {os.getenv('DB_HOST', 'Não definido')}")
    print(f"   DB_PORT: {os.getenv('DB_PORT', 'Não definido')}")
    print(f"   DB_DATABASE: {os.getenv('DB_DATABASE', 'Não definido')}")
    print(f"   DB_USER: {os.getenv('DB_USER', 'Não definido')}")


if __name__ == "__main__":
    print("🚀 Teste de Conexão ODBC com FreeTDS")
    print("=" * 50)

    show_env_config()
    success = test_connection()

    if success:
        print("\n🎉 Configuração ODBC funcionando perfeitamente!")
    else:
        print("\n💡 Próximos passos para resolver:")
        print("   1. Verificar se odbcinst.ini está correto")
        print("   2. Confirmar variáveis de ambiente")
        print("   3. Testar conexão direta com tsql")
