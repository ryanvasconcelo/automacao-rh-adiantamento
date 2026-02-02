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

# INSS 2026 - Tabela Progressiva (Estimativa baseada em Salário Mínimo R$ 1.621)
# Faixas ajustadas para refletir progressão típica
INSS_TETO_2026 = 988.07
INSS_TABLE_2026 = [
    (1621.00, 0.075, 0.00),
    (
        2902.84,
        0.09,
        24.31,
    ),  # (1621 * 0.075) = 121.57. (2902-1621)*0.09=115.36. deducao pra faciltar? Fortes usa progressivo puro.
    (4354.27, 0.12, 130.60),
    (8475.55, 0.14, 217.68),  # Teto de contribuição aumenta
]

# Salário Família 2026
TETO_SALARIO_FAMILIA_2026 = 1980.38
VALOR_COTA_SALARIO_FAMILIA_2026 = 67.54

# IRRF 2026 - Tabela com Redutor (Lei 15.270/2025) - Conforme Print Fortes
IRRF_DEDUCAO_DEPENDENTE_2026 = 189.59
IRRF_TABLE_2026 = [
    (2428.80, 0.0, 0.0),  # Isento até 2428.80
    (2826.65, 0.075, 182.16),  # Deducao 182.16
    (3751.05, 0.15, 394.16),  # Deducao 394.16
    (4664.68, 0.225, 675.49),  # Deducao 675.49
    (float("inf"), 0.275, 908.73),  # Deducao 908.73
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


def calc_inss_progressivo_2026(
    salario_bruto: float, detalhes_base: list = None, abatimentos: list = None
):
    """
    Calcula INSS progressivo 2026 - MÉTODO FORTES.
    Retorna dicionário {valor, memoria}.
    :param salario_bruto: Base total de INSS.
    :param detalhes_base: Lista opcional de dicts {"nome": str, "valor": float} que compõem a base.
    :param abatimentos: Lista opcional de dicts {"nome": str, "valor": float} já descontados (ex: Férias).
    """
    inss_total = 0.0
    base_anterior = 0.0
    memoria_variaveis = []

    # --- 1. DETALHAMENTO DA BASE ---
    if detalhes_base:
        memoria_variaveis.append(
            {
                "nome": "Base de Cálculo",
                "valor": f"R$ {salario_bruto:,.2f}",
                "destaque": True,
            }
        )
        memoria_variaveis.append({"nome": "Eventos da Base de Cálculo", "valor": "---"})
        for item in detalhes_base:
            memoria_variaveis.append(
                {"nome": f"   {item['nome']}", "valor": f"R$ {item['valor']:,.2f}"}
            )
    else:
        memoria_variaveis.append(
            {"nome": "Base de Cálculo", "valor": f"R$ {salario_bruto:,.2f}"}
        )

    memoria_variaveis.append({"nome": "Cálculo Faixa a Faixa", "valor": "---"})

    # Cálculo progressivo com arredondamento por faixa
    for idx, (limite, aliquota, _) in enumerate(INSS_TABLE_2026):
        if salario_bruto > base_anterior:
            # Base tributável nesta faixa
            base_faixa = min(salario_bruto, limite) - base_anterior

            # Calcula INSS desta faixa
            inss_faixa = base_faixa * aliquota
            inss_faixa_arredondado = round(inss_faixa, 2)

            inss_total += inss_faixa_arredondado

            # Registro na memória
            memoria_variaveis.append(
                {
                    "nome": f"Faixa {idx+1} ({base_faixa:,.2f} x {aliquota*100}%)",
                    "valor": f"R$ {inss_faixa_arredondado:,.2f}",
                }
            )

            base_anterior = limite

            # Se a base está dentro desta faixa, para
            if salario_bruto <= limite:
                break

    # Trava no Teto se passar
    if inss_total > INSS_TETO_2026:
        inss_total = INSS_TETO_2026
        memoria_variaveis.append(
            {"nome": "Ajuste Teto Máximo", "valor": f"Limitado a R$ {INSS_TETO_2026}"}
        )

    # --- 2. ABATIMENTOS (INSS JÁ DESCONTADO) ---
    total_abatimentos = 0.0
    if abatimentos:
        memoria_variaveis.append({"nome": "INSS já descontado", "valor": "---"})
        for item in abatimentos:
            valor_abatimento = item["valor"]
            total_abatimentos += valor_abatimento
            memoria_variaveis.append(
                {"nome": f"   {item['nome']}", "valor": f"R$ {valor_abatimento:,.2f} -"}
            )

        inss_total -= total_abatimentos

    inss_final = max(0, round(inss_total, 2))

    return {
        "valor": inss_final,
        "memoria": {
            "tipo": "INSS Progressivo 2026 (Detalhado)",
            "variaveis": memoria_variaveis,
            "resultado": f"R$ {inss_final:,.2f}",
        },
    }


# Wrapper para compatibilidade legado (se necessário em outros pontos que esperam float direto)
def calc_inss(salario_bruto: float) -> float:
    return calc_inss_progressivo_2026(salario_bruto)["valor"]


# ============================================================================
# CÁLCULO DE IRRF - 2026 COM REDUTOR (LEI 15.270/2025)
# ============================================================================


def calc_irrf_detalhado(
    rendimento_input: float, inss: float, deps: int, is_net: bool = False
) -> dict:
    """
    IRRF 2026 - MÉTODO FORTES (Lei 15.270/2025)
    Restaurado conforme solicitação do usuário.
    :param rendimento_input: Salário Bruto (se is_net=False) ou Base Líquida (se is_net=True)
    :param is_net: Se True, considera que rendimento_input já é a base líquida (após INSS/Deps).
    """
    deducao_dependentes = deps * IRRF_DEDUCAO_DEPENDENTE_2026

    if is_net:
        base_liquida = round(rendimento_input, 2)
        # Reconstitui bruto para redutor
        base_para_redutor = round(base_liquida + inss + deducao_dependentes, 2)
        bruto_display = base_para_redutor  # Estimado
    else:
        rendimento_bruto = rendimento_input
        # Nota: A pensão já deve ter sido deduzida do 'rendimento_bruto' pelo auditor antes de chamar esta função.
        base_liquida = round(rendimento_bruto - inss - deducao_dependentes, 2)
        base_para_redutor = round(rendimento_bruto, 2)  # Bruto Original
        bruto_display = rendimento_bruto

    if base_liquida <= 0:
        return {
            "valor": 0.0,
            "memoria": {
                "tipo": "IRRF 2026 - Fortes",
                "variaveis": [
                    {"nome": "Base IRRF (Bruta)", "valor": f"R$ {bruto_display:,.2f}"},
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
    # 3. Aplica a ALÍQUOTA na BASE LÍQUIDA (Confirmado no print Fortes: 4.954,45 * 27,50%)
    # -----------------------------
    irrf_parcial = round(base_liquida * aliquota, 2)

    # -----------------------------
    # 4. Dedução Fixa (Look up na tabela)
    # Precisamos pegar a dedução da faixa correta
    # -----------------------------
    DEDUCAO_FIXA = 0.0
    for lim, aliq, ded in IRRF_TABLE_2026:
        if base_liquida <= lim:
            DEDUCAO_FIXA = ded
            break

    irrf_antes_reducao = max(0.0, round(irrf_parcial - DEDUCAO_FIXA, 2))

    # -----------------------------
    # 5. Redutor Lei 15.270/2025
    # Base para redutor = BASE BRUTA (Rendimentos Tributáveis)
    # Fórmula print: 978,62 - (0,133145 x 5.750,63)
    # -----------------------------

    if base_para_redutor <= 5000.00:
        # Isento até R$ 5.000 (na verdade, redutor anula o imposto)
        # O print diz: "até R$ 5.000,00 ... de modo que imposto seja zero"
        redutor = irrf_antes_reducao
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

    return {
        "valor": irrf_final,
        "memoria": {
            "tipo": "IRRF 2026 - Fortes",
            "variaveis": [
                {"nome": "Base IRRF", "valor": f"R$ {bruto_display:,.2f}"},
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
                    "nome": "Dedução Fixa",
                    "valor": f"R$ -{DEDUCAO_FIXA:,.2f}",
                },
                {
                    "nome": "IRRF antes Redução",
                    "valor": f"R$ {irrf_antes_reducao:,.2f}",
                },
                {
                    "nome": "Base p/ Redutor (Rendimentos Tributáveis)",
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


def calc_fgts(base: float, is_aprendiz: bool = False):
    """Calcula FGTS: 8% para funcionários normais, 2% para aprendizes."""
    aliq = 0.02 if is_aprendiz else 0.08
    valor = truncate(base * aliq, 2)
    return {
        "valor": valor,
        "memoria": {
            "tipo": "FGTS Mensal",
            "variaveis": [
                {"nome": "Base de Cálculo", "valor": f"R$ {base:,.2f}"},
                {"nome": "Categoria", "valor": "Aprendiz" if is_aprendiz else "Normal"},
                {"nome": "Alíquota", "valor": f"{aliq*100:.0f}%"},
            ],
            "resultado": f"R$ {valor:,.2f}",
        },
    }


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


def calc_adicional_noturno(salario_base: float, horas: float, divisor: float = 220.0):
    """Calcula Adicional Noturno (20% sobre o salário base)."""
    val_hora = salario_base / divisor
    valor = round(val_hora * 0.20 * horas, 2)
    return {
        "valor": valor,
        "memoria": {
            "tipo": "Adicional Noturno (20%)",
            "variaveis": [
                {"nome": "Salário Base", "valor": f"R$ {salario_base:,.2f}"},
                {"nome": "Divisor", "valor": f"{divisor}h"},
                {"nome": "Valor Hora", "valor": f"R$ {val_hora:,.2f}"},
                {"nome": "Horas Noturnas", "valor": f"{horas:.2f}h"},
                {"nome": "Percentual", "valor": "20%"},
            ],
            "resultado": f"R$ {valor:,.2f}",
        },
    }


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


def calc_dsr(valor_variaveis, dias_uteis, dias_dsr):
    if dias_uteis == 0:
        return {"valor": 0.0, "memoria": None}

    valor = round((valor_variaveis / dias_uteis) * dias_dsr, 2)
    return {
        "valor": valor,
        "memoria": {
            "tipo": "DSR (Reflexo)",
            "variaveis": [
                {"nome": "Total Variáveis", "valor": f"R$ {valor_variaveis:,.2f}"},
                {"nome": "Dias Úteis", "valor": str(dias_uteis)},
                {"nome": "Dias DSR (Dom/Fer)", "valor": str(dias_dsr)},
            ],
            "resultado": f"R$ {valor:,.2f}",
        },
    }


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


def calc_vt_aprendiz(salario_base: float, dias_trabalhados: int) -> float:
    """
    Calcula VT Proporcional para Aprendiz (Código 323).
    Geralmente 6% sobre o salário proporcional aos dias trabalhados.
    """
    base_prop = (salario_base / 30) * dias_trabalhados
    return round(base_prop * 0.06, 2)
