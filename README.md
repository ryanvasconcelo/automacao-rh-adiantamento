CONTENT_PACK

Lição Aprendida / Investigação de Bug (Concluída)
Projeto: Módulo de Auditoria FOPAG Data: 13/11/2025 Assunto: Falha na inicialização do Banco de Dados de Desenvolvimento

1. Contexto do Problema (O que aconteceu?)
O objetivo era criar as tabelas do Banco de Regras (Novo) em um banco de dados de desenvolvimento local (SQLite).

2. Hipóteses e Validação (O que tentamos?)
Nós passamos por uma série de hipóteses, onde cada uma falhou e nos deu uma nova pista:

Hipótese 1: Prisma + SQL Server VM

Tentativa: Conectar ao SQL Server da VM (192.168.0.166).

Resultado: Falha (P1013). A string de conexão do SQL Server (com @ na senha e \ na instância) é frágil e falhou.

Lição: Conectar a um SQL Server de um Mac é complexo e frágil.

Hipótese 2: Prisma + SQLite

Tentativa: Mudar para SQLite (provider = "sqlite").

Resultado: Falha (EngineConnectionError). O "Cliente" (Python) não conseguia se conectar ao "Motor" (binário).

Lição: prisma-client-py é uma camada de abstração que pode falhar em ambientes não-padrão (como Anaconda em Apple M1/M2).

Hipótese 3: SQLAlchemy (Async) + SQLite (Nosso Pivot)

Tentativa: Abandonar o Prisma e usar SQLAlchemy com async (aiosqlite).

Resultado: Falha (unable to open database file).

Lição: Usar um driver async em um script sync (nosso python -m src.rules_db) é excessivamente complexo e falha.

Hipótese 4: SQLAlchemy (Sync) + SQLite (A Solução)

Tentativa: Simplificar para o driver sync (sqlite:///) e um script sync (create_engine).

Resultado: SUCESSO. O log mostra que as tabelas foram criadas.

3. Resolução (O que funcionou?)
O problema foi resolvido por uma simplificação radical do nosso ferramental de criação de banco de dados:

Ferramenta Correta: Usamos SQLAlchemy (100% Python) em vez de Prisma (Python + Binário).

Driver Correto: Usamos o driver síncrono (sqlite:///) para um script de criação síncrono.

Caminho Correto: Usamos um caminho relativo simples (dev.db) em vez de um caminho absoluto complexo (/Users/.../prisma/dev.db), o que resolveu o erro final de permissão unable to open database file.

4. Erros a Evitar no Futuro (As Lições)
YAGNI (You Ain't Gonna Need It): Não devemos usar uma ferramenta async (como aiosqlite) quando uma ferramenta sync simples (como sqlite) resolve o problema (para este script).

KISS (Keep It Simple): A falha do Prisma (EngineConnectionError) foi um sinal para abandonarmos a ferramenta, em vez de tentarmos depurar um binário compilado.