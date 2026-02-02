meu chapa, perfeito, vamos em frente com o proximo passo de alteracao:

Lógica
- Colocar um sistema básico de autenticacao (o sistema mais básico possivel, que reset a cada 12 horas, nao queremos algo complexo é apenas uma validacao basica de usuario e senha, ate porque se trata de um ambiente interno, entao nao vamos nos demorar nessa feature, ele deve ser a ultima feat a ser implementada, vamos dar prioridade as outras)
- Adicionar totalidade de eventos vindos do conecta - analisar logs - Natureza Total 3 - Vale R$ 1031.66 5 - Hora Extra 100% 668:38h 7 - Adicional Noturno 1016:45h - adicionar totalizador de eventos por empresa na fopag

*Lista de Tarefas - Auditor GFS*
Correções e Ajustes de Base de Cálculo
* Salário-família: Corrigir incidência - o valor de salário-família não deve ser considerado no cálculo do salário base
* IRRF: Incluir dedução de pensão alimentícia nas bases de cálculo do Imposto de Renda Retido na Fonte
* INSS sobre férias: Garantir que as férias integrem corretamente a base de cálculo do INSS
* INSS proporcional: Implementar cálculo de proporcionalidade do INSS conforme dias trabalhados
* Desconto de VT para aprendizes: Aplicar código 323 para desconto proporcional de vale-transporte

Pensão Alimentícia
* Múltiplos códigos de pensão: Expandir captura para incluir código 922 e demais códigos de pensão (não limitar a um único código)

Categorização e Totalização
* Classificação de eventos: Identificar e categorizar cada verba como provento ou desconto
* Totalizadores por funcionário: Calcular e exibir valor total de proventos recebidos e descontos aplicados por colaborador
* Memória de cálculo: Adicionar registro detalhado de memória de cálculo para todos os eventos que não sejam de leitura direta da base de dados

Dependentes
* Filtro de dependentes: Ao buscar dependentes para fins de IRRF e salário-família, aplicar filtro para capturar apenas filhos e enteados

Alíquotas e Percentuais Específicos
* INSS pró-labore: Aplicar alíquota fixa de 11% para a categoria pró-labore
* Adicional noturno: Calcular sempre sobre o salário contratual integral, independentemente de descontos ou proporcionalização

Próximos 3 passos (futuro):
* Módulo de regras de negócio: Desenvolver módulo centralizado para gestão e aplicação das regras específicas
* Adição de totalizadores: Adicionar valores totais de variáveis vindas do Conecta (horas-extras, atrasos, vale-transporte etc.)
* Validar novamente as regras aplicadas.
Para o modulo de regras
Atraso nao incide quebra de caixa em algumas empresas
Premio nao conta nas bases em algumas empresas




Demonstracao
V-Baso do Calculo....2.148,14
    V Eventos da Base de Cálculo.....275,00 =
            Salario-Base 275,00 +
        Férias nesta Competência...1.873,14 +
    INSS Faixa 1: 1.621,00 x 7,5%...................121,57 +
    INSS Faixa 2: (2.148,14 - 1.621,00) = 9,0%......47,44 +
    V-INSS já descontado............................145,81 -
        Férias..................................145,81 +
    INSS Total......................................23,20 =





Categorização de Eventos: Proventos/Descontos funcionando - implementar no frontend

Totalizadores por Funcionário: Implementado (proventos, descontos, líquido) - implementar no frontend

Memória de Cálculo: Implementada para IRRF e INSS - implementar para todos os eventos que sao calculados, sem excecao, se nao for leitura direta, deve ter calculo exibido