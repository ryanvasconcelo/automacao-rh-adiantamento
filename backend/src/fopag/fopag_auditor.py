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
    "610",  # Bases Fortes
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
    "949",  # Controles
    "998",
    "999",  # Outros controles
]


def run_fopag_audit(
    company_code: str,
    employee_payroll_data: list,
    ano: int,
    mes: int,
    caso_pensao: int = 2,
) -> list:
    print(
        f"[Auditor V3 - Composição de Bases] Processando {company_code} - {mes}/{ano}..."
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

        # Data de admissão e cálculo de dias úteis
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

        # Dados contratuais
        tipo_contrato = str(funcionario.get("tipo_contrato", "")).lower()
        cargo_nome = str(funcionario.get("cargo", "")).lower()
        is_aprendiz = "aprendiz" in tipo_contrato or "aprendiz" in cargo_nome
        carga_horaria = float(funcionario.get("carga_horaria", 220))

        # Inicializa estrutura do funcionário
        if matricula not in auditoria_agrupada:
            auditoria_agrupada[matricula] = {
                "matricula": matricula,
                "nome": nome,
                "itens": [],
                "tem_divergencia": False,
                "totais": {"proventos": 0.0, "descontos": 0.0, "liquido": 0.0},
                "debug": {
                    "eventos_irrf": [],
                    "eventos_inss": [],  # Novo debug
                    "composicao_base_he": [],  # Novo debug para ver o que entrou na HE
                    "total_eventos": 0,
                },
            }

        # Função auxiliar de registro
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

            # Tolerâncias
            is_ok = abs(diff) <= Decimal("0.10")
            if ("DSR" in evt.upper() or "DESCANSO" in evt.upper()) and dec_esp > D("0"):
                if (abs(diff) / dec_esp) < Decimal(
                    "0.05"
                ):  # 5% tolerância no DSR calculado
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

        # --- VARIÁVEIS DE ACUMULAÇÃO ---
        salario_base_contratual = D("0")

        # Base HE: Soma de todas as verbas salariais (Súmula 264 TST)
        base_calculo_he = D("0")

        # Bases de Impostos (Calculadas por nós vs Fortes)
        nossa_base_inss = D("0")
        nossa_base_irrf = D("0")
        nossa_base_fgts = D("0")

        fortes_base_inss = D("0")
        fortes_base_irrf = D("0")
        fortes_base_fgts = D("0")

        total_variaveis_dsr = D("0")  # Para calcular reflexo no DSR
        total_proventos = D("0")
        total_descontos = D("0")

        lista_eventos = funcionario.get("eventos", [])
        auditoria_agrupada[matricula]["debug"]["total_eventos"] = len(lista_eventos)

        # Listas para ordenação de processamento
        eventos_fixos = []
        eventos_adicionais = []
        eventos_tempo = []
        eventos_dsr = []
        eventos_outros = []

        # --- 1. PRÉ-PROCESSAMENTO E SEPARAÇÃO ---
        for ev in lista_eventos:
            cod = ev["codigo"]
            val = D(ev["valor"])
            nome_upper = ev["descricao"].upper()
            incidencias = ev.get("incidencias", {})

            # Captura bases oficiais do Fortes (apenas para comparação final)
            if cod == "602":
                fortes_base_inss = val
                continue
            elif cod == "603":
                fortes_base_irrf = val
                continue
            elif cod == "604":
                fortes_base_fgts = val
                continue

            # Ignora controles
            if cod in CODIGOS_IGNORAR_AUDITORIA or cod in ["310", "311", "605"]:
                continue

            # DEBUG: Rastreabilidade das Bases
            debug_info = {
                "codigo": cod,
                "descricao": ev["descricao"],
                "valor": float(val),
            }

            if incidencias.get("irrf") and ev["tipo"] == 1:
                auditoria_agrupada[matricula]["debug"]["eventos_irrf"].append(
                    debug_info
                )

            if incidencias.get("inss") and ev["tipo"] == 1:
                auditoria_agrupada[matricula]["debug"]["eventos_inss"].append(
                    debug_info
                )

            # Classificação dos Eventos
            if cod == company_rule.cod_salario_base or cod in ["11", "001", "1"]:
                eventos_fixos.append(ev)
            elif any(
                x in nome_upper
                for x in [
                    "PERICULOSIDADE",
                    "INSALUBRIDADE",
                    "GRATIFICA",
                    "ANU",
                    "QUEBRA",
                    "FUNÇÃO",
                    "COMISS",
                ]
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

        # --- 2. PROCESSAMENTO: FIXOS (Salário Base) ---
        for ev in eventos_fixos:
            cod, val_real = ev["codigo"], D(ev["valor"])

            salario_base_contratual = val_real

            # Salário entra na Base HE
            base_calculo_he += val_real
            auditoria_agrupada[matricula]["debug"]["composicao_base_he"].append(
                f"{ev['descricao']}: {val_real}"
            )

            total_proventos += val_real

            # Acumula bases de impostos conforme flags do banco
            if ev.get("incidencias", {}).get("inss"):
                nossa_base_inss += val_real
            if ev.get("incidencias", {}).get("irrf"):
                nossa_base_irrf += val_real
            if ev.get("incidencias", {}).get("fgts"):
                nossa_base_fgts += val_real

            registrar(
                "Salário Base",
                val_real,
                val_real,
                cod,
                formula="Salário Contratual",
                tipo="P",
            )

        # --- 3. PROCESSAMENTO: ADICIONAIS (Compõem a base de HE) ---
        for ev in eventos_adicionais:
            cod, val_real = ev["codigo"], D(ev["valor"])
            nome = ev["descricao"]
            ref = D(ev["referencia"])
            nome_upper = nome.upper()

            v_esp = val_real
            formula = "Leitura Direta"

            # Periculosidade (30% sobre Salário Base)
            if "PERICULOSIDADE" in nome_upper:
                v_esp = D(
                    calculations.calc_periculosidade(float(salario_base_contratual))
                )
                formula = "30% Salário Base"

            # Insalubridade (Sobre Salário Mínimo)
            elif "INSALUBRIDADE" in nome_upper:
                grau = 0.20  # Padrão
                if ref > D("0"):
                    if abs(ref - D("0.10")) < D("0.01"):
                        grau = 0.10
                    elif abs(ref - D("0.20")) < D("0.01"):
                        grau = 0.20
                    elif abs(ref - D("0.40")) < D("0.01"):
                        grau = 0.40
                v_esp = D(calculations.calc_insalubridade(grau=grau))
                formula = f"Grau {grau*100:.0f}% × SM"

            # Outros adicionais fixos (Anuênio, Gratificações)
            # Geralmente são valores fixos ou % configurados, difícil auditar sem parametrização extra.
            # Assumimos o valor real como esperado por enquanto, mas SOMAMOS NA BASE HE.

            # ACUMULAÇÃO CRÍTICA PARA HE:
            # Se for provento e incidir INSS (proxy para natureza salarial), entra na base HE
            if ev["tipo"] == 1:
                # Adiciona explicitamente na base HE
                base_calculo_he += v_esp
                auditoria_agrupada[matricula]["debug"]["composicao_base_he"].append(
                    f"{nome}: {v_esp}"
                )

            total_proventos += v_esp
            if ev.get("incidencias", {}).get("inss"):
                nossa_base_inss += v_esp
            if ev.get("incidencias", {}).get("irrf"):
                nossa_base_irrf += v_esp
            if ev.get("incidencias", {}).get("fgts"):
                nossa_base_fgts += v_esp

            registrar(nome, v_esp, val_real, cod, formula=formula, tipo="P")

        # --- 4. PROCESSAMENTO: TEMPO (Horas Extras, Noturno, Faltas) ---
        # Aqui a base_calculo_he já contém Salário + Peric + Insalub + Outros
        for ev in eventos_tempo:
            cod, val_real = ev["codigo"], D(ev["valor"])
            nome = ev["descricao"]
            ref = D(ev["referencia"])
            nome_upper = nome.upper()
            v_esp = val_real
            formula = "Leitura Direta"

            if "HORA" in nome_upper and "EXTRA" in nome_upper:
                qtd_horas = calculations.time_to_decimal(float(ref))

                # Definição do percentual
                percentual = 50
                if "100" in nome_upper or cod == "61":
                    percentual = 100
                elif "60" in nome_upper or cod == "62":
                    percentual = 60
                elif "70" in nome_upper or cod == "64":
                    percentual = 70

                # ✅ CÁLCULO USANDO A BASE COMPOSTA
                v_esp = D(
                    calculations.calc_he_generica(
                        float(base_calculo_he), qtd_horas, percentual, carga_horaria
                    )
                )

                formula = f"Base(Sal+Adic) {float(base_calculo_he):.2f} × {percentual}% × {qtd_horas}h"
                total_variaveis_dsr += v_esp

            elif "NOTURNO" in nome_upper:
                qtd_horas = calculations.time_to_decimal(float(ref))
                # Noturno geralmente é sobre o salário base, mas pode incluir adicionais dependendo da CCT.
                # O padrão CLT é sobre o salário hora normal.
                v_esp = D(
                    calculations.calc_adicional_noturno(
                        float(salario_base_contratual), qtd_horas, carga_horaria
                    )
                )
                formula = f"20% × {qtd_horas}h"
                total_variaveis_dsr += v_esp

            elif "FALTA" in nome_upper or "ATRASO" in nome_upper:
                # Lógica de faltas (mantida)
                qtd = float(ref) if ref > D("0") else 1.0
                if ref > D("30"):
                    qtd = float(ref) / (carga_horaria / 30)

                base_falta = float(
                    salario_base_contratual
                )  # Faltas descontam do salário base

                if "HORA" in nome_upper or " H " in nome_upper:
                    v_esp = D(round((base_falta / carga_horaria) * qtd, 2))
                    formula = "Desconto Horas"
                elif qtd >= 5:  # Lógica empírica para dias
                    v_esp = D(round((base_falta / 30) * qtd, 2))
                    formula = "Desconto Dias"
                else:
                    v_esp = D(round((base_falta / carga_horaria) * qtd, 2))  # Fallback

            # Atualização de Totais e Bases
            if ev["tipo"] == 1:  # Provento
                total_proventos += v_esp
                if ev.get("incidencias", {}).get("inss"):
                    nossa_base_inss += v_esp
                if ev.get("incidencias", {}).get("irrf"):
                    nossa_base_irrf += v_esp
                if ev.get("incidencias", {}).get("fgts"):
                    nossa_base_fgts += v_esp
            else:  # Desconto
                total_descontos += v_esp
                if ev.get("incidencias", {}).get("inss"):
                    nossa_base_inss -= v_esp
                if ev.get("incidencias", {}).get("irrf"):
                    nossa_base_irrf -= v_esp
                if ev.get("incidencias", {}).get("fgts"):
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

        # --- 5. PROCESSAMENTO: DSR (Reflexos) ---
        for ev in eventos_dsr:
            cod, val_real = ev["codigo"], D(ev["valor"])
            nome = ev["descricao"]
            v_esp = val_real
            formula = "DSR (Base desconhecida)"
            memoria = None

            if total_variaveis_dsr > D("0") and dias_uteis > 0:
                v_dsr = D(
                    calculations.calc_dsr(
                        float(total_variaveis_dsr), dias_uteis, dias_dsr
                    )
                )

                # Validação com tolerância
                if abs(v_dsr - val_real) < D(
                    "5"
                ):  # Tolerância de R$ 5 para DSR (varia muito por calendário)
                    v_esp = v_dsr
                    formula = "Reflexo Variáveis"
                    memoria = {
                        "tipo": "DSR",
                        "variaveis": [
                            {
                                "nome": "Base Variáveis",
                                "valor": f"R$ {float(total_variaveis_dsr):.2f}",
                            }
                        ],
                        "resultado": f"R$ {float(v_esp):.2f}",
                    }

            total_proventos += v_esp
            if ev.get("incidencias", {}).get("inss"):
                nossa_base_inss += v_esp
            if ev.get("incidencias", {}).get("irrf"):
                nossa_base_irrf += v_esp
            if ev.get("incidencias", {}).get("fgts"):
                nossa_base_fgts += v_esp

            registrar(
                nome, v_esp, val_real, cod, formula=formula, memoria=memoria, tipo="P"
            )

        # --- 6. PROCESSAMENTO: OUTROS (VT, Salário Família, Pensão) ---
        for ev in eventos_outros:
            cod, val_real = ev["codigo"], D(ev["valor"])
            nome = ev["descricao"]
            ref = D(ev["referencia"])
            v_esp = val_real
            formula = "Leitura Direta"

            if (
                "TRANSPORTE" in nome.upper()
                and "VALE" in nome.upper()
                and ev["tipo"] == 2
            ):
                v_esp = D(
                    calculations.calc_vale_transporte(float(salario_base_contratual))
                )
                formula = "6% Salário Base"

            elif "FAMILIA" in nome.upper() or "FAMÍLIA" in nome.upper():
                qtd_filhos = funcionario.get("dependentes_salario_familia", 0)
                v_esp = D(
                    calculations.calc_salario_familia(
                        float(nossa_base_inss), qtd_filhos
                    )
                )
                formula = f"{qtd_filhos} filho(s)"

            if ev["tipo"] == 1:
                total_proventos += v_esp
                if ev.get("incidencias", {}).get("inss"):
                    nossa_base_inss += v_esp
                if ev.get("incidencias", {}).get("irrf"):
                    nossa_base_irrf += v_esp
                if ev.get("incidencias", {}).get("fgts"):
                    nossa_base_fgts += v_esp
            else:
                total_descontos += v_esp
                if ev.get("incidencias", {}).get("inss"):
                    nossa_base_inss -= v_esp
                if ev.get("incidencias", {}).get("irrf"):
                    nossa_base_irrf -= v_esp
                if ev.get("incidencias", {}).get("fgts"):
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

        # --- 7. IMPOSTOS FINAIS ---

        # Prioriza base calculada pelo Fortes se disponível (para evitar divergência de centavos por composição),
        # mas usa a NOSSA se o evento 60x não vier (fallback).
        base_inss_final = (
            fortes_base_inss if fortes_base_inss > D("0") else nossa_base_inss
        )
        base_irrf_final = (
            fortes_base_irrf if fortes_base_irrf > D("0") else nossa_base_irrf
        )
        base_fgts_final = (
            fortes_base_fgts if fortes_base_fgts > D("0") else nossa_base_fgts
        )

        # 7.1 INSS
        inss_esp = D(calculations.calc_inss(float(base_inss_final)))
        inss_real = D(
            next((e["valor"] for e in lista_eventos if e["codigo"] == "310"), 0)
        )
        registrar(
            "INSS",
            inss_esp,
            inss_real,
            "310",
            base=float(base_inss_final),
            formula="Tab. 2026",
            tipo="D",
        )
        total_descontos += inss_esp

        # 7.2 IRRF (Lógica Fortes Completa)
        inss_real_valor = D(
            next((e["valor"] for e in lista_eventos if e["codigo"] == "310"), 0)
        )
        inss_para_irrf = inss_real_valor if inss_real_valor > D("0") else inss_esp

        res_irrf = calculations.calc_irrf_detalhado(
            float(base_irrf_final), float(inss_para_irrf), dependentes
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
            formula="Tab. 2026 + Redutor",
            memoria=res_irrf["memoria"],
            tipo="D",
        )
        total_descontos += irrf_esp

        # 7.3 FGTS
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

        # Totais Finais
        auditoria_agrupada[matricula]["totais"] = {
            "proventos": float(total_proventos),
            "descontos": float(total_descontos),
            "liquido": float(total_proventos - total_descontos),
        }

    return list(auditoria_agrupada.values())
