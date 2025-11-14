# No arquivo: backend/src/fopag/calculations.py

"""
Componente 1: As "Ferramentas" (A Lógica de Cálculo)
Versão com lógica de INSS e IRRF implementadas.
"""

# --- CONSTANTES DE INSS (Exemplo 2025) ---
INSS_TABLE_2025 = [
    (1556.94, 0.075, 0.0),
    (2700.00, 0.09, 23.35),
    (4500.00, 0.12, 104.35),
    (7786.02, 0.14, 194.35),
]
INSS_TETO_2025 = 908.85

# --- CONSTANTES DE IRRF (Exemplo 2025) ---
IRRF_DEDUCAO_DEPENDENTE_2025 = 189.59

# Formato: (limite_da_faixa, aliquota_percentual, deducao_da_parcela)
IRRF_TABLE_2025 = [
    (2259.20, 0.0, 0.0),  # Isento
    (2826.65, 0.075, 169.44),
    (3751.05, 0.15, 381.44),
    (4664.68, 0.225, 662.77),
    # Acima de 4664.68 é a última faixa
    (float("inf"), 0.275, 896.00),
]


# --- FUNÇÕES DE CÁLCULO ---


def calc_inss(salario_bruto: float) -> float:
    """
    Calcula o valor do INSS com base no salário bruto (Base de INSS).
    """
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

    final_value = round(inss_calculado, 2)
    print(f"[Cálculo] INSS: Base R$ {salario_bruto}, Calculado R$ {final_value}")
    return final_value


def calc_irrf(
    base_bruta_irrf: float, inss_descontado: float, dependentes: int
) -> float:
    """
    Calcula o valor do IRRF com base na (Base Bruta - INSS - Dependentes).
    """

    # 1. Calcular a dedução total por dependentes
    deducao_dependentes = dependentes * IRRF_DEDUCAO_DEPENDENTE_2025

    # 2. Calcular a Base de Cálculo REAL do IRRF
    base_de_calculo_irrf = base_bruta_irrf - inss_descontado - deducao_dependentes

    # 3. Encontrar a faixa correta na tabela
    irrf_calculado = 0.0
    for limite, aliquota, deducao in IRRF_TABLE_2025:
        if base_de_calculo_irrf <= limite:
            # Encontrou a faixa! Aplica a fórmula (Alíquota * Base) - Dedução
            irrf_calculado = (base_de_calculo_irrf * aliquota) - deducao
            break  # Para o loop

    final_value = round(irrf_calculado, 2)

    print(
        f"[Cálculo] IRRF: Base Bruta R$ {base_bruta_irrf}, INSS R$ {inss_descontado}, Base Líquida R$ {base_de_calculo_irrf}, Calculado R$ {final_value}"
    )

    # IRRF nunca pode ser negativo
    return max(0.0, final_value)


def calc_fgts(base_de_calculo_fgts: float) -> float:
    """
    Calcula o valor do depósito de FGTS (8%).
    """
    fgts_calculado = round(base_de_calculo_fgts * 0.08, 2)
    print(
        f"[Cálculo] FGTS: Base R$ {base_de_calculo_fgts}, Calculado R$ {fgts_calculado}"
    )
    return fgts_calculado
