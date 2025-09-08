import os  # Biblioteca padrão do Python para interagir com o sistema operacional.
import pyodbc  # Nosso "tradutor" para o banco de dados.
from dotenv import load_dotenv  # O "guardião" que carrega nossas variáveis do .env.

# Esta linha é crucial. Ela procura por um arquivo .env e o carrega.
load_dotenv()


def get_db_connection():
    """
    Cria e retorna uma conexão com o banco de dados do RH.
    Utiliza as credenciais armazenadas de forma segura no arquivo .env.
    Retorna:
        pyodbc.Connection: Objeto de conexão com o banco de dados.
        None: Se a conexão falhar.
    """
    try:
        # Buscando as credenciais que o load_dotenv() carregou do arquivo .env.
        # Usar os.getenv() é mais seguro do que os.environ[], pois retorna None se a variável não for encontrada.
        server = os.getenv("DB_SERVER")
        database = os.getenv("DB_DATABASE")
        username = os.getenv("DB_USER")
        password = os.getenv("DB_PASSWORD")
        

        # Verificação de segurança: garantir que todas as credenciais foram carregadas.
        if not all([server, database, username, password]):
            log.info(
                "Erro: As variáveis de ambiente do banco de dados não foram configuradas corretamente no arquivo .env."
            )
            return None

        # A "string de conexão" é o endereço completo que o pyodbc usa para encontrar e autenticar no banco.
        # A parte 'DRIVER' pode variar. '{ODBC Driver 17 for SQL Server}' é comum para SQL Server.
        # Você talvez precise verificar qual driver está instalado na sua máquina.
        connection_string = (
            f"DRIVER=/opt/homebrew/lib/libtdsodbc.so;"
            f"SERVER={server};"
            f"DATABASE={database};"
            f"UID={username};"
            f"PWD={password};"
            f"TDS_Version=7.4;"
            f"Port=1433;"
        )

        log.info("Tentando conectar ao banco de dados...")
        conn = pyodbc.connect(connection_string)
        log.info("Conexão estabelecida com sucesso!")
        return conn

    except pyodbc.Error as ex:
        # Um bom código antecipa erros. Se a conexão falhar (senha errada, servidor offline),
        # o 'try...except' captura o erro e nos dá uma mensagem clara, em vez de quebrar o programa.
        sqlstate = ex.args[0]
        log.info(f"Erro ao conectar ao banco de dados. SQLSTATE: {sqlstate}")
        log.info(ex)
        return None


# Bloco de teste: este código só roda quando executamos este arquivo diretamente.
# É uma boa prática para testar a funcionalidade do módulo de forma isolada.
if __name__ == "__main__":
    connection = get_db_connection()
    if connection:
        log.info("Teste de conexão bem-sucedido. Fechando a conexão.")
        connection.close()
    else:
        log.info(
            "Teste de conexão falhou. Verifique as credenciais no .env e a disponibilidade do banco/rede."
        )
