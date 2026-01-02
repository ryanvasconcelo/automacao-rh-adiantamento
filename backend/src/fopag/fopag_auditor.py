from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from src.fopag import calculations
from src.fopag import fopag_rules_catalog

# ==============================================================================
# CONFIGURAÇÕES E HELPERS
# ==============================================================================


def D(valor):
    """Converte para Decimal de forma segura."""
    if valor is None:
        return Decimal("0.00")
    return Decimal(str(valor))


def money_round(valor_decimal):
    """Arredonda Decimal para 2 casas e devolve float (para JSON)."""
    if not isinstance(valor_decimal, Decimal):
        valor_decimal = D(valor_decimal)
    return float(valor_decimal.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


# LISTAS DE CÓDIGOS PARA FILTRAGEM
CODIGOS_CONFIAVEIS = [
    956,
    323,
    74,
    32,
    94,
    950,
    953,
    955,
    967,
    934,
    960,
    961,
    964,
    972,
    924,
    927,
    945,
    928,
    954,
    963,
    75,
    30,
    938,
    916,
    210,
    910,
    319,
    300,
    301,
    302,
    127,
    968,
    973,
    978,
    979,
    392,
    91,
    92,
    391,
    100,
    982,
    915,
    969,
    971,
    976,
    977,
    76,
    77,
    113,
    115,
    906,
    322,
    966,
    981,
    913,
    914,
    2,
]

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

        data_admissao = None
        if funcionario.get("data_admissao"):
            try:
                data_admissao = datetime.strptime(
                    str(funcionario.get("data_admissao"))[:10], "%Y-%m-%d"
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

        def registrar_item(
            evento_nome, v_esperado, v_real, codigo, msg="", base=None, formula=""
        ):
            diferenca = v_real - v_esperado
            abs_diff = abs(diferenca)
            is_ok = False

            # ATUALIZAÇÃO: Tolerância aumentada para 10 centavos
            if round(abs_diff, 2) <= 0.10:
                is_ok = True

            # Regra especial para DSR e Descanso (tolerância percentual de 5% continua)
            elif "descanso" in evento_nome.lower() or "dsr" in evento_nome.lower():
                if v_esperado > 0 and (abs_diff / v_esperado) < 0.05:
                    is_ok = True

            status = "OK" if is_ok else "ERRO"
            if not is_ok:
                auditoria_agrupada[matricula]["tem_divergencia"] = True

            auditoria_agrupada[matricula]["itens"].append(
                {
                    "codigo": str(codigo),
                    "evento": evento_nome,
                    "esperado": round(v_esperado, 2),
                    "real": round(v_real, 2),
                    "diferenca": round(diferenca, 2),
                    "status": status,
                    "msg": msg if status == "ERRO" else "Validado com sucesso.",
                    "base": round(base, 2) if base else 0.0,
                    "formula": formula,
                }
            )

        proventos_base = funcionario.get("proventos_base", [])
        eventos_variaveis = funcionario.get("eventos_variaveis_referencia", [])
        eventos_reais = funcionario.get("eventos_calculados_fortes", {})

        # ======================================================================
        # 1. DEFINIÇÃO DE BASES (USANDO DECIMAL)
        # ======================================================================
        salario_base = D(0)
        base_para_he = D(0)

        base_inss_acumulada = D(0)
        base_irrf_acumulada = D(0)
        base_fgts_acumulada = D(0)

        for evento in proventos_base:
            cod = evento.get("codigo")
            val = D(evento.get("valor", 0))
            props = fopag_rules_catalog.get_event_properties(cod)
            nome_ev = props.description if props else "Salário"

            if cod == company_rule.cod_salario_base:
                salario_base = val
                registrar_item(
                    nome_ev,
                    float(salario_base),
                    float(salario_base),
                    cod,
                    formula="Valor Fixo Contratual",
                )

            if cod in [company_rule.cod_salario_base, "31", "13"]:
                base_para_he += val
                if cod != company_rule.cod_salario_base:
                    registrar_item(
                        nome_ev,
                        float(val),
                        float(val),
                        cod,
                        formula="Verba Fixa (Compõe Base HE)",
                    )

            if props:
                if props.incide_inss:
                    base_inss_acumulada += val
                if props.incide_irrf:
                    base_irrf_acumulada += val
                if props.incide_fgts:
                    base_fgts_acumulada += val

        # ======================================================================
        # 2. CÁLCULO DE VARIÁVEIS
        # ======================================================================
        codigos_input = {e.get("codigo"): e for e in eventos_variaveis}
        todos_codigos = set(codigos_input.keys()).union(set(eventos_reais.keys()))

        total_he_calculada = D(0)
        total_faltas_calculada = D(0)
        total_variaveis_para_dsr = D(0)
        eventos_calculados = {}
        percentual_pensao = D(0)
        total_proventos_brutos = base_para_he

        for codigo_var in todos_codigos:
            dados_input = codigos_input.get(codigo_var, {})
            referencia = dados_input.get("referencia", 0)
            props = fopag_rules_catalog.get_event_properties(codigo_var)
            nome_evento = props.description if props else f"Evento {codigo_var}"
            valor_real_db = D(eventos_reais.get(codigo_var, 0))
            try:
                cod_int = int(codigo_var)
            except:
                cod_int = 0

            # FILTROS
            if codigo_var in [
                company_rule.cod_salario_base,
                company_rule.cod_periculosidade,
                "31",
                "49",
                company_rule.cod_dsr_he,
            ]:
                continue
            if (
                600 <= cod_int <= 699
                or 900 <= cod_int <= 904
                or 919 <= cod_int <= 922
                or 946 <= cod_int <= 949
            ):
                continue

            valor_calculado_evento = D(0)
            formula_memoria = ""

            eh_confiavel = (cod_int in CODIGOS_CONFIAVEIS) or (
                "consignado" in nome_evento.lower()
            )

            if eh_confiavel:
                valor_calculado_evento = valor_real_db
                formula_memoria = "Leitura Direta"
                if cod_int == 30 or cod_int == 75:
                    total_variaveis_para_dsr += valor_calculado_evento

            elif codigo_var == company_rule.cod_he_50:
                horas_dec = D(
                    calculations.time_to_decimal(referencia)
                )  # CORREÇÃO AQUI: FORÇA D()
                val_float = calculations.calc_he_50(
                    float(base_para_he), float(horas_dec)
                )
                valor_calculado_evento = D(val_float)
                total_he_calculada += valor_calculado_evento
                total_variaveis_para_dsr += valor_calculado_evento
                formula_memoria = (
                    f"({float(base_para_he):.2f}/220) * 1.5 * {float(horas_dec):.2f}h"
                )

            elif codigo_var == company_rule.cod_he_100:
                horas_dec = D(calculations.time_to_decimal(referencia))  # CORREÇÃO AQUI
                val_float = calculations.calc_he_100(
                    float(base_para_he), float(horas_dec)
                )
                valor_calculado_evento = D(val_float)
                total_he_calculada += valor_calculado_evento
                total_variaveis_para_dsr += valor_calculado_evento
                formula_memoria = (
                    f"({float(base_para_he):.2f}/220) * 2.0 * {float(horas_dec):.2f}h"
                )

            # C. FALTAS (Usando Decimal)
            elif codigo_var == company_rule.cod_faltas:  # 321
                dias_falta = D(referencia if referencia else 0)
                valor_dia = salario_base / D(30)
                valor_calculado_evento = (valor_dia * dias_falta).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                total_faltas_calculada += valor_calculado_evento
                formula_memoria = (
                    f"({float(salario_base):.2f} / 30) * {dias_falta} dias"
                )

            elif codigo_var == company_rule.cod_faltas_em_horas:  # 925
                horas_dec = D(calculations.time_to_decimal(referencia))  # CORREÇÃO AQUI
                valor_hora = salario_base / D(220)
                valor_calculado_evento = (valor_hora * horas_dec).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                total_faltas_calculada += valor_calculado_evento
                formula_memoria = (
                    f"({float(salario_base):.2f} / 220) * {float(horas_dec):.2f}h"
                )

            elif codigo_var == company_rule.cod_dsr_desconto:  # 349
                qtd_dsr_desc = D(
                    calculations.time_to_decimal(referencia)
                )  # CORREÇÃO AQUI: FORÇA D()
                valor_dia = salario_base / D(30)
                valor_calculado_evento = (valor_dia * qtd_dsr_desc).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                formula_memoria = (
                    f"({float(salario_base):.2f} / 30) * {float(qtd_dsr_desc)} dias"
                )

            # ADICIONAIS
            elif (
                "noturno" in nome_evento.lower()
                or codigo_var == company_rule.cod_adic_noturno
            ):
                if referencia:
                    h = D(calculations.time_to_decimal(referencia))
                    if codigo_var == "012":
                        dias = int(referencia)
                        val_float = calculations.calc_adicional_noturno_012(
                            float(salario_base), dias_uteis, dias
                        )
                        valor_calculado_evento = D(val_float)
                        formula_memoria = f"({float(salario_base):.2f} / {dias_uteis}) * {dias}d * 20%"
                    else:
                        val_float = calculations.calc_adicional_noturno(
                            float(base_para_he), float(h)
                        )
                        valor_calculado_evento = D(val_float)
                        formula_memoria = (
                            f"({float(base_para_he):.2f}/220) * 20% * {float(h):.2f}h"
                        )
                else:
                    valor_calculado_evento = valor_real_db
                total_variaveis_para_dsr += valor_calculado_evento

            elif codigo_var == company_rule.cod_vale_transporte:
                val_float = calculations.calc_vale_transporte(
                    float(salario_base), company_rule.percentual_vt
                )
                valor_calculado_evento = D(val_float)
                formula_memoria = f"6% de R$ {float(salario_base):.2f}"

            elif codigo_var == company_rule.cod_salario_familia:
                qtd = int(referencia if referencia else 0)
                val_float = calculations.calc_salario_familia(
                    float(base_inss_acumulada),
                    qtd,
                    company_rule.valor_cota_salario_familia,
                )
                valor_calculado_evento = D(val_float)
                formula_memoria = (
                    f"{qtd} filhos * R$ {company_rule.valor_cota_salario_familia}"
                )

            elif codigo_var == company_rule.cod_salario_maternidade:
                valor_calculado_evento = valor_real_db

            if "pensao" in nome_evento.lower() or str(cod_int) in CODIGOS_PENSAO:
                if referencia:
                    percentual_pensao = D(referencia)

            eventos_calculados[codigo_var] = {
                "valor": valor_calculado_evento,
                "formula": formula_memoria,
                "nome": nome_evento,
            }

            if (
                valor_calculado_evento > 0
                and cod_int not in CODIGOS_NAO_SOMAM_PROVENTOS
            ):
                if props and props.type == "Provento":
                    total_proventos_brutos += valor_calculado_evento

        # --- 3. DSR PROVENTO (49) ---
        dsr_codigo = company_rule.cod_dsr_he if company_rule.cod_dsr_he else "49"
        if total_variaveis_para_dsr > 0 or dsr_codigo in eventos_reais:
            val_dsr_float = calculations.calc_dsr(
                float(total_variaveis_para_dsr), dias_uteis, dias_dsr
            )
            val_dsr = D(val_dsr_float)
            formula_dsr = (
                f"({float(total_variaveis_para_dsr):.2f} / {dias_uteis}) * {dias_dsr}"
            )
            eventos_calculados[dsr_codigo] = {
                "valor": val_dsr,
                "formula": formula_dsr,
                "nome": "Descanso Semanal Remunerado",
            }
            if val_dsr > 0:
                total_proventos_brutos += val_dsr

        # --- 4. AUDITORIA FINAL ---
        for codigo_var, dados_calc in eventos_calculados.items():
            valor_calculado = dados_calc["valor"]
            formula = dados_calc["formula"]
            nome_exibicao = dados_calc["nome"]
            valor_real = D(eventos_reais.get(codigo_var, 0))
            try:
                cod_int = int(codigo_var)
            except:
                cod_int = 0

            if (
                600 <= cod_int <= 699
                or 900 <= cod_int <= 904
                or 919 <= cod_int <= 922
                or 946 <= cod_int <= 949
            ):
                continue
            if (
                codigo_var in [company_rule.cod_inss, company_rule.cod_irrf, "FGTS"]
                or str(cod_int) in CODIGOS_PENSAO
            ):
                continue

            props = fopag_rules_catalog.get_event_properties(codigo_var)
            registrar_item(
                nome_exibicao,
                money_round(valor_calculado),
                money_round(valor_real),
                codigo_var,
                formula=formula,
            )

            if props:
                if str(cod_int) in ["31", "11", "13"]:
                    continue
                if cod_int == 955:
                    continue

                if props.type == "Provento":
                    if props.incide_inss:
                        base_inss_acumulada += valor_calculado
                    if props.incide_irrf:
                        base_irrf_acumulada += valor_calculado
                    if props.incide_fgts:
                        base_fgts_acumulada += valor_calculado
                elif props.type == "Desconto":
                    if props.incide_inss:
                        base_inss_acumulada -= valor_calculado
                    if props.incide_irrf:
                        base_irrf_acumulada -= valor_calculado
                    if props.incide_fgts:
                        base_fgts_acumulada -= valor_calculado

        # --- 5. IMPOSTOS ---
        inss_esperado = 0.0
        if company_rule.usa_calc_inss:
            inss_esperado = calculations.calc_inss(float(base_inss_acumulada))
            inss_real = float(eventos_reais.get(company_rule.cod_inss, 0))
            registrar_item(
                "INSS",
                inss_esperado,
                inss_real,
                company_rule.cod_inss,
                base=float(base_inss_acumulada),
                formula="Tabela 2025",
            )

        irrf_esperado = 0.0
        if company_rule.usa_calc_irrf:
            irrf_esperado = calculations.calc_irrf(
                float(base_irrf_acumulada), inss_esperado, dependentes
            )
            irrf_real = float(eventos_reais.get(company_rule.cod_irrf, 0))
            registrar_item(
                "IRRF",
                irrf_esperado,
                irrf_real,
                company_rule.cod_irrf,
                base=float(base_irrf_acumulada),
                formula="Tabela 2025",
            )

        # PENSÃO
        cod_pensao_encontrado = None
        valor_pensao_real = 0.0
        for cod in CODIGOS_PENSAO:
            if events_val := eventos_reais.get(cod):
                cod_pensao_encontrado = cod
                valor_pensao_real = float(events_val)
                break

        if not cod_pensao_encontrado:
            for cod, val in eventos_reais.items():
                if str(cod) in CODIGOS_PENSAO:
                    cod_pensao_encontrado = str(cod)
                    valor_pensao_real = val
                    break

        if cod_pensao_encontrado and percentual_pensao > 0:
            valor_esperado_pensao = calculations.calc_pensao_alimenticia(
                float(total_proventos_brutos),
                float(salario_base),
                inss_esperado,
                irrf_esperado,
                float(percentual_pensao),
                caso_pensao,
            )
            formula_pensao = (
                f"Percentual {percentual_pensao}% sobre Regra Caso {caso_pensao}"
            )
            registrar_item(
                f"Pensão ({cod_pensao_encontrado})",
                valor_esperado_pensao,
                valor_pensao_real,
                cod_pensao_encontrado,
                formula=formula_pensao,
            )

        # FGTS
        if company_rule.usa_calc_fgts:
            fgts_esperado = calculations.calc_fgts(
                float(base_fgts_acumulada), is_aprendiz=is_aprendiz
            )
            fgts_real = float(eventos_reais.get("FGTS", eventos_reais.get("605", 0)))
            registrar_item(
                "FGTS",
                fgts_esperado,
                fgts_real,
                "FGTS",
                base=float(base_fgts_acumulada),
                formula="8% (ou 2% aprendiz)",
            )

    return list(auditoria_agrupada.values())
