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
# (Baseado em "Cadastro de Eventos.csv")
EVENT_CATALOG: Dict[str, EventProperties] = {
    # --- Proventos ---
    "001": EventProperties(
        code="001",
        description="SALARIO BASE",
        type="Provento",
        incide_inss=True,
        incide_irrf=True,
        incide_fgts=True,
    ),
    "002": EventProperties(
        code="002",
        description="HORA EXTRA 50%",
        type="Provento",
        incide_inss=True,
        incide_irrf=True,
        incide_fgts=True,
    ),
    "003": EventProperties(
        code="003",
        description="HORA EXTRA 100%",
        type="Provento",
        incide_inss=True,
        incide_irrf=True,
        incide_fgts=True,
    ),
    "004": EventProperties(
        code="004",
        description="ADICIONAL NOTURNO",
        type="Provento",
        incide_inss=True,
        incide_irrf=True,
        incide_fgts=True,
    ),
    "005": EventProperties(
        code="005",
        description="DSR S/ HE",
        type="Provento",
        incide_inss=True,
        incide_irrf=True,
        incide_fgts=True,
    ),
    "010": EventProperties(
        code="010",
        description="PERICULOSIDADE",
        type="Provento",
        incide_inss=True,
        incide_irrf=True,
        incide_fgts=True,
    ),
    "020": EventProperties(
        code="020",
        description="PLR",
        type="Provento",
        incide_inss=False,
        incide_irrf=True,
        incide_fgts=False,
    ),  # Exemplo de regra especial
    "050": EventProperties(
        code="050",
        description="FERIAS",
        type="Provento",
        incide_inss=True,
        incide_irrf=True,
        incide_fgts=True,
    ),
    "051": EventProperties(
        code="051",
        description="1/3 FERIAS",
        type="Provento",
        incide_inss=True,
        incide_irrf=True,
        incide_fgts=True,
    ),
    "060": EventProperties(
        code="060",
        description="13o SALARIO",
        type="Provento",
        incide_inss=True,
        incide_irrf=True,
        incide_fgts=True,
    ),
    # --- Descontos ---
    "100": EventProperties(code="100", description="DESCONTO INSS", type="Desconto"),
    "101": EventProperties(code="101", description="DESCONTO IRRF", type="Desconto"),
    "102": EventProperties(code="102", description="FALTAS", type="Desconto"),
    "103": EventProperties(code="103", description="DSR S/ FALTAS", type="Desconto"),
    "104": EventProperties(
        code="104", description="ADIANTAMENTO SALARIAL", type="Desconto"
    ),
    "105": EventProperties(code="105", description="VALE TRANSPORTE", type="Desconto"),
    "106": EventProperties(
        code="106", description="PENSAO ALIMENTICIA", type="Desconto"
    ),
}


# --- PARTE 2: A CONFIGURAÇÃO POR EMPRESA (O "Blueprint") ---


@dataclass(frozen=True)
class FopagCompanyRule:
    """Define as exceções e parâmetros de FOPAG para uma empresa."""

    # Parâmetros de Cálculo (Exemplos)
    percentual_vt: float = 0.06  # 6% padrão
    dia_limite_beneficio: int = 20

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
    cod_salario_base: str = "001"
    cod_he_50: str = "002"
    cod_inss: str = "100"
    cod_irrf: str = "101"


# Este é o catálogo que seu chefe pediu, "hardcoded"
COMPANY_CATALOG: Dict[str, FopagCompanyRule] = {
    # A regra padrão que se aplica a todos
    "DEFAULT": FopagCompanyRule(),
    # Exceção para a Empresa JR
    "JR": FopagCompanyRule(
        dia_limite_beneficio=15,  # Exceção da JR
        calcula_insalubridade=False,  # JR não tem insalubridade
    ),
    # Exceção para a Empresa CMD
    "CMD": FopagCompanyRule(percentual_vt=0.04),  # CMD só desconta 4% (exemplo)
}


# --- Funções "Getter" (Como o Auditor vai usar este arquivo) ---


def get_event_properties(code: str) -> EventProperties | None:
    """Busca as propriedades de um evento pelo código."""
    return EVENT_CATALOG.get(code)


def get_company_rule(company_code: str) -> FopagCompanyRule:
    """Busca a regra de FOPAG da empresa, ou a regra Padrão."""
    return COMPANY_CATALOG.get(company_code, COMPANY_CATALOG["DEFAULT"])
