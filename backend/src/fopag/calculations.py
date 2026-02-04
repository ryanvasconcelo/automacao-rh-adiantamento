# backend/src/fopag/calculations.py

import math
import calendar
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
import holidays

# ============================================================================
# HELPER DECIMAL
# ============================================================================

def D(valor):
    """Converte para Decimal de forma segura."""
    if valor is None:
        return Decimal("0.00")
    if isinstance(valor, Decimal):
        return valor
    return Decimal(str(valor))

def money_round(valor_decimal):
    """Arredonda Decimal para 2 casas."""
    if not isinstance(valor_decimal, Decimal):
        valor_decimal = D(valor_decimal)
    return valor_decimal.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

# ============================================================================
# TABELAS OFICIAIS 2026 - PORTARIA INTERMINISTERIAL MPS/MF Nº 13/2026
# ============================================================================

# Salário Mínimo Nacional 2026
SALARIO_MINIMO_2026 = D("1621.00")

# INSS 2026 - Tabela Progressiva (Estimativa baseada em Salário Mínimo R$ 1.621)
# Faixas ajustadas para refletir progressão típica
INSS_TETO_2026 = D("988.07")
INSS_TABLE_2026 = [
    (D("1621.00"), D("0.075"), D("0.00")),
    (D("2902.84"), D("0.09"), D("24.31")),
    (D("4354.27"), D("0.12"), D("130.60")),
    (D("8475.55"), D("0.14"), D("217.68")),  # Teto de contribuição aumenta
]

# Salário Família 2026
TETO_SALARIO_FAMILIA_2026 = D("1980.38")
VALOR_COTA_SALARIO_FAMILIA_2026 = D("67.54")

# IRRF 2026 - Tabela com Redutor (Lei 15.270/2025)
IRRF_DEDUCAO_DEPENDENTE_2026 = D("189.59")
IRRF_TABLE_2026 = [
    (D("2428.80"), D("0.0"), D("0.0")),      
    (D("2826.65"), D("0.075"), D("182.16")), 
    (D("3751.05"), D("0.15"), D("394.16")),  
    (D("4664.68"), D("0.225"), D("675.49")), 
    (float("inf"), D("0.275"), D("908.73")), # Infinito ok ficar como float/object, a logica trata
]

# Constantes
DIVISOR_HORA_PADRAO = D("220.0")


# ============================================================================
# HELPERS
# ============================================================================


def time_to_decimal(entrada) -> Decimal:
    """Converte entrada de tempo para decimal (horas)."""
    try:
        if isinstance(entrada, (float, int, Decimal)):
            return D(entrada)
        s = str(entrada).strip()
        if ":" in s:
            h, m = map(int, s.split(":"))
            return D(h) + (D(m) / D("60.0"))
        return D(s)
    except:
        return D("0.0")


def truncate(number, digits) -> Decimal:
    """Trunca número com precisão de dígitos (retorna Decimal)."""
    # Em Decimal, quantize com ROUND_DOWN funciona como truncate se for positivo
    # Mas para ser fiel à lógica matemática simples:
    if not isinstance(number, Decimal):
        number = D(number)
    
    stepper = D(10) ** digits
    truncated = math.trunc(stepper * number) / stepper
    return D(truncated)


# ============================================================================
# CÁLCULOS DE CALENDÁRIO
# ============================================================================


def get_dias_uteis_dsr(ano: int, mes: int, data_admissao: date = None) -> dict:
    """
    Calcula dias úteis e DSR (Domingos e Feriados) para o mês.
    Considera feriados nacionais e de Manaus/AM.
    """
    try:
        feriados_obj = holidays.Brazil(state="AM", years=ano)
        # Fixando feriados adicionais manuais se necessário
        feriados_obj.append({date(ano, 10, 24): "Aniversário de Manaus"})
        feriados_obj.append({date(ano, 12, 8): "Nossa Senhora da Conceição"})
    except:
        feriados_obj = []

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

    # Otimização: se feriados_obj for dict/list, checagem rápida
    while curr <= fim:
        if curr.weekday() == 6:
            domingos += 1
        elif curr in feriados_obj:
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


def calc_inss_progressivo_2026(salario_bruto, detalhes_base: list = None, abatimentos: list = None):
    """
    Calcula INSS progressivo 2026 - MÉTODO FORTES.
    Todas as entradas e saídas são Decimal.
    """
    salario_bruto = D(salario_bruto)
    
    inss_total = D("0.00")
    base_anterior = D("0.00")
    memoria_variaveis = []
    
    # --- 1. DETALHAMENTO DA BASE ---
    if detalhes_base:
        memoria_variaveis.append({"nome": "Base de Cálculo", "valor": f"R$ {salario_bruto:,.2f}", "destaque": True})
        memoria_variaveis.append({"nome": "Eventos da Base de Cálculo", "valor": "---"})
        for item in detalhes_base:
             val = D(item['valor'])
             memoria_variaveis.append({"nome": f"   {item['nome']}", "valor": f"R$ {val:,.2f}"})
    else:
        memoria_variaveis.append({"nome": "Base de Cálculo", "valor": f"R$ {salario_bruto:,.2f}"})
        
    memoria_variaveis.append({"nome": "Cálculo Faixa a Faixa", "valor": "---"})

    # Cálculo progressivo com arredondamento por faixa
    for idx, (limite, aliquota, _) in enumerate(INSS_TABLE_2026):
        if salario_bruto > base_anterior:
            # Base tributável nesta faixa
            base_faixa = min(salario_bruto, limite) - base_anterior
            
            # Calcula INSS desta faixa
            inss_faixa = base_faixa * aliquota
            inss_faixa_arredondado = money_round(inss_faixa)
            
            inss_total += inss_faixa_arredondado
            
            # Registro na memória
            memoria_variaveis.append({
                "nome": f"Faixa {idx+1} ({base_faixa:,.2f} x {aliquota*100}%)", 
                "valor": f"R$ {inss_faixa_arredondado:,.2f}"
            })

            base_anterior = limite

            # Se a base está dentro desta faixa, para
            if salario_bruto <= limite:
                break
                
    # Trava no Teto se passar
    if inss_total > INSS_TETO_2026:
        inss_total = INSS_TETO_2026
        memoria_variaveis.append({"nome": "Ajuste Teto Máximo", "valor": f"Limitado a R$ {INSS_TETO_2026}"})

    # --- 2. ABATIMENTOS (INSS JÁ DESCONTADO) ---
    total_abatimentos = D("0.00")
    if abatimentos:
        memoria_variaveis.append({"nome": "INSS já descontado", "valor": "---"})
        for item in abatimentos:
            valor_abatimento = D(item['valor'])
            total_abatimentos += valor_abatimento
            memoria_variaveis.append({"nome": f"   {item['nome']}", "valor": f"R$ {valor_abatimento:,.2f} -"})
        
        inss_total -= total_abatimentos

    inss_final = max(D("0.00"), money_round(inss_total))
    
    return {
        "valor": inss_final,
        "memoria": {
            "tipo": "INSS Progressivo 2026 (Detalhado)",
            "variaveis": memoria_variaveis,
            "resultado": f"R$ {inss_final:,.2f}"
        }
    }
    
def calc_inss(salario_bruto) -> Decimal:
    """Wrapper simples."""
    return calc_inss_progressivo_2026(salario_bruto)["valor"]


# ============================================================================
# CÁLCULO DE IRRF - 2026 COM REDUTOR (LEI 15.270/2025)
# ============================================================================

def calc_irrf_detalhado(rendimento_input, inss, deps: int, pensao, is_net: bool = False, base_redutor_override=None) -> dict:
    """
    IRRF 2026 - MÉTODO FORTES (Lei 15.270/2025)
    Usa Decimal.
    """
    rendimento_input = D(rendimento_input)
    inss = D(inss)
    pensao = D(pensao)
    d_deps = D(deps)
    
    deducao_dependentes = d_deps * IRRF_DEDUCAO_DEPENDENTE_2026
    
    if is_net:
        base_liquida = money_round(rendimento_input)
        # Reconstitui bruto para redutor (aproximado)
        base_para_redutor = money_round(base_liquida + inss + deducao_dependentes + pensao)
        bruto_display = base_para_redutor 
    else:
        rendimento_bruto = rendimento_input
        # Deduz INSS, Deps e PENSÃO
        base_liquida = money_round(rendimento_bruto - inss - deducao_dependentes - pensao)
        base_para_redutor = money_round(rendimento_bruto) 
        bruto_display = rendimento_bruto

    # OVERRIDE: Se o usuário especificou uma base para o redutor (ex: usar Base INSS)
    if base_redutor_override is not None:
        base_para_redutor = D(base_redutor_override)

    if base_liquida <= 0:
        return {
            "valor": D("0.00"),
            "memoria": {
                "tipo": "IRRF 2026 - Fortes",
                "variaveis": [
                    {"nome": "Base IRRF (Bruta)", "valor": f"R$ {bruto_display:,.2f}"},
                    {"nome": "INSS", "valor": f"R$ {inss:,.2f} (-)"},
                    {"nome": "Dependentes", "valor": f"{deps} (R$ {deducao_dependentes:,.2f}) (-)"},
                    {"nome": "Pensão Alimentícia", "valor": f"R$ {pensao:,.2f} (-)"},
                    {"nome": "Base Líquida", "valor": f"R$ {base_liquida:,.2f}"},
                ],
                "resultado": "R$ 0,00 (Isento)",
            },
        }

    # -----------------------------
    # 2. Determina a FAIXA pela base líquida
    # -----------------------------
    aliquota = D("0.0")
    faixa_nome = "Isento"
    
    if base_liquida <= D("2428.80"):
        aliquota = D("0.0")
        faixa_nome = "Isento"
    elif base_liquida <= D("2826.65"):
        aliquota = D("0.075")
        faixa_nome = "7,5%"
    elif base_liquida <= D("3751.05"):
        aliquota = D("0.15")
        faixa_nome = "15%"
    elif base_liquida <= D("4664.68"):
        aliquota = D("0.225")
        faixa_nome = "22,5%"
    else:
        aliquota = D("0.275")
        faixa_nome = "27,5%"

    # -----------------------------
    # 3. Aplica a ALÍQUOTA na BASE LÍQUIDA
    # -----------------------------
    irrf_parcial = money_round(base_liquida * aliquota)

    # -----------------------------
    # 4. Dedução Fixa (Look up na tabela)
    # -----------------------------
    DEDUCAO_FIXA = D("0.00")
    for lim, aliq, ded in IRRF_TABLE_2026:
        if base_liquida <= (lim if isinstance(lim, Decimal) else D(str(lim))):
             DEDUCAO_FIXA = ded
             break
    
    irrf_antes_reducao = max(D("0.00"), money_round(irrf_parcial - DEDUCAO_FIXA))

    # -----------------------------
    # 5. Redutor Lei 15.270/2025
    # -----------------------------
    
    if base_para_redutor <= D("5000.00"):
        # Isento até R$ 5.000 (na verdade, redutor anula o imposto)
        redutor = irrf_antes_reducao 
        faixa_redutor = "Isento até R$ 5.000"
    elif base_para_redutor <= D("7350.00"):
        # Redutor decrescente: 978.62 - (0.133145 * base_para_redutor)
        # Atenção aos coeficientes
        redutor_calculado = D("978.62") - (D("0.133145") * base_para_redutor)
        redutor = max(D("0.00"), min(irrf_antes_reducao, money_round(redutor_calculado)))
        faixa_redutor = "Redutor decrescente (R$ 5.000,01 a R$ 7.350)"
    else:
        redutor = D("0.00")
        faixa_redutor = "Sem redutor (> R$ 7.350)"

    # -----------------------------
    # 6. IRRF Final
    # -----------------------------
    irrf_final = max(D("0.00"), money_round(irrf_antes_reducao - redutor))

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
                {"nome": "Pensão Alimentícia", "valor": f"R$ {pensao:,.2f}"},
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


def calc_fgts(base, is_aprendiz: bool = False):
    """Calcula FGTS: 8% para funcionários normais, 2% para aprendizes."""
    base = D(base)
    aliq = D("0.02") if is_aprendiz else D("0.08")
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
        }
    }


# ============================================================================
# CÁLCULOS DE HORAS E ADICIONAIS
# ============================================================================


def calc_he_generica(
    salario_base_he, horas, percentual, divisor=220.0
) -> Decimal:
    """Calcula Hora Extra com base composta (Salário + Adicionais)."""
    salario_base_he = D(salario_base_he)
    horas = D(horas)
    percentual = D(percentual)
    divisor = D(divisor)
    
    salario_hora = salario_base_he / divisor
    fator = D("1") + (percentual / D("100.0"))
    return money_round(salario_hora * fator * horas)


def calc_adicional_noturno(
    salario_base, horas, divisor=220.0
):
    """Calcula Adicional Noturno (20% sobre o salário base)."""
    salario_base = D(salario_base)
    horas = D(horas)
    divisor = D(divisor)
    
    val_hora = salario_base / divisor
    valor = money_round(val_hora * D("0.20") * horas)
    return {
        "valor": valor,
        "memoria": {
            "tipo": "Adicional Noturno (20%)",
            "variaveis": [
                {"nome": "Salário Contratual", "valor": f"R$ {salario_base:,.2f}"},
                {"nome": "Divisor", "valor": f"{divisor}h"},
                {"nome": "Valor Hora", "valor": f"R$ {val_hora:,.2f}"},
                {"nome": "Horas Noturnas", "valor": f"{horas:.2f}h"},
                {"nome": "Percentual", "valor": "20%"},
            ],
            "resultado": f"R$ {valor:,.2f}",
        }
    }


def calc_periculosidade(salario) -> Decimal:
    """Calcula adicional de periculosidade (30% do salário base)."""
    return money_round(D(salario) * D("0.30"))


def calc_insalubridade(
    salario_minimo=SALARIO_MINIMO_2026, grau=0.20
) -> Decimal:
    """
    Calcula adicional de insalubridade sobre o salário mínimo.
    Graus: 10% (mínimo), 20% (médio), 40% (máximo)
    """
    salario_minimo = D(salario_minimo)
    grau = D(grau)
    return money_round(salario_minimo * grau)


def calc_dsr(valor_variaveis, dias_uteis, dias_dsr):
    valor_variaveis = D(valor_variaveis)
    dias_uteis = D(dias_uteis)
    dias_dsr = D(dias_dsr)
    
    if dias_uteis == 0:
        return {"valor": D("0.00"), "memoria": None}
    
    valor = money_round((valor_variaveis / dias_uteis) * dias_dsr)
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
        }
    }


def calc_salario_familia(remuneracao, filhos: int) -> Decimal:
    """Calcula salário família 2026."""
    remuneracao = D(remuneracao)
    # Teto já definido como decimal lá em cima
    if filhos <= 0:
        return D("0.00")
    if remuneracao <= TETO_SALARIO_FAMILIA_2026:
        return money_round(D(filhos) * VALOR_COTA_SALARIO_FAMILIA_2026)
    return D("0.00")


def calc_vale_transporte(salario, percentual=0.06) -> Decimal:
    """Calcula desconto de vale transporte."""
    salario = D(salario)
    percentual = D(percentual)
    return money_round(salario * percentual)


def calc_falta(salario_base, qtd_dias) -> Decimal:
    """Calcula desconto de falta em dias."""
    salario_base = D(salario_base)
    qtd_dias = D(qtd_dias)
    return money_round((salario_base / D("30")) * qtd_dias)


def calc_vt_aprendiz(salario_base, dias_trabalhados: int) -> Decimal:
    """
    Calcula VT Proporcional para Aprendiz (Código 323).
    Geralmente 6% sobre o salário proporcional aos dias trabalhados.
    """
    salario_base = D(salario_base)
    dias_trabalhados = D(dias_trabalhados)
    base_prop = (salario_base / D("30")) * dias_trabalhados
    return money_round(base_prop * D("0.06"))
