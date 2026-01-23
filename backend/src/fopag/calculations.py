# backend/src/fopag/calculations.py

import math
import calendar
from datetime import date, timedelta
import holidays

# ==============================================================================
# CONSTANTES E TABELAS - VIGÊNCIA 2026
# ==============================================================================

# --- INSS 2026 ---
INSS_TETO_2026 = 988.07
INSS_TABLE_2026 = [
    (1621.00, 0.075, 0.00),
    (2902.84, 0.09, 22.77),
    (4354.27, 0.12, 106.59),
    (8475.55, 0.14, 190.40),
]

# --- SALÁRIO FAMÍLIA 2026 ---
TETO_SALARIO_FAMILIA_2026 = 1980.38
VALOR_COTA_SALARIO_FAMILIA_2026 = 67.54

# --- IRRF 2026 ---
IRRF_DEDUCAO_DEPENDENTE_2026 = 189.59
IRRF_TABLE_2026 = [
    (2259.20, 0.0, 0.0),
    (2826.65, 0.075, 169.44),
    (3751.05, 0.15, 381.44),
    (4664.68, 0.225, 662.77),
    (float("inf"), 0.275, 908.73),
]

DIVISOR_HORA_PADRAO = 220.0

# ==============================================================================
# HELPERS
# ==============================================================================


def time_to_decimal(entrada) -> float:
    try:
        if isinstance(entrada, (float, int)):
            return float(entrada)
        s = str(entrada).strip()
        if ":" in s:
            h, m = map(int, s.split(":"))
            return h + (m / 60.0)
        return float(s)
    except:
        return 0.0


def truncate(number, digits) -> float:
    stepper = 10.0**digits
    return math.trunc(stepper * number) / stepper


# ==============================================================================
# CÁLCULOS DE CALENDÁRIO (ESSENCIAL PARA DSR)
# ==============================================================================


def get_dias_uteis_dsr(ano: int, mes: int, data_admissao: date = None) -> dict:
    try:
        feriados = holidays.Brazil(state="AM", years=ano)
        # Adicione feriados locais se necessário
    except:
        feriados = []

    ultimo = calendar.monthrange(ano, mes)[1]
    inicio = date(ano, mes, 1)
    fim = date(ano, mes, ultimo)
    inicio_c = (
        data_admissao
        if (data_admissao and data_admissao.year == ano and data_admissao.month == mes)
        else inicio
    )

    domingos = 0
    curr = inicio_c
    while curr <= fim:
        if curr.weekday() == 6:
            domingos += 1
        elif curr in feriados:
            domingos += 1  # Feriado conta como DSR
        curr += timedelta(days=1)

    dsr = domingos
    uteis = ((fim - inicio_c).days + 1) - dsr
    if uteis <= 0:
        uteis = 1

    return {"dias_uteis": uteis, "dias_dsr": dsr}


# ==============================================================================
# CÁLCULOS FINANCEIROS
# ==============================================================================


def calc_inss(salario_bruto: float) -> float:
    if salario_bruto > INSS_TABLE_2026[-1][0]:
        return INSS_TETO_2026
    inss = 0.0
    for limite, aliq, deducao in INSS_TABLE_2026:
        if salario_bruto <= limite:
            inss = (salario_bruto * aliq) - deducao
            break
    if inss == 0.0 and salario_bruto > INSS_TABLE_2026[0][0]:
        l, a, d = INSS_TABLE_2026[-1]
        inss = (salario_bruto * a) - d
    return truncate(inss, 2)


def calc_irrf(renda: float, inss: float, deps: int) -> float:
    base_liq = renda - inss - (deps * IRRF_DEDUCAO_DEPENDENTE_2026)
    parcial = 0.0
    for lim, aliq, ded in IRRF_TABLE_2026:
        if base_liq <= lim:
            parcial = (base_liq * aliq) - ded
            break
    if base_liq > IRRF_TABLE_2026[-2][0]:
        _, aliq, ded = IRRF_TABLE_2026[-1]
        parcial = (base_liq * aliq) - ded

    parcial = max(0.0, parcial)

    reducao = 0.0
    if renda <= 5000:
        reducao = min(parcial, 312.89)
    elif renda <= 7350:
        reducao = max(0.0, 978.62 - (0.133145 * renda))

    return round(max(0.0, parcial - reducao), 2)


def calc_fgts(base: float, aprendiz: bool = False) -> float:
    return truncate(base * (0.02 if aprendiz else 0.08), 2)


def _get_salario_hora(salario: float) -> float:
    return salario / DIVISOR_HORA_PADRAO if salario > 0 else 0.0


def calc_he_generica(salario: float, horas: float, percentual: float) -> float:
    salario_hora = _get_salario_hora(salario)
    fator = 1 + (percentual / 100.0)
    return round(salario_hora * fator * horas, 2)


def calc_adicional_noturno(salario: float, horas: float) -> float:
    return round((_get_salario_hora(salario) * 0.20) * horas, 2)


def calc_periculosidade(salario: float) -> float:
    return round(salario * 0.30, 2)


def calc_dsr(val, uteis, dsr):
    if uteis == 0:
        return 0.0
    return round((val / uteis) * dsr, 2)


def calc_salario_familia(remuneracao: float, filhos: int) -> float:
    if filhos <= 0:
        return 0.0
    if remuneracao <= TETO_SALARIO_FAMILIA_2026:
        return round(filhos * VALOR_COTA_SALARIO_FAMILIA_2026, 2)
    return 0.0


def calc_vale_transporte(salario: float, percentual: float = 0.06) -> float:
    return round(salario * percentual, 2)


# --- Wrappers de Compatibilidade ---
def calc_he_50(salario, horas):
    return calc_he_generica(salario, horas, 50)


def calc_he_100(salario, horas):
    return calc_he_generica(salario, horas, 100)


def calc_adicional_noturno_012(sb, du, dt):
    return round((sb / du) * dt * 0.20, 2)


def calc_adicional_noturno_050(th, vh):
    return round(th * vh * 0.20, 2)


def calc_dsr_desconto(vf, du, dd):
    return round((vf / du) * dd, 2)
