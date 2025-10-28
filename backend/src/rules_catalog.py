# src/rules_catalog.py (Versão Definitiva com Todas as Empresas Mapeadas)
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .emp_ids import CODE_TO_EMP_ID


@dataclass(frozen=True)
class PayWindow:
    analysis_days: int = 30  # Obsoleto - será calculado dinamicamente
    pay_day: int = 20
    process_from_day: int = 15
    use_real_month_days: bool = True  # Usar dias reais do mês


@dataclass(frozen=True)
class GeneralPolicy:
    maternity_full_pay: bool = True
    sick_leave_company_days: int = 15
    consignado_provision_pct: float = 0.40
    advance_pct_over_salary: float = 0.40
    min_worked_days_for_eligibility: int = 15
    use_commercial_month_always: bool = True
    use_real_days_on_first_month: bool = True


@dataclass(frozen=True)
class Day20RuleSet:
    window: PayWindow = PayWindow(pay_day=20)
    policy: GeneralPolicy = GeneralPolicy()
    admission_receive_until_day: int = 10
    vacation_start_block_until_day: int = 15
    resignation_block_until_day: int = 15


# NOVO: Conjunto de regras para empresas do dia 15
@dataclass(frozen=True)
class Day15RuleSet:
    window: PayWindow = PayWindow(pay_day=15)
    policy: GeneralPolicy = GeneralPolicy()
    # TODO: Validar se as regras de admissão, férias, etc. são as mesmas do dia 20
    admission_receive_until_day: int = 10
    vacation_start_block_until_day: int = 15
    resignation_block_until_day: int = 15


@dataclass(frozen=True)
class SpecialRoles:
    gerente_loja_value: float = 1500.0
    subgerente_loja_value: float = 900.0
    name_overrides: Dict[str, float] = field(
        default_factory=lambda: {"ANA VALESCA LOPES TURIBIO": 1500.0}
    )


@dataclass(frozen=True)
class CompanyRule:
    code: str
    name: str
    base: Day20RuleSet | Day15RuleSet  # Tipo atualizado
    special: Optional[SpecialRoles] = None
    overrides: Dict[str, object] = field(default_factory=dict)
    emp_id: Optional[int] = None


_DAY_20_PADRAO = Day20RuleSet()
_DAY_15_PADRAO = Day15RuleSet()  # Instância da nova regra
_JR_SPECIALS = SpecialRoles()

CATALOG: Dict[str, CompanyRule] = {
    # --- EMPRESAS DIA 15 ---
    "TACACA": CompanyRule(
        "TACACA",
        "TACACÁ DA TIA SOCORRO",
        _DAY_15_PADRAO,
        overrides={"no_rounding": True},
    ),
    "AMM": CompanyRule(
        "AMM", "AMM SERVICOS DE APOIO ADMINISTRATIVO LTDA", _DAY_15_PADRAO
    ),
    "RIO": CompanyRule(
        "RIO", "FABRICACAO DE CERVEJAS E CHOPES RIO NEGRO LTDA", _DAY_15_PADRAO
    ),
    "CMD": CompanyRule(
        "CMD",
        "C.M. DISTRIBUIDORA DE ALIMENTOS LTDA - MATRIZ",
        _DAY_15_PADRAO,
        overrides={"no_rounding": True},
    ),
    "MAP": CompanyRule("MAP", "M.A. DE O. PINHEIRO LTDA", _DAY_15_PADRAO),
    "RPC": CompanyRule(
        "RPC",
        "REAL PROTEINA COMERCIO DE CARNES LTDA",
        _DAY_15_PADRAO,
        overrides={"no_rounding": True},
    ),
    "REMBRAZ": CompanyRule(
        "REMBRAZ", "DISTRIBUIDORA COMERCIAL REMBRAZ EIRELI", _DAY_15_PADRAO
    ),
    "ROLL": CompanyRule(
        "ROLL", "ROLL PET INDUSTRIA E COMERCIO DE PLASTICOS LTDA", _DAY_15_PADRAO
    ),
    "GON": CompanyRule(
        "GON",
        "GONCALES INDUSTRIA E COMERCIO DE PRODUTOS ALIMENTICIOS LTDA",
        _DAY_15_PADRAO,
    ),
    "IMI": CompanyRule("IMI", "INGRID MAIA EIRELI", _DAY_15_PADRAO),
    "PHY": CompanyRule(
        "PHY",
        "PHYSIO VIDA - HYK SERVICOS DE FISIOTERAPIA E COMERCIO DE ARTIGOS ESPORTIVOS LTDA",
        _DAY_15_PADRAO,
    ),
    "SUP": CompanyRule(
        "SUP",
        "SUPPORT NORT COMERCIO DE EQUIPAMENTOS E COMPONENTES INDUSTRIAIS LTDA",
        _DAY_15_PADRAO, 
    ),
    "CSR": CompanyRule(
        "CSR",
        "CSR FORNECIMENTO DE REFEICOES E SERVICOS EMPRESARIAIS LTDA",
        _DAY_15_PADRAO,
    ),
    "LUBRINORTE": CompanyRule(
        "LUBRINORTE", "IMPORTADORA LUBRINORTE LTDA", _DAY_15_PADRAO
    ),
    "UNI1": CompanyRule(
        "UNI1", "UNIMAR - AMAZONAS DESPACHOS ADUANEIROS EIRELI", _DAY_15_PADRAO
    ),
    "UNI2": CompanyRule(
        "UNI2", "UNIMAR - AMAZONAS DESPACHOS ADUANEIROS LTDA", _DAY_15_PADRAO
    ),
    "ABF": CompanyRule(
        "ABF",
        "ABF DISTRIBUIDORA DE PRODUTOS DE LIMPEZA E ESCRITORIO LTDA",
        _DAY_15_PADRAO,
    ),
    # --- EMPRESAS DIA 20 ---
    "JR": CompanyRule("JR", "JR RODRIGUES DP", _DAY_20_PADRAO, special=_JR_SPECIALS),
    "REAL": CompanyRule(
        "REAL",
        "REAL COMERCIO DE ARTIGOS DE ARMARINHO LTDA",
        _DAY_20_PADRAO,
        special=_JR_SPECIALS,
    ),
    "JCR": CompanyRule("JCR", "JONIVAL - SL91", _DAY_20_PADRAO, special=_JR_SPECIALS),
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
    "ACB": CompanyRule(
        "ACB",
        "A. C. B. LOCADORA DE VEICULOS LTDA",
        _DAY_20_PADRAO,
        overrides={"no_rounding": True},
    ),
    "BEL": CompanyRule(
        "BEL",
        "BEL MICRO INDUSTRIAL LTDA",
        _DAY_20_PADRAO,
        overrides={"consignado_provision_pct": 0.0},
    ),
    "MASTER": CompanyRule(
        "MASTER",
        "MASTERFOOD COMERCIO DE ALIMENTOS LTDA. (MATRIZ 0001-00)",
        _DAY_20_PADRAO,
        overrides={"calculates_quebra_caixa": True, "calculates_gratificacao": True},
    ),
    "ASDAF": CompanyRule(
        "ASDAF",
        "A S DA FROTA E CIA LTDA",
        _DAY_20_PADRAO,
        overrides={"calculates_vale_loan": True, "fixed_advance_value": True},
    ),
    "BERGA1": CompanyRule(
        "BERGA1",
        "BERGA ONE COMERCIO DE PRODUTOS FARMACEUTICOS E HOSPITALARES LTDA",
        _DAY_20_PADRAO,
    ),
    "MTZ-ICM": CompanyRule(
        "MTZ-ICM", "MTZ - ICM INDUSTRIA E COMERCIO DE METAIS LTDA", _DAY_20_PADRAO
    ),
    "LMB": CompanyRule("LMB", "LMB RESTAURANTES LTDA (MATRIZ 0001-37)", _DAY_20_PADRAO),
    "NEYMARX": CompanyRule(
        "NEYMARX", "MATRIZ - NEYMARX COMERCIO DE MATERIAIS LTDA", _DAY_20_PADRAO
    ),
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
    "PV": CompanyRule(
        "PV", "PV COMERCIO ATACADISTA DE MAQUINAS E EQUIPAMENTOS LTDA", _DAY_20_PADRAO
    ),
    "BBPE": CompanyRule("BBPE", "BBPE SERVICOS DE CONSTRUCAO LTDA", _DAY_20_PADRAO),
    "EBRE": CompanyRule("EBRE", "EMPRESA BRASILEIRA DE ENERGIA LTDA", _DAY_20_PADRAO),
    "TRANSF": CompanyRule(
        "TRANSF",
        "TRANSFORMAR LOCACAO DE VEICULOS E SERVICOS AMBIENTAIS LTDA",
        _DAY_20_PADRAO,
    ),
    "COPEF": CompanyRule("COPEF", "COPEF CONSTRUCAO LTDA", _DAY_20_PADRAO),
    "TKA": CompanyRule("TKA", "T K A DE SOUZA", _DAY_20_PADRAO),
    "TPA": CompanyRule("TPA", "T P A DE SOUZA", _DAY_20_PADRAO),
    "TET-MTZ": CompanyRule(
        "TET-MTZ",
        "MTZ - T E T COMERCIO E INDUSTRIA DE HORTIFRUTIGRANJEIROS LTDA",
        _DAY_20_PADRAO,
    ),
    "SOLAPOWER": CompanyRule(
        "SOLAPOWER",
        "SOLAPOWER SERVICOS DE ENGENHARIA E MANUTENCAO LTDA",
        _DAY_20_PADRAO,
    ),
    "PROJECONT-TAX": CompanyRule(
        "PROJECONT-TAX", "PROJECONT TAX SERVICOS DE RECUPERACAO", _DAY_20_PADRAO
    ),
}


def _apply_emp_ids() -> None:
    """Injects the Fortes `emp_id` into each rule in the catalog."""
    for code, empid in CODE_TO_EMP_ID.items():
        if code in CATALOG and empid:
            # Creates a new CompanyRule instance with the emp_id filled in
            CATALOG[code] = CompanyRule(
                **{**CATALOG[code].__dict__, "emp_id": int(empid)}
            )


_apply_emp_ids()


def get_company_rule(code: str) -> CompanyRule:
    if code not in CATALOG:
        raise ValueError(f"Empresa não mapeada no catálogo: {code}")
    rule = CATALOG[code]
    if not rule.emp_id:
        raise ValueError(f"ID da empresa (emp_id) não encontrado para o código: {code}")
    return rule


def get_all_company_names() -> List[str]:
    return [rule.name for rule in CATALOG.values()]


def get_code_by_name(name: str) -> str:
    search_name = name.upper().strip()
    for code, rule in CATALOG.items():
        if rule.name.upper().strip() == search_name:
            return code
    for code, rule in CATALOG.items():
        if search_name in rule.name.upper().strip():
            return code
    raise ValueError(f"Nome da empresa não encontrado no catálogo: {name}")


def get_name_by_code(code: str) -> str:
    return get_company_rule(code).name
