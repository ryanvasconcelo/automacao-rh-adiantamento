# config/logging_config.py

import sys
from loguru import logger

# Remove o handler padrão para evitar duplicação de logs no console.
logger.remove()

# Adiciona um handler para o console com um formato mais limpo e colorido.
# O level="INFO" significa que mensagens de INFO, SUCCESS, WARNING, ERROR, CRITICAL serão mostradas.
logger.add(
    sys.stderr,
    level="INFO",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    colorize=True
)

# Adiciona um handler para salvar os logs em um arquivo.
# 'logs/automacao.log': O arquivo de log será criado dentro de uma nova pasta 'logs'.
# rotation="10 MB": Cria um novo arquivo de log quando o atual atingir 10 MB.
# retention="30 days": Mantém os arquivos de log por no máximo 30 dias, depois os apaga.
# level="DEBUG": Salva tudo no arquivo, desde o nível mais baixo (DEBUG) para depuração detalhada.
logger.add(
    "logs/automacao_{time}.log",
    rotation="10 MB",
    retention="30 days",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
)

# Exporta o logger configurado para ser usado em outros módulos.
log = logger