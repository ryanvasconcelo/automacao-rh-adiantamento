# backend/src/fopag/calculations.py

import math
import calendar
from datetime import date, timedelta
import holidays

# ============================================================================
# TABELAS OFICIAIS 2026 - PORTARIA INTERMINISTERIAL MPS/MF Nº 13/2026
# ============================================================================

# Salário Mínimo Nacional 2026
SALARIO_MINIMO_2026 = 1621.00

# INSS 2026 - Tabela Progressiva OFICIAL
# IMPORTANTE: O Fortes usa cálculo PROGRESSIVO (não por dedução)
# Fonte: Portaria Interministerial MPS/MF Nº 13, de 9 de janeiro de 2026
INSS_TETO_2026 = 988.07
INSS_TABLE_2026 = [
    (1621.00, 0.075, 0.00),
    (2902.84, 0.09, 24.30),
    (4354.27, 0.12, 130.59),
    (8475.55, 0.14, 217.60),
]

# Salário Família 2026
TETO_SALARIO_FAMILIA_2026 = 1980.38
VALOR_COTA_SALARIO_FAMILIA_2026 = 67.54

# IRRF 2026 - Tabela com Redutor (Lei 15.270/2025)
IRRF_DEDUCAO_DEPENDENTE_2026 = 189.59
IRRF_TABLE_2026 = [
    (2428.80, 0.0, 0.0),
    (2826.65, 0.075, 182.16),
    (3751.05, 0.15, 394.16),
    (4664.68, 0.225, 675.49),
    (float("inf"), 0.275, 908.73),
]

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
        feriados.append({date(ano, 10, 24): "Aniversário de Manaus"})
        feriados.append({date(ano, 12, 8): "Nossa Senhora da Conceição"})
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
    feriados_qtd = 0
    curr = inicio_c

    while curr <= fim:
        if curr.weekday() == 6:
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
# CÁLCULO DE INSS - PROGRESSIVO 2026 (MÉTODO FORTES)
# ============================================================================


def calc_inss(salario_bruto: float) -> float:
    """
    Calcula INSS progressivo 2026 - MÉTODO FAIXA POR FAIXA.

    Este é o método que o Fortes Sistemas usa:
    - Calcula cada faixa separadamente
    - Arredonda cada faixa (round, não truncate)
    - Soma todas as faixas

    Base VITOR (R$ 7.156,89):
    - Faixa 1: 1621.00 × 7,5% = 121.58
    - Faixa 2: (2902.84 - 1621.00) × 9% = 115.37
    - Faixa 3: (4354.27 - 2902.84) × 12% = 174.17
    - Faixa 4: (7156.89 - 4354.27) × 14% = 392.37
    - TOTAL: 803.49 (aprox 803.46 com arredondamentos)
    """
    if salario_bruto > INSS_TABLE_2026[-1][0]:
        return INSS_TETO_2026

    inss_total = 0.0
    base_anterior = 0.0

    # Cálculo progressivo com arredondamento por faixa
    for limite, aliquota, _ in INSS_TABLE_2026:
        if salario_bruto > base_anterior:
            # Base tributável nesta faixa
            base_faixa = min(salario_bruto, limite) - base_anterior

            # Calcula INSS desta faixa
            inss_faixa = base_faixa * aliquota

            # Arredonda (round) - O Fortes usa round, não truncate
            inss_faixa_arredondado = round(inss_faixa, 2)

            inss_total += inss_faixa_arredondado
            base_anterior = limite

            # Se a base está dentro desta faixa, para
            if salario_bruto <= limite:
                break

    return round(inss_total, 2)


# ============================================================================
# CÁLCULO DE IRRF - 2026 COM REDUTOR (LEI 15.270/2025)
# ============================================================================


def calc_irrf_detalhado(rendimento_bruto: float, inss: float, deps: int) -> dict:
    """
    IRRF 2026 - MÉTODO FORTES CORRETO (DESCOBERTO APÓS ANÁLISE!)
    Lei 15.270/2025

    O Fortes calcula assim (diferente da lei, mas é o que eles fazem):
    1. Calcula base líquida (bruto - inss - deps) → para DETERMINAR A FAIXA
    2. Aplica a ALÍQUOTA da faixa na BASE BRUTA → IRRF Parcial
    3. Deduz R$ 908,73 (dedução fixa) → IRRF antes da Redução
    4. Calcula Redutor usando (BASE BRUTA + INSS)
    5. IRRF Final = IRRF antes Redução - Redutor

    Exemplo Real (Base: 6.547,84; INSS: 794,14; Deps: 0):
    - Base Líquida: 6.547,84 - 794,14 - 0 = 5.753,70
    - Faixa: 27,5% (pois 5.753,70 > 4.664,68)
    - IRRF Parcial: 6.547,84 × 0,275 = 1.800,66
    - Dedução: -908,73
    - IRRF antes Redução: 891,93
    - Base Redutor: 6.547,84 + 794,14 = 7.341,98
    - Redutor: 978,62 - (0,133145 × 7.341,98) = 1,07
    - IRRF Final: 891,93 - 1,07 = 890,86 ✓
    """

    # -----------------------------
    # 1. Base Líquida (para determinar a faixa)
    # -----------------------------
    deducao_dependentes = deps * IRRF_DEDUCAO_DEPENDENTE_2026
    base_liquida = round(rendimento_bruto - inss - deducao_dependentes, 2)

    if base_liquida <= 0:
        return {
            "valor": 0.0,
            "memoria": {
                "tipo": "IRRF 2026 - Fortes",
                "variaveis": [
                    {"nome": "Base IRRF", "valor": f"R$ {rendimento_bruto:,.2f}"},
                    {"nome": "INSS", "valor": f"R$ {inss:,.2f}"},
                    {"nome": "Dependentes", "valor": deps},
                    {"nome": "Base Líquida", "valor": f"R$ {base_liquida:,.2f}"},
                ],
                "resultado": "R$ 0,00 (Isento)",
            },
        }

    # -----------------------------
    # 2. Determina a FAIXA pela base líquida
    # -----------------------------
    if base_liquida <= 2428.80:
        aliquota = 0.0
        faixa_nome = "Isento"
    elif base_liquida <= 2826.65:
        aliquota = 0.075
        faixa_nome = "7,5%"
    elif base_liquida <= 3751.05:
        aliquota = 0.15
        faixa_nome = "15%"
    elif base_liquida <= 4664.68:
        aliquota = 0.225
        faixa_nome = "22,5%"
    else:
        aliquota = 0.275
        faixa_nome = "27,5%"

    # -----------------------------
    # 3. Aplica a ALÍQUOTA na BASE BRUTA (não na líquida!)
    # -----------------------------
    irrf_parcial = round(rendimento_bruto * aliquota, 2)

    # -----------------------------
    # 4. Dedução Fixa de R$ 908,73
    # -----------------------------
    DEDUCAO_FIXA = 908.73
    irrf_antes_reducao = max(0.0, round(irrf_parcial - DEDUCAO_FIXA, 2))

    # -----------------------------
    # 5. Redutor Lei 15.270/2025
    # Base para redutor = BASE BRUTA + INSS (não base líquida!)
    # -----------------------------
    base_para_redutor = round(rendimento_bruto + inss, 2)

    if base_para_redutor <= 5000.00:
        # Isento até R$ 5.000
        redutor = irrf_antes_reducao  # Zera o imposto
        faixa_redutor = "Isento até R$ 5.000"
    elif base_para_redutor <= 7350.00:
        # Redutor decrescente
        redutor_calculado = 978.62 - (0.133145 * base_para_redutor)
        redutor = max(0.0, min(irrf_antes_reducao, round(redutor_calculado, 2)))
        faixa_redutor = "Redutor decrescente (R$ 5.000,01 a R$ 7.350)"
    else:
        # Sem redutor acima de R$ 7.350
        redutor = 0.0
        faixa_redutor = "Sem redutor (> R$ 7.350)"

    # -----------------------------
    # 6. IRRF Final
    # -----------------------------
    irrf_final = max(0.0, round(irrf_antes_reducao - redutor, 2))

    # -----------------------------
    # 7. Memória de Auditoria (igual ao Fortes)
    # -----------------------------
    return {
        "valor": irrf_final,
        "memoria": {
            "tipo": "IRRF 2026 - Fortes",
            "variaveis": [
                {"nome": "Base IRRF", "valor": f"R$ {rendimento_bruto:,.2f}"},
                {"nome": "INSS", "valor": f"R$ {inss:,.2f}"},
                {"nome": "Dependentes", "valor": deps},
                {
                    "nome": "Dedução Dependentes",
                    "valor": f"R$ {deducao_dependentes:,.2f}",
                },
                {"nome": "Base Líquida", "valor": f"R$ {base_liquida:,.2f}"},
                {"nome": "Faixa/Alíquota", "valor": faixa_nome},
                {
                    "nome": "IRRF Parcial (Bruta × Alíq)",
                    "valor": f"R$ {irrf_parcial:,.2f}",
                },
                {
                    "nome": "Dedução Fixa (R$ 908,73)",
                    "valor": f"R$ -{DEDUCAO_FIXA:,.2f}",
                },
                {
                    "nome": "IRRF antes Redução",
                    "valor": f"R$ {irrf_antes_reducao:,.2f}",
                },
                {
                    "nome": "Base p/ Redutor (Bruta+INSS)",
                    "valor": f"R$ {base_para_redutor:,.2f}",
                },
                {"nome": "Faixa Redutor", "valor": faixa_redutor},
                {"nome": "Redutor", "valor": f"R$ {redutor:,.2f}"},
            ],
            "resultado": f"R$ {irrf_final:,.2f}",
        },
    }


# ============================================================================
# CÁLCULO DE FGTS
# ============================================================================


def calc_fgts(base: float, is_aprendiz: bool = False) -> float:
    """Calcula FGTS: 8% para funcionários normais, 2% para aprendizes."""
    aliq = 0.02 if is_aprendiz else 0.08
    return truncate(base * aliq, 2)


# ============================================================================
# CÁLCULOS DE HORAS E ADICIONAIS
# ============================================================================


def calc_he_generica(
    salario_base_he: float, horas: float, percentual: float, divisor: float = 220.0
) -> float:
    """Calcula Hora Extra com base composta (Salário + Adicionais)."""
    salario_hora = salario_base_he / divisor
    fator = 1 + (percentual / 100.0)
    return round(salario_hora * fator * horas, 2)


def calc_adicional_noturno(
    salario_base: float, horas: float, divisor: float = 220.0
) -> float:
    """Calcula Adicional Noturno (20% sobre o salário base)."""
    return round((salario_base / divisor) * 0.20 * horas, 2)


def calc_periculosidade(salario: float) -> float:
    """Calcula adicional de periculosidade (30% do salário base)."""
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
    """Calcula Descanso Semanal Remunerado sobre valores variáveis."""
    if uteis == 0:
        return 0.0
    return round((valor_variavel / uteis) * dsr, 2)


def calc_salario_familia(remuneracao: float, filhos: int) -> float:
    """Calcula salário família 2026."""
    if filhos <= 0:
        return 0.0
    if remuneracao <= TETO_SALARIO_FAMILIA_2026:
        return round(filhos * VALOR_COTA_SALARIO_FAMILIA_2026, 2)
    return 0.0


def calc_vale_transporte(salario: float, percentual: float = 0.06) -> float:
    """Calcula desconto de vale transporte (6% do salário)."""
    return round(salario * percentual, 2)


def calc_falta(salario_base: float, qtd_dias: float) -> float:
    """Calcula desconto de falta em dias."""
    return round((float(salario_base) / 30) * float(qtd_dias), 2)
