meu chapa, perfeito, vamos em frente com o proximo passo de alteracao:

Lógica
- Colocar um sistema básico de autenticacao (o sistema mais básico possivel, que reset a cada 12 horas, nao queremos algo complexo é apenas uma validacao basica de usuario e senha, ate porque se trata de um ambiente interno, entao nao vamos nos demorar nessa feature, ele deve ser a ultima feat a ser implementada, vamos dar prioridade as outras)
- Adicionar totalidade de eventos vindos do conecta - analisar logs - Natureza Total 3 - Vale R$ 1031.66 5 - Hora Extra 100% 668:38h 7 - Adicional Noturno 1016:45h - adicionar totalizador de eventos por empresa na fopag

Correcoes

Falta: o sistema ainda nao consegue diferenciar se o valor de falta é em dias ou é em horas, aparentemente os valores de faltam em dias e falta em horas vem do mesmo lugar e o nosso auditor nao consegue diferenciar, temos que trabalhar em cima disso  salario família, o valor do salario família esta definido no código, mas ele nao esta sendo atribuído, temos que capturar do banco quantos dependentes o funcionário tem aparentemente

IRRF - nao sei por que esta errado

Descanso Semanal Remunerado: tbm n sei exatamente porque esta errado


Insalubridade: temos que fazer o sistema capturar do banco a porcentagem exata da insalubridade (geralmente 20 ou 40%)

Hora Extra 50% estao com uma leve divergência, nao sei a origem ainda
Hora Extra 100% estao com uma leve divergência, nao sei a origem ainda


mapear insalubridade
Vale transporte fixo ou percentual
Dependentes do salario familia
Diferenciar falta em horas e falta em dias


Como se calcular o irrf?
Estou enviando a lista de tarefas/ajustes/melhorias que definimos em nossa última reunião. Vamos fazer um checklist delas na próxima reunião para garantir que todas elas foram aplicadas a versão oficial do Auditor GFS
Esta será uma rotina padrão nos nossos encontros, a fim de termos transparência e clareza sobre o progresso que estamos realizando no Projeto. Se alguma das tarefas não estiver conforme o que foi discutido, por gentileza, comuniquem ao nosso time aqui neste grupo mesmo

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











