algumas tarefas foram realizadas, mas todas essas ainda estao pendentes

_Lista de Tarefas - Auditor GFS_
seguinte, vamos precisar pegar o valor recebido das ferias para descontar o imposto
Tudo o que acontece numa competência compõe a base de cálculo do INSS, IR e FGTS. Então férias e folha de pagamento devem ser somados totalizando uma base só. Como a folha de pagamento é sempre a última ocorrência de uma competência, o desconto efetivo ocorre nela, abatendo o que já foi "provisionado" de INSS ou IR no recibo de férias.
As rubricas de férias são eventos sim. Não constam no recibo de pagamento da folha, mas constam no recibo de férias.

Por exemplo: Empresa X paga adicional noturno por horas noturnas trabalhadas Funcionaria Gisele teve 2:30 de adicional noturno (formula: salario/220*20%* 2,30) na empresa X vamos usar esse modelo de calculo , já na empresa Y para alguns cargos não informa as horas noturnas trabalhadas , ela paga 20% sobre o salario. (Formula: salario \* 20%)
precisamos captar isso do banco tbm, quando usar uma ou outra formula

- Adicional noturno: Calcular sempre sobre o salário contratual integral, independentemente de descontos ou proporcionalização

- INSS sobre férias: Garantir que as férias integrem corretamente a base de cálculo do INSS
- INSS proporcional: Implementar cálculo de proporcionalidade do INSS conforme dias trabalhados
- Desconto de VT para aprendizes: Aplicar código 323 para desconto proporcional de vale-transporte

- Colocar um sistema básico de autenticacao (o sistema mais básico possivel, que reset a cada 12 horas, nao queremos algo complexo é apenas uma validacao basica de usuario e senha, ate porque se trata de um ambiente interno, entao nao vamos nos demorar nessa feature, ele deve ser a ultima feat a ser implementada, vamos dar prioridade as outras)

Pensão Alimentícia

Alíquotas e Percentuais Específicos

- INSS pró-labore: Aplicar alíquota fixa de 11% para a categoria pró-labore

essas sao as querys necessarias para acessar a tabela de ferias:

## 📊 Tabelas Principais de Férias

### **FER (Férias)**

- Tabela central de férias
- Campos principais: `DTGOZOINICIAL`, `DTGOZOFINAL`, `DTRETORNO`, `DIASABONO`, `EFO_FOL_SEQ`, `EFO_EPG_CODIGO`
- Uso: armazena períodos de gozo de férias dos empregados

### **PAF (Períodos Aquisitivos de Férias)**

- Relaciona férias com períodos aquisitivos
- Campos: `FER_EMP_CODIGO`, `FER_EFO_FOL_SEQ`, `FER_EFO_EPG_CODIGO`, `PAE_DTINICIAL`
- Uso: vincula gozo de férias aos períodos de direito

### **PAE (Períodos Aquisitivos de Empregado)**

- Períodos aquisitivos individuais
- Campos: `DTINICIAL`, `DTFINAL`, `EPG_CODIGO`
- Uso: controla períodos de 12 meses para direito a férias

## 🔗 Tabelas Relacionadas

### **Folha de Pagamento**

- **FOL**: Folhas de pagamento (tipo 4, 5 ou 20 = férias)
- **EFO**: Empregados na folha
- **EFP**: Eventos da folha de pagamento (proventos/descontos)
- **FPG**: Períodos de folha

### **Cadastros Base**

- **EPG**: Empregados (código, nome, CPF, data admissão)
- **SEP**: Situações do empregado (lotação, cargo, vínculo)
- **LOT**: Lotações
- **EST**: Estabelecimentos
- **CAR/SCAR**: Cargos e situações de cargo

### **Eventos de Pagamento**

- **EVE**: Eventos (códigos específicos consultados: 600, 602, 603, 604, 605, 606, 900, 311)
  - 600: Salário contratual
  - 602: Base INSS
  - 603: Base IRRF
  - 604: Base FGTS
  - 605: FGTS
  - 606: FGTS Contrib. Social
  - 900: Multa FGTS

## 📋 Resumo das Queries Principais

### **1. Consulta de Folha de Férias Sintética**

```sql
SELECT FER.*, EFO.*, EPG.NOME, SEP.LOT_CODIGO,
       SUM(EVENTO1.VALOR) AS EVENTO1, ...
FROM FER
JOIN EFO, FOL, EPG, SEP, LOT, SCAR
WHERE FER.DTGOZOINICIAL BETWEEN '12/01/2025' AND '02/03/2026'
AND FOL.FOLHA IN (4, 5, 20)
```

**Propósito**: Listar férias por período com valores de eventos

### **2. Consulta de Listagem de Férias**

```sql
SELECT SEP.LOT_CODIGO, FER.*, EPG.NOME,
       COUNT(PAF.*) AS COUNT_PAF,
       MAX(PAF.PAE_DTINICIAL) AS DTAQUISINICIAL
FROM FER
JOIN EFO, FOL, EPG, SEP, PAF, PAE
WHERE FER.DTGOZOINICIAL BETWEEN datas
```

**Propósito**: Relatório detalhado com períodos aquisitivos

### **3. Cálculo de Competências (CPT)**

```sql
SELECT FER.EFO_EPG_CODIGO,
       SUM(BCFGTS.VALOR) AS BCFGTS,
       SUM(BCINSS.VALOR) AS BCINSS
FROM FER JOIN CPT
```

**Propósito**: Totalizar bases de cálculo por competência

### **4. Consulta de Eventos (EFP)**

```sql
SELECT EFP.*, EVE.NOMEAPR, EVE.INFPROVDESC
FROM FER JOIN EFO JOIN EFP JOIN EVE
WHERE EVE.INFPROVDESC IN ('1', '2')
```

**Propósito**: Listar proventos e descontos das férias

## 🎯 Filtros Aplicados

- **Período**: `DTGOZOINICIAL BETWEEN '12/01/2025' AND '02/03/2026'`
- **Tipo de Folha**: `FOL.FOLHA IN (4, 5, 20)` (Férias, Adiantamento, Rescisão)
- **Estabelecimento**: `EST_CODIGO = '0001'`
- **Empresa**: `EMP_CODIGO = '9098'`
- **Excluir folhas pai**: `FOL.FOL_SEQ_PAI IS NULL`

## 📌 Outras Tabelas Acessadas

- **TOM**: Tomadores de serviço
- **CES**: Categorias eSocial
- **VIN**: Vínculos
- **DEP**: Dependentes
- **CFG/CFE/CFU**: Configurações (geral/empresa/usuário)
- **DICT**: Dicionário de dados (menus recentes, favoritos)
- **SES**: Sessões de usuário
  Próximos 3 passos (futuro):

* Módulo de regras de negócio: Desenvolver módulo centralizado para gestão e aplicação das regras específicas
* Adição de totalizadores: Adicionar valores totais de variáveis vindas do Conecta (horas-extras, atrasos, vale-transporte etc.) - remover fgts e add consignado
* Validar novamente as regras aplicadas.
  Para o modulo de regras
  Atraso nao incide quebra de caixa em algumas empresas
  Premio nao conta nas bases em algumas empresas

exemplo de calculo de ferias, os valores dos impostos (fgts, irrf, inss) sao descontados somente agora, mesmo que os valores das ferias ja tenham sito provisionados

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

O que voce acha disso?
Como seu Líder Técnico, aqui está o meu **Relatório de Análise de Código (Code Review)** e o entendimento do estado atual da arquitetura.

### 📊 1. Diagnóstico Arquitetural Geral

Você construiu uma arquitetura robusta e pragmática.

- **Infraestrutura Híbrida (`database.py`):** A `DatabaseFactory` é excelente. A detecção automática de driver (`pymssql` para Unix/Mac vs `pyodbc` para Windows) resolve o maior pesadelo de quem integra Python com SQL Server legado.
- **Separação de Responsabilidades:**
  - `calculations.py`: Motor matemático puro (Stateless).
  - `fopag_auditor.py`: Regras de negócio, orquestração e "sujeira" do mundo real (tratamento de dados do banco).
  - `router.py`: Camada de transporte (API).
- **Lógica Dinâmica:** O uso de `ev.get("incidencias", {})` no `fopag_auditor.py` confirma que você abandonou as listas fixas (`INSS_EVENTS = [...]`) e está confiando na parametrização do ERP (Tabela `EVE`). Isso é vital para escalabilidade.

---

### 🚨 2. Pontos Críticos de Atenção (A "Divergência de Centavos")

Identifiquei a causa raiz provável das divergências de centavos que você mencionou (INSS/IRRF/Noturno).

**O Problema do `float` no Motor de Cálculo (`calculations.py`):**
Embora o `fopag_auditor.py` use `Decimal` e a função `D()`, o arquivo `calculations.py` está operando quase inteiramente com **floats**.

- _Exemplo:_ `INSS_TABLE_2026` usa `0.075`, `0.09`.
- _Risco:_ Em Python, `0.1 + 0.2` resulta em `0.30000000000000004`.
- _Impacto:_ Quando você calcula `base * 0.075` em float e depois converte para Decimal no auditor, o erro de precisão já ocorreu.
- **Ação Necessária:** Precisamos refatorar `calculations.py` para tipagem estrita com `Decimal`.

### 🔎 3. Análise Específica por Módulo

#### A. Adicional Noturno (`calculations.py` + `auditor`)

- **Lógica Atual:** `(Salario / 220) * 20% * Horas`.
- **Onde pode falhar:**
  1.  **Conversão de Horas:** A função `time_to_decimal` trata `HH:MM`, mas se o Fortes enviar horas em centesimal (ex: 1h30m = 1.50) e o código tratar como relógio, dá erro.
  2.  **Base de Cálculo:** No auditor (V20), vi que você força `base_calc = salario_contratual_cheio`. Isso está correto para mensalistas puros, mas precisamos garantir que periculosidade/insalubridade não deveriam compor a base (a Súmula 60 do TST diz que sim, mas depende da parametrização da empresa).

#### B. INSS 2026 (`calc_inss_progressivo_2026`)

- A lógica de faixas está correta (iterar, calcular o delta, somar).
- **Ponto Forte:** A implementação da memória de cálculo detalhada (`memoria_variaveis`) é excelente para o frontend explicar o "porquê" do valor.
- **Ajuste:** A tabela está com valores `float`. Precisamos converter para `Decimal` para bater o centavo com o Fortes.

#### C. IRRF Híbrido (Lei 15.270/2025)

- Vi que você implementou a lógica do "Redutor Simplificado" vs "Deduções Legais".
- **Observação:** No `fopag_auditor.py`, existe uma lógica de "Best Fit" (Tentativa e Erro) que compara o cálculo usando a Base Bruta vs Base Líquida (`melhor_diff_banco`).
  - _Opinião de Arquiteto:_ Isso é perigoso. É uma "gambiarra inteligente" para fazer bater, mas mascara se a regra real é Bruta ou Líquida. O ideal é determinarmos a regra exata.
- **Pensão Alimentícia:** O tratamento está correto (deduzindo da base antes do cálculo).

---

### 🛠️ 4. Conclusão e Prontidão

Entendi o contexto. O sistema está sólido, mas precisa de **Refinamento de Precisão (Refactoring para Decimal)** e **Validação das Regras de Borda** (IRRF Simplificado).

Estou com o ambiente mental carregado. Pode passar as tarefas.

**Sugestão de ordem de ataque:**

1.  **Refatoração Core:** Converter `calculations.py` para usar `decimal.Decimal` estrito.
2.  **Correção IRRF:** Revisar a regra do Redutor Simplificado para garantir que não estamos dependendo do "Best Fit".
3.  **Adicional Noturno:** Validar a conversão de horas (Centesimal vs Sexagesimal).
