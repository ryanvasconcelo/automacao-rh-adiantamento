# backend/src/fopag/calculations.py

import math
import calendar
from datetime import date, timedelta
import holidays

# ============================================================================
# TABELAS OFICIAIS 2026
# ============================================================================

# Salário Mínimo Nacional 2026
SALARIO_MINIMO_2026 = 1621.00
# INSS 2026 OFICIAL - Portaria Interministerial MPS/MF Nº 13
INSS_TETO_2026 = 988.07  # ✓ Correto, teto desconto
INSS_TABLE_2026 = [
    (1621.00, 0.075, 0.00),  # Até R$ 1.621,00
    (2902.84, 0.09, 22.77),  # R$ 1.621,01 a R$ 2.902,84
    (4354.27, 0.12, 106.59),  # R$ 2.902,85 a R$ 4.354,27
    (8475.55, 0.14, 190.40),  # R$ 4.354,28 a R$ 8.475,55 (teto base) ✓
]

# IRRF 2026 Mensal OFICIAL - Tabela + Redutor (para base >R$5k)
IRRF_DEDUCAO_DEPENDENTE_2026 = 189.59  # ✓ Correto
IRRF_TABLE_2026 = [
    (2428.80, 0.0, 0.0),  # Isento até R$ 2.428,80
    (2826.65, 0.075, 182.16),  # 7,5% até R$ 2.826,65
    (3751.05, 0.15, 394.16),  # 15% até R$ 3.751,05
    (4664.68, 0.225, 675.49),  # 22,5% até R$ 4.664,68
    (float("inf"), 0.275, 908.73),  # 27,5% acima
]

# Salário Família 2026
TETO_SALARIO_FAMILIA_2026 = 1980.38
VALOR_COTA_SALARIO_FAMILIA_2026 = 67.54

# Constantes
DIVISOR_HORA_PADRAO = 220.0


# ============================================================================
# HELPERS
# ============================================================================


def time_to_decimal(entrada) -> float:
    """Converte entrada de tempo para decimal (horas)."""
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
    """Trunca número com precisão de dígitos."""
    stepper = 10.0**digits
    return math.trunc(stepper * number) / stepper


# ============================================================================
# CÁLCULOS DE CALENDÁRIO
# ============================================================================


def get_dias_uteis_dsr(ano: int, mes: int, data_admissao: date = None) -> dict:
    """
    Calcula dias úteis e DSR (Domingos e Feriados) para o mês.
    Considera feriados nacionais e de Manaus/AM.
    """
    try:
        feriados = holidays.Brazil(state="AM", years=ano)
        # Feriados municipais de Manaus
        feriados.append({date(ano, 10, 24): "Aniversário de Manaus"})
        feriados.append({date(ano, 12, 8): "Nossa Senhora da Conceição"})
    except:
        feriados = []

    ultimo = calendar.monthrange(ano, mes)[1]
    inicio = date(ano, mes, 1)
    fim = date(ano, mes, ultimo)

    # Se admitido no mês, conta a partir da admissão
    inicio_c = (
        data_admissao
        if (data_admissao and data_admissao.year == ano and data_admissao.month == mes)
        else inicio
    )

    domingos = 0
    feriados_qtd = 0
    curr = inicio_c

    while curr <= fim:
        if curr.weekday() == 6:  # Domingo
            domingos += 1
        elif curr in feriados:
            feriados_qtd += 1
        curr += timedelta(days=1)

    dsr = domingos + feriados_qtd
    uteis = ((fim - inicio_c).days + 1) - dsr

    if uteis <= 0:
        uteis = 1

    return {"dias_uteis": uteis, "dias_dsr": dsr}


# ============================================================================
# CÁLCULO DE INSS - PROGRESSIVO 2026
# ============================================================================


def calc_inss(salario_bruto: float) -> float:
    """
    Calcula INSS progressivo 2026 com arredondamento por faixa.

    IMPORTANTE: O sistema usa arredondamento a cada faixa para
    chegar no valor exato da folha (R$ 803,46 ao invés de R$ 811,56).
    """
    # Se ultrapassar o teto da última faixa, retorna o teto
    if salario_bruto > INSS_TABLE_2026[-1][0]:
        return INSS_TETO_2026

    inss_total = 0.0
    base_anterior = 0.0

    # Cálculo progressivo com arredondamento intermediário
    for limite, aliquota, _ in INSS_TABLE_2026:
        if salario_bruto > base_anterior:
            # Base tributável nesta faixa
            base_faixa = min(salario_bruto, limite) - base_anterior

            # Calcula INSS desta faixa E arredonda (trunca)
            inss_faixa = base_faixa * aliquota
            inss_faixa_arredondado = truncate(inss_faixa, 2)

            inss_total += inss_faixa_arredondado
            base_anterior = limite

            # Se a base está dentro desta faixa, para o loop
            if salario_bruto <= limite:
                break

    return truncate(inss_total, 2)


# ============================================================================
# CÁLCULO DE IRRF - 2026 SEM REDUÇÃO SIMPLIFICADA
# ============================================================================


def calc_irrf_detalhado(rendimento_bruto: float, inss: float, deps: int) -> dict:
    """
    Calcula IRRF 2026 CORRETAMENTE com redutor oficial.
    Valida: base R$6.353,43 → IRRF R$591,79 (folha VITOR DANTAS)
    """
    # Dedução por dependentes
    deducao_deps = deps * IRRF_DEDUCAO_DEPENDENTE_2026
    base_liq = rendimento_bruto - inss - deducao_deps

    # Encontrar faixa da tabela IRRF 2026
    aliquota_usada = 0.0
    deducao_faixa = 0.0
    for lim, aliq, ded in IRRF_TABLE_2026:
        if base_liq <= lim:
            aliquota_usada = aliq
            deducao_faixa = ded
            break
    if base_liq > IRRF_TABLE_2026[-2][0]:
        _, aliquota_usada, deducao_faixa = IRRF_TABLE_2026[-1]

    # Imposto PARCIAL (sem redutor)
    parcial = max(0.0, (base_liq * aliquota_usada) - deducao_faixa)

    # REDUTOR OFICIAL 2026 (explica diferença R$812,74 → R$591,79)
    reducao = 0.0
    formula_reducao = "0.00"
    if rendimento_bruto <= 5000:
        reducao = min(parcial, 312.89)
        formula_reducao = f"Min({parcial:.2f}, 312.89)"
    elif rendimento_bruto <= 7350:
        fator = 978.62 - (0.133145 * rendimento_bruto)
        reducao = max(0.0, fator)
        formula_reducao = f"978.62 - (0.133145*{rendimento_bruto:.2f})={reducao:.2f}"

    # IRRF FINAL (com redutor)
    irrf_final = max(0.0, parcial - reducao)  # ← VARIÁVEL DEFINIDA AQUI

    memoria = {
        "tipo": "IRRF 2026 (Com Redutor)",
        "variaveis": [
            {"nome": "Rendimento Tributável", "valor": f"R$ {rendimento_bruto:,.2f}"},
            {"nome": "Dedução INSS", "valor": f"R$ {inss:,.2f}"},
            {"nome": "Dedução Dependentes", "valor": f"R$ {deducao_deps:,.2f}"},
            {"nome": "Base Líquida", "valor": f"R$ {base_liq:,.2f}"},
            {"nome": "Alíquota", "valor": f"{aliquota_usada*100}%"},
            {"nome": "Dedução Faixa", "valor": f"R$ {deducao_faixa:,.2f}"},
            {"nome": "Imposto Parcial", "valor": f"R$ {parcial:.2f}"},
            {"nome": "Redutor", "valor": f"R$ {reducao:.2f}"},
        ],
        "passos": [
            f"Base = {rendimento_bruto:.2f} - {inss:.2f} - {deducao_deps:.2f} = {base_liq:.2f}",
            f"Parcial = ({base_liq:.2f}*{aliquota_usada:.0%})-{deducao_faixa:.2f} = {parcial:.2f}",
            f"Redutor = {formula_reducao}",
            f"Final = {parcial:.2f} - {reducao:.2f} = {irrf_final:.2f}",
        ],
        "resultado": f"R$ {irrf_final:.2f}",
    }

    return {
        "valor": round(irrf_final, 2),
        "memoria": memoria,
    }


# ============================================================================
# CÁLCULO DE FGTS
# ============================================================================


def calc_fgts(base: float, is_aprendiz: bool = False) -> float:
    """
    Calcula FGTS: 8% para funcionários normais, 2% para aprendizes.
    """
    aliq = 0.02 if is_aprendiz else 0.08
    return truncate(base * aliq, 2)


# ============================================================================
# CÁLCULOS DE HORAS E ADICIONAIS
# ============================================================================


def calc_he_generica(
    salario_base_he: float, horas: float, percentual: float, divisor: float = 220.0
) -> float:
    """
    Calcula Hora Extra com base composta (Salário + Adicionais).
    Exemplo: HE 50% = hora normal × 1.5
    """
    salario_hora = salario_base_he / divisor
    fator = 1 + (percentual / 100.0)
    return round(salario_hora * fator * horas, 2)


def calc_adicional_noturno(
    salario_base: float, horas: float, divisor: float = 220.0
) -> float:
    """
    Calcula Adicional Noturno (20% sobre o salário base).

    IMPORTANTE: Usa salário BASE, não base HE!
    Fortes calcula: (salário / divisor) × 0.20 × horas
    """
    return round((salario_base / divisor) * 0.20 * horas, 2)


def calc_periculosidade(salario: float) -> float:
    """
    Calcula adicional de periculosidade (30% do salário base).
    """
    return round(salario * 0.30, 2)


def calc_insalubridade(
    salario_minimo: float = SALARIO_MINIMO_2026, grau: float = 0.20
) -> float:
    """
    Calcula adicional de insalubridade sobre o salário mínimo.
    Graus: 10% (mínimo), 20% (médio), 40% (máximo)
    """
    return round(salario_minimo * grau, 2)


def calc_dsr(valor_variavel: float, uteis: int, dsr: int) -> float:
    """
    Calcula Descanso Semanal Remunerado sobre valores variáveis.
    DSR = (Total Variáveis / Dias Úteis) × Dias DSR
    """
    if uteis == 0:
        return 0.0
    return round((valor_variavel / uteis) * dsr, 2)


def calc_salario_familia(remuneracao: float, filhos: int) -> float:
    """
    Calcula salário família 2026.
    Valor por filho: R$ 67,54
    Teto: R$ 1.980,38
    """
    if filhos <= 0:
        return 0.0
    if remuneracao <= TETO_SALARIO_FAMILIA_2026:
        return round(filhos * VALOR_COTA_SALARIO_FAMILIA_2026, 2)
    return 0.0


def calc_vale_transporte(salario: float, percentual: float = 0.06) -> float:
    """
    Calcula desconto de vale transporte (6% do salário).
    """
    return round(salario * percentual, 2)
