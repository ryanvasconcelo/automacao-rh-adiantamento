# test_connection.py
import os
import pyodbc
from dotenv import load_dotenv

print("Iniciando teste de conexão isolado...")

# Carrega as variáveis do arquivo .env
load_dotenv(override=True)
DRV = os.getenv("DB_DRIVER", "").strip()
HOST = os.getenv("DB_HOST", "").strip()
PORT = os.getenv("DB_PORT", "1433").strip()
DB = os.getenv("DB_DATABASE", "").strip()
USR = os.getenv("DB_USER", "").strip()
PWD = os.getenv("DB_PASSWORD", "").strip()

# A string de conexão explícita que estávamos tentando
connection_string = (
    f"Driver={{{DRV}}};"
    f"Server={HOST};"
    f"Port={PORT};"
    f"Database={DB};"
    f"UID={USR};"
    f"PWD={PWD};"
    f"TDS_Version=7.4;"
    f"timeout=30;"
)

# A consulta mais simples possível
simple_query = "SELECT TOP 5 EMP_CODIGO, CODIGO, NOME FROM EPG;"

try:
    print(f"Tentando conectar com a string: {connection_string.replace(PWD, '******')}")
    # Conecta ao banco de dados
    cnxn = pyodbc.connect(connection_string, autocommit=True)
    cursor = cnxn.cursor()
    
    print("\n✅ Conexão bem-sucedida!")
    
    print(f"\nExecutando a query simples: {simple_query}")
    cursor.execute(simple_query)
    
    print("\n✅ Query executada com sucesso!")
    
    # Busca e imprime os resultados
    rows = cursor.fetchall()
    print(f"\nResultados encontrados ({len(rows)} linhas):")
    for row in rows:
        print(row)

except Exception as e:
    print("\n❌ FALHA NO TESTE. Erro encontrado:")
    print(e)

finally:
    print("\nTeste finalizado.")