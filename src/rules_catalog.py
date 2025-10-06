# src/rules_catalog.py (Versão Definitiva com Todas as Empresas Mapeadas)
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .emp_ids import EMP_ID_MAP, CODE_TO_EMP_ID


@dataclass(frozen=True)
class PayWindow:
    analysis_days: int = 30
    pay_day: int = 20
    process_from_day: int = 15


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
    window: PayWindow = PayWindow()
    policy: GeneralPolicy = GeneralPolicy()
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
    base: Day20RuleSet
    special: Optional[SpecialRoles] = None
    overrides: Dict[str, object] = field(default_factory=dict)
    emp_id: Optional[int] = None


_DAY_20_PADRAO = Day20RuleSet()
_JR_SPECIALS = SpecialRoles()

CATALOG: Dict[str, CompanyRule] = {
    # --- GRUPO JR E CLONES ---
    "JR": CompanyRule("JR", "JR RODRIGUES DP", _DAY_20_PADRAO, special=_JR_SPECIALS),
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
    # --- EMPRESAS COM REGRAS ESPECÍFICAS JÁ MAPEADAS ---
    "ACB": CompanyRule(
        "ACB", "A C B LOCADORA", _DAY_20_PADRAO, overrides={"no_rounding": True}
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
    # --- ATUALIZAÇÃO: A S DA FROTA ADICIONADA COM SUAS REGRAS ---
    "ASDAF": CompanyRule(
        "ASDAF",
        "A S FROTA E CIA LTDA",
        _DAY_20_PADRAO,
        overrides={"calculates_vale_loan": True, "fixed_advance_value": True},
    ),
    # --- RESTANTES EMPRESAS COM REGRA PADRÃO DIA 20 ---
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
    "AMM": CompanyRule("AMM", "AMM SERVICOS", _DAY_20_PADRAO),
    "RPC": CompanyRule("RPC", "REAL PROTEINA", _DAY_20_PADRAO),
    "RIO": CompanyRule("RIO", "RIO NEGRO CERVE", _DAY_20_PADRAO),
    "CMD": CompanyRule("CMD", "CM DISTRIBUIDOR", _DAY_20_PADRAO),
    "MAP": CompanyRule("MAP", "MA DE O PINHEIR", _DAY_20_PADRAO),
    "REM": CompanyRule("REM", "REMBRAZ", _DAY_20_PADRAO),
    "ROL": CompanyRule("ROL", "ROLL PET", _DAY_20_PADRAO),
    "GON": CompanyRule("GON", "GONCALES INDUST", _DAY_20_PADRAO),
    "IMI": CompanyRule("IMI", "INGRID MAIA EIR", _DAY_20_PADRAO),
    "PHY": CompanyRule("PHY", "PHYSIO VIDA", _DAY_20_PADRAO),
    "SUP": CompanyRule("SUP", "SUPPORT NORT", _DAY_20_PADRAO),
    "CSR": CompanyRule("CSR", "CSR REFEIÇÕES", _DAY_20_PADRAO),
    "LUB": CompanyRule("LUB", "LUBRINORTE", _DAY_20_PADRAO),
    "UNI1": CompanyRule("UNI1", "UNIMAR EIRELI", _DAY_20_PADRAO),
    "UNI2": CompanyRule("UNI2", "UNIMAR", _DAY_20_PADRAO),
    "ABF": CompanyRule("ABF", "ABF DISTRIBUIDO", _DAY_20_PADRAO),
    "MAR": CompanyRule("MAR", "MARINARA PIZZAR", _DAY_20_PADRAO),
}


def _apply_emp_ids() -> None:
    for code, empid in CODE_TO_EMP_ID.items():
        if code in CATALOG and empid:
            CATALOG[code] = CompanyRule(
                **{**CATALOG[code].__dict__, "emp_id": int(empid)}
            )
    for code, rule in list(CATALOG.items()):
        if rule.emp_id:
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


def get_company_rule(code: str) -> CompanyRule:
    if code not in CATALOG:
        raise ValueError(f"Empresa não mapeada no catálogo: {code}")
    return CATALOG[code]


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
