# No arquivo: backend/src/fopag/fopag_auditor.py

from datetime import datetime
from src.fopag import calculations
from src.fopag import fopag_rules_catalog

# ==============================================================================
# CÓDIGOS DE EVENTOS CONFIÁVEIS (Valor Real = Valor Esperado)
# ==============================================================================
CODIGOS_CONFIAVEIS = [
    # Reembolsos e Ajustes
    956,
    31,
    323,
    74,
    32,
    94,
    950,
    953,
    955,
    967,  # Reembolsos Diversos
    934,
    960,
    961,
    964,
    972,
    924,
    927,
    945,  # Bancos de Horas
    928,
    954,
    963,
    75,  # Prêmios/Bonificações
    30,  # Comissão
    938,
    916,
    210,
    910,  # Quebra de Caixa/Ajudas
    319,
    300,
    301,
    302,
    127,
    968,
    973,
    978,
    979,  # Descontos (VR, Adiant, Convênios, Consig)
    392,
    91,
    92,
    391,  # Arredondamentos
    100,
    982,
    915,
    969,
    971,  # Ajustes/Devoluções
    976,
    977,
    76,
    77,  # Dissídios/Diferenças Salariais
    113,
    115,  # Abonos (Indenizatórios)
    906,
    312,
    322,
    966,
    981,
    913,
    914,  # Sindicatos
]

# Códigos que NÃO devem somar no "Total Proventos Brutos"
CODIGOS_NAO_SOMAM_PROVENTOS = [
    955,
    94,
    950,
    967,
    953,
    969,
    971,
    300,
    127,
    319,
    301,
    302,
    340,
]

CODIGOS_PENSAO = ["340", "911", "912", "800"]


def run_fopag_audit(
    company_code: str,
    employee_payroll_data: list,
    ano: int,
    mes: int,
    caso_pensao: int = 2,
) -> list:
    print(
        f"[Auditor] Iniciando auditoria para a empresa: {company_code} (Ref: {mes}/{ano})..."
    )

    try:
        company_rule = fopag_rules_catalog.get_company_rule(company_code)
    except Exception as e:
        return [{"error": f"Falha ao carregar regras: {e}"}]

    auditoria_agrupada = {}

    for funcionario in employee_payroll_data:
        matricula = funcionario.get("matricula", "N/A")
        nome = funcionario.get("nome", "N/A")
        dependentes = funcionario.get("dependentes", 0)

        data_admissao_str = funcionario.get("data_admissao")
        data_admissao = None
        if data_admissao_str:
            try:
                data_admissao = datetime.strptime(
                    str(data_admissao_str)[:10], "%Y-%m-%d"
                ).date()
            except:
                pass

        tipo_contrato = funcionario.get("tipo_contrato", "").lower()
        cargo_nome = funcionario.get("cargo", "").lower()
        is_aprendiz = "aprendiz" in tipo_contrato or "aprendiz" in cargo_nome

        dados_calendario = calculations.get_dias_uteis_dsr(ano, mes, data_admissao)
        dias_uteis = dados_calendario["dias_uteis"]
        dias_dsr = dados_calendario["dias_dsr"]

        if matricula not in auditoria_agrupada:
            auditoria_agrupada[matricula] = {
                "matricula": matricula,
                "nome": nome,
                "itens": [],
                "tem_divergencia": False,
            }

        def registrar_item(evento_nome, v_esperado, v_real, msg="", base=None):
            diferenca = v_real - v_esperado
            abs_diff = abs(diferenca)

            # Lógica de Tolerância Inteligente
            is_ok = False

            # 1. Tolerância absoluta de centavos (aumentada para 10 centavos)
            if round(abs_diff, 2) <= 0.10:
                is_ok = True

            # 2. Tolerância percentual para DSR (5% de margem para calendário)
            elif "descanso" in evento_nome.lower() or "dsr" in evento_nome.lower():
                if v_esperado > 0 and (abs_diff / v_esperado) < 0.05:
                    is_ok = True

            if is_ok:
                status = "OK"
            else:
                status = "ERRO"
                auditoria_agrupada[matricula]["tem_divergencia"] = True

            auditoria_agrupada[matricula]["itens"].append(
                {
                    "evento": evento_nome,
                    "esperado": round(v_esperado, 2),
                    "real": round(v_real, 2),
                    "diferenca": round(diferenca, 2),
                    "status": status,
                    "msg": msg if status == "ERRO" else "Validado com sucesso.",
                    "base": round(base, 2) if base else 0.0,
                }
            )

        proventos_base = funcionario.get("proventos_base", [])
        eventos_variaveis = funcionario.get("eventos_variaveis_referencia", [])
        eventos_reais = funcionario.get("eventos_calculados_fortes", {})

        # --- 1. SALÁRIO BASE ---
        salario_base = 0.0
        for evento in proventos_base:
            if evento.get("codigo") == company_rule.cod_salario_base:
                salario_base = evento.get("valor", 0.0)
                registrar_item("Salário Base", salario_base, salario_base)
                break

        # --- 2. BASES DE CÁLCULO ---
        base_inss_esperada = 0.0
        base_irrf_esperada = 0.0
        base_fgts_esperada = 0.0
        total_proventos_brutos = 0.0

        for evento in proventos_base:
            codigo = evento.get("codigo")
            valor = evento.get("valor", 0.0)
            total_proventos_brutos += valor

            if (
                codigo == company_rule.cod_periculosidade
                and company_rule.calcula_periculosidade
            ):
                valor_esperado = calculations.calc_periculosidade(salario_base)
                registrar_item(
                    "Periculosidade", valor_esperado, valor, "30% sobre Salário Base"
                )
                valor = valor_esperado

            props = fopag_rules_catalog.get_event_properties(codigo)
            if props:
                if props.incide_inss:
                    base_inss_esperada += valor
                if props.incide_irrf:
                    base_irrf_esperada += valor
                if props.incide_fgts:
                    base_fgts_esperada += valor

        # ======================================================================
        # LOOP 2: EVENTOS VARIÁVEIS (UNIFICADO)
        # ======================================================================
        codigos_input = {e.get("codigo"): e for e in eventos_variaveis}
        todos_codigos = set(codigos_input.keys()).union(set(eventos_reais.keys()))

        total_he_calculada = 0.0
        total_faltas_calculada = 0.0
        total_variaveis_para_dsr = 0.0
        eventos_calculados = {}
        percentual_pensao = 0.0

        for codigo_var in todos_codigos:
            dados_input = codigos_input.get(codigo_var, {})
            referencia = dados_input.get("referencia", 0.0)
            nome_evento = dados_input.get("nome", "").lower()
            if not nome_evento and codigo_var in eventos_reais:
                props_temp = fopag_rules_catalog.get_event_properties(codigo_var)
                nome_evento = props_temp.description.lower() if props_temp else ""

            valor_real_db = eventos_reais.get(codigo_var, 0.0)

            try:
                cod_int = int(codigo_var)
            except:
                cod_int = 0

            # FILTROS
            if codigo_var == company_rule.cod_salario_base:
                continue
            if codigo_var == company_rule.cod_periculosidade:
                continue
            if codigo_var == "49" or codigo_var == company_rule.cod_dsr_he:
                continue
            if 600 <= cod_int <= 699:
                continue
            if 900 <= cod_int <= 904:
                continue
            if 919 <= cod_int <= 922:
                continue
            if 946 <= cod_int <= 949:
                continue

            valor_calculado_evento = 0.0

            # --- A. EVENTOS CONFIÁVEIS ---
            eh_confiavel = (cod_int in CODIGOS_CONFIAVEIS) or (
                "consignado" in nome_evento
            )
            if eh_confiavel:
                valor_calculado_evento = valor_real_db

                # SOMA NO DSR: Apenas Comissão (30) e Gratificações (75)
                # Banco de Horas (934) NÃO soma no DSR, mas SOMARÁ na base de INSS lá embaixo
                if cod_int == 30 or cod_int == 75:
                    total_variaveis_para_dsr += valor_calculado_evento

            # --- B. HORAS EXTRAS ---
            elif codigo_var == company_rule.cod_he_50:
                horas_dec = calculations.time_to_decimal(referencia)
                valor_calculado_evento = calculations.calc_he_50(
                    salario_base, horas_dec
                )
                total_he_calculada += valor_calculado_evento
                total_variaveis_para_dsr += valor_calculado_evento

            elif codigo_var == company_rule.cod_he_100:
                horas_dec = calculations.time_to_decimal(referencia)
                valor_calculado_evento = calculations.calc_he_100(
                    salario_base, horas_dec
                )
                total_he_calculada += valor_calculado_evento
                total_variaveis_para_dsr += valor_calculado_evento

            # --- C. ADICIONAL NOTURNO ---
            elif (
                "noturno" in nome_evento or codigo_var == company_rule.cod_adic_noturno
            ):
                if referencia > 0:
                    if codigo_var == "012":
                        dias = int(referencia)
                        valor_calculado_evento = (
                            calculations.calc_adicional_noturno_012(
                                salario_base, dias_uteis, dias
                            )
                        )
                    elif codigo_var == "050":
                        h = calculations.time_to_decimal(referencia)
                        sh = calculations._get_salario_hora(salario_base)
                        valor_calculado_evento = (
                            calculations.calc_adicional_noturno_050(h, sh)
                        )
                    else:
                        h = calculations.time_to_decimal(referencia)
                        valor_calculado_evento = calculations.calc_adicional_noturno(
                            salario_base, h
                        )
                else:
                    if valor_real_db > 0:
                        valor_calculado_evento = valor_real_db

                total_variaveis_para_dsr += valor_calculado_evento

            # --- D. FALTAS ---
            elif codigo_var == company_rule.cod_faltas:
                horas_dec = calculations.time_to_decimal(referencia)
                salario_hora = calculations._get_salario_hora(salario_base)
                valor_calculado_evento = round(salario_hora * horas_dec, 2)
                total_faltas_calculada += valor_calculado_evento

            # --- E. BENEFÍCIOS ---
            elif codigo_var == company_rule.cod_salario_familia:
                qtd_filhos = int(referencia)
                valor_calculado_evento = calculations.calc_salario_familia(
                    base_inss_esperada,
                    qtd_filhos,
                    company_rule.valor_cota_salario_familia,
                )

            elif codigo_var == company_rule.cod_vale_transporte and cod_int != 955:
                valor_teto = calculations.calc_vale_transporte(
                    salario_base, company_rule.percentual_vt
                )
                valor_calculado_evento = (
                    valor_teto if valor_real_db > (valor_teto + 0.01) else valor_real_db
                )

            elif codigo_var == company_rule.cod_salario_maternidade:
                valor_calculado_evento = valor_real_db

            # Pensão
            if (
                "pensao" in nome_evento
                or "pensão" in nome_evento
                or str(cod_int) in CODIGOS_PENSAO
            ):
                if referencia > 0:
                    percentual_pensao = referencia

            eventos_calculados[codigo_var] = valor_calculado_evento

            if (
                valor_calculado_evento > 0
                and cod_int not in CODIGOS_NAO_SOMAM_PROVENTOS
            ):
                props = fopag_rules_catalog.get_event_properties(codigo_var)
                if props and props.type == "Provento":
                    total_proventos_brutos += valor_calculado_evento

        # ======================================================================
        # LOOP 3: DSR (Código 49)
        # ======================================================================
        dsr_codigo = company_rule.cod_dsr_he if company_rule.cod_dsr_he else "49"

        deve_calcular_dsr = total_variaveis_para_dsr > 0
        existe_no_real = dsr_codigo in eventos_reais

        if deve_calcular_dsr or existe_no_real:
            val_dsr = calculations.calc_dsr(
                total_variaveis_para_dsr, dias_uteis, dias_dsr
            )
            eventos_calculados[dsr_codigo] = val_dsr
            if val_dsr > 0:
                total_proventos_brutos += val_dsr

        if (
            company_rule.cod_dsr_desconto
            and company_rule.cod_dsr_desconto in todos_codigos
        ):
            val = calculations.calc_dsr_desconto(
                total_faltas_calculada, dias_uteis, dias_dsr
            )
            eventos_calculados[company_rule.cod_dsr_desconto] = val

        # ======================================================================
        # LOOP 4: AUDITORIA FINAL
        # ======================================================================
        for codigo_var, valor_calculado in eventos_calculados.items():
            valor_real = eventos_reais.get(codigo_var, 0.0)
            try:
                cod_int = int(codigo_var)
            except:
                cod_int = 0

            if 600 <= cod_int <= 699:
                continue
            if 900 <= cod_int <= 904:
                continue
            if 919 <= cod_int <= 922:
                continue
            if 946 <= cod_int <= 949:
                continue

            if (
                codigo_var in [company_rule.cod_inss, company_rule.cod_irrf, "FGTS"]
                or str(cod_int) in CODIGOS_PENSAO
            ):
                continue

            props = fopag_rules_catalog.get_event_properties(codigo_var)
            nome_ev = props.description if props else f"Cód. {codigo_var}"

            registrar_item(nome_ev, valor_calculado, valor_real)

            if props:
                if cod_int == 955:
                    continue
                if cod_int in [956, 30]:
                    base_inss_esperada += valor_calculado
                    base_irrf_esperada += valor_calculado
                    base_fgts_esperada += valor_calculado
                    continue

                if props.type == "Provento":
                    if props.incide_inss:
                        base_inss_esperada += valor_calculado
                    if props.incide_irrf:
                        base_irrf_esperada += valor_calculado
                    if props.incide_fgts:
                        base_fgts_esperada += valor_calculado
                elif props.type == "Desconto":
                    if props.incide_inss:
                        base_inss_esperada -= valor_calculado
                    if props.incide_irrf:
                        base_irrf_esperada -= valor_calculado
                    if props.incide_fgts:
                        base_fgts_esperada -= valor_calculado

        # --- IMPOSTOS ---
        inss_esperado = 0.0
        if company_rule.usa_calc_inss:
            inss_esperado = calculations.calc_inss(base_inss_esperada)
            inss_real = eventos_reais.get(company_rule.cod_inss, 0.0)
            registrar_item("INSS", inss_esperado, inss_real, base=base_inss_esperada)

        irrf_esperado = 0.0
        if company_rule.usa_calc_irrf:
            irrf_esperado = calculations.calc_irrf(
                base_irrf_esperada, inss_esperado, dependentes
            )
            irrf_real = eventos_reais.get(company_rule.cod_irrf, 0.0)
            registrar_item("IRRF", irrf_esperado, irrf_real, base=base_irrf_esperada)

        # --- PENSÃO ---
        cod_pensao_encontrado = None
        valor_pensao_real = 0.0
        for cod in CODIGOS_PENSAO:
            if eventos_reais.get(cod, 0.0) > 0:
                cod_pensao_encontrado = cod
                valor_pensao_real = eventos_reais[cod]
                break

        if not cod_pensao_encontrado:
            for cod, val in eventos_reais.items():
                if str(cod) in CODIGOS_PENSAO:
                    cod_pensao_encontrado = str(cod)
                    valor_pensao_real = val
                    break

        if cod_pensao_encontrado and percentual_pensao > 0:
            valor_esperado_pensao = calculations.calc_pensao_alimenticia(
                total_proventos=total_proventos_brutos,
                salario_base=salario_base,
                inss=inss_esperado,
                irrf=irrf_esperado,
                percentual=percentual_pensao,
                caso=caso_pensao,
            )
            registrar_item(
                f"Pensão ({cod_pensao_encontrado})",
                valor_esperado_pensao,
                valor_pensao_real,
                msg=f"Caso {caso_pensao}",
            )

        # --- FGTS ---
        if company_rule.usa_calc_fgts:
            fgts_esperado = calculations.calc_fgts(
                base_fgts_esperada, is_aprendiz=is_aprendiz
            )
            fgts_real = eventos_reais.get("FGTS", 0.0)
            if fgts_real == 0.0:
                fgts_real = eventos_reais.get("605", 0.0)
            registrar_item("FGTS", fgts_esperado, fgts_real, base=base_fgts_esperada)

    return list(auditoria_agrupada.values())
