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
CODIGOS_IGNORAR = [
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


def run_fopag_audit(
    company_code: str,
    employee_payroll_data: list,
    ano: int,
    mes: int,
    caso_pensao: int = 2,
) -> list:
    print(f"[Auditor 2026] Processando {company_code} - {mes}/{ano}...")
    try:
        company_rule = fopag_rules_catalog.get_company_rule(company_code)
    except Exception as e:
        return [{"error": f"Erro de regras: {e}"}]

    auditoria_agrupada = {}

    for funcionario in employee_payroll_data:
        matricula = funcionario.get("matricula", "N/A")
        nome = funcionario.get("nome", "N/A")
        dependentes = funcionario.get("dependentes", 0)

        # Prepara dados
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
        dias_uteis, dias_dsr = (
            dados_calendario["dias_uteis"],
            dados_calendario["dias_dsr"],
        )

        if matricula not in auditoria_agrupada:
            auditoria_agrupada[matricula] = {
                "matricula": matricula,
                "nome": nome,
                "itens": [],
                "tem_divergencia": False,
            }

        # --- REGISTRADOR COM SUPORTE A MEMÓRIA DETALHADA ---
        def registrar_item(
            evento_nome,
            v_esperado,
            v_real,
            codigo,
            msg="",
            base=None,
            formula="",
            memoria=None,
        ):
            diferenca = v_real - v_esperado
            is_ok = False
            if round(abs(diferenca), 2) <= 0.10:
                is_ok = True
            elif (
                ("descanso" in evento_nome.lower() or "dsr" in evento_nome.lower())
                and v_esperado > 0
                and (abs(diferenca) / v_esperado) < 0.05
            ):
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
                    "msg": msg,
                    "base": round(base, 2) if base else 0.0,
                    "formula": formula,
                    "memoria": memoria,  # Objeto JSON detalhado
                }
            )

        # VARIÁVEIS
        salario_base = D(0)
        base_he = D(0)
        base_inss_acumulada = D(0)
        base_irrf_acumulada = D(0)
        base_fgts_acumulada = D(0)
        total_proventos_brutos = D(0)
        total_variaveis_para_dsr = D(0)

        # 1. FIXOS
        for evento in funcionario.get("proventos_base", []):
            cod, val = evento.get("codigo"), D(evento.get("valor", 0))
            props = fopag_rules_catalog.get_event_properties(cod)
            nome_ev = props.description if props else "Salário Base"

            if cod == company_rule.cod_salario_base or cod in ["11", "001", "1"]:
                salario_base = val
                base_he = val
                registrar_item(
                    nome_ev, float(val), float(val), cod, formula="Fixo Contratual"
                )

            if props:
                if props.incide_inss:
                    base_inss_acumulada += val
                if props.incide_irrf:
                    base_irrf_acumulada += val
                if props.incide_fgts:
                    base_fgts_acumulada += val
                total_proventos_brutos += val

        # 2. DINÂMICO
        eventos_reais = funcionario.get("eventos_calculados_fortes", {})
        lista_eventos_completa = funcionario.get("eventos_variaveis_referencia", [])
        mapa_eventos = {e["codigo"]: e for e in lista_eventos_completa}

        eventos_dsr_pendentes = []

        for cod, val_float in eventos_reais.items():
            valor_real = D(val_float)
            if valor_real == 0:
                continue
            if (
                cod
                in [
                    company_rule.cod_salario_base,
                    "11",
                    "001",
                    "1",
                    "310",
                    "311",
                    "605",
                    "INSS",
                    "IRRF",
                    "FGTS",
                ]
                + CODIGOS_IGNORAR
            ):
                continue

            dados = mapa_eventos.get(cod, {})
            props = fopag_rules_catalog.get_event_properties(cod)
            nome = dados.get("descricao") or (
                props.description if props else f"Evento {cod}"
            )
            ref = D(dados.get("referencia", 0))
            nome_upper = nome.upper()

            if "DSR" in nome_upper or "DESCANSO" in nome_upper:
                eventos_dsr_pendentes.append((cod, nome, valor_real, ref))
                continue

            valor_esp = valor_real
            formula = "Original"
            memoria = None

            # --- CÁLCULO HE ---
            if "HORA" in nome_upper and ("EXTRA" in nome_upper or "HE" in nome_upper):
                match = re.search(r"(\d+)%", nome_upper)
                pct = (
                    int(match.group(1))
                    if match
                    else (100 if "100" in nome_upper else 50)
                )

                if ref > 0:
                    h_dec = D(calculations.time_to_decimal(ref))
                    v_calc = D(
                        calculations.calc_he_generica(float(base_he), float(h_dec), pct)
                    )
                    valor_esp = v_calc
                    formula = f"HE {pct}%"
                    total_variaveis_para_dsr += valor_esp

                    # Memória de Cálculo Rica
                    memoria = {
                        "tipo": "Cálculo de Hora Extra",
                        "variaveis": [
                            {
                                "nome": "Salário Base (Base HE)",
                                "valor": f"R$ {base_he:,.2f}",
                            },
                            {"nome": "Divisor", "valor": 220},
                            {"nome": "Adicional", "valor": f"{pct}%"},
                            {"nome": "Qtd. Horas", "valor": f"{h_dec:.2f}"},
                        ],
                        "passos": [
                            f"Valor Hora = {float(base_he):.2f} / 220 = {float(base_he)/220:.4f}",
                            f"Valor Hora + Adicional = Valor Hora * {1 + pct/100:.2f}",
                            f"Total = (Valor Hora + Adic) * {float(h_dec):.2f}",
                        ],
                        "resultado": f"R$ {float(valor_esp):.2f}",
                    }

            # --- PERICULOSIDADE ---
            elif "PERICULOSIDADE" in nome_upper:
                valor_esp = D(calculations.calc_periculosidade(float(salario_base)))
                formula = "30% Salário"
                base_he += valor_esp  # Periculosidade compõe base HE

                memoria = {
                    "tipo": "Adicional de Periculosidade",
                    "variaveis": [
                        {"nome": "Salário Base", "valor": f"R$ {salario_base:,.2f}"},
                        {"nome": "Percentual", "valor": "30%"},
                    ],
                    "passos": [f"{float(salario_base):.2f} * 0.30"],
                    "resultado": f"R$ {float(valor_esp):.2f}",
                }

            # Acumula bases
            valor_final_base = valor_esp
            if cod not in CODIGOS_NAO_SOMAM_PROVENTOS:
                total_proventos_brutos += valor_final_base
                base_inss_acumulada += valor_final_base
                base_irrf_acumulada += valor_final_base
                base_fgts_acumulada += valor_final_base

            registrar_item(
                nome,
                money_round(valor_esp),
                money_round(valor_real),
                cod,
                formula=formula,
                base=float(ref),
                memoria=memoria,
            )

        # DSR
        for cod, nome, valor_real, ref in eventos_dsr_pendentes:
            valor_esp = valor_real
            formula = "DSR (Base desconhecida)"
            memoria = None

            if total_variaveis_para_dsr > 0 and dias_uteis > 0:
                v_dsr = D(
                    calculations.calc_dsr(
                        float(total_variaveis_para_dsr), dias_uteis, dias_dsr
                    )
                )
                if abs(v_dsr - valor_real) < 5.00:
                    valor_esp = v_dsr
                    formula = f"DSR S/ Variáveis"
                    memoria = {
                        "tipo": "Descanso Semanal Remunerado",
                        "variaveis": [
                            {
                                "nome": "Total Variáveis (HE/Adic)",
                                "valor": f"R$ {total_variaveis_para_dsr:,.2f}",
                            },
                            {"nome": "Dias Úteis", "valor": dias_uteis},
                            {"nome": "Domingos/Feriados", "valor": dias_dsr},
                        ],
                        "passos": [
                            f"Média Diária = {float(total_variaveis_para_dsr):.2f} / {dias_uteis}",
                            f"Total = Média Diária * {dias_dsr}",
                        ],
                        "resultado": f"R$ {float(valor_esp):.2f}",
                    }

            total_proventos_brutos += valor_esp
            base_inss_acumulada += valor_esp
            base_irrf_acumulada += valor_esp
            base_fgts_acumulada += valor_esp

            registrar_item(
                nome,
                money_round(valor_esp),
                money_round(valor_real),
                cod,
                formula=formula,
                memoria=memoria,
            )

        # 3. IMPOSTOS (COM MEMÓRIA RICA)
        # INSS
        inss_esp = calculations.calc_inss(float(base_inss_acumulada))
        inss_real = float(
            eventos_reais.get("310", eventos_reais.get(company_rule.cod_inss, 0))
        )

        mem_inss = {
            "tipo": "INSS (Tabela Progressiva 2026)",
            "variaveis": [
                {"nome": "Base de Cálculo", "valor": f"R$ {base_inss_acumulada:,.2f}"}
            ],
            "passos": ["Aplicação das faixas progressivas sobre a base."],
            "resultado": f"R$ {inss_esp:.2f}",
        }
        registrar_item(
            "INSS",
            inss_esp,
            inss_real,
            "310",
            base=float(base_inss_acumulada),
            formula="Tab. 2026",
            memoria=mem_inss,
        )

        # IRRF
        irrf_esp = calculations.calc_irrf(
            float(base_irrf_acumulada), inss_esp, dependentes
        )
        irrf_real = float(
            eventos_reais.get("311", eventos_reais.get(company_rule.cod_irrf, 0))
        )

        base_liq_irrf = float(base_irrf_acumulada) - inss_esp - (dependentes * 189.59)

        mem_irrf = {
            "tipo": "IRRF (Nova Regra 2026)",
            "variaveis": [
                {"nome": "Rendimento Bruto", "valor": f"R$ {base_irrf_acumulada:,.2f}"},
                {"nome": "Dedução INSS", "valor": f"R$ {inss_esp:,.2f}"},
                {"nome": "Dependentes", "valor": dependentes},
                {"nome": "Base Líquida Legal", "valor": f"R$ {base_liq_irrf:,.2f}"},
            ],
            "passos": [
                "1. Calcular Imposto Parcial sobre Base Líquida (Tabela Progressiva)",
                "2. Calcular Redução Simplificada (Fórmula sobre Renda Bruta)",
                "3. Final = Max(0, Parcial - Redução)",
            ],
            "resultado": f"R$ {irrf_esp:.2f}",
        }
        registrar_item(
            "IRRF",
            irrf_esp,
            irrf_real,
            "311",
            base=float(base_irrf_acumulada),
            formula="Redução 2026",
            memoria=mem_irrf,
        )

        # FGTS
        fgts_esp = calculations.calc_fgts(float(base_fgts_acumulada), is_aprendiz)
        fgts_real = float(eventos_reais.get("605", 0))
        registrar_item(
            "FGTS",
            fgts_esp,
            fgts_real,
            "605",
            base=float(base_fgts_acumulada),
            formula="8%",
        )

    return list(auditoria_agrupada.values())
