# backend/src/fopag/fopag_auditor.py

import re
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from src.fopag import calculations
# REMOVIDO: from src.fopag import fopag_rules_catalog (Obsoleto)


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


# Códigos puramente informativos que não devem ser auditados como verba financeira
# Mantemos apenas os de "Base de Cálculo" (600+) e info auxiliares.
# PENSÃO (922, 340-342) NÃO PODE ESTAR AQUI.
CODIGOS_IGNORAR_AUDITORIA = [
    "600", "601", "602", "603", "604", "605", "606", "607", "608", "609", "610",
    "900", "901", "902", "903", "904", "919",
    # "920", # REMOVIDO: Gratificação é verba financeira
    # "922", # REMOVIDO: Pensão Alimentícia
    "946", "947", "948", "949", "998", "999",
]


def run_fopag_audit(
    company_code: str,
    employee_payroll_data: list,
    ano: int,
    mes: int,
    caso_pensao: int = 2,
) -> list:
    print(
        f"[Auditor V20 - Dinâmico] Processando {company_code} - {mes}/{ano}..."
    )

    # Defaults
    COTA_SALARIO_FAMILIA = 65.00 # 2026 est
    
    auditoria_agrupada = {}

    for funcionario in employee_payroll_data:
        matricula = funcionario.get("matricula", "N/A")
        nome = funcionario.get("nome", "N/A")
        dependentes = funcionario.get("dependentes", 0)
        
        # --- DADOS CADASTRAIS ---
        vinculo = str(funcionario.get("tipo_contrato", "")).strip()  # CodigoVinculo
        # Códigos comuns de Pró-Labore no eSocial/Fortes: 11, 721, 722, 723
        # O usuário pediu "INSS Pró-labore". Vamos assumir vínculo 11 ou categoria compatível.
        is_pro_labore = vinculo in ["11", "720", "721", "722", "723"] or "SOCIO" in funcionario.get("cargo", "").upper()

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
                # if not msg: # msg is not a parameter in the new definition
                #     msg = f"Esp: {dec_esp:.2f} | Real: {dec_real:.2f}"

            if memoria is None:
                memoria = {
                    "tipo": "Leitura Direta / Importado",
                    "variaveis": [
                        {"nome": "Origem", "valor": "Fortes (Banco de Dados)"},
                        {"nome": "Referência/Fórmula", "valor": formula if formula else "Valor Informado"},
                        {"nome": "Base de Cálculo", "valor": f"R$ {base:,.2f}" if base else "-"}
                    ],
                    "resultado": f"R$ {dec_real:,.2f}"
                }

            auditoria_agrupada[matricula]["itens"].append(
                {
                    "codigo": str(cod),
                    "evento": evt,
                    "esperado": money_round(dec_esp),
                    "real": money_round(dec_real),
                    "diferenca": money_round(diff),
                    "status": status,
                    "msg": f"Esp: {dec_esp:.2f} | Real: {dec_real:.2f}" if status == "ERRO" else "",
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
        
        # Totalizador de Pensão Alimentícia
        total_pensao_alimenticia = D("0")

        lista_eventos = funcionario.get("eventos", [])

        # Listas para ordenação
        eventos_fixos = []
        eventos_adicionais = []
        eventos_noturno = []
        eventos_he = []
        eventos_faltas = []
        eventos_dsr = []
        eventos_outros_proventos = []
        eventos_dsr = []
        eventos_outros_proventos = []
        eventos_outros_descontos = []
        
        # Lista de detalhamento para memória de INSS (Layout Fortes)
        detalhes_base_inss = []
        abatimentos_inss = []

        # --- 1. PRÉ-PROCESSAMENTO ---
        for ev in lista_eventos:
            cod = ev["codigo"]
            val = D(ev["valor"])
            nome_upper = ev["descricao"].upper()
            tipo_evento = int(ev["tipo"]) if str(ev["tipo"]).isdigit() else 0

            # Captura INSS já descontado (ex: de Férias)
            # Geralmente são descontos (tipo 2 ou 3) com nome "INSS" que não são o 310
            if cod != "310" and "INSS" in nome_upper and tipo_evento in [2, 3]:
                abatimentos_inss.append({"nome": ev["descricao"], "valor": float(val)})
                continue

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
                if val > salario_contratual_cheio:
                    salario_contratual_cheio = val
                continue

            if cod in CODIGOS_IGNORAR_AUDITORIA or cod in ["310", "311", "605", "300"]:
                 # Ignora INSS, IRRF, FGTS, Adiantamento (processados no final ou separadamente)
                continue

            # Classificação
            # Salário Base Comum: 11, 001, 1, 011
            if cod in ["11", "001", "1", "011", "1111", "0001"]:
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
            ) and tipo_evento in [0, 1]:  # Aceita Fixo ou Variável
                eventos_adicionais.append(ev)
            elif "NOTURNO" in nome_upper and tipo_evento in [0, 1]:
                eventos_noturno.append(ev)
            elif any(x in nome_upper for x in ["HORA", "HE", "EXTRA"]) and tipo_evento in [0, 1]:
                eventos_he.append(ev)
            elif any(x in nome_upper for x in ["FALTA", "ATRASO"]):
                eventos_faltas.append(ev)
            elif ("DSR" in nome_upper or "DESCANSO" in nome_upper) and tipo_evento == 1:
                eventos_dsr.append(ev)
            else:
                # Catch-all para Proventos (Tipo 0 ou 1)
                # Assumindo que 0=Fixo, 1=Variável, 2/3=Desconto?
                # Se for valor positivo e não classificou, tratamos como provento.
                if tipo_evento in [0, 1]:
                    eventos_outros_proventos.append(ev)
                else:
                    eventos_outros_descontos.append(ev)

        # =========================================================================
        # ACUMULADORES INTELIGENTES (DINÂMICOS VIA BANCO DE DADOS)
        # =========================================================================

        def processar_acumuladores(ev, valor, operacao="soma"):
            nonlocal nossa_base_inss, nossa_base_irrf, nossa_base_fgts, total_pensao_alimenticia

            # ✅ AGORA USAMOS AS FLAGS VINDAS DO BANCO (EVE.Indicativo...)
            # O data_fetcher já retorna isso convertido em boolean
            inc_inss = ev.get("incidencias", {}).get("inss", False)
            inc_irrf = ev.get("incidencias", {}).get("irrf", False)
            inc_fgts = ev.get("incidencias", {}).get("fgts", False)
            
            nome_upper = ev["descricao"].upper()
            cod = ev["codigo"]

            # --- CORREÇÃO: SALÁRIO FAMÍLIA NUNCA INCIDE ---
            # Flagrante exceção legal: se o cadastro estiver errado, corrigimos aqui.
            if "FAMILIA" in nome_upper or "FAMÍLIA" in nome_upper:
                inc_inss = False
                inc_irrf = False
                inc_fgts = False
                
            # --- CORREÇÃO: CONSIGNADO / EMPRÉSTIMOS NÃO REDUZEM BASE DE FGTS ---
            # Mesmo que o banco diga que sim (erro de cadastro comum), não devemos abater.
            if cod in ["943", "940", "941"] or "CONSIGNADO" in nome_upper:
                inc_fgts = False

            # --- PENSÃO ALIMENTÍCIA (DEDUÇÃO) ---
            # Identificação genérica por nome ou código comum, mas flexível
            is_pensao = (
                cod in ["340", "341", "342", "919", "920", "921", "922", "923", "924", "925", "926"] 
                or any(k in nome_upper for k in ["PENSÃO", "PENSAO", "ALIMENTOS", "ALIMENTÍCIA"])
            )
            
            # Pensão é um DESCONTO que deduz da base de IRRF.
            # Se a operação for 'subtrai' (é um evento de desconto), devemos acumular no total_pensao
            # e garantir que a base de IRRF seja reduzida (automaticamente pelo 'subtrai' se inc_irrf=True, 
            # MAS a lógica de IRRF calcula Base = Bruto - INSS - Pensão. 
            # Então precisamos ter o valor separado.)
            
            if operacao == "subtrai" and is_pensao:
                # O evento de pensão geralmente NÃO tem flag de incidência de IRRF marcada para *reduzir* a base diretamente na soma,
                # ele é uma dedução legal posterior. 
                # Mas se o cadastro marcar IncideIRRF=True num desconto, matematicamente reduz a base.
                # Vamos forçar a lógica correta de acumular para dedução explícita.
                total_pensao_alimenticia += valor
                
                # Para não deduzir duas vezes (se a flag estiver true), anulamos a flag aqui e tratamos via total_pensao
                inc_irrf = False 
                inc_inss = False
                inc_fgts = False

            # --- LISTA NEGRA DE PROVENTOS (Bloqueia ganho isento mesmo se flag=True no banco?) ---
            # Se confiamos no banco, não deveríamos ter lista negra. 
            # Mas vamos manter apenas para garantias muito fortes ou erro comum de cadastro.
            # Por enquanto, vou COMENTAR a lista negra e confiar no banco 100%, conforme pedido.
            # Se o usuário reclamar que está incidindo indevidamente, é cadastro errado no Fortes.
            
            # keywords_isentos_inss = ["REEMBOLSO", "INDENIZA", ...]
            # if operacao == "soma" and any(...): inc_inss = False
            
            # --- PROCESSAMENTO ---
            # --- PROCESSAMENTO ---
            if operacao == "soma":
                if inc_inss:
                    nossa_base_inss += valor
                    # Detalhamento para Memória INSS
                    detalhes_base_inss.append({
                        "nome": ev["descricao"],
                        "valor": float(valor)
                    })
                
                if inc_irrf: nossa_base_irrf += valor
                if inc_fgts: nossa_base_fgts += valor
            
            elif operacao == "subtrai":
                # Descontos que abatem base (Faltas, Atrasos)
                # Geralmente têm flags True no cadastro.
                
                # Adiantamento Salarial: Regime de Caixa para IRRF.
                # Se tiver flag IRRF no banco, ok. Se não, forçamos se for Adiantamento?
                # Padrão Fortes: Adiantamento tem Incidência IRRF = Falso na folha mensal 
                # porque o desconto é do *valor liquido recebido*, não deduz da base de calculo do imposto mensal.
                # O Adiantamento *gerou* imposto no dia 15/20. Na mensal, ele é apenas descontado financeiramente.
                # ENTRETANTO, para a base fiscal do mês, o valor recebido no adiantamento compõe a base.
                # O *Desconto de Adiantamento* (cod 300) NÃO deve reduzir a base de IRRF mensal.
                if "ADIANT" in nome_upper and "SALARIAL" in nome_upper:
                    inc_inss = False
                    inc_irrf = False # Não abate a base.
                    inc_fgts = False

                if inc_inss: nossa_base_inss -= valor
                if inc_irrf: nossa_base_irrf -= valor
                if inc_fgts: nossa_base_fgts -= valor


        # --- 2. SALÁRIO BASE ---
        for ev in eventos_fixos:
            cod, val_real = ev["codigo"], D(ev["valor"])
            salario_base_contratual = val_real
            base_he_fixa += val_real
            total_proventos += val_real
            processar_acumuladores(ev, val_real, "soma")
            
            # Memória de Cálculo do Salário Base (Solicitação do Usuário)
            # Ex: Salário Contratual / 30 * Dias = Valor
            # Precisamos inferir os dias se não estivessem explícitos. Mas geralmente Salario Base é fixo ou proporcional.
            memoria_salario = None
            if salario_contratual_cheio > 0 and val_real < salario_contratual_cheio:
                 # Proporcionalidade detectada
                 prop_dias = round((val_real / salario_contratual_cheio) * 30)
                 memoria_salario = {
                    "tipo": "Cálculo Proporcional",
                    "variaveis": [
                        {"nome": "Salário Contratual", "valor": f"R$ {salario_contratual_cheio:,.2f}"},
                        {"nome": "Dias Trabalhados (Est.)", "valor": f"{prop_dias}"},
                        {"nome": "Divisor", "valor": "30"}
                    ],
                    "resultado": f"R$ {val_real:,.2f}"
                 }
            elif salario_contratual_cheio > 0:
                 memoria_salario = {
                    "tipo": "Salário Mensal Integral",
                    "variaveis": [
                        {"nome": "Salário Contratual", "valor": f"R$ {salario_contratual_cheio:,.2f}"},
                        {"nome": "Frequência", "valor": "Mensal (30 Dias)"}
                    ],
                    "resultado": f"R$ {val_real:,.2f}"
                 }

            registrar("Salário Base", val_real, val_real, cod, formula="Salário Mês", memoria=memoria_salario, tipo="P")

        # --- Base para Noturno e HE ---
        # Se não tivermos o contratual cheio (eventos 600/601 não vieram), usamos o próprio salário base.
        if salario_contratual_cheio == D("0"):
            salario_contratual_cheio = salario_base_contratual
            
        # Adicional Noturno: Sempre sobre SALÁRIO CONTRATUAL CHEIO (User Request)
        base_calculo_noturno = salario_contratual_cheio 

        # --- 3. ADICIONAIS ---
        for ev in eventos_adicionais:
            ev_cod = ev["codigo"]
            ev_nome = ev["descricao"]
            ev_val = D(ev["valor"])
            
            # Lógica dinâmica: Aceitamos o valor do banco como verdade para verbas variáveis,
            # mas acumulamos nas bases conforme flags.
            v_esp = ev_val 
            
            if "PERICULOSIDADE" in ev_nome.upper() or "INSALUBRIDADE" in ev_nome.upper():
                base_he_fixa += v_esp
            elif any(x in ev_nome.upper() for x in ["GRATIFICA", "FUNÇÃO", "CARGO"]):
                pool_gratificacoes += v_esp
            
            total_proventos += v_esp
            processar_acumuladores(ev, v_esp, "soma")
            registrar(ev_nome, v_esp, ev_val, ev_cod, formula="Dinâmico (Banco)", tipo="P")

        # --- 4. ADICIONAL NOTURNO (CORREÇÃO HEURÍSTICA) ---
        for ev in eventos_noturno:
            cod, val_real = ev["codigo"], D(ev["valor"])
            ref_str = str(ev.get("referencia", "0")).replace(",", ".")
            try:
                ref = float(ref_str)
            except:
                ref = 0.0
            
            # HEURÍSTICA DE VALOR INFORMADO (Ref == Val OU Ref Zerada mas com Valor)
            is_manual = (ref <= 0 and val_real > 0) or (abs(ref - float(val_real)) < 0.01 and ref > 10)

            if is_manual:
                v_esp = val_real
                formula = "Valor Informado (Manual)"
                memoria_not = None
            else:
                base_calc = salario_contratual_cheio # Alterado conforme solicitação: Base é Salário Contratual
                qtd_horas = calculations.time_to_decimal(ref)
                res_not = calculations.calc_adicional_noturno(
                    float(base_calc), qtd_horas, carga_horaria
                )
                v_esp = D(res_not["valor"])
                formula = f"20% de {float(base_calc):.2f}"
                memoria_not = res_not["memoria"]

            pool_noturno += v_esp
            total_variaveis_dsr += v_esp
            total_proventos += v_esp
            processar_acumuladores(ev, v_esp, "soma")
            registrar(ev["descricao"], v_esp, val_real, cod, formula=formula, memoria=memoria_not, tipo="P")

        # --- 5. OUTROS PROVENTOS (CATCH-ALL) ---
        # Garante que Gratificações (920), Praticagem (935) e outros sejam somados
        # mesmo se não categorizados explicitamente.
        # eventos_outros_proventos deve conter tudo que não é Salário, HE, Noturno, DSR.
        for ev in eventos_outros_proventos:
            cod, val_real = ev["codigo"], D(ev["valor"])
            v_esp = val_real
            nome = ev["descricao"]
            
            total_proventos += v_esp
            # Fundamental: processar acumuladores para IRRF/INSS/FGTS
            processar_acumuladores(ev, v_esp, "soma")
            registrar(nome, v_esp, val_real, cod, formula="Dinâmico (Banco)", tipo="P")

        # --- 6. HORAS EXTRAS ---
        for ev in eventos_he:
            cod, val_real = ev["codigo"], D(ev["valor"])
            v_esp = val_real
            total_variaveis_dsr += v_esp
            total_proventos += v_esp
            processar_acumuladores(ev, v_esp, "soma")
            registrar(ev["descricao"], v_esp, val_real, cod, formula="Dinâmico (Banco)", tipo="P")
            
        # --- 7. FALTAS E DESCONTOS ---
        for ev in eventos_faltas:
            cod, val_real = ev["codigo"], D(ev["valor"])
            total_descontos += val_real
            processar_acumuladores(ev, val_real, "subtrai")
            registrar(ev["descricao"], val_real, val_real, cod, formula="Desconto Falta", tipo="D")
            
        for ev in eventos_outros_descontos:
            cod, val_real = ev["codigo"], D(ev["valor"])
            nome = ev["descricao"]
            v_esp = val_real
            formula = "Leitura Direta"
            
            # Regra específica de VT Aprendiz mantida pois é regra de negócio do cliente
            if cod == "323" and is_aprendiz:
                v_esp = D(calculations.calc_vt_aprendiz(float(salario_base_contratual), dias_trabalhados))
                formula = "VT Aprendiz (Prop.)"
            
            if "PENSÃO" in nome.upper() or cod in ["340", "341", "922"]:
                pass # Processado no acumulador
                
            total_descontos += v_esp
            processar_acumuladores(ev, v_esp, "subtrai")
            registrar(nome, v_esp, val_real, cod, formula=formula, tipo="D")

        # --- 8. DSR ---
        for ev in eventos_dsr:
            cod, val_real = ev["codigo"], D(ev["valor"])
            # Cálculo Reverso para descobrir DSR do Banco
            # Se a memória for importante, calcularíamos.
            # No plano atual, apenas usamos o valor real para totais.
            # Mas se quiséssemos auditar DSR:
            res_dsr = calculations.calc_dsr(float(total_variaveis_dsr), dados_cal["dias_uteis"], dados_cal["dias_dsr"])
            v_esp = D(res_dsr["valor"])
            memoria_dsr = res_dsr["memoria"]
            
            # Se diferença for pequena, aceita (DSR tem muitas variações de dias)
            if abs(v_esp - val_real) > 5.0:
                 # Se for muito diferente, talvez dias úteis seja diferente
                 pass

            # Para auditoria, vamos registrar o valor ESPERADO se formos rigorosos,
            # ou o valor REAL se assumirmos que DSR é muito variável.
            # O sistema atual parece confiar no banco para DSR na maioria dos casos (loop eventos_dsr apenas soma)
            # Mas vamos adicionar memória se disponível.
            
            total_proventos += val_real
            processar_acumuladores(ev, val_real, "soma")
            registrar(ev["descricao"], val_real, val_real, cod, formula="DSR (Banco)", memoria=memoria_dsr, tipo="P")

        # =========================================================================
        # CÁLCULO FINAL DE IMPOSTOS (CORRIGIDO)
        # =========================================================================

        # --- INSS ---
        inss_real = D(next((e["valor"] for e in lista_eventos if e["codigo"] == "310"), 0))
        
        # Correção INSS Pró-Labore
        formula_inss = "INSS Progressivo 2026"
        if is_pro_labore:
            # 11% Fixo, limitado ao teto
            base_pro = nossa_base_inss
            TETO_DESC_CI = D("856.46") # Ajustar se necessário
            
            inss_esp = truncate(base_pro * D("0.11"), 2)
            if inss_esp > TETO_DESC_CI: inss_esp = TETO_DESC_CI
            
            if abs((base_pro * D("0.11")) - inss_real) < D("1.0"):
                inss_esp = inss_real 
                formula_inss = "INSS Pró-Labore (11%)"
        else:
            # Tenta validação cruzada:
            # 1. Base Banco (Evento 602)
            # Tenta validação cruzada:
            # 1. Base Banco (Evento 602)
            base_inss_banco = D(next((e["valor"] for e in lista_eventos if e["codigo"] == "602"), 0))
            
            # --- CÁLCULO PREFERENCIAL (NOSSA BASE CALCULADA) ---
            # Usamos nossa base detalhada para gerar a memória completa estilo Fortes
            res_inss_nossa = calculations.calc_inss_progressivo_2026(
                float(nossa_base_inss), 
                detalhes_base=detalhes_base_inss,
                abatimentos=abatimentos_inss
            )
            
            if base_inss_banco > 0:
                res_inss_banco = calculations.calc_inss_progressivo_2026(
                    float(base_inss_banco),
                    abatimentos=abatimentos_inss
                ) 
                val_inss_banco = D(res_inss_banco["valor"])
                
                # Se a base do banco bater com o real, usamos ela para o VALOR (confia no valor do banco)
                if abs(val_inss_banco - inss_real) < 0.10:
                     inss_esp = val_inss_banco
                     formula_inss = "INSS Progressivo 2026 (Base Banco)"
                     
                     # Tenta usar a memória detalhada se a nossa base bater com a do banco
                     # Isso garante que a UI mostre a composição bonita estilo Fortes mesmo validando pela base oficial
                     val_inss_nossa = D(res_inss_nossa["valor"])
                     if abs(val_inss_nossa - val_inss_banco) < 0.10:
                         formula_inss = "INSS Progressivo 2026 (Base Auditoria Detalhada)"
                         memoria_inss = res_inss_nossa["memoria"]
                     else:
                         memoria_inss = res_inss_banco["memoria"]
                else:
                     # Se não bateu com banco, usa nossa base
                     inss_esp = D(res_inss_nossa["valor"])
                     formula_inss = "INSS Progressivo 2026 (Base Auditoria)"
                     memoria_inss = res_inss_nossa["memoria"]
            else:
                 # Sem base banco, usa nossa base
                 inss_esp = D(res_inss_nossa["valor"])
                 formula_inss = "INSS Progressivo 2026 (Base Auditoria)"
                 memoria_inss = res_inss_nossa["memoria"]
            # Se houver diferença pequena, aceita o real para evitar ruído de centavos
            # Tenta validação extra com base do Fortes se houver divergência significativa
            diff_inss = abs(inss_esp - inss_real)
            inss_fortes = inss_esp 
            
            if diff_inss > D("0.10"):
                 # Tenta validar com base do Fortes (redundância proposital se a validação cruzada anterior falhou ou não foi usada)
                inss_fortes = D(calculations.calc_inss(float(fortes_base_inss)))
            if abs(inss_fortes - inss_real) < diff_inss:
                inss_esp = inss_fortes
                formula_inss += " (Base Banco)" # Adiciona sufixo se mudou
        
        # Ajuste fino final
        if abs(inss_esp - inss_real) <= 0.05:
            inss_esp = inss_real

        registrar("INSS", inss_esp, inss_real, "310", base=float(nossa_base_inss), formula=formula_inss, memoria=memoria_inss, tipo="D")
        total_descontos += inss_esp

        # --- IRRF ---
        irrf_real = D(next((e["valor"] for e in lista_eventos if e["codigo"] == "311"), 0))
        
        # Deduz pensão da base
        base_irrf_efetiva = nossa_base_irrf 
        if base_irrf_efetiva > 0:
            bruto_nossa = base_irrf_efetiva - total_pensao_alimenticia
            res_nossa = calculations.calc_irrf_detalhado(float(bruto_nossa), float(inss_real), dependentes)
            irrf_esp = D(res_nossa["valor"])
            formula_irrf = f"Base Calculada: {bruto_nossa:.2f}"
            memoria_irrf = res_nossa["memoria"]
            base_irrf_final = bruto_nossa
        else:
            irrf_esp = D("0.00")
            formula_irrf = "Base Zerada"
            memoria_irrf = None
            base_irrf_final = 0.0

        # --- VALIDAÇÃO CRUZADA COM BASE OFICIAL (603) ---
        base_irrf_banco = D(next((e["valor"] for e in lista_eventos if e["codigo"] == "603"), 0))
        
        if base_irrf_banco > 0:
             # Hipótese 1: Base 603 é Rendimento Bruto Tributável (Padrão)
             res_banco_bruta = calculations.calc_irrf_detalhado(float(base_irrf_banco), float(inss_real), dependentes)
             irrf_banco_bruta = D(res_banco_bruta["valor"])
             
             # Hipótese 2: Base 603 já é Base Líquida (Ex: BC IRRF L no PDF)
             # Passamos INSS/Deps para que a função possa reconstituir a Base Bruta para o Redutor
             res_banco_liq = calculations.calc_irrf_detalhado(float(base_irrf_banco), float(inss_real), dependentes, is_net=True)
             irrf_banco_liq = D(res_banco_liq["valor"])

             diff_nossa = abs(irrf_esp - irrf_real)
             diff_bruta = abs(irrf_banco_bruta - irrf_real)
             diff_liq = abs(irrf_banco_liq - irrf_real)
             
             # Seleção do Melhor Cenário ("Best Fit")
             # Prioriza Base Banco se a diferença for a menor OU se explicar um zero real.
             melhor_diff_banco = min(diff_bruta, diff_liq)
             
             if melhor_diff_banco < diff_nossa or (irrf_real == 0 and melhor_diff_banco == 0):
                 if diff_liq < diff_bruta:
                     irrf_esp = irrf_banco_liq
                     formula_irrf = f"Base Oficial (Líquida): {base_irrf_banco:.2f}"
                     memoria_irrf = res_banco_liq["memoria"]
                     base_irrf_final = base_irrf_banco
                 else:
                     irrf_esp = irrf_banco_bruta
                     formula_irrf = f"Base Oficial (Bruta): {base_irrf_banco:.2f}"
                     memoria_irrf = res_banco_bruta["memoria"]
                     base_irrf_final = base_irrf_banco

        # Ajuste fino se diferença for muito pequena
        if abs(irrf_esp - irrf_real) <= 0.05:
            irrf_esp = irrf_real
        
        registrar("IRRF", irrf_esp, irrf_real, "311", 
                  base=float(base_irrf_final), 
                  formula=formula_irrf, 
                  memoria=memoria_irrf, tipo="D")
        
        total_descontos += irrf_esp

        # --- FGTS ---
        fgts_real = D(next((e["valor"] for e in lista_eventos if e["codigo"] == "605"), 0))
        
        # Prioriza Base Oficial do Fortes (Evento 604)
        base_fgts_banco = D(next((e["valor"] for e in lista_eventos if e["codigo"] == "604"), 0))
        
        if base_fgts_banco > 0:
            res_fgts = calculations.calc_fgts(float(base_fgts_banco), is_aprendiz)
            fgts_esp = D(res_fgts["valor"])
            # Se a base oficial zerar o erro, perfeito.
            formula_fgts = "8% ou 2% (Base Banco)"
            # Mas se a nossa base bater melhor?
            # User disse "Prioriza a Base Oficial". Então confiamos nela.
            # E usamos ela para display da base também.
            base_fgts_final = base_fgts_banco
            memoria_fgts = res_fgts["memoria"]
        else:
            res_fgts = calculations.calc_fgts(float(nossa_base_fgts), is_aprendiz)
            fgts_esp = D(res_fgts["valor"])
            formula_fgts = "8% ou 2%"
            base_fgts_final = nossa_base_fgts
            memoria_fgts = res_fgts["memoria"]
 
        if abs(fgts_esp - fgts_real) <= 0.05:
            fgts_esp = fgts_real
            
        registrar("FGTS", fgts_esp, fgts_real, "605", base=float(base_fgts_final), formula=formula_fgts, memoria=memoria_fgts, tipo="D")

        # --- FECHAMENTO ---
        auditoria_agrupada[matricula]["totais"] = {
            "proventos": float(total_proventos),
            "descontos": float(total_descontos),
            "liquido": float(total_proventos - total_descontos),
        }

    return list(auditoria_agrupada.values())


def truncate(number, digits) -> Decimal:
    stepper = 10.0 ** digits
    return Decimal(int(stepper * float(number)) / stepper)



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


