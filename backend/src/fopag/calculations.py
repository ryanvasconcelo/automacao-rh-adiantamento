import math
import calendar
from datetime import date, timedelta
import holidays

# --- CONSTANTES DE INSS (Vigência 2025 - Base SM R$ 1.621,00) ---
INSS_TABLE_2025 = [
    (1621.00, 0.075, 0.00),
    (2902.84, 0.09, 22.77),
    (4354.27, 0.12, 106.59),
    (8475.55, 0.14, 190.40),
]
INSS_TETO_2025 = 988.07

# --- CONSTANTES DE IRRF (Vigência 2025) ---
IRRF_DEDUCAO_DEPENDENTE_2025 = 189.59
IRRF_TABLE_2025 = [
    (2259.20, 0.0, 0.0),
    (2826.65, 0.075, 169.44),
    (3751.05, 0.15, 381.44),
    (4664.68, 0.225, 662.77),
    (float("inf"), 0.275, 896.00),
]

DIVISOR_HORA_PADRAO = 220.0
PERCENTUAL_DSR_PLACEHOLDER = 0.20

# --- CONSTANTES PARA SALÁRIO FAMÍLIA ---
TETO_SALARIO_FAMILIA = 1980.38
VALOR_COTA_SALARIO_FAMILIA = 67.54


# ==============================================================================
# HELPERS (CONVERSÃO E ARREDONDAMENTO)
# ==============================================================================


def time_to_decimal(entrada) -> float:
    """
    Converte referências de tempo para decimal (horas).
    Ex: "00:30" -> 0.5
    """
    try:
        if isinstance(entrada, (float, int)):
            valor = float(entrada)
            if valor >= 24:
                return valor / 60.0
            return valor

        s_entrada = str(entrada).strip()

        if ":" in s_entrada:
            partes = s_entrada.split(":")
            h = int(partes[0])
            m = int(partes[1])
            return h + (m / 60.0)

        valor = float(s_entrada)
        if valor >= 24:
            return valor / 60.0
        return valor

    except Exception as e:
        print(f"[ERRO] time_to_decimal falhou para entrada '{entrada}': {e}")
        return 0.0


def truncate(number, digits) -> float:
    """
    Trunca um número para uma quantidade específica de casas decimais
    sem arredondar para cima.
    Ex: truncate(150.058, 2) -> 150.05 (round daria 150.06)
    """
    stepper = 10.0**digits
    return math.trunc(stepper * number) / stepper


# ==============================================================================
# LÓGICA DE CALENDÁRIO
# ==============================================================================
def get_dias_uteis_dsr(ano: int, mes: int, data_admissao: date = None) -> dict:
    """
    Calcula dias úteis e DSR (Domingos + Feriados) considerando feriados de Manaus/AM.
    """
    feriados = holidays.Brazil(state="AM", years=ano)
    feriados.append({date(ano, 10, 24): "Aniversário de Manaus"})
    feriados.append({date(ano, 12, 8): "Nossa Senhora da Conceição"})

    ultimo_dia_mes = calendar.monthrange(ano, mes)[1]
    data_inicio_mes = date(ano, mes, 1)
    data_fim_mes = date(ano, mes, ultimo_dia_mes)

    is_admissao_mes = False
    data_inicio_contagem = data_inicio_mes

    if data_admissao and data_admissao.year == ano and data_admissao.month == mes:
        is_admissao_mes = True
        data_inicio_contagem = data_admissao

    qtd_domingos = 0
    qtd_feriados = 0

    current_date = data_inicio_contagem
    while current_date <= data_fim_mes:
        is_domingo = current_date.weekday() == 6
        is_feriado = current_date in feriados

        if is_domingo:
            qtd_domingos += 1
        elif is_feriado:
            qtd_feriados += 1

        current_date += timedelta(days=1)

    total_dsr = qtd_domingos + qtd_feriados

    if is_admissao_mes:
        dias_totais_contrato = (data_fim_mes - data_inicio_contagem).days + 1
        dias_uteis = dias_totais_contrato - total_dsr
    else:
        dias_uteis = 30 - total_dsr

    if dias_uteis <= 0:
        dias_uteis = 1

    print(f"[Calendário] {mes}/{ano}: Úteis={dias_uteis}, DSR={total_dsr}")

    return {"dias_uteis": dias_uteis, "dias_dsr": total_dsr}


# ==============================================================================
# FUNÇÕES DE CÁLCULO - IMPOSTOS
# ==============================================================================


def calc_inss(salario_bruto: float) -> float:
    """Calcula o valor do INSS (TRUNCANDO na 2ª casa)."""
    if salario_bruto >= 7786.02:
        return INSS_TETO_2025

    inss_calculado = 0.0
    for limite, aliquota, deducao in INSS_TABLE_2025:
        if salario_bruto <= limite:
            inss_calculado = (salario_bruto * aliquota) - deducao
            break

    if inss_calculado == 0.0:
        limite, aliquota, deducao = INSS_TABLE_2025[-1]
        inss_calculado = (salario_bruto * aliquota) - deducao

    # ALTERAÇÃO: Usar truncate para bater com o Fortes
    final_value = truncate(inss_calculado, 2)
    print(f"[Cálculo] INSS: Base R$ {salario_bruto:.2f}, Calculado R$ {final_value}")
    return final_value


def calc_irrf(
    base_bruta_irrf: float, inss_descontado: float, dependentes: int
) -> float:
    """Calcula o valor do IRRF (Arredondamento padrão)."""
    deducao_dependentes = dependentes * IRRF_DEDUCAO_DEPENDENTE_2025
    base_de_calculo_irrf = base_bruta_irrf - inss_descontado - deducao_dependentes

    irrf_calculado = 0.0
    for limite, aliquota, deducao in IRRF_TABLE_2025:
        if base_de_calculo_irrf <= limite:
            irrf_calculado = (base_de_calculo_irrf * aliquota) - deducao
            break

    final_value = round(irrf_calculado, 2)
    print(
        f"[Cálculo] IRRF: Base Líquida R$ {base_de_calculo_irrf:.2f}, Calculado R$ {final_value}"
    )

    return max(0.0, final_value)


def calc_fgts(base_de_calculo_fgts: float, is_aprendiz: bool = False) -> float:
    """
    Calcula o FGTS (TRUNCANDO na 2ª casa).
    """
    aliquota = 0.02 if is_aprendiz else 0.08
    # ALTERAÇÃO: Truncar para evitar arredondamento para cima em dízimas
    fgts_calculado = truncate(base_de_calculo_fgts * aliquota, 2)

    tipo = "Aprendiz (2%)" if is_aprendiz else "Normal (8%)"
    print(
        f"[Cálculo] FGTS [{tipo}]: Base R$ {base_de_calculo_fgts:.2f}, Calculado R$ {fgts_calculado}"
    )

    return fgts_calculado


# ==============================================================================
# FUNÇÕES DE CÁLCULO - HORAS E ADICIONAIS
# ==============================================================================


def _get_salario_hora(salario_base: float) -> float:
    """Função auxiliar para calcular o valor da hora."""
    if salario_base == 0:
        return 0.0
    return salario_base / DIVISOR_HORA_PADRAO


def calc_he_50(salario_base: float, total_horas: float) -> float:
    """Calcula o valor da Hora Extra 50%."""
    salario_hora = _get_salario_hora(salario_base)
    valor_he_50 = (salario_hora * 1.5) * total_horas

    final_value = round(valor_he_50, 2)
    print(
        f"[Cálculo] HE 50%: Salário-Hora R$ {salario_hora:.2f}, Horas {total_horas}, Calculado R$ {final_value}"
    )

    return final_value


def calc_he_100(salario_base: float, total_horas: float) -> float:
    """Calcula o valor da Hora Extra 100%."""
    salario_hora = _get_salario_hora(salario_base)
    valor_he_100 = (salario_hora * 2.0) * total_horas

    final_value = round(valor_he_100, 2)
    print(
        f"[Cálculo] HE 100%: Salário-Hora R$ {salario_hora:.2f}, Horas {total_horas}, Calculado R$ {final_value}"
    )

    return final_value


def calc_adicional_noturno(salario_base: float, total_horas: float) -> float:
    """
    Calcula o valor do Adicional Noturno (20% sobre a hora normal).
    """
    salario_hora = _get_salario_hora(salario_base)
    valor_adicional = (salario_hora * 0.20) * total_horas

    final_value = round(valor_adicional, 2)
    print(
        f"[Cálculo] Adic. Noturno: Salário-Hora R$ {salario_hora:.2f}, Horas {total_horas}, Calculado R$ {final_value}"
    )

    return final_value


def calc_adicional_noturno_012(
    salario_base: float, dias_uteis: int, dias_trabalhados: int
) -> float:
    """
    Calcula o Adicional Noturno 012 (incide sobre salário contratual).
    """
    if dias_uteis == 0:
        return 0.0

    valor_dia = salario_base / dias_uteis
    valor_adicional = valor_dia * dias_trabalhados * 0.20

    final_value = round(valor_adicional, 2)
    print(
        f"[Cálculo] Adic. Noturno 012 (s/ Salário): Base R$ {salario_base:.2f}, Dias {dias_trabalhados}, Calculado R$ {final_value}"
    )

    return final_value


def calc_adicional_noturno_050(total_horas: float, valor_hora: float) -> float:
    """
    Calcula o Adicional Noturno 050 (incide sobre horas trabalhadas).
    """
    valor_adicional = total_horas * valor_hora * 0.20

    final_value = round(valor_adicional, 2)
    print(
        f"[Cálculo] Adic. Noturno 050 (s/ Horas): Horas {total_horas}, Valor/Hora R$ {valor_hora:.2f}, Calculado R$ {final_value}"
    )

    return final_value


def calc_periculosidade(salario_base: float) -> float:
    """Calcula a Periculosidade (30% sobre o Salário Base)."""
    valor_periculosidade = salario_base * 0.30

    final_value = round(valor_periculosidade, 2)
    print(
        f"[Cálculo] Periculosidade: Salário Base R$ {salario_base:.2f}, Calculado R$ {final_value}"
    )

    return final_value


# ==============================================================================
# FUNÇÕES DE CÁLCULO - DSR
# ==============================================================================


def calc_dsr(base_valor: float, dias_uteis: int, dias_dsr: int) -> float:
    """
    Calcula o DSR (Descanso Semanal Remunerado) - Código 49.
    """
    if base_valor <= 0 or dias_uteis == 0:
        return 0.0

    dsr_calculado = (base_valor / dias_uteis) * dias_dsr

    final_value = round(dsr_calculado, 2)
    print(
        f"[Cálculo] DSR (49): Base R$ {base_valor:.2f} | Úteis: {dias_uteis} | DSRs: {dias_dsr} | Resultado R$ {final_value}"
    )

    return final_value


def calc_dsr_desconto(
    valor_total_faltas: float, dias_uteis: int, dias_dsr: int
) -> float:
    """
    Calcula o Desconto de DSR com base no valor total das Faltas.
    """
    if valor_total_faltas <= 0 or dias_uteis == 0:
        return 0.0

    dsr_desconto = (valor_total_faltas / dias_uteis) * dias_dsr

    final_value = round(dsr_desconto, 2)
    print(
        f"[Cálculo] DSR Desconto: Base Faltas R$ {valor_total_faltas:.2f}, Calculado R$ {final_value}"
    )

    return final_value


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
