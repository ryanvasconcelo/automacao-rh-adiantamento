# src/rules_catalog.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Optional, Any
from .emp_ids import CODE_TO_EMP_ID

# --- DEFINIÇÃO DAS ESTRUTURAS (DATACLASSES) ---


@dataclass(frozen=True)
class PayWindow:
    pay_day: int = 20
    process_from_day: int = 15
    use_real_month_days: bool = True


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
class DayRuleSet:
    window: PayWindow
    policy: GeneralPolicy = field(default_factory=GeneralPolicy)
    admission_receive_until_day: int = 10
    vacation_start_block_until_day: int = 15
    resignation_block_until_day: int = 15


@dataclass(frozen=True)
class SpecialRoles:
    gerente_loja_value: float = 1500.0
    subgerente_loja_value: float = 900.0
    name_overrides: Dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class CompanyRule:
    code: str
    name: str
    base: DayRuleSet
    special: Optional[SpecialRoles] = None
    overrides: Dict[str, Any] = field(default_factory=dict)
    emp_id: Optional[int] = None


# --- INSTÂNCIAS PADRÃO ---

_WINDOW_20 = PayWindow(pay_day=20)
_WINDOW_15 = PayWindow(pay_day=15)

_RULE_20 = DayRuleSet(window=_WINDOW_20)
_RULE_15 = DayRuleSet(window=_WINDOW_15)

_JR_SPECIALS = SpecialRoles()

# --- CATÁLOGO DE EMPRESAS ---

CATALOG: Dict[str, CompanyRule] = {
    # EMPRESAS DIA 15
    "TACACA": CompanyRule(
        "TACACA", "TACACÁ DA TIA SOCORRO", _RULE_15, overrides={"no_rounding": True}
    ),
    "AMM": CompanyRule("AMM", "AMM SERVICOS DE APOIO ADMINISTRATIVO LTDA", _RULE_15),
    "RIO": CompanyRule(
        "RIO", "FABRICACAO DE CERVEJAS E CHOPES RIO NEGRO LTDA", _RULE_15
    ),
    "CMD": CompanyRule(
        "CMD",
        "C.M. DISTRIBUIDORA DE ALIMENTOS LTDA - MATRIZ",
        _RULE_15,
        overrides={"no_rounding": True},
    ),
    "MAP": CompanyRule("MAP", "M.A. DE O. PINHEIRO LTDA", _RULE_15),
    "RPC": CompanyRule(
        "RPC",
        "REAL PROTEINA COMERCIO DE CARNES LTDA",
        _RULE_15,
        overrides={"no_rounding": True},
    ),
    "REMBRAZ": CompanyRule(
        "REMBRAZ", "DISTRIBUIDORA COMERCIAL REMBRAZ EIRELI", _RULE_15
    ),
    "ROLL": CompanyRule(
        "ROLL", "ROLL PET INDUSTRIA E COMERCIO DE PLASTICOS LTDA", _RULE_15
    ),
    "GON": CompanyRule(
        "GON", "GONCALES INDUSTRIA E COMERCIO DE PRODUTOS ALIMENTICIOS LTDA", _RULE_15
    ),
    "IMI": CompanyRule("IMI", "INGRID MAIA EIRELI", _RULE_15),
    "PHY": CompanyRule("PHY", "PHYSIO VIDA", _RULE_15),
    "SUP": CompanyRule("SUP", "SUPPORT NORT COMERCIO", _RULE_15),
    "CSR": CompanyRule("CSR", "CSR FORNECIMENTO DE REFEICOES", _RULE_15),
    "LUBRINORTE": CompanyRule("LUBRINORTE", "IMPORTADORA LUBRINORTE LTDA", _RULE_15),
    "UNI1": CompanyRule(
        "UNI1", "UNIMAR - AMAZONAS DESPACHOS ADUANEIROS EIRELI", _RULE_15
    ),
    "UNI2": CompanyRule(
        "UNI2", "UNIMAR - AMAZONAS DESPACHOS ADUANEIROS LTDA", _RULE_15
    ),
    "ABF": CompanyRule("ABF", "ABF DISTRIBUIDORA", _RULE_15),
    # EMPRESAS DIA 20
    "JR": CompanyRule("JR", "JR RODRIGUES DP", _RULE_20, special=_JR_SPECIALS),
    "REAL": CompanyRule(
        "REAL", "REAL COMERCIO DE ARTIGOS", _RULE_20, special=_JR_SPECIALS
    ),
    "JCR": CompanyRule("JCR", "JONIVAL - SL91", _RULE_20, special=_JR_SPECIALS),
    "RSR": CompanyRule("RSR", "GP SALMO 91 - RSR", _RULE_20, special=_JR_SPECIALS),
    "JRRV": CompanyRule("JRRV", "GP SALMO 91 - JRRV", _RULE_20, special=_JR_SPECIALS),
    "ACB": CompanyRule(
        "ACB", "A. C. B. LOCADORA", _RULE_20, overrides={"no_rounding": True}
    ),
    "BEL": CompanyRule(
        "BEL",
        "BEL MICRO INDUSTRIAL LTDA",
        _RULE_20,
        overrides={"consignado_provision_pct": 0.0},
    ),
    "MASTER": CompanyRule(
        "MASTER",
        "MASTERFOOD COMERCIO",
        _RULE_20,
        overrides={"calculates_quebra_caixa": True},
    ),
    "ASDAF": CompanyRule(
        "ASDAF",
        "A S DA FROTA E CIA LTDA",
        _RULE_20,
        overrides={"calculates_vale_loan": True, "fixed_advance_value": True},
    ),
    "BERGA1": CompanyRule("BERGA1", "BERGA ONE COMERCIO", _RULE_20),
    "MTZ-ICM": CompanyRule("MTZ-ICM", "MTZ - ICM INDUSTRIA", _RULE_20),
    "LMB": CompanyRule("LMB", "LMB RESTAURANTES LTDA", _RULE_20),
    "NEYMARX": CompanyRule("NEYMARX", "MATRIZ - NEYMARX", _RULE_20),
    "ANDREY": CompanyRule(
        "ANDREY",
        "ANDREY E SOUZA SERVICOS",
        _RULE_20,
        overrides={"output_split_by_lotacao": True},
    ),
    "NEWEN": CompanyRule(
        "NEWEN",
        "NEWEN CONSTRUTORA",
        _RULE_20,
        overrides={"output_split_by_lotacao": True},
    ),
    "TET-GESTAO": CompanyRule("TET-GESTAO", "T E T GESTAO EMPRESARIAL", _RULE_20),
    "PV": CompanyRule("PV", "PV COMERCIO ATACADISTA", _RULE_20),
    "BBPE": CompanyRule("BBPE", "BBPE SERVICOS DE CONSTRUCAO", _RULE_20),
    "EBRE": CompanyRule("EBRE", "EMPRESA BRASILEIRA DE ENERGIA", _RULE_20),
    "TRANSF": CompanyRule("TRANSF", "TRANSFORMAR LOCACAO", _RULE_20),
    "COPEF": CompanyRule("COPEF", "COPEF CONSTRUCAO LTDA", _RULE_20),
    "TKA": CompanyRule("TKA", "T K A DE SOUZA", _RULE_20),
    "TPA": CompanyRule("TPA", "T P A DE SOUZA", _RULE_20),
    "TET-MTZ": CompanyRule("TET-MTZ", "MTZ - T E T COMERCIO", _RULE_20),
    "SOLAPOWER": CompanyRule("SOLAPOWER", "SOLAPOWER SERVICOS", _RULE_20),
    "PROJECONT-TAX": CompanyRule("PROJECONT-TAX", "PROJECONT TAX SERVICOS", _RULE_20),
}


# --- INJEÇÃO DOS IDS DO SQL ---
def _apply_emp_ids() -> None:
    for code, empid in CODE_TO_EMP_ID.items():
        if code in CATALOG and empid:
            # Clona e atualiza o emp_id
            rule = CATALOG[code]
            # Usando object.__setattr__ para contornar o frozen=True
            object.__setattr__(rule, "emp_id", int(empid))


_apply_emp_ids()


def get_company_rule(empresa_id: str):
    """
    Retorna a regra da empresa. Se não encontrar, retorna uma REGRA PADRÃO (DIA 20)
    que possui a estrutura correta (.base.window.pay_day).
    """
    if empresa_id in CATALOG:
        # print(f">>> Regra encontrada para: {empresa_id}")
        return CATALOG[empresa_id]
    else:
        # print(f">>> AVISO: Empresa {empresa_id} sem regra. Usando Fallback (JR/Dia 20).")
        # Retorna uma cópia da JR ou cria uma nova genérica
        fallback = CompanyRule(
            "FALLBACK", "Regra Padrão (Fallback)", _RULE_20, emp_id=None
        )
        return fallback


# Funções auxiliares mantidas para compatibilidade
def get_code_by_name(name: str) -> str:
    search_name = name.upper().strip()
    for code, rule in CATALOG.items():
        if rule.name.upper().strip() == search_name:
            return code
    return "JR"  # Fallback seguro
