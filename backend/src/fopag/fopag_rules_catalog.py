# No NOVO arquivo: backend/src/fopag/fopag_rules_catalog.py

"""
Componente 2: O "Blueprint" (O Catálogo de Regras)

Este arquivo contém duas lógicas principais:
1. EVENT_CATALOG: A "Matriz de Incidência" (traduzida do CSV do stakeholder).
   Define as propriedades de cada evento (Provento/Desconto) e suas
   incidências em impostos (INSS, IRRF, FGTS).
2. COMPANY_CATALOG: A "Configuração por Empresa".
   Define as exceções e parâmetros específicos de cada empresa
   (a parte "hardcoded" da nossa arquitetura híbrida).
"""

from dataclasses import dataclass
from typing import Dict
from typing import Optional

# --- PARTE 1: A MATRIZ DE INCIDÊNCIA (Baseada no Cadastro de Eventos.csv) ---


@dataclass(frozen=True)
class EventProperties:
    """Define as propriedades de um Evento (variável) da folha."""

    code: str
    description: str
    type: str  # "Provento" ou "Desconto"

    # Incidências (o mais importante!)
    incide_inss: bool = False
    incide_irrf: bool = False
    incide_fgts: bool = False


# Este é o nosso CSV "traduzido" para um Dicionário Python
EVENT_CATALOG: Dict[str, EventProperties] = {
    # --- PROVENTOS (SALÁRIO E ADICIONAIS) ---
    "11": EventProperties(
        code="11",
        description="Salário-Base",
        type="Provento",
        incide_inss=True,
        incide_irrf=True,
        incide_fgts=True,
    ),
    "5": EventProperties(
        code="5",
        description="Salário-hora",
        type="Provento",
        incide_inss=True,
        incide_irrf=True,
        incide_fgts=True,
    ),
    "13": EventProperties(
        code="13",
        description="Periculosidade",
        type="Provento",
        incide_inss=True,
        incide_irrf=True,
        incide_fgts=True,
    ),
    "16": EventProperties(
        code="16",
        description="Insalubridade",
        type="Provento",
        incide_inss=True,
        incide_irrf=True,
        incide_fgts=True,
    ),
    "17": EventProperties(
        code="17",
        description="Anuênio",
        type="Provento",
        incide_inss=True,
        incide_irrf=True,
        incide_fgts=True,
    ),
    "30": EventProperties(
        code="30",
        description="Comissões",
        type="Provento",
        incide_inss=True,
        incide_irrf=True,
        incide_fgts=True,
    ),
    "171": EventProperties(
        code="171",
        description="Gorjeta",
        type="Provento",
        incide_inss=True,
        incide_irrf=True,
        incide_fgts=True,
    ),
    # --- HORAS EXTRAS E NOTURNO ---
    "60": EventProperties(
        code="60",
        description="Hora Extra 50%",
        type="Provento",
        incide_inss=True,
        incide_irrf=True,
        incide_fgts=True,
    ),
    "61": EventProperties(
        code="61",
        description="Hora Extra 100%",
        type="Provento",
        incide_inss=True,
        incide_irrf=True,
        incide_fgts=True,
    ),
    "62": EventProperties(
        code="62",
        description="Hora Extra 60%",
        type="Provento",
        incide_inss=True,
        incide_irrf=True,
        incide_fgts=True,
    ),
    "12": EventProperties(
        code="12",
        description="Adicional Noturno",
        type="Provento",
        incide_inss=True,
        incide_irrf=True,
        incide_fgts=True,
    ),
    "50": EventProperties(
        code="50",
        description="Adicional Noturno",
        type="Provento",
        incide_inss=True,
        incide_irrf=True,
        incide_fgts=True,
    ),
    "51": EventProperties(
        code="51",
        description="Adicional Noturno 25%",
        type="Provento",
        incide_inss=True,
        incide_irrf=True,
        incide_fgts=True,
    ),
    "52": EventProperties(
        code="52",
        description="Adicional Noturno 21%",
        type="Provento",
        incide_inss=True,
        incide_irrf=True,
        incide_fgts=True,
    ),
    "49": EventProperties(
        code="49",
        description="DSR",
        type="Provento",
        incide_inss=True,
        incide_irrf=True,
        incide_fgts=True,
    ),
    # --- BENEFÍCIOS E REEMBOLSOS (GERALMENTE NÃO INCIDEM) ---
    "10": EventProperties(
        code="10",
        description="Salário-Família",
        type="Provento",
        incide_inss=False,
        incide_irrf=False,
        incide_fgts=False,
    ),
    "9": EventProperties(
        code="9",
        description="Auxílio-Creche",
        type="Provento",
        incide_inss=False,
        incide_irrf=False,
        incide_fgts=False,
    ),
    "2": EventProperties(
        code="2",
        description="Bolsa-Salário",
        type="Provento",
        incide_inss=True,
        incide_irrf=True,
        incide_fgts=True,
    ),  # Verificar incidência
    "31": EventProperties(
        code="31",
        description="Reembolso salarial",
        type="Provento",
        incide_inss=False,
        incide_irrf=False,
        incide_fgts=False,
    ),
    "32": EventProperties(
        code="32",
        description="Reembolso Gorjeta",
        type="Provento",
        incide_inss=False,
        incide_irrf=False,
        incide_fgts=False,
    ),
    "74": EventProperties(
        code="74",
        description="Reembolso de Gratificação",
        type="Provento",
        incide_inss=False,
        incide_irrf=False,
        incide_fgts=False,
    ),
    "94": EventProperties(
        code="94",
        description="Reembolso VT",
        type="Provento",
        incide_inss=False,
        incide_irrf=False,
        incide_fgts=False,
    ),
    "172": EventProperties(
        code="172",
        description="Ajuda de Custo",
        type="Provento",
        incide_inss=False,
        incide_irrf=False,
        incide_fgts=False,
    ),  # Se < 50% salário
    # --- FÉRIAS E 13º (CÁLCULOS ESPECIAIS) ---
    "110": EventProperties(
        code="110",
        description="Remuneração de Férias",
        type="Provento",
        incide_inss=True,
        incide_irrf=True,
        incide_fgts=True,
    ),
    "111": EventProperties(
        code="111",
        description="1/3 de Férias",
        type="Provento",
        incide_inss=True,
        incide_irrf=True,
        incide_fgts=True,
    ),
    "160": EventProperties(
        code="160",
        description="13º Salário",
        type="Provento",
        incide_inss=True,
        incide_irrf=True,
        incide_fgts=True,
    ),
    "150": EventProperties(
        code="150",
        description="Adiantamento 13º",
        type="Provento",
        incide_inss=False,
        incide_irrf=False,
        incide_fgts=True,
    ),  # Incide FGTS no adiantamento
    # --- MATERNIDADE (PAGO PELO INSS, MAS INCIDE) ---
    "8": EventProperties(
        code="8",
        description="Salário-Maternidade",
        type="Provento",
        incide_inss=True,
        incide_irrf=True,
        incide_fgts=True,
    ),
    "3": EventProperties(
        code="3",
        description="Sal. Maternidade Prorrogação",
        type="Provento",
        incide_inss=True,
        incide_irrf=True,
        incide_fgts=True,
    ),
    # --- OUTROS PROVENTOS ---
    "75": EventProperties(
        code="75",
        description="Bonificação",
        type="Provento",
        incide_inss=True,
        incide_irrf=True,
        incide_fgts=True,
    ),
    "76": EventProperties(
        code="76",
        description="Dif. Salarial",
        type="Provento",
        incide_inss=True,
        incide_irrf=True,
        incide_fgts=True,
    ),
    "120": EventProperties(
        code="120",
        description="PLR",
        type="Provento",
        incide_inss=False,
        incide_irrf=True,
        incide_fgts=False,
    ),  # Regra Específica PLR
    # --- DESCONTOS ---
    "310": EventProperties(code="310", description="INSS", type="Desconto"),
    "311": EventProperties(code="311", description="IRRF", type="Desconto"),
    "300": EventProperties(code="300", description="Adiantamento", type="Desconto"),
    # Faltas e Atrasos (Reduzem Base)
    "321": EventProperties(
        code="321",
        description="Falta",
        type="Desconto",
        incide_inss=True,
        incide_irrf=True,
        incide_fgts=True,
    ),
    "314": EventProperties(
        code="314",
        description="Atrasos",
        type="Desconto",
        incide_inss=True,
        incide_irrf=True,
        incide_fgts=True,
    ),
    "349": EventProperties(
        code="349",
        description="DSR Desconto",
        type="Desconto",
        incide_inss=True,
        incide_irrf=True,
        incide_fgts=True,
    ),
    # Vale Transporte e Refeição (Geralmente não reduzem base, exceto IRRF em casos raros)
    "320": EventProperties(code="320", description="Vale-Transporte", type="Desconto"),
    "319": EventProperties(code="319", description="Vale Refeição", type="Desconto"),
    # Outros Descontos
    "312": EventProperties(
        code="312", description="Contribuição Sindical", type="Desconto"
    ),
    "322": EventProperties(
        code="322", description="Mensalidade Sindical", type="Desconto"
    ),
    "340": EventProperties(
        code="340", description="Pensão Alimentícia", type="Desconto", incide_irrf=True
    ),  # Reduz base de IRRF!
    "301": EventProperties(
        code="301", description="Convenio Drogaria", type="Desconto"
    ),
    "302": EventProperties(
        code="302", description="Assistência Médica", type="Desconto"
    ),
    "127": EventProperties(code="127", description="Consignado", type="Desconto"),
}


@dataclass(frozen=True)
class FopagCompanyRule:
    """Define as exceções e parâmetros de FOPAG para uma empresa."""

    # Parâmetros de Cálculo (Exemplos)
    percentual_vt: float = 0.06  # 6% padrão
    dia_limite_beneficio: int = 20
    valor_cota_salario_familia: float = 62.04  # Valor padrão do governo

    # Módulos de Cálculo (Exemplos)
    # Podemos usar isso para "ligar/desligar" cálculos do Componente 1
    calcula_periculosidade: bool = True
    calcula_insalubridade: bool = True
    usa_calc_inss: bool = True
    usa_calc_irrf: bool = True
    usa_calc_fgts: bool = True

    # Mapeamento de Eventos (O "De-Para")
    # Diz ao auditor qual código do Fortes corresponde a qual evento
    # (No futuro, podemos preencher isso)
    cod_salario_base: str = "11"
    cod_inss: str = "310"
    cod_irrf: str = "311"

    # codigos de H.E.
    cod_he_50: str = "60"
    cod_he_100: str = "61"
    cod_dsr_he: str = "49"

    # codigo de adicional noturno
    cod_adic_noturno: str = "12"
    cod_periculosidade: str = "13"
    cod_desconto_adiantamento: str = "300"
    cod_faltas: str = "321"
    cod_dsr_desconto: str = "349"

    cod_vale_transporte: str = "320"
    cod_vale_refeicao: str = "319"
    cod_salario_familia: str = "10"
    cod_salario_maternidade: str = "8"
    cod_reembolso_salarial: Optional[int] = None


# Este é o catálogo que seu chefe pediu, "hardcoded"
COMPANY_CATALOG: Dict[str, FopagCompanyRule] = {
    "DEFAULT": FopagCompanyRule(),
    # ATUALIZE ESTA PARTE:
    "JR": FopagCompanyRule(
        dia_limite_beneficio=15,
        calcula_insalubridade=False,
        # ADICIONE ESTA LINHA:
        valor_cota_salario_familia=65.00,
    ),
    "CMD": FopagCompanyRule(percentual_vt=0.04),
}


# --- Funções "Getter" (Como o Auditor vai usar este arquivo) ---


def get_event_properties(code: str) -> EventProperties | None:
    """Busca as propriedades de um evento pelo código."""
    return EVENT_CATALOG.get(code)


def get_company_rule(company_code: str) -> FopagCompanyRule:
    """Busca a regra de FOPAG da empresa, ou a regra Padrão."""
    return COMPANY_CATALOG.get(company_code, COMPANY_CATALOG["DEFAULT"])
