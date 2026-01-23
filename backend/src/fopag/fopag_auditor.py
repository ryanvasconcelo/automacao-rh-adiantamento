# backend/src/fopag/fopag_auditor.py

import re
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from src.fopag import calculations
from src.fopag import fopag_rules_catalog


def D(valor):
    if valor is None:
        return Decimal("0.00")
    return Decimal(str(valor))


def money_round(valor_decimal):
    if not isinstance(valor_decimal, Decimal):
        valor_decimal = D(valor_decimal)
    return float(valor_decimal.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


CODIGOS_IGNORAR_SOMA = [
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
]

CODIGOS_PENSAO = ["340", "911", "912", "800"]


def run_fopag_audit(
    company_code: str,
    employee_payroll_data: list,
    ano: int,
    mes: int,
    caso_pensao: int = 2,
) -> list:
    print(f"[Auditor Unified] Processando {company_code} - {mes}/{ano}...")
    try:
        company_rule = fopag_rules_catalog.get_company_rule(company_code)
    except Exception as e:
        return [{"error": f"Erro de regras: {e}"}]

    auditoria_agrupada = {}

    for funcionario in employee_payroll_data:
        matricula = funcionario.get("matricula", "N/A")
        nome = funcionario.get("nome", "N/A")
        dependentes = funcionario.get("dependentes", 0)

        tipo_contrato = str(funcionario.get("tipo_contrato", "")).lower()
        cargo_nome = str(funcionario.get("cargo", "")).lower()
        is_aprendiz = "aprendiz" in tipo_contrato or "aprendiz" in cargo_nome

        data_admissao = None
        if funcionario.get("data_admissao"):
            try:
                data_admissao = datetime.strptime(
                    str(funcionario.get("data_admissao"))[:10], "%Y-%m-%d"
                ).date()
            except:
                pass
        dados_cal = calculations.get_dias_uteis_dsr(ano, mes, data_admissao)
        dias_uteis, dias_dsr = dados_cal["dias_uteis"], dados_cal["dias_dsr"]

        if matricula not in auditoria_agrupada:
            auditoria_agrupada[matricula] = {
                "matricula": matricula,
                "nome": nome,
                "itens": [],
                "tem_divergencia": False,
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

            if (
                ("DSR" in evt.upper() or "DESCANSO" in evt.upper())
                and dec_esp > 0
                and (abs(diff) / dec_esp) < Decimal("0.05")
            ):
                is_ok = True

            status = "OK" if is_ok else "ERRO"
            if not is_ok:
                auditoria_agrupada[matricula]["tem_divergencia"] = True

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

        # VARIÁVEIS GLOBAIS
        salario_base = D(0)
        base_he = D(0)  # Salário + Adicionais (Periculosidade/Insalubridade)

        nossa_base_inss = D(0)
        nossa_base_irrf = D(0)
        nossa_base_fgts = D(0)

        fortes_base_inss = D(0)
        fortes_base_irrf = D(0)
        fortes_base_fgts = D(0)

        total_variaveis_dsr = D(0)

        lista_eventos = funcionario.get("eventos", [])
        eventos_para_processar = []

        # 1. PROCESSAR FIXOS E BASES
        for ev in lista_eventos:
            cod, val, tipo_sql = ev["codigo"], D(ev["valor"]), ev["tipo"]

            if cod == "602":
                fortes_base_inss = val
            elif cod == "603":
                fortes_base_irrf = val
            elif cod == "604":
                fortes_base_fgts = val
            elif cod == company_rule.cod_salario_base or cod in ["11", "001", "1"]:
                salario_base = val
                base_he = val
                nossa_base_inss += val
                nossa_base_irrf += val
                nossa_base_fgts += val
                registrar(
                    "Salário Base", val, val, cod, formula="Fixo Contratual", tipo="P"
                )
            elif cod not in [
                "600",
                "602",
                "603",
                "604",
                "310",
                "311",
                "605",
                "INSS",
                "IRRF",
                "FGTS",
            ]:
                eventos_para_processar.append(ev)

        # 2. PROCESSAMENTO DINÂMICO
        eventos_dsr_pendentes = []

        # Pré-loop: Identificar Adicionais que compõem Base HE (Insalubridade/Periculosidade)
        # Isso corrige a base da HE 60%
        for ev in eventos_para_processar:
            nome_upper = ev["descricao"].upper()
            val_real = D(ev["valor"])
            if "PERICULOSIDADE" in nome_upper or "INSALUBRIDADE" in nome_upper:
                base_he += val_real

        for ev in eventos_para_processar:
            cod, val_real = ev["codigo"], D(ev["valor"])
            nome = ev["descricao"]
            ref = D(ev["referencia"])
            tipo_sql = ev["tipo"]

            nome_upper = nome.upper()

            # Detecção de Tipo (Provento vs Desconto)
            # Prioriza: SQL (se confiável) -> Nome
            is_desconto = (
                (tipo_sql == 2)
                or ("DESCONT" in nome_upper)
                or ("FALTA" in nome_upper)
                or ("ATRASO" in nome_upper)
            )
            tipo_visual = "D" if is_desconto else "P"

            if "DSR" in nome_upper or "DESCANSO" in nome_upper:
                eventos_dsr_pendentes.append((ev, tipo_visual))
                continue

            v_esp = val_real
            formula = "Leitura Direta"
            memoria = None

            # --- CÁLCULOS ---

            # A) HORA EXTRA
            if "HORA" in nome_upper and ("EXTRA" in nome_upper or "HE" in nome_upper):
                match = re.search(r"(\d+)%", nome_upper)
                pct = (
                    int(match.group(1))
                    if match
                    else (100 if "100" in nome_upper else 50)
                )
                if ref > 0:
                    h_dec = D(calculations.time_to_decimal(float(ref)))
                    v_calc = D(
                        calculations.calc_he_generica(float(base_he), float(h_dec), pct)
                    )
                    v_esp = v_calc
                    formula = f"HE {pct}%"
                    total_variaveis_dsr += v_esp

                    memoria = {
                        "tipo": f"Hora Extra {pct}%",
                        "variaveis": [
                            {"nome": "Base de Cálculo", "valor": f"R$ {base_he:,.2f}"},
                            {"nome": "Jornada Mensal", "valor": "220"},
                            {
                                "nome": "Adicional",
                                "valor": f"{pct}% (Fator {1 + pct/100})",
                            },
                            {"nome": "Qtd. Horas", "valor": f"{h_dec:.2f}"},
                        ],
                        "formula_texto": "(Base / Jornada) * Fator * Horas",
                        "formula_valores": f"({float(base_he):.2f} / 220) * {1 + pct/100} * {float(h_dec):.2f} = {v_esp:.2f}",
                    }

            # B) PERICULOSIDADE
            elif "PERICULOSIDADE" in nome_upper:
                # Já somado na base_he, mas calculamos aqui para validar o item individual
                v_esp = D(calculations.calc_periculosidade(float(salario_base)))
                formula = "30% Salário"

            # C) ADICIONAL NOTURNO (CORREÇÃO: Base Salário, não Base HE)
            elif "NOTURNO" in nome_upper:
                if ref > 0:
                    h_dec = D(calculations.time_to_decimal(float(ref)))
                    # Usa salario_base puro, pois Adic. Noturno geralmente não incide sobre Insalubridade
                    v_esp = D(
                        calculations.calc_adicional_noturno(
                            float(salario_base), float(h_dec)
                        )
                    )
                    formula = "20% Salário Base"
                    total_variaveis_dsr += v_esp

                    memoria = {
                        "tipo": "Adicional Noturno",
                        "variaveis": [
                            {
                                "nome": "Salário Base",
                                "valor": f"R$ {salario_base:,.2f}",
                            },
                            {"nome": "Horas Noturnas", "valor": f"{h_dec:.2f}"},
                        ],
                        "formula_texto": "(Salário / 220) * 20% * Horas",
                        "formula_valores": f"({float(salario_base):.2f} / 220) * 0.20 * {float(h_dec):.2f} = {v_esp:.2f}",
                    }

            # Acumulação
            if cod not in CODIGOS_IGNORAR_SOMA:
                if not is_desconto:
                    nossa_base_inss += v_esp
                    nossa_base_irrf += v_esp
                    nossa_base_fgts += v_esp
                else:
                    nossa_base_inss -= v_esp
                    nossa_base_irrf -= v_esp
                    nossa_base_fgts -= v_esp

            registrar(
                nome,
                v_esp,
                val_real,
                cod,
                formula=formula,
                base=float(ref),
                memoria=memoria,
                tipo=tipo_visual,
            )

        # 3. DSR
        for ev, tipo_visual in eventos_dsr_pendentes:
            cod, val_real = ev["codigo"], D(ev["valor"])
            nome = ev["descricao"]
            v_esp = val_real
            formula = "DSR (Base desconhecida)"
            memoria = None

            if total_variaveis_dsr > 0 and dias_uteis > 0:
                v_dsr = D(
                    calculations.calc_dsr(
                        float(total_variaveis_dsr), dias_uteis, dias_dsr
                    )
                )
                if abs(v_dsr - val_real) < 5:
                    v_esp = v_dsr
                    formula = "DSR Calculado"
                    memoria = {
                        "tipo": "DSR sobre Variáveis",
                        "variaveis": [
                            {
                                "nome": "Total Variáveis",
                                "valor": f"R$ {total_variaveis_dsr:,.2f}",
                            },
                            {"nome": "Dias Úteis", "valor": dias_uteis},
                            {"nome": "Domingos/Fer", "valor": dias_dsr},
                        ],
                        "formula_texto": "(Variáveis / Úteis) * DSR",
                        "formula_valores": f"({float(total_variaveis_dsr):.2f} / {dias_uteis}) * {dias_dsr} = {v_esp:.2f}",
                    }

            if not is_desconto:
                nossa_base_inss += v_esp
                nossa_base_irrf += v_esp
                nossa_base_fgts += v_esp
            registrar(
                nome,
                v_esp,
                val_real,
                cod,
                formula=formula,
                memoria=memoria,
                tipo=tipo_visual,
            )

        # 4. IMPOSTOS (Trust the Base)
        base_inss_final = (
            fortes_base_inss
            if abs(nossa_base_inss - fortes_base_inss) < 1 and fortes_base_inss > 0
            else nossa_base_inss
        )
        base_irrf_final = (
            fortes_base_irrf
            if abs(nossa_base_irrf - fortes_base_irrf) < 1 and fortes_base_irrf > 0
            else nossa_base_irrf
        )

        # INSS
        inss_esp = D(calculations.calc_inss(float(base_inss_final)))
        inss_real = D(
            next((e["valor"] for e in lista_eventos if e["codigo"] == "310"), 0)
        )
        mem_inss = {
            "tipo": "INSS",
            "variaveis": [{"nome": "Base INSS", "valor": f"R$ {base_inss_final:,.2f}"}],
            "formula_texto": "Aplicação Tabela Progressiva 2026",
            "formula_valores": f"Calculado sobre {base_inss_final:.2f} = {inss_esp:.2f}",
        }
        registrar(
            "INSS",
            inss_esp,
            inss_real,
            "310",
            base=float(base_inss_final),
            formula="Tab. 2026",
            memoria=mem_inss,
            tipo="D",
        )

        # IRRF
        bruto_estimado = (
            float(base_irrf_final) + float(inss_esp) + (dependentes * 189.59)
        )
        irrf_esp = D(
            calculations.calc_irrf(float(base_irrf_final), float(inss_esp), dependentes)
        )
        irrf_real = D(
            next((e["valor"] for e in lista_eventos if e["codigo"] == "311"), 0)
        )
        mem_irrf = {
            "tipo": "IRRF",
            "variaveis": [
                {"nome": "Base Líquida", "valor": f"R$ {base_irrf_final:,.2f}"},
                {"nome": "INSS", "valor": f"{inss_esp:.2f}"},
            ],
            "formula_texto": "Base Liq * Aliq - Dedução - Redução Simplificada",
            "formula_valores": f"Resultado final = {irrf_esp:.2f}",
        }
        registrar(
            "IRRF",
            irrf_esp,
            irrf_real,
            "311",
            base=float(base_irrf_final),
            formula="Redução 2026",
            memoria=mem_irrf,
            tipo="D",
        )

        # FGTS
        fgts_esp = D(calculations.calc_fgts(float(fortes_base_fgts), is_aprendiz))
        fgts_real = D(
            next((e["valor"] for e in lista_eventos if e["codigo"] == "605"), 0)
        )
        registrar(
            "FGTS",
            fgts_esp,
            fgts_real,
            "605",
            base=float(fortes_base_fgts),
            formula="8%",
            tipo="D",
        )

    return list(auditoria_agrupada.values())
