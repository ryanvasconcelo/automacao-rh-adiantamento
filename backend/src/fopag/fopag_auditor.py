# No arquivo: backend/src/fopag/fopag_auditor.py

from src.fopag import calculations
from src.fopag import fopag_rules_catalog


def run_fopag_audit(company_code: str, employee_payroll_data: list) -> list:
    """
    Executa a auditoria completa da FOPAG para uma empresa,
    comparando os dados reais com os cálculos esperados.
    """

    print(f"[Auditor] Iniciando auditoria para a empresa: {company_code}...")

    try:
        company_rule = fopag_rules_catalog.get_company_rule(company_code)
    except Exception as e:
        print(f"ERRO CRÍTICO: Não foi possível carregar o catálogo de regras. {e}")
        return [{"error": "Falha ao carregar o catálogo de regras."}]

    todas_as_divergencias = []

    for funcionario in employee_payroll_data:

        matricula = funcionario.get("matricula", "N/A")
        nome = funcionario.get("nome", "N/A")
        dependentes = funcionario.get(
            "dependentes", 0
        )  # <-- NOVO: Pegamos os dependentes
        eventos_reais = funcionario.get("eventos_calculados_fortes", {})
        proventos_base = funcionario.get("proventos_base", [])

        # --- PASSO 3: Calcular Bases de Cálculo (LÓGICA IMPLEMENTADA) ---
        base_inss_esperada = 0.0
        base_irrf_esperada = 0.0
        base_fgts_esperada = 0.0

        for evento in proventos_base:
            codigo = evento.get("codigo")
            valor = evento.get("valor", 0.0)
            props = fopag_rules_catalog.get_event_properties(codigo)

            if props:
                if props.incide_inss:
                    base_inss_esperada += valor
                if props.incide_irrf:
                    base_irrf_esperada += valor
                if props.incide_fgts:
                    base_fgts_esperada += valor

        # --- PASSO 4: Chamar as "Ferramentas" (em ordem) ---

        inss_esperado = 0.0  # <-- IMPORTANTE: Inicializamos o INSS aqui

        # --- Auditoria do INSS (PRECISA VIR PRIMEIRO) ---
        if company_rule.usa_calc_inss:
            inss_esperado = calculations.calc_inss(base_inss_esperada)
            inss_real = eventos_reais.get(company_rule.cod_inss, 0.0)

            if abs(inss_esperado - inss_real) > 0.01:
                divergencia = {
                    "matricula": matricula,
                    "nome": nome,
                    "evento": "INSS (Cód. 100)",
                    "valor_esperado": inss_esperado,
                    "valor_real": inss_real,
                    "base_calculada": base_inss_esperada,
                    "mensagem": "Valor do INSS calculado não bate com o valor do Fortes.",
                }
                todas_as_divergencias.append(divergencia)

        # --- Auditoria do IRRF (USA O CÁLCULO DO INSS) ---
        if company_rule.usa_calc_irrf:

            # Chama a "ferramenta" com a base correta E o INSS descontado
            irrf_esperado = calculations.calc_irrf(
                base_bruta_irrf=base_irrf_esperada,
                inss_descontado=inss_esperado,  # <-- Usamos o INSS que acabamos de calcular
                dependentes=dependentes,
            )

            # Pega o valor real do Fortes
            irrf_real = eventos_reais.get(company_rule.cod_irrf, 0.0)

            # --- PASSO 5: A Auditoria (Comparação) ---
            if abs(irrf_esperado - irrf_real) > 0.01:
                divergencia = {
                    "matricula": matricula,
                    "nome": nome,
                    "evento": "IRRF (Cód. 101)",
                    "valor_esperado": irrf_esperado,
                    "valor_real": irrf_real,
                    "base_calculada": base_irrf_esperada,
                    "mensagem": "Valor do IRRF calculado não bate com o valor do Fortes.",
                }
                todas_as_divergencias.append(divergencia)

        # --- Auditoria do FGTS ---
        if company_rule.usa_calc_fgts:
            fgts_esperado = calculations.calc_fgts(base_fgts_esperada)
            fgts_real = eventos_reais.get("FGTS", 0.0)  # (Assumindo um código 'FGTS')

            # (Adicionamos o FGTS calculado ao relatório)
            todas_as_divergencias.append(
                {
                    "matricula": matricula,
                    "nome": nome,
                    "evento": "FGTS (Cálculo)",
                    "valor_esperado": fgts_esperado,
                    "valor_real": fgts_real,
                    "base_calculada": base_fgts_esperada,
                    "mensagem": "Valor do FGTS esperado.",
                }
            )

    print(
        f"[Auditor] Auditoria concluída. {len(todas_as_divergencias)} divergências encontradas."
    )
    return todas_as_divergencias
