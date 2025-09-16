# src/rules_catalog.py (Versão Multi-Empresa)
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .emp_ids import EMP_ID_MAP, CODE_TO_EMP_ID

# As definições de PayWindow, GeneralPolicy, Day15RuleSet, Day20RuleSet permanecem as mesmas...
# (O código anterior foi omitido por brevidade, apenas o CATALOG é alterado)


@dataclass(frozen=True)
class PayWindow:
    """Define a janela de análise e pagamento."""

    analysis_days: int = 30
    pay_day: int = 20  # Padronizando para o dia 20 por enquanto
    process_from_day: int = 15


@dataclass(frozen=True)
class GeneralPolicy:
    """Define políticas gerais de cálculo e elegibilidade."""

    maternity_full_pay: bool = True
    sick_leave_company_days: int = 15
    consignado_provision_pct: float = 0.40
    advance_pct_over_salary: float = 0.40
    min_worked_days_for_eligibility: int = 15  # Regra geral para dia 20
    use_commercial_month_always: bool = True
    use_real_days_on_first_month: bool = True


@dataclass(frozen=True)
class Day20RuleSet:
    """Conjunto de regras base para empresas que pagam no dia 20."""

    window: PayWindow = PayWindow()
    policy: GeneralPolicy = GeneralPolicy()
    admission_receive_until_day: int = 10
    vacation_start_block_until_day: int = 15
    resignation_block_until_day: int = 15


@dataclass(frozen=True)
class SpecialRoles:
    """Define valores fixos para cargos especiais, como na JR."""

    gerente_loja_value: float = 1500.0
    subgerente_loja_value: float = 900.0
    name_overrides: Dict[str, float] = field(
        default_factory=lambda: {"ANA VALESCA LOPES TURIBIO": 1500.0}
    )


@dataclass(frozen=True)
class CompanyRule:
    """Estrutura final que representa todas as regras de uma empresa."""

    code: str
    name: str
    base: Day20RuleSet
    special: Optional[SpecialRoles] = None
    overrides: Dict[str, object] = field(default_factory=dict)
    emp_id: Optional[int] = None


# --- DEFINIÇÃO DOS CONJUNTOS DE REGRAS ---
_DAY_20_PADRAO = Day20RuleSet()
_JR_SPECIALS = SpecialRoles()

# --- CATÁLOGO DE EMPRESAS - DIA 20 ---
CATALOG: Dict[str, CompanyRule] = {
    # --- Padrão JR Rodrigues ---
    "JR": CompanyRule("JR", "JR RODRIGUES DP", _DAY_20_PADRAO, special=_JR_SPECIALS),
    # --- Clones da JR (Grupo Salmo 91) ---
    "REAL": CompanyRule(
        "REAL",
        "REAL COMERCIO DE ARTIGOS DE ARMARINHO LTDA",
        _DAY_20_PADRAO,
        special=_JR_SPECIALS,
    ),
    "JCR": CompanyRule(
        "JCR",
        "GP SALMO 91 - JONIVAL COSTA RODRIGUES",
        _DAY_20_PADRAO,
        special=_JR_SPECIALS,
    ),
    "RSR": CompanyRule(
        "RSR",
        "GP SALMO 91 - (MTZ) R DE S RODRIGUES VARIEDADES LTDA",
        _DAY_20_PADRAO,
        special=_JR_SPECIALS,
    ),
    "JRRV": CompanyRule(
        "JRRV",
        "GP SALMO 91 - (MTZ) J R RODRIGUES VARIEDADES LTDA",
        _DAY_20_PADRAO,
        special=_JR_SPECIALS,
    ),
    # --- Empresas com Regras Padrão Dia 20 ---
    "BERGA1": CompanyRule(
        "BERGA1",
        "BERGA ONE COMERCIO DE PRODUTOS FARMACEUTICOS E HOSPITALARES LTDA",
        _DAY_20_PADRAO,
    ),
    "ACB": CompanyRule("ACB", "A. C. B. LOCADORA DE VEICULOS LTDA", _DAY_20_PADRAO),
    "MTZ-ICM": CompanyRule(
        "MTZ-ICM", "MTZ - ICM INDUSTRIA E COMERCIO DE METAIS LTDA", _DAY_20_PADRAO
    ),
    "LMB": CompanyRule("LMB", "LMB RESTAURANTES LTDA (MATRIZ 0001-37)", _DAY_20_PADRAO),
    "NEYMARX": CompanyRule(
        "NEYMARX", "MATRIZ - NEYMARX COMERCIO DE MATERIAIS LTDA", _DAY_20_PADRAO
    ),
    # --- Empresas com Variações Simples ---
    "BEL": CompanyRule(
        "BEL",
        "BEL MICRO INDUSTRIAL LTDA",
        _DAY_20_PADRAO,
        overrides={"consignado_provision_pct": 0.0},
    ),
    # --- Empresas que precisam de formatação de saída especial (Lógica de cálculo é padrão) ---
    "ANDREY": CompanyRule(
        "ANDREY",
        "ANDREY E SOUZA SERVICOS DE CONSTRUCAO CIVIL LTDA",
        _DAY_20_PADRAO,
        overrides={"output_split_by_lotacao": True},
    ),
    "NEWEN": CompanyRule(
        "NEWEN",
        "NEWEN CONSTRUTORA E INCORPORADORA LTDA",
        _DAY_20_PADRAO,
        overrides={"output_split_by_lotacao": True, "generate_remessa": True},
    ),
    "TET-GESTAO": CompanyRule(
        "TET-GESTAO",
        "T E T GESTAO EMPRESARIAL LTDA",
        _DAY_20_PADRAO,
        overrides={"generate_remessa": True},
    ),
    # --- Empresas que precisarão de NOVOS DADOS (marcadas para o futuro) ---
    "PV": CompanyRule(
        "PV",
        "PV COMERCIO ATACADISTA DE MAQUINAS E EQUIPAMENTOS LTDA",
        _DAY_20_PADRAO,
        overrides={"calculates_periculosidade": True},
    ),
    "BBPE": CompanyRule(
        "BBPE",
        "BBPE SERVICOS DE CONSTRUCAO LTDA",
        _DAY_20_PADRAO,
        overrides={"calculates_periculosidade": True},
    ),
    "EBE": CompanyRule(
        "EBE",
        "EMPRESA BRASILEIRA DE ENERGIA LTDA",
        _DAY_20_PADRAO,
        overrides={"calculates_periculosidade": True},
    ),
    "TRANSF": CompanyRule(
        "TRANSF",
        "TRANSFORMAR LOCACAO DE VEICULOS E SERVICOS AMBIENTAIS LTDA",
        _DAY_20_PADRAO,
        overrides={"calculates_periculosidade": True},
    ),
    "ASDAF": CompanyRule(
        "ASDAF",
        "A S DA FROTA E CIA LTDA",
        _DAY_20_PADRAO,
        overrides={"calculates_vale_loan": True, "fixed_advance_value": True},
    ),
    "MASTER": CompanyRule(
        "MASTER",
        "MASTERFOOD COMERCIO DE ALIMENTOS LTDA. (MATRIZ 0001-00)",
        _DAY_20_PADRAO,
        overrides={"calculates_quebra_caixa": True, "calculates_gratificacao": True},
    ),
    "TPAS": CompanyRule(
        "TPAS",
        "T P A DE SOUZA",
        _DAY_20_PADRAO,
        overrides={"calculates_vale_loan": True},
    ),
    "TKAS": CompanyRule(
        "TKAS",
        "T K A DE SOUZA",
        _DAY_20_PADRAO,
        overrides={"calculates_vale_loan": True},
    ),
    "TET-COM": CompanyRule(
        "TET-COM",
        "MTZ - T E T COMERCIO E INDUSTRIA DE HORTIFRUTIGRANJEIROS LTDA",
        _DAY_20_PADRAO,
        overrides={"generate_remessa": True},
    ),
    # --- Empresas Dia 15 (Mantidas para referência) ---
    "MAR": CompanyRule(
        "MAR",
        "MARINARA PIZZARIA E RESTAURANTE LTDA",
        _DAY_20_PADRAO,
        overrides={"source_from_excel_not_fortes": True, "check_consignado": True},
    ),
    # ... etc
}


# (O restante do arquivo com as funções _apply_emp_ids, get_company_rule, etc., permanece o mesmo)
# -------- Função para aplicar IDs do banco de dados ao catálogo --------
def _apply_emp_ids() -> None:
    # 1) Aplica IDs baseados no código curto (ex: "JR" -> 9098)
    for code, empid in CODE_TO_EMP_ID.items():
        if code in CATALOG and empid:
            # Recria o objeto CompanyRule com o emp_id preenchido
            CATALOG[code] = CompanyRule(
                **{**CATALOG[code].__dict__, "emp_id": int(empid)}
            )

    # 2) Tenta encontrar IDs para as empresas restantes, casando pelo nome completo
    for code, rule in list(CATALOG.items()):
        if rule.emp_id:  # Pula se já encontrou um ID
            continue
        for fortes_name, empid in EMP_ID_MAP.items():
            if not empid:
                continue
            if (
                rule.name.upper() in fortes_name.upper()
                or fortes_name.upper() in rule.name.upper()
            ):
                CATALOG[code] = CompanyRule(**{**rule.__dict__, "emp_id": int(empid)})
                break


_apply_emp_ids()


# --- Funções públicas para acessar o catálogo ---
def get_company_rule(code: str) -> CompanyRule:
    if code not in CATALOG:
        raise ValueError(f"Empresa não mapeada no catálogo: {code}")
    return CATALOG[code]


def get_all_company_names() -> List[str]:
    return [rule.name for rule in CATALOG.values()]


def get_code_by_name(name: str) -> str:
    for code, rule in CATALOG.items():
        if rule.name == name:
            return code
    raise ValueError(f"Nome da empresa não encontrado no catálogo: {name}")


def get_name_by_code(code: str) -> str:
    return get_company_rule(code).name
