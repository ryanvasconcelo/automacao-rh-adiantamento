# backend/src/fopag/fopag_auditor.py

import re
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from src.fopag import calculations
from src.fopag import fopag_rules_catalog


def D(valor):
    """Converte para Decimal de forma segura."""
    if valor is None:
        return Decimal("0.00")
    return Decimal(str(valor))


def money_round(valor_decimal):
    """Arredonda Decimal para 2 casas e devolve float."""
    if not isinstance(valor_decimal, Decimal):
        valor_decimal = D(valor_decimal)
    return float(valor_decimal.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


CODIGOS_IGNORAR_AUDITORIA = [
    "600",
    "601",
    "602",
    "603",
    "604",
    "605",
    "606",
    "607",
    "608",
    "609",
    "610",
    "900",
    "901",
    "902",
    "903",
    "904",
    "919",
    "920",
    "922",
    "946",
    "947",
    "948",
    "949",
    "998",
    "999",
]


def run_fopag_audit(
    company_code: str,
    employee_payroll_data: list,
    ano: int,
    mes: int,
    caso_pensao: int = 2,
) -> list:
    print(
        f"[Auditor V18 - Regime de Caixa & Lista Negra de Isentos] Processando {company_code} - {mes}/{ano}..."
    )

    try:
        company_rule = fopag_rules_catalog.get_company_rule(company_code)
    except Exception as e:
        return [{"error": f"Erro de regras: {e}"}]

    auditoria_agrupada = {}

    for funcionario in employee_payroll_data:
        matricula = funcionario.get("matricula", "N/A")
        nome = funcionario.get("nome", "N/A")
        dependentes = funcionario.get("dependentes", 0)

        # --- DADOS DE TEMPO ---
        data_admissao = None
        dias_trabalhados = 30

        if funcionario.get("data_admissao"):
            try:
                data_admissao = datetime.strptime(
                    str(funcionario.get("data_admissao"))[:10], "%Y-%m-%d"
                ).date()
                if data_admissao.year == ano and data_admissao.month == mes:
                    dias_trabalhados = max(1, 30 - data_admissao.day + 1)
            except:
                pass

        fator_prop_padrao = dias_trabalhados / 30.0
        fator_prop_plus = (dias_trabalhados + 1) / 30.0

        dados_cal = calculations.get_dias_uteis_dsr(ano, mes, data_admissao)
        dias_uteis, dias_dsr = dados_cal["dias_uteis"], dados_cal["dias_dsr"]

        carga_horaria = float(funcionario.get("carga_horaria", 220))
        is_aprendiz = "aprendiz" in str(funcionario.get("cargo", "")).lower()

        if matricula not in auditoria_agrupada:
            auditoria_agrupada[matricula] = {
                "matricula": matricula,
                "nome": nome,
                "itens": [],
                "tem_divergencia": False,
                "totais": {"proventos": 0.0, "descontos": 0.0, "liquido": 0.0},
                "debug": {
                    "eventos_irrf": [],
                    "composicao_base_he": [],
                },
            }

        def registrar(
            evt,
            v_esp,
            v_real,
            cod,
            msg="",
            base=0.0,
            formula="",
            memoria=None,
            tipo="P",
        ):
            dec_esp = D(v_esp)
            dec_real = D(v_real)
            diff = dec_real - dec_esp

            is_ok = abs(diff) <= Decimal("0.10")
            if not is_ok and dec_esp > D("0"):
                if (abs(diff) / dec_esp) < Decimal("0.02"):
                    is_ok = True

            status = "OK" if is_ok else "ERRO"
            if not is_ok:
                auditoria_agrupada[matricula]["tem_divergencia"] = True
                if not msg:
                    msg = f"Esp: {dec_esp:.2f} | Real: {dec_real:.2f}"

            auditoria_agrupada[matricula]["itens"].append(
                {
                    "codigo": str(cod),
                    "evento": evt,
                    "esperado": money_round(dec_esp),
                    "real": money_round(dec_real),
                    "diferenca": money_round(diff),
                    "status": status,
                    "msg": msg,
                    "base": float(base),
                    "formula": formula,
                    "memoria": memoria,
                    "tipo_evento": tipo,
                }
            )

        # --- VARIÁVEIS DE ACUMULAÇÃO ---
        salario_base_contratual = D("0")
        base_he_fixa = D("0")
        pool_gratificacoes = D("0")
        pool_noturno = D("0")
        salario_contratual_cheio = D("0")

        nossa_base_inss = D("0")
        nossa_base_irrf = D("0")
        nossa_base_fgts = D("0")

        fortes_base_inss = D("0")
        fortes_base_irrf = D("0")
        fortes_base_fgts = D("0")

        total_variaveis_dsr = D("0")
        total_proventos = D("0")
        total_descontos = D("0")

        lista_eventos = funcionario.get("eventos", [])

        # Listas para ordenação
        eventos_fixos = []
        eventos_adicionais = []
        eventos_noturno = []
        eventos_he = []
        eventos_faltas = []
        eventos_dsr = []
        eventos_outros = []

        # --- 1. PRÉ-PROCESSAMENTO ---
        for ev in lista_eventos:
            cod = ev["codigo"]
            val = D(ev["valor"])
            nome_upper = ev["descricao"].upper()

            # Captura bases Fortes
            if cod == "602":
                fortes_base_inss = val
                continue
            elif cod == "603":
                fortes_base_irrf = val
                continue
            elif cod == "604":
                fortes_base_fgts = val
                continue
            elif cod in ["600", "601"]:
                salario_contratual_cheio = val
                continue

            if cod in CODIGOS_IGNORAR_AUDITORIA or cod in ["310", "311", "605"]:
                continue

            # Classificação
            if cod == company_rule.cod_salario_base or cod in ["11", "001", "1"]:
                eventos_fixos.append(ev)
            elif any(
                x in nome_upper
                for x in [
                    "PERICULOSIDADE",
                    "INSALUBRIDADE",
                    "GRATIFICA",
                    "PRATICAGEM",
                    "COMANDO",
                    "COZINHEIRA",
                    "FUNÇÃO",
                    "CARGO",
                    "ANU",
                    "QUEBRA",
                    "PRÊMIO",
                ]
            ):
                eventos_adicionais.append(ev)
            elif "NOTURNO" in nome_upper:
                eventos_noturno.append(ev)
            elif any(x in nome_upper for x in ["HORA", "HE", "EXTRA"]):
                eventos_he.append(ev)
            elif any(x in nome_upper for x in ["FALTA", "ATRASO"]):
                eventos_faltas.append(ev)
            elif "DSR" in nome_upper or "DESCANSO" in nome_upper:
                eventos_dsr.append(ev)
            else:
                eventos_outros.append(ev)

        # =========================================================================
        # LÓGICA V18: REGIME DE CAIXA FORÇADO & LISTA NEGRA DE ISENTOS
        # =========================================================================

        def processar_acumuladores(ev, valor, operacao="soma"):
            """
            Gerencia a incidência.
            V18: Força abatimento de Adiantamentos (Regime de Caixa) e bloqueia verbas indenizatórias.
            """
            nonlocal nossa_base_inss, nossa_base_irrf, nossa_base_fgts

            # 1. Recupera flags do banco
            inc_inss = ev.get("incidencias", {}).get("inss", False)
            inc_irrf = ev.get("incidencias", {}).get("irrf", False)
            inc_fgts = ev.get("incidencias", {}).get("fgts", False)

            nome_upper = ev["descricao"].upper()

            if operacao == "soma":
                # --- LISTA NEGRA DE PROVENTOS (Bloqueia ganho isento mesmo se flag=True) ---
                # Resolve o problema do Clayton (Indenizações inflando a base)
                keywords_isentos = [
                    "REEMBOLSO",
                    "INDENIZA",
                    "SALARIO FAMILIA",
                    "SALÁRIO FAMÍLIA",
                    "AJUDA DE CUSTO",
                    "ABONO PECUNI",
                    "VALE TRANSPORTE",
                    "MULTA",
                    "AVISO PREVIO",
                    "AVISO PRÉVIO",
                    "FERIAS PROPORCIONAIS",
                    "FÉRIAS PROPORCIONAIS",
                    "TERCO CONST",
                    "TERÇO CONST",
                    "1/3 FERIAS",
                    "1/3 FÉRIAS",
                    "LICENÇA PRÊMIO",
                ]

                if any(k in nome_upper for k in keywords_isentos):
                    inc_inss = False
                    inc_irrf = False
                    inc_fgts = False

                if inc_inss:
                    nossa_base_inss += valor
                if inc_irrf:
                    nossa_base_irrf += valor
                if inc_fgts:
                    nossa_base_fgts += valor

            elif operacao == "subtrai":
                # --- TRATAMENTO ESPECIAL DE DESCONTOS ---

                # A) ADIANTAMENTO SALARIAL (Regime de Caixa - Lei do IRRF)
                # O Adiantamento Salarial pago no dia 20 DEVE ser deduzido da base de cálculo
                # do IRRF mensal para evitar dupla tributação. O Fortes faz isso automaticamente.
                # Se o nome é "Adiantamento", nós FORÇAMOS a dedução do IRRF.
                if "ADIANT" in nome_upper and "SALARIAL" in nome_upper:  # Refinando
                    inc_irrf = True
                elif "ADIANT" in nome_upper:  # Caso genérico "Adiantamento"
                    inc_irrf = True

                # B) PENSÃO ALIMENTÍCIA (Sempre deduz IRRF)
                if any(k in nome_upper for k in ["PENSÃO", "ALIMENTOS", "ALIMENTÍCIA"]):
                    inc_irrf = True  # Força Sim
                    inc_inss = False  # Força Não

                # C) FINANCEIROS PUROS (Não deduzem NADA)
                # Empréstimos, Farmácia, Planos de Saúde (exceto parte da empresa, mas aqui é desconto do funcionário)
                keywords_financeiros_puros = [
                    "EMPRÉSTIMO",
                    "CONSIGNADO",
                    "FARMÁCIA",
                    "PLANO",
                    "UNIMED",
                    "BRADESCO",
                    "SEGURO",
                    "VALE TRANSPORTE",
                ]

                if any(k in nome_upper for k in keywords_financeiros_puros):
                    # Bloqueia tudo, empréstimo é dívida pessoal, não reduz imposto.
                    inc_inss = False
                    inc_irrf = False
                    inc_fgts = False

                # Processa os abatimentos finais
                if inc_inss:
                    nossa_base_inss -= valor
                if inc_irrf:
                    nossa_base_irrf -= valor
                if inc_fgts:
                    nossa_base_fgts -= valor

        # --- 2. SALÁRIO BASE ---
        for ev in eventos_fixos:
            cod, val_real = ev["codigo"], D(ev["valor"])
            salario_base_contratual = val_real
            base_he_fixa += val_real
            total_proventos += val_real

            processar_acumuladores(ev, val_real, "soma")
            registrar(
                "Salário Base", val_real, val_real, cod, formula="Salário Mês", tipo="P"
            )

        # --- 3. ADICIONAIS ---
        for ev in eventos_adicionais:
            cod, val_real = ev["codigo"], D(ev["valor"])
            nome = ev["descricao"]
            ref = D(ev["referencia"])
            nome_upper = nome.upper()
            v_esp = val_real
            formula = "Leitura Direta"

            is_gratificacao = any(
                x in nome_upper
                for x in [
                    "GRATIFICA",
                    "PRATICAGEM",
                    "COMANDO",
                    "FUNÇÃO",
                    "CARGO",
                    "COZINHEIRA",
                ]
            )
            is_insalub_peric = (
                "INSALUBRIDADE" in nome_upper or "PERICULOSIDADE" in nome_upper
            )
            v_full_calc = D("0")
            base_ref_nome = ""

            if "PERICULOSIDADE" in nome_upper:
                v_full_calc = D(
                    calculations.calc_periculosidade(float(salario_base_contratual))
                )
                base_ref_nome = "30% Salário Base"
            elif "INSALUBRIDADE" in nome_upper:
                grau = 0.20
                ref_float = float(ref)
                if ref_float >= 1.0:
                    ref_float /= 100.0
                if abs(ref_float - 0.10) < 0.01:
                    grau = 0.10
                elif abs(ref_float - 0.40) < 0.01:
                    grau = 0.40
                v_full_calc = D(calculations.calc_insalubridade(grau=grau))
                base_ref_nome = f"Grau {grau*100:.0f}% x SM"

            if v_full_calc > D("0"):
                v_prop_padrao = v_full_calc * D(fator_prop_padrao)
                v_prop_plus = v_full_calc * D(fator_prop_plus)
                diff_full = abs(v_full_calc - val_real)
                diff_prop = abs(v_prop_padrao - val_real)
                min_diff = min(diff_full, diff_prop, abs(v_prop_plus - val_real))

                if min_diff == diff_full:
                    v_esp = v_full_calc
                    formula = f"{base_ref_nome} (Integral)"
                elif min_diff == diff_prop:
                    v_esp = v_prop_padrao
                    formula = f"{base_ref_nome} (Prop. {dias_trabalhados}/30)"
                else:
                    v_esp = v_prop_plus
                    formula = f"{base_ref_nome} (Prop. {dias_trabalhados+1}/30)"

            if abs(ref - val_real) < D("0.10") and ref > D("10"):
                v_esp = val_real
                formula = "Valor Informado (Ref=Valor)"

            if is_insalub_peric:
                base_he_fixa += v_esp
            elif is_gratificacao:
                pool_gratificacoes += v_esp
            else:
                base_he_fixa += v_esp

            total_proventos += v_esp
            processar_acumuladores(ev, v_esp, "soma")
            registrar(nome, v_esp, val_real, cod, formula=formula, tipo="P")

        # --- 4. ADICIONAL NOTURNO ---
        for ev in eventos_noturno:
            cod, val_real = ev["codigo"], D(ev["valor"])
            ref = D(ev["referencia"])
            qtd_horas = calculations.time_to_decimal(float(ref))
            v_esp = D(
                calculations.calc_adicional_noturno(
                    float(salario_base_contratual), qtd_horas, carga_horaria
                )
            )
            formula = "20% Salário Base"

            if abs(ref - val_real) < D("0.10") and ref > D("10"):
                v_esp = val_real
                formula = "Valor Informado"

            pool_noturno += v_esp
            total_variaveis_dsr += v_esp
            total_proventos += v_esp
            processar_acumuladores(ev, v_esp, "soma")
            registrar(ev["descricao"], v_esp, val_real, cod, formula=formula, tipo="P")

        # --- 5. OUTROS ---
        for ev in eventos_outros:
            cod, val_real = ev["codigo"], D(ev["valor"])
            nome = ev["descricao"]
            nome_upper = nome.upper()
            v_esp = val_real
            formula = "Leitura Direta"

            if "TRANSPORTE" in nome_upper and "VALE" in nome_upper and ev["tipo"] == 2:
                v_esp = D(
                    calculations.calc_vale_transporte(float(salario_base_contratual))
                )
                formula = "6% Salário Base"
            elif "FAMILIA" in nome_upper:
                qtd_filhos = funcionario.get("dependentes_salario_familia", 0)
                v_esp = D(
                    calculations.calc_salario_familia(
                        float(nossa_base_inss), qtd_filhos
                    )
                )
                formula = f"{qtd_filhos} filhos"

            if ev["tipo"] == 1:
                # PROVENTO
                total_proventos += v_esp
                is_salario_familia = "FAMILIA" in nome_upper
                incide_inss = ev.get("incidencias", {}).get("inss")
                if incide_inss and not is_salario_familia:
                    pool_gratificacoes += v_esp
                processar_acumuladores(ev, v_esp, "soma")
                tipo_reg = "P"
            else:
                # DESCONTO
                total_descontos += v_esp
                processar_acumuladores(ev, v_esp, "subtrai")
                tipo_reg = "D"

            registrar(nome, v_esp, val_real, cod, formula=formula, tipo=tipo_reg)

        # --- 6. HORAS EXTRAS ---
        for ev in eventos_he:
            cod, val_real = ev["codigo"], D(ev["valor"])
            ref = D(ev["referencia"])
            qtd_horas = calculations.time_to_decimal(float(ref))
            percentual = 50
            if "100" in ev["descricao"] or cod == "61":
                percentual = 100
            elif "60" in ev["descricao"] or cod == "62":
                percentual = 60

            bases_teste = [
                (base_he_fixa, "Base Fixa"),
                (base_he_fixa + pool_gratificacoes, "Base Fixa + Gratificações"),
                (base_he_fixa + pool_noturno, "Base Fixa + Noturno"),
                (base_he_fixa + pool_noturno + pool_gratificacoes, "Base Completa"),
            ]
            if salario_contratual_cheio > D("0"):
                bases_teste.append(
                    (salario_contratual_cheio, "Salário Contratual Cheio")
                )

            v_esp_final = D("0")
            formula_final = ""
            menor_diff = Decimal("999999")

            for base_val, base_nome in bases_teste:
                v_teste = D(
                    calculations.calc_he_generica(
                        float(base_val), qtd_horas, percentual, carga_horaria
                    )
                )
                diff = abs(v_teste - val_real)
                if diff < menor_diff:
                    menor_diff = diff
                    v_esp_final = v_teste
                    formula_final = f"{base_nome} {float(base_val):.2f} × {percentual}%"

            total_variaveis_dsr += v_esp_final
            total_proventos += v_esp_final
            processar_acumuladores(ev, v_esp_final, "soma")
            registrar(
                ev["descricao"],
                v_esp_final,
                val_real,
                cod,
                formula=formula_final,
                tipo="P",
            )

        # --- 7. FALTAS ---
        for ev in eventos_faltas:
            cod, val_real = ev["codigo"], D(ev["valor"])
            ref = D(ev["referencia"])
            qtd = float(ref) if ref > D("0") else 1.0

            bases_teste = [base_he_fixa, base_he_fixa + pool_gratificacoes]
            v_esp_final = D("0")
            formula_final = ""
            menor_diff = Decimal("999999")

            for base_val in bases_teste:
                val_dia = D(round((float(base_val) / 30) * qtd, 2))
                val_hora = D(round((float(base_val) / carga_horaria) * qtd, 2))
                if abs(val_dia - val_real) < menor_diff:
                    menor_diff = abs(val_dia - val_real)
                    v_esp_final = val_dia
                    formula_final = f"Desconto {qtd} Dias (Base {base_val:.2f})"
                if abs(val_hora - val_real) < menor_diff:
                    menor_diff = abs(val_hora - val_real)
                    v_esp_final = val_hora
                    formula_final = f"Desconto {qtd} Horas (Base {base_val:.2f})"

            total_descontos += v_esp_final
            processar_acumuladores(ev, v_esp_final, "subtrai")
            registrar(
                ev["descricao"],
                v_esp_final,
                val_real,
                cod,
                formula=formula_final,
                tipo="D",
            )

        # --- 8. DSR ---
        for ev in eventos_dsr:
            cod, val_real = ev["codigo"], D(ev["valor"])
            nome = ev["descricao"]
            v_esp = val_real
            formula = "DSR (Base desconhecida)"

            if total_variaveis_dsr > D("0") and dias_uteis > 0:
                v_dsr = D(
                    calculations.calc_dsr(
                        float(total_variaveis_dsr), dias_uteis, dias_dsr
                    )
                )
                if abs(v_dsr - val_real) < D("5"):
                    v_esp = v_dsr
                    formula = "Reflexo Variáveis"

            if ev["tipo"] == 1:
                total_proventos += v_esp
                processar_acumuladores(ev, v_esp, "soma")
                tipo_reg = "P"
            else:
                total_descontos += v_esp
                processar_acumuladores(ev, v_esp, "subtrai")
                tipo_reg = "D"

            registrar(nome, v_esp, val_real, cod, formula=formula, tipo=tipo_reg)

        # --- 9. IMPOSTOS (DUPLA CHECAGEM INTELIGENTE) ---
        inss_real = D(
            next((e["valor"] for e in lista_eventos if e["codigo"] == "310"), 0)
        )

        # INSS
        inss_fortes = D(calculations.calc_inss(float(fortes_base_inss)))
        diff_fortes = abs(inss_fortes - inss_real)

        inss_nossa = D(calculations.calc_inss(float(nossa_base_inss)))
        diff_nossa = abs(inss_nossa - inss_real)

        if diff_fortes <= diff_nossa and diff_fortes < D("5.0"):
            base_inss_final = fortes_base_inss
            inss_esp = inss_fortes
            formula_inss = "Tab. 2026 (Base Banco)"
        else:
            base_inss_final = nossa_base_inss
            inss_esp = inss_nossa
            formula_inss = "Tab. 2026 (Base Calc. V18)"

        registrar(
            "INSS",
            inss_esp,
            inss_real,
            "310",
            base=float(base_inss_final),
            formula=formula_inss,
            tipo="D",
        )
        total_descontos += inss_esp

        # IRRF
        inss_real_val = inss_real
        res_fortes = calculations.calc_irrf_detalhado(
            float(fortes_base_irrf), float(inss_real_val), dependentes
        )
        irrf_fortes = D(res_fortes["valor"])

        res_nossa = calculations.calc_irrf_detalhado(
            float(nossa_base_irrf), float(inss_real_val), dependentes
        )
        irrf_nossa = D(res_nossa["valor"])

        irrf_real = D(
            next((e["valor"] for e in lista_eventos if e["codigo"] == "311"), 0)
        )
        diff_fortes_irrf = abs(irrf_fortes - irrf_real)
        diff_nossa_irrf = abs(irrf_nossa - irrf_real)

        if diff_fortes_irrf <= diff_nossa_irrf and diff_fortes_irrf < D("5.0"):
            base_irrf_final = fortes_base_irrf
            irrf_esp = irrf_fortes
            memoria = res_fortes["memoria"]
            formula_irrf = "Tab. 2026 (Base Banco)"
        else:
            base_irrf_final = nossa_base_irrf
            irrf_esp = irrf_nossa
            memoria = res_nossa["memoria"]
            formula_irrf = "Tab. 2026 (Base Calc. V18)"

        registrar(
            "IRRF",
            irrf_esp,
            irrf_real,
            "311",
            base=float(base_irrf_final),
            formula=formula_irrf,
            memoria=memoria,
            tipo="D",
        )
        total_descontos += irrf_esp

        # FGTS
        base_fgts_final = (
            fortes_base_fgts if fortes_base_fgts > D("0") else nossa_base_fgts
        )
        fgts_esp = D(calculations.calc_fgts(float(base_fgts_final), is_aprendiz))
        fgts_real = D(
            next((e["valor"] for e in lista_eventos if e["codigo"] == "605"), 0)
        )
        registrar(
            "FGTS",
            fgts_esp,
            fgts_real,
            "605",
            base=float(base_fgts_final),
            formula="8%" if not is_aprendiz else "2%",
            tipo="D",
        )

        auditoria_agrupada[matricula]["totais"] = {
            "proventos": float(total_proventos),
            "descontos": float(total_descontos),
            "liquido": float(total_proventos - total_descontos),
        }

    return list(auditoria_agrupada.values())
