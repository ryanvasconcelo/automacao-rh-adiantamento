# backend/src/fopag/calculations.py

import math
import calendar
from datetime import date, timedelta
import holidays

# ==============================================================================
# CONSTANTES E TABELAS - VIGÊNCIA 2026 (Ajustado conforme Print Fortes)
# ==============================================================================

# --- INSS 2026 ---
INSS_TETO = 988.07
INSS_TABLE = [
    (1621.00, 0.075, 0.00),
    (2902.84, 0.09, 22.77),
    (4354.27, 0.12, 106.59),
    (8475.55, 0.14, 190.40),
]

# --- SALÁRIO FAMÍLIA 2026 ---
TETO_SALARIO_FAMILIA = 1980.38
VALOR_COTA_SALARIO_FAMILIA = 67.54

# --- IRRF 2026 ---
# Conforme print: A dedução da última faixa é 908.73
IRRF_DEDUCAO_DEPENDENTE = 189.59

IRRF_TABLE = [
    (2259.20, 0.0, 0.0),
    (2826.65, 0.075, 169.44),
    (3751.05, 0.15, 381.44),
    (4664.68, 0.225, 662.77),
    (float("inf"), 0.275, 908.73),  # Valor exato do print
]

DIVISOR_HORA_PADRAO = 220.0

# ==============================================================================
# HELPERS
# ==============================================================================


def time_to_decimal(entrada) -> float:
    """
    Converte referências de tempo para decimal (horas).
    CORREÇÃO CRÍTICA: Se vier float (ex: 95.00), assume que já são horas.
    Só converte se vier string com ':' (ex: '95:30').
    """
    try:
        # Se já é número, retorna direto (O banco manda 95.0 para 95 horas)
        if isinstance(entrada, (float, int)):
            return float(entrada)

        s_entrada = str(entrada).strip()

        # Se tem dois pontos, é formato hora:minuto
        if ":" in s_entrada:
            partes = s_entrada.split(":")
            h = int(partes[0])
            m = int(partes[1])
            return h + (m / 60.0)

        # Se é string numérica simples, converte para float
        return float(s_entrada)

    except Exception as e:
        print(f"[ERRO] time_to_decimal falhou para '{entrada}': {e}")
        return 0.0


def truncate(number, digits) -> float:
    stepper = 10.0**digits
    return math.trunc(stepper * number) / stepper


# ==============================================================================
# CÁLCULOS
# ==============================================================================


def get_dias_uteis_dsr(ano: int, mes: int, data_admissao: date = None) -> dict:
    try:
        feriados = holidays.Brazil(state="AM", years=ano)
        feriados.append({date(ano, 10, 24): "Aniversário de Manaus"})
        feriados.append({date(ano, 12, 8): "Nossa Senhora da Conceição"})
    except:
        feriados = []

    ultimo_dia = calendar.monthrange(ano, mes)[1]
    inicio = date(ano, mes, 1)
    fim = date(ano, mes, ultimo_dia)
    inicio_contagem = (
        data_admissao
        if (data_admissao and data_admissao.year == ano and data_admissao.month == mes)
        else inicio
    )

    domingos = 0
    feriados_qtd = 0
    curr = inicio_contagem
    while curr <= fim:
        if curr.weekday() == 6:
            domingos += 1
        elif curr in feriados:
            feriados_qtd += 1
        curr += timedelta(days=1)

    dsr = domingos + feriados_qtd
    uteis = ((fim - inicio_contagem).days + 1) - dsr
    if uteis <= 0:
        uteis = 1

    return {"dias_uteis": uteis, "dias_dsr": dsr}


def calc_inss(salario_bruto: float) -> float:
    if salario_bruto > INSS_TABLE[-1][0]:
        return INSS_TETO
    inss = 0.0
    for limite, aliq, deducao in INSS_TABLE:
        if salario_bruto <= limite:
            inss = (salario_bruto * aliq) - deducao
            break
    if inss == 0.0 and salario_bruto > INSS_TABLE[0][0]:
        limite, aliq, deducao = INSS_TABLE[-1]
        inss = (salario_bruto * aliq) - deducao
    return truncate(inss, 2)


def calc_irrf(
    rendimento_bruto_tributavel: float, inss_descontado: float, dependentes: int
) -> float:
    """
    Calcula o IRRF 2026 com redução simplificada.
    Valores validados com o print do Fortes.
    """
    # 1. Base Líquida
    deducao_dep = dependentes * IRRF_DEDUCAO_DEPENDENTE
    base_calculo_liquida = rendimento_bruto_tributavel - inss_descontado - deducao_dep

    # 2. Imposto Parcial (Tabela)
    irrf_parcial = 0.0
    for limite, aliq, deducao in IRRF_TABLE:
        if base_calculo_liquida <= limite:
            irrf_parcial = (base_calculo_liquida * aliq) - deducao
            break

    if base_calculo_liquida > IRRF_TABLE[-2][0]:
        _, aliq_max, deducao_max = IRRF_TABLE[-1]
        irrf_parcial = (base_calculo_liquida * aliq_max) - deducao_max

    irrf_parcial = max(0.0, irrf_parcial)

    # 3. Redução (Lei 15.022/2026)
    reducao = 0.0
    if rendimento_bruto_tributavel <= 5000.00:
        reducao = min(irrf_parcial, 312.89)
    elif rendimento_bruto_tributavel <= 7350.00:
        # Fórmula exata do print: 978,62 - (0,133145 * Renda)
        fator_reducao = 978.62 - (0.133145 * rendimento_bruto_tributavel)
        reducao = max(0.0, fator_reducao)

    irrf_final = max(0.0, irrf_parcial - reducao)

    # Debug no console do backend para validação
    # print(f"DEBUG IRRF: Bruto={rendimento_bruto_tributavel:.2f} BaseLiq={base_calculo_liquida:.2f} Parcial={irrf_parcial:.2f} Reducao={reducao:.2f} Final={irrf_final:.2f}")

    return round(irrf_final, 2)


def calc_fgts(base: float, is_aprendiz: bool = False) -> float:
    aliq = 0.02 if is_aprendiz else 0.08
    return truncate(base * aliq, 2)


# --- CÁLCULOS ---
def _get_salario_hora(salario: float) -> float:
    return salario / DIVISOR_HORA_PADRAO if salario > 0 else 0.0


def calc_he_generica(salario: float, horas: float, percentual: float) -> float:
    """HE com qualquer %."""
    salario_hora = _get_salario_hora(salario)
    fator = 1 + (percentual / 100.0)
    return round(salario_hora * fator * horas, 2)


def calc_adicional_noturno(salario: float, horas: float) -> float:
    return round((_get_salario_hora(salario) * 0.20) * horas, 2)


def calc_periculosidade(salario: float) -> float:
    return round(salario * 0.30, 2)


def calc_dsr(valor_variavel: float, uteis: int, dsr: int) -> float:
    if uteis == 0:
        return 0.0
    return round((valor_variavel / uteis) * dsr, 2)


def calc_salario_familia(remuneracao: float, filhos: int) -> float:
    if filhos <= 0:
        return 0.0
    if remuneracao <= TETO_SALARIO_FAMILIA:
        return round(filhos * VALOR_COTA_SALARIO_FAMILIA, 2)
    return 0.0


def calc_vale_transporte(salario: float, percentual: float = 0.06) -> float:
    return round(salario * percentual, 2)


# Wrappers Legado
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


# ==============================================================================
# FUNÇÕES DE CÁLCULO - BENEFÍCIOS
# ==============================================================================


def calc_vale_transporte(salario_base: float, percentual: float = 0.06) -> float:
    """Calcula o teto do desconto de VT (padrão 6% do Salário Base)."""
    if salario_base <= 0:
        return 0.0

    desconto_vt = salario_base * percentual
    final_value = round(desconto_vt, 2)

    print(f"[Cálculo] VT: Base R$ {salario_base:.2f}, Teto Calculado R$ {final_value}")

    return final_value


def calc_salario_familia(
    remuneracao_mensal: float,
    qtd_filhos: int,
    valor_cota: float = VALOR_COTA_SALARIO_FAMILIA,
) -> float:
    """
    Calcula o Salário Família.
    """
    if qtd_filhos <= 0:
        return 0.0

    if remuneracao_mensal <= TETO_SALARIO_FAMILIA:
        valor_total = qtd_filhos * valor_cota
        print(
            f"[Cálculo] Sal. Família: Renda R$ {remuneracao_mensal:.2f} <= Teto. Cota: R$ {valor_cota}. Total: R$ {valor_total}"
        )
        return round(valor_total, 2)
    else:
        print(
            f"[Cálculo] Sal. Família: Renda R$ {remuneracao_mensal:.2f} > Teto ({TETO_SALARIO_FAMILIA}). Não paga."
        )
        return 0.0


# ==============================================================================
# FUNÇÕES DE CÁLCULO - PENSÃO ALIMENTÍCIA
# ==============================================================================


def calc_pensao_alimenticia(
    total_proventos: float,
    salario_base: float,
    inss: float,
    irrf: float,
    percentual: float,
    caso: int = 1,
) -> float:
    """
    Calcula a Pensão Alimentícia conforme o caso selecionado.
    """
    pct = percentual / 100.0 if percentual > 1.0 else percentual

    if caso == 1:
        valor = round(total_proventos * pct, 2)
        print(
            f"[Cálculo] Pensão (Caso 1 - Bruto): R$ {total_proventos:.2f} * {pct:.2%} = R$ {valor}"
        )

    elif caso == 2:
        base_liquida = total_proventos - inss - irrf
        valor = round(base_liquida * pct, 2)
        print(
            f"[Cálculo] Pensão (Caso 2 - Líquido): R$ {base_liquida:.2f} * {pct:.2%} = R$ {valor}"
        )

    elif caso == 3:
        valor = round(salario_base * pct, 2)
        print(
            f"[Cálculo] Pensão (Caso 3 - Base): R$ {salario_base:.2f} * {pct:.2%} = R$ {valor}"
        )

    else:
        print(f"[ERRO] Caso inválido para pensão: {caso}. Usando Caso 1.")
        valor = round(total_proventos * pct, 2)

    return valor
