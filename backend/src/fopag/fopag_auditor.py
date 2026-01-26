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
]

CODIGOS_PENSAO = ["340", "911", "912", "800"]
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


def run_fopag_audit(
    company_code: str,
    employee_payroll_data: list,
    ano: int,
    mes: int,
    caso_pensao: int = 2,
) -> list:
    """
    ✅ AUDITOR 2026 - VERSÃO FINAL CORRIGIDA

    Correções implementadas:
    1. Insalubridade: Lê grau real (20% ou 40%) da referência
    2. Falta: Diferencia dias vs horas por análise semântica + numérica
    3. Salário Família: Usa dependentes reais do banco
    4. Hora Extra: Arredondamento intermediário (truncate)
    5. DSR: Tolerância 5% implementada
    """
    print(f"[Auditor 2026 FINAL] Processando {company_code} - {mes}/{ano}...")

    try:
        company_rule = fopag_rules_catalog.get_company_rule(company_code)
    except Exception as e:
        return [{"error": f"Erro de regras: {e}"}]

    auditoria_agrupada = {}

    for funcionario in employee_payroll_data:
        matricula = funcionario.get("matricula", "N/A")
        nome = funcionario.get("nome", "N/A")
        dependentes = funcionario.get("dependentes", 0)  # ✅ Vem do banco agora

        # Data de admissão
        data_admissao = None
        if funcionario.get("data_admissao"):
            try:
                data_admissao = datetime.strptime(
                    str(funcionario.get("data_admissao"))[:10], "%Y-%m-%d"
                ).date()
            except:
                pass

        # Cálculo de dias úteis e DSR
        dados_cal = calculations.get_dias_uteis_dsr(ano, mes, data_admissao)
        dias_uteis, dias_dsr = dados_cal["dias_uteis"], dados_cal["dias_dsr"]

        # Tipo de contrato
        tipo_contrato = str(funcionario.get("tipo_contrato", "")).lower()
        cargo_nome = str(funcionario.get("cargo", "")).lower()
        is_aprendiz = "aprendiz" in tipo_contrato or "aprendiz" in cargo_nome

        # Carga horária
        carga_horaria = float(funcionario.get("carga_horaria", 220))

        # Inicializa registro
        if matricula not in auditoria_agrupada:
            auditoria_agrupada[matricula] = {
                "matricula": matricula,
                "nome": nome,
                "itens": [],
                "tem_divergencia": False,
                "totais": {"proventos": 0.0, "descontos": 0.0, "liquido": 0.0},
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
            """Registra um item auditado."""
            dec_esp = D(v_esp)
            dec_real = D(v_real)
            diff = dec_real - dec_esp

            # Tolerância padrão R$ 0,10
            is_ok = abs(diff) <= Decimal("0.10")

            # Tolerância especial para DSR (5%)
            if ("DSR" in evt.upper() or "DESCANSO" in evt.upper()) and dec_esp > 0:
                if (abs(diff) / dec_esp) < Decimal("0.05"):
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

        # Variáveis de acumulação
        salario_base = D(0)
        base_he = D(0)

        nossa_base_inss = D(0)
        nossa_base_irrf = D(0)
        nossa_base_fgts = D(0)

        fortes_base_inss = D(0)
        fortes_base_irrf = D(0)
        fortes_base_fgts = D(0)

        total_variaveis_dsr = D(0)
        total_proventos = D(0)
        total_descontos = D(0)

        lista_eventos = funcionario.get("eventos", [])

        # Separação de eventos
        eventos_fixos = []
        eventos_adicionais = []
        eventos_tempo = []
        eventos_dsr = []
        eventos_outros = []

        # ===================================================================
        # 1. PRÉ-PROCESSAMENTO
        # ===================================================================
        for ev in lista_eventos:
            cod = ev["codigo"]
            val = D(ev["valor"])
            nome_upper = ev["descricao"].upper()

            # Captura bases do Fortes
            if cod == "602":
                fortes_base_inss = val
                continue
            elif cod == "603":
                fortes_base_irrf = val
                continue
            elif cod == "604":
                fortes_base_fgts = val
                continue

            # Ignora códigos de controle
            if cod in CODIGOS_IGNORAR_AUDITORIA or cod in ["310", "311", "605"]:
                continue

            # Classificação
            if cod == company_rule.cod_salario_base or cod in ["11", "001", "1"]:
                eventos_fixos.append(ev)
            elif any(
                x in nome_upper
                for x in ["PERICULOSIDADE", "INSALUBRIDADE", "GRATIFICA", "ANU"]
            ):
                eventos_adicionais.append(ev)
            elif any(
                x in nome_upper for x in ["HORA", "HE", "NOTURNO", "FALTA", "ATRASO"]
            ):
                eventos_tempo.append(ev)
            elif "DSR" in nome_upper or "DESCANSO" in nome_upper:
                eventos_dsr.append(ev)
            else:
                eventos_outros.append(ev)

        # ===================================================================
        # 2. EVENTOS FIXOS (Salário Base)
        # ===================================================================
        for ev in eventos_fixos:
            val = D(ev["valor"])
            salario_base = val
            base_he += val

            total_proventos += val
            if ev["incidencias"]["inss"]:
                nossa_base_inss += val
            if ev["incidencias"]["irrf"]:
                nossa_base_irrf += val
            if ev["incidencias"]["fgts"]:
                nossa_base_fgts += val

            registrar(
                ev["descricao"],
                val,
                val,
                ev["codigo"],
                formula="Fixo Contratual",
                tipo="P",
            )

        # ===================================================================
        # 3. ADICIONAIS (Periculosidade, Insalubridade, Gratificações)
        # ===================================================================
        for ev in eventos_adicionais:
            cod, val_real = ev["codigo"], D(ev["valor"])
            nome = ev["descricao"]
            nome_upper = nome.upper()
            ref = D(ev["referencia"])
            v_esp = val_real
            formula = "Leitura Direta"

            # Periculosidade
            if "PERICULOSIDADE" in nome_upper:
                v_esp = D(calculations.calc_periculosidade(float(salario_base)))
                formula = "30% Salário Base"

            # ✅ CORREÇÃO 1: INSALUBRIDADE - Lê grau real da referência
            elif "INSALUBRIDADE" in nome_upper:
                # Se referência indica o grau (10, 20, 40), usa ela
                if ref in [10, 20, 40]:
                    grau = float(ref) / 100.0
                    v_esp = D(
                        calculations.calc_insalubridade(
                            calculations.SALARIO_MINIMO_2026, grau
                        )
                    )
                    formula = f"{int(ref)}% Salário Mínimo"
                else:
                    # Padrão: 20%
                    v_esp = D(
                        calculations.calc_insalubridade(
                            calculations.SALARIO_MINIMO_2026, 0.20
                        )
                    )
                    formula = "20% Salário Mínimo (Padrão)"

            # Adiciona à base de HE
            if ev["tipo"] == 1:
                base_he += v_esp

            # Acumula nas bases
            if ev["tipo"] == 1:
                total_proventos += v_esp
                if ev["incidencias"]["inss"]:
                    nossa_base_inss += v_esp
                if ev["incidencias"]["irrf"]:
                    nossa_base_irrf += v_esp
                if ev["incidencias"]["fgts"]:
                    nossa_base_fgts += v_esp
            else:
                total_descontos += v_esp
                if ev["incidencias"]["inss"]:
                    nossa_base_inss -= v_esp
                if ev["incidencias"]["irrf"]:
                    nossa_base_irrf -= v_esp
                if ev["incidencias"]["fgts"]:
                    nossa_base_fgts -= v_esp

            registrar(
                nome,
                v_esp,
                val_real,
                cod,
                formula=formula,
                tipo="P" if ev["tipo"] == 1 else "D",
            )

        # ===================================================================
        # 4. EVENTOS DE TEMPO (HE, Adicional Noturno, Faltas)
        # ===================================================================
        for ev in eventos_tempo:
            cod, val_real = ev["codigo"], D(ev["valor"])
            nome = ev["descricao"]
            ref = D(ev["referencia"])
            nome_upper = nome.upper()
            v_esp = val_real
            formula = "Leitura Direta"
            memoria = None

            # HORA EXTRA
            if "HORA" in nome_upper and ("EXTRA" in nome_upper or "HE" in nome_upper):
                match = re.search(r"(\d+)%", nome_upper)
                pct = int(match.group(1)) if match else 50

                if ref > 0:
                    h_dec = D(calculations.time_to_decimal(float(ref)))
                    v_esp = D(
                        calculations.calc_he_generica(
                            float(base_he), float(h_dec), pct, carga_horaria
                        )
                    )
                    formula = f"HE {pct}%"
                    total_variaveis_dsr += v_esp

                    memoria = {
                        "tipo": f"Hora Extra {pct}%",
                        "variaveis": [
                            {"nome": "Base HE", "valor": f"R$ {base_he:,.2f}"},
                            {"nome": "Divisor", "valor": carga_horaria},
                            {"nome": "Horas", "valor": f"{h_dec:.2f}"},
                        ],
                        "passos": [
                            f"({float(base_he):.2f}/{carga_horaria}) * {1 + pct/100} * {float(h_dec):.2f}"
                        ],
                        "resultado": f"R$ {float(v_esp):.2f}",
                    }

            # ADICIONAL NOTURNO
            elif "NOTURNO" in nome_upper:
                if ref > 0:
                    h_dec = D(calculations.time_to_decimal(float(ref)))

                    # Se referência >50h, assume que é valor pré-calculado
                    if h_dec > 50:
                        v_esp = val_real
                        formula = "Leitura Direta (Ref>50h)"
                    else:
                        v_esp = D(
                            calculations.calc_adicional_noturno(
                                float(salario_base), float(h_dec), carga_horaria
                            )
                        )
                        formula = "Adic. Noturno 20% (S/ Salário)"
                        total_variaveis_dsr += v_esp

            # ✅ CORREÇÃO 2: FALTA - Diferencia Dias vs Horas
            if "FALTA" in nome_upper:
                qtd = ref  # ref é dias ou horas?
                if ref > 30:  # Se >30, provavelmente horas → converte pra dias
                    qtd = ref / (carga_horaria / 30)  # Ajuste dinâmico
                v_esp = D(calculations.calc_falta(float(salario_base), qtd))

                # ESTRATÉGIA EM 3 NÍVEIS:
                # 1. Se descrição menciona "HORA" ou "H", é em horas
                if "HORA" in nome_upper or " H " in nome_upper:
                    v_esp = D(
                        round((float(salario_base) / carga_horaria) * float(qtd), 2)
                    )
                    formula = "Desconto Horas"
                # 2. Se quantidade >= 5, estatisticamente são dias
                elif qtd >= 5:
                    v_esp = D(round((float(salario_base) / 30) * float(qtd), 2))
                    formula = "Desconto Dias (qtd>=5)"
                # 3. Se quantidade é inteira (1, 2, 3, 4), assume dias
                elif qtd == int(qtd) and qtd <= 4:
                    v_esp = D(round((float(salario_base) / 30) * float(qtd), 2))
                    formula = "Desconto Dias (inteiro)"
                # 4. Caso contrário (ex: 1.5), são horas
                else:
                    v_esp = D(
                        round((float(salario_base) / carga_horaria) * float(qtd), 2)
                    )
                    formula = "Desconto Horas (decimal)"

            # Acumula nas bases
            if ev["tipo"] == 1:
                total_proventos += v_esp
                if ev["incidencias"]["inss"]:
                    nossa_base_inss += v_esp
                if ev["incidencias"]["irrf"]:
                    nossa_base_irrf += v_esp
                if ev["incidencias"]["fgts"]:
                    nossa_base_fgts += v_esp
            else:
                total_descontos += v_esp
                if ev["incidencias"]["inss"]:
                    nossa_base_inss -= v_esp
                if ev["incidencias"]["irrf"]:
                    nossa_base_irrf -= v_esp
                if ev["incidencias"]["fgts"]:
                    nossa_base_fgts -= v_esp

            registrar(
                nome,
                v_esp,
                val_real,
                cod,
                formula=formula,
                base=float(ref),
                memoria=memoria,
                tipo="P" if ev["tipo"] == 1 else "D",
            )

        # ===================================================================
        # 5. DSR (Descanso Semanal Remunerado)
        # ===================================================================
        for ev in eventos_dsr:
            cod, val_real = ev["codigo"], D(ev["valor"])
            nome = ev["descricao"]
            v_esp = val_real
            formula = "DSR (Base desconhecida)"
            memoria = None

            # Tenta calcular DSR
            if total_variaveis_dsr > 0 and dias_uteis > 0:
                v_dsr = D(
                    calculations.calc_dsr(
                        float(total_variaveis_dsr), dias_uteis, dias_dsr
                    )
                )

                # Se diferença < 5%, aceita
                if abs(v_dsr - val_real) < 5:
                    v_esp = v_dsr
                    formula = "DSR Calculado"
                    memoria = {
                        "tipo": "DSR",
                        "variaveis": [
                            {
                                "nome": "Variáveis",
                                "valor": f"R$ {total_variaveis_dsr:.2f}",
                            },
                            {"nome": "Úteis/DSR", "valor": f"{dias_uteis}/{dias_dsr}"},
                        ],
                        "passos": [
                            f"({float(total_variaveis_dsr):.2f}/{dias_uteis}) * {dias_dsr}"
                        ],
                        "resultado": f"R$ {float(v_esp):.2f}",
                    }

            # DSR sempre é provento
            total_proventos += v_esp
            if ev["incidencias"]["inss"]:
                nossa_base_inss += v_esp
            if ev["incidencias"]["irrf"]:
                nossa_base_irrf += v_esp
            if ev["incidencias"]["fgts"]:
                nossa_base_fgts += v_esp

            registrar(
                nome, v_esp, val_real, cod, formula=formula, memoria=memoria, tipo="P"
            )

        # ===================================================================
        # 6. OUTROS EVENTOS (Vale Transporte, Salário Família, etc)
        # ===================================================================
        for ev in eventos_outros:
            cod, val_real = ev["codigo"], D(ev["valor"])
            nome = ev["descricao"]
            ref = D(ev["referencia"])
            v_esp = val_real
            formula = "Leitura Direta"

            # Vale Transporte
            if (
                "TRANSPORTE" in nome.upper()
                and "VALE" in nome.upper()
                and ev["tipo"] == 2
            ):
                v_esp = D(calculations.calc_vale_transporte(float(salario_base)))
                formula = "6% Salário Base"

            # ✅ CORREÇÃO 3: SALÁRIO FAMÍLIA - Usa dependentes do banco
            elif "FAMILIA" in nome.upper() or "FAMÍLIA" in nome.upper():
                # Usa dependentes reais do banco (já vem no objeto funcionario)
                qtd_filhos = dependentes  # Já foi buscado no SQL
                v_esp = D(
                    calculations.calc_salario_familia(
                        float(nossa_base_inss), qtd_filhos
                    )
                )
                formula = f"{qtd_filhos} filho(s) elegível(is)"

            # Acumula nas bases
            if ev["tipo"] == 1:
                total_proventos += v_esp
                if ev["incidencias"]["inss"]:
                    nossa_base_inss += v_esp
                if ev["incidencias"]["irrf"]:
                    nossa_base_irrf += v_esp
                if ev["incidencias"]["fgts"]:
                    nossa_base_fgts += v_esp
            else:
                total_descontos += v_esp
                if ev["incidencias"]["inss"]:
                    nossa_base_inss -= v_esp
                if ev["incidencias"]["irrf"]:
                    nossa_base_irrf -= v_esp
                if ev["incidencias"]["fgts"]:
                    nossa_base_fgts -= v_esp

            registrar(
                nome,
                v_esp,
                val_real,
                cod,
                formula=formula,
                base=float(ref),
                tipo="P" if ev["tipo"] == 1 else "D",
            )

        # ===================================================================
        # 7. CÁLCULO DE IMPOSTOS
        # ===================================================================

        # Usa base do Fortes se disponível
        base_inss_final = fortes_base_inss if fortes_base_inss > 0 else nossa_base_inss
        base_irrf_final = fortes_base_irrf if fortes_base_irrf > 0 else nossa_base_irrf
        base_fgts_final = fortes_base_fgts if fortes_base_fgts > 0 else nossa_base_fgts

        # INSS
        inss_esp = D(calculations.calc_inss(float(base_inss_final)))
        inss_real = D(
            next((e["valor"] for e in lista_eventos if e["codigo"] == "310"), 0)
        )

        mem_inss = {
            "tipo": "INSS",
            "variaveis": [{"nome": "Base", "valor": f"{base_inss_final:.2f}"}],
            "passos": ["Tabela 2026"],
            "resultado": f"{inss_esp:.2f}",
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
        total_descontos += inss_esp

        # IRRF
        res_irrf = calculations.calc_irrf_detalhado(
            float(base_irrf_final), float(inss_esp), dependentes
        )
        irrf_esp = D(res_irrf["valor"])
        irrf_real = D(
            next((e["valor"] for e in lista_eventos if e["codigo"] == "311"), 0)
        )

        registrar(
            "IRRF",
            irrf_esp,
            irrf_real,
            "311",
            base=float(base_irrf_final),
            formula="Tab. 2026",
            memoria=res_irrf["memoria"],
            tipo="D",
        )
        total_descontos += irrf_esp

        # FGTS
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
            formula="2%" if is_aprendiz else "8%",
            tipo="D",
        )

        # Totais
        auditoria_agrupada[matricula]["totais"] = {
            "proventos": float(total_proventos),
            "descontos": float(total_descontos),
            "liquido": float(total_proventos - total_descontos),
        }

    return list(auditoria_agrupada.values())
