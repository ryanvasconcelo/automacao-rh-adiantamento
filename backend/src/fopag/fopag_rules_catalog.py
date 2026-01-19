# No arquivo: backend/src/fopag/fopag_rules_catalog.py

"""
Componente 2: O "Blueprint" (O Catálogo de Regras)
Atualizado e Sincronizado com a planilha 'Cadastro de Eventos.csv' (187 itens).
"""

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class EventProperties:
    """Define as propriedades de um Evento (variável) da folha."""

    code: str
    description: str
    type: str  # "Provento", "Desconto" ou "Informação"

    # Incidências (True = Soma na base / False = Não afeta)
    # Definido com base na natureza jurídica padrão da verba
    incide_inss: bool = False
    incide_irrf: bool = False
    incide_fgts: bool = False


# --- CATÁLOGO COMPLETO (187 EVENTOS) ---
EVENT_CATALOG: Dict[str, EventProperties] = {
    # 1 a 99 - Proventos Comuns e Adicionais
    "1": EventProperties("1", "Adiantamento.", "Provento", False, False, False),
    "2": EventProperties("2", "Bolsa-Salário", "Provento", True, True, True),
    "3": EventProperties(
        "3", "Salário Maternidade Prorrogação", "Provento", True, True, True
    ),
    "4": EventProperties("4", "Saldo de Salário", "Provento", True, True, True),
    "5": EventProperties("5", "Salário-hora", "Provento", True, True, True),
    "8": EventProperties("8", "Salário-Maternidade", "Provento", True, True, True),
    "9": EventProperties("9", "Auxílio-Creche", "Provento", False, False, False),
    "10": EventProperties("10", "Salário-Família", "Provento", False, False, False),
    "11": EventProperties("11", "Salário-Base", "Provento", True, True, True),
    "12": EventProperties("12", "Adicional Noturno.", "Provento", True, True, True),
    "13": EventProperties("13", "Periculosidade", "Provento", True, True, True),
    "16": EventProperties("16", "Insalubridade", "Provento", True, True, True),
    "17": EventProperties("17", "Anuênio", "Provento", True, True, True),
    "30": EventProperties("30", "Comissões", "Provento", True, True, True),
    "31": EventProperties("31", "Quebra de Caixa", "Provento", True, True, True),
    "32": EventProperties("32", "Reembolso Gorjeta", "Provento", False, False, False),
    "49": EventProperties(
        "49", "Descanso Semanal Remunerado", "Provento", True, True, True
    ),
    "50": EventProperties("50", "Adicional Noturno", "Provento", True, True, True),
    "51": EventProperties("51", "Adicional Noturno 25%", "Provento", True, True, True),
    "52": EventProperties("52", "Adicional Noturno 21%", "Provento", True, True, True),
    "60": EventProperties("60", "Hora Extra 50%", "Provento", True, True, True),
    "61": EventProperties("61", "Hora Extra 100%", "Provento", True, True, True),
    "62": EventProperties("62", "Hora Extra 60%", "Provento", True, True, True),
    "74": EventProperties(
        "74", "Reembolso de Gratificação", "Provento", False, False, False
    ),
    "75": EventProperties("75", "Bonificação.", "Provento", False, False, False),
    "76": EventProperties(
        "76", "Dif.salarial do Dissidio ref. 06.2024", "Provento", True, True, True
    ),
    "77": EventProperties(
        "77", "Dif. Salarial Dissidio ref. 07.2022", "Provento", True, True, True
    ),
    "88": EventProperties(
        "88", "Líquido de 13º Salário", "Provento", False, False, False
    ),
    "89": EventProperties(
        "89", "Líquido de Adiantamento de 13º Salário", "Provento", False, False, False
    ),
    "90": EventProperties("90", "Líquido Negativo", "Provento", False, False, False),
    "91": EventProperties("91", "Arredondamento", "Provento", False, False, False),
    "92": EventProperties(
        "92", "Arredondamento Compensação (Provento)", "Provento", False, False, False
    ),
    "94": EventProperties("94", "Reembolso VT", "Provento", False, False, False),
    "99": EventProperties("99", "Complemento de Folha", "Provento", True, True, True),
    # 100 a 299 - Férias, Rescisão e Outros
    "100": EventProperties(
        "100", "Provisão Cred. Trab.- Provento", "Provento", False, False, False
    ),
    "110": EventProperties(
        "110", "Remuneração de Férias", "Provento", True, True, True
    ),
    "111": EventProperties("111", "1/3 de Férias", "Provento", True, True, True),
    "112": EventProperties(
        "112", "Remuneração de Férias em Dobro", "Provento", True, True, True
    ),
    "113": EventProperties("113", "Abono Pecuniário", "Provento", False, False, False),
    "114": EventProperties(
        "114", "Complemento de Férias", "Provento", True, True, True
    ),
    "115": EventProperties(
        "115", "Complemento de Abono Pecuniário", "Provento", False, False, False
    ),
    "120": EventProperties(
        "120", "Participação nos Lucros", "Provento", False, True, False
    ),
    "127": EventProperties(
        "127", "Consignado Crédito do Trabalhador. 1", "Desconto", False, False, False
    ),
    "150": EventProperties(
        "150", "Adiantamento de 13º Salário", "Provento", False, False, True
    ),
    "151": EventProperties(
        "151", "Adiantamento de 13º Salário (Férias)", "Provento", False, False, True
    ),
    "160": EventProperties("160", "13º Salário", "Provento", True, True, True),
    "170": EventProperties(
        "170", "Complemento de 13º Salário", "Provento", True, True, True
    ),
    "171": EventProperties("171", "Gorjeta", "Provento", True, True, True),
    "172": EventProperties("172", "Ajuda de Custo", "Provento", False, False, False),
    "200": EventProperties(
        "200", "Aviso Prévio (Provento)", "Provento", False, False, True
    ),
    "201": EventProperties(
        "201", "Resc. Antes do Prazo Determinado (Prov.)", "Provento", True, True, True
    ),
    "202": EventProperties(
        "202", "Dispensa Próxima à Data-Base", "Provento", False, False, False
    ),
    "203": EventProperties("203", "Férias Vencidas", "Provento", False, False, False),
    "204": EventProperties(
        "204", "Férias Vencidas em Dobro", "Provento", False, False, False
    ),
    "205": EventProperties(
        "205", "Férias Proporcionais", "Provento", False, False, False
    ),
    "206": EventProperties(
        "206", "Férias (Aviso Prévio)", "Provento", False, False, False
    ),
    "207": EventProperties(
        "207", "1/3 de Férias (Rescisão)", "Provento", False, False, False
    ),
    "208": EventProperties(
        "208", "13º Salário (Rescisão)", "Provento", True, True, True
    ),
    "209": EventProperties(
        "209", "13º Salário (Aviso Prévio)", "Provento", False, False, True
    ),
    "210": EventProperties(
        "210", "Quebra de caixa mês anterior", "Provento", True, True, True
    ),
    "299": EventProperties("299", "Outros (Provento)", "Provento", True, True, True),
    # 300 a 599 - Descontos
    "300": EventProperties("300", "Adiantamento", "Desconto", False, False, False),
    "301": EventProperties("301", "Convenio Drogaria", "Desconto", False, False, False),
    "302": EventProperties(
        "302", "Assistência Médica - Desconto", "Desconto", False, False, False
    ),
    "305": EventProperties("305", "Atrasos", "Desconto", True, True, True),
    "310": EventProperties("310", "INSS", "Desconto", False, False, False),
    "311": EventProperties("311", "IRRF", "Desconto", False, False, False),
    "312": EventProperties(
        "312", "Contribuição Sindical", "Desconto", False, False, False
    ),
    "314": EventProperties("314", "Atrasos", "Desconto", True, True, True),
    "315": EventProperties(
        "315", "Adiantamento de gorjeta", "Desconto", False, False, False
    ),
    # "319": EventProperties("319", "Vale Refeição", "Desconto", False, False, False),
    "320": EventProperties("320", "Vale-Transporte", "Desconto", False, False, False),
    "321": EventProperties("321", "Faltas em Horas", "Desconto", True, True, True),
    "322": EventProperties(
        "322", "Mensalidade Sindical", "Desconto", False, False, False
    ),
    "323": EventProperties("323", "Reembolso de salario", "Provento", True, True, True),
    "324": EventProperties(
        "324", "Desc. transporte s/ falta", "Desconto", False, False, False
    ),
    "330": EventProperties("330", "Desc. de Vale", "Desconto", False, False, False),
    "340": EventProperties(
        "340", "Pensão Alimentícia (1)", "Desconto", False, True, False
    ),
    "349": EventProperties("349", "DSR s/ Faltas", "Desconto", True, True, True),
    "390": EventProperties(
        "390", "Líquido Negativo Compensação", "Desconto", False, False, False
    ),
    "391": EventProperties(
        "391", "Arredondamento (Desconto)", "Desconto", False, False, False
    ),
    "392": EventProperties(
        "392", "Arredondamento (Desc)", "Desconto", False, False, False
    ),
    "450": EventProperties(
        "450",
        "Adiantamento de 13º Salário Compensação",
        "Desconto",
        False,
        False,
        False,
    ),
    "451": EventProperties(
        "451", "Salário-Maternidade 13º Salário", "Desconto", False, False, False
    ),
    "452": EventProperties(
        "452", "Indenização Lei 12.506/11", "Provento", False, False, True
    ),
    "500": EventProperties(
        "500", "Aviso Prévio (Desconto)", "Desconto", False, False, True
    ),
    "501": EventProperties(
        "501",
        "Resc. Antes do Prazo Determinado (Desc.)",
        "Desconto",
        False,
        False,
        False,
    ),
    "502": EventProperties("502", "INSS (Rescisão)", "Desconto", False, False, False),
    "504": EventProperties(
        "504", "INSS 13º Salário (Rescisão)", "Desconto", False, False, False
    ),
    "505": EventProperties("505", "IRRF (Rescisão)", "Desconto", False, False, False),
    "506": EventProperties(
        "506", "IRRF Férias (Rescisão)", "Desconto", False, False, False
    ),
    "507": EventProperties(
        "507", "IRRF 13º Salário (Rescisão)", "Desconto", False, False, False
    ),
    "508": EventProperties(
        "508", "IRRF(Participação nos Lucros)", "Desconto", False, False, False
    ),
    "599": EventProperties("599", "Outros (Desconto)", "Desconto", False, False, False),
    # 600 a 699 - Bases Informativas
    "600": EventProperties(
        "600", "Salário Contratual", "Informação", False, False, False
    ),
    "601": EventProperties(
        "601", "Remuneração Fixa", "Informação", False, False, False
    ),
    "602": EventProperties(
        "602", "INSS Base de Cálculo", "Informação", False, False, False
    ),
    "603": EventProperties(
        "603", "IRRF Base de Cálculo", "Informação", False, False, False
    ),
    "604": EventProperties(
        "604", "FGTS Base de Cálculo", "Informação", False, False, False
    ),
    "605": EventProperties("605", "FGTS", "Informação", False, False, False),
    "606": EventProperties(
        "606", "FGTS Contribuição Social", "Informação", False, False, False
    ),
    "607": EventProperties(
        "607", "Salário-Maternidade", "Informação", False, False, False
    ),
    "608": EventProperties(
        "608", "Adiantamento Base de Cálculo", "Informação", False, False, False
    ),
    "609": EventProperties(
        "609",
        "Salário-Maternidade 13º Salário (Info.)",
        "Informação",
        False,
        False,
        False,
    ),
    "610": EventProperties(
        "610", "Salário-Família Base de Cálculo", "Informação", False, False, False
    ),
    # 900+ - Eventos Customizados
    "900": EventProperties("900", "Multa FGTS", "Informação", False, False, False),
    "901": EventProperties(
        "901", "Multa FGTS Contribuição Social", "Informação", False, False, False
    ),
    "902": EventProperties(
        "902", "FTGS Aviso Indenizado", "Informação", False, False, False
    ),
    "903": EventProperties(
        "903",
        "FGTS Contrib. Social Aviso Indenizado",
        "Informação",
        False,
        False,
        False,
    ),
    "904": EventProperties(
        "904", "Saldo para Fins Rescisórios", "Informação", False, False, False
    ),
    "905": EventProperties("905", "Desc. Ad. Salário", "Desconto", False, False, False),
    "906": EventProperties(
        "906", "Contribuicao Negocial", "Desconto", False, False, False
    ),
    "907": EventProperties(
        "907", "Desconto Vale Transporte", "Desconto", False, False, False
    ),
    "908": EventProperties(
        "908", "Desc. Vale Alimentação", "Desconto", False, False, False
    ),
    "909": EventProperties("909", "Gratificação", "Provento", True, True, True),
    "910": EventProperties("910", "Quebra de caixa", "Provento", True, True, True),
    "911": EventProperties(
        "911", "Cont. Assistencial", "Desconto", False, False, False
    ),
    "912": EventProperties(
        "912", "Retroativo salario familia", "Provento", False, False, False
    ),
    "913": EventProperties(
        "913", "Contribuição Negocial 2%", "Desconto", False, False, False
    ),
    "914": EventProperties(
        "914", "Contribuição Negocial 3%", "Desconto", False, False, False
    ),
    "915": EventProperties(
        "915", "Dev. de V.T mês 04,05, 06/2019", "Provento", False, False, False
    ),
    "916": EventProperties("916", "Quebra de Caixa.", "Provento", True, True, True),
    "917": EventProperties(
        "917", "1/3 de Férias Proporcionais", "Provento", False, False, False
    ),
    "918": EventProperties(
        "918", "1/3 de Férias Vencidas", "Provento", False, False, False
    ),
    "919": EventProperties(
        "919", "FGTS Base de Cálculo - Militar", "Informação", False, False, False
    ),
    "920": EventProperties(
        "920", "FGTS B. de Cálculo - Acidente", "Informação", False, False, False
    ),
    "921": EventProperties(
        "921", "Sal. Maternidade 13º Salário", "Provento", True, True, True
    ),
    "922": EventProperties(
        "922", "FGTS B. de Cálculo - Rescisão", "Informação", False, False, False
    ),
    "923": EventProperties("923", "Horas injustificadas", "Desconto", True, True, True),
    "924": EventProperties(
        "924", "Quitação Banco de Horas 2019", "Provento", False, False, False
    ),
    "319": EventProperties("319", "Faltas em Horas", "Desconto", True, True, True),
    "926": EventProperties(
        "926", "Saldo Banco de Horas Negativo", "Desconto", True, True, True
    ),
    "927": EventProperties(
        "927", "Quitação Banco de Horas 2020", "Provento", False, False, False
    ),
    "928": EventProperties("928", "Prêmio", "Provento", True, True, True),
    "929": EventProperties(
        "929", "Afastamento por Covid-19", "Informação", False, False, False
    ),
    "930": EventProperties(
        "930", "Ajuda Compensatória", "Provento", False, False, False
    ),
    "931": EventProperties(
        "931", "INSS13ºSalario- Intermitente", "Desconto", False, False, False
    ),
    "932": EventProperties(
        "932", "IRRF13ºSalario-Intermetente", "Desconto", False, False, False
    ),
    "933": EventProperties(
        "933", "IRRFferias-Intermetente", "Desconto", False, False, False
    ),
    "934": EventProperties(
        "934", "Saldo de Banco de Horas", "Provento", False, False, False
    ),
    "935": EventProperties("935", "INSS 13° Salario", "Desconto", False, False, False),
    "936": EventProperties("936", "IRRF 13° Salario", "Desconto", False, False, False),
    "937": EventProperties(
        "937", "Desconto de valores recebidos", "Desconto", False, False, False
    ),
    "938": EventProperties(
        "938", "Ajuda de Custo - Cópia", "Provento", False, False, False
    ),
    "939": EventProperties("939", "Salário Licença", "Provento", True, True, True),
    "940": EventProperties(
        "940", "Salário Licença Previdenciário", "Provento", True, True, True
    ),
    "941": EventProperties(
        "941", "1/3 de Abono Pecuniário", "Provento", False, False, False
    ),
    "942": EventProperties(
        "942", "Adiant. de Férias Desconto", "Desconto", False, False, False
    ),
    "943": EventProperties(
        "943", "Adiant. de Férias Provento", "Provento", False, False, False
    ),
    "944": EventProperties(
        "944", "Antecipação reajuste CCT", "Provento", True, True, True
    ),
    "945": EventProperties(
        "945", "Quitação Banco de Horas 2022/2023", "Provento", False, False, False
    ),
    "946": EventProperties(
        "946", "Assistência Médica - Benefício", "Informação", False, False, False
    ),
    "947": EventProperties(
        "947", "Assistência Odonto - Benefício", "Informação", False, False, False
    ),
    "948": EventProperties(
        "948", "Transporte - Benefício", "Informação", False, False, False
    ),
    "949": EventProperties(
        "949", "Alimentação -Benefício", "Informação", False, False, False
    ),
    "950": EventProperties("950", "Reembolso Vale", "Provento", False, False, False),
    "951": EventProperties(
        "951", "Taxa de Transferencia", "Desconto", False, False, False
    ),
    "952": EventProperties(
        "952", "Salario hora - indice 1006", "Provento", True, True, True
    ),
    "953": EventProperties(
        "953", "Reembolso de Bonificação", "Provento", False, False, False
    ),
    "954": EventProperties("954", "Bonificação", "Provento", True, True, True),
    "955": EventProperties(
        "955", "Reembolso Bonificação", "Provento", False, False, False
    ),
    "956": EventProperties(
        "956", "Reemb Bonificação/Premiação", "Provento", True, True, True
    ),
    "957": EventProperties("957", "Estabilidade", "Provento", True, True, True),
    "958": EventProperties(
        "958", "Adiantamento 13º Comp.(Mensal)", "Desconto", False, False, False
    ),
    "959": EventProperties(
        "959", "Adiantamento 13º Comp.(Aviso)", "Desconto", False, False, False
    ),
    "960": EventProperties(
        "960", "Saldo de Banco de Horas 2023", "Provento", False, False, False
    ),
    "961": EventProperties(
        "961", "Saldo de Banco de Horas 2024", "Provento", False, False, False
    ),
    "962": EventProperties(
        "962", "Sal. Maternidade Prorrogação Emp. Cidadã", "Provento", True, True, True
    ),
    "963": EventProperties("963", "Premiação", "Provento", True, True, True),
    "964": EventProperties(
        "964", "Saldo de Banco de Horas 2025", "Provento", False, False, False
    ),
    "965": EventProperties(
        "965", "Desc. VT Retroativo", "Desconto", False, False, False
    ),
    "966": EventProperties(
        "966", "Mensalidade Sindical - Retroativo", "Desconto", False, False, False
    ),
    "967": EventProperties(
        "967", "Reembolso Vale Alimentação", "Provento", False, False, False
    ),
    "968": EventProperties(
        "968", "Consignado Crédito do Trabalhador", "Desconto", False, False, False
    ),
    "969": EventProperties(
        "969", "Devolução de Vale transporte", "Desconto", False, False, False
    ),
    "970": EventProperties(
        "970", "Provisão Cred. Trab.- Desconto", "Desconto", False, False, False
    ),
    "971": EventProperties(
        "971", "Devolução de Vale Refeição", "Desconto", False, False, False
    ),
    "972": EventProperties(
        "972", "Quitação Banco de Horas 2024", "Provento", False, False, False
    ),
    "973": EventProperties(
        "973", "Consignado Crédito do Trabalhador. 2", "Desconto", False, False, False
    ),
    "974": EventProperties("974", "Vale/ Compra", "Desconto", False, False, False),
    "975": EventProperties("975", "Acordo Trabalhista", "Provento", True, True, True),
    "976": EventProperties(
        "976", "Dif. Salarial Dissidio ref. 06.2025", "Provento", False, False, False
    ),
    "977": EventProperties(
        "977", "Dif. Salarial Dissidio ref. 07.2025", "Provento", False, False, False
    ),
    "978": EventProperties(
        "978", "Consignado Crédito do Trabalhador. 3", "Desconto", False, False, False
    ),
    "979": EventProperties(
        "979", "Consignado Crédito do Trabalhador. 4", "Desconto", False, False, False
    ),
    "980": EventProperties("980", "Diferença de Ferias", "Provento", True, True, True),
    "981": EventProperties(
        "981", "Contribuição Assistencial", "Desconto", False, False, False
    ),
    "982": EventProperties(
        "982", "Desc. Pagto Indevido", "Desconto", False, False, False
    ),
}


@dataclass(frozen=True)
class FopagCompanyRule:
    # --- CAMPO NOVO PARA CORRIGIR O ERRO ---
    base: str = (
        "11"  # O sistema antigo chama de 'base', nós chamamos de cod_salario_base. Isso resolve.
    )
    # ---------------------------------------

    percentual_vt: float = 0.06
    dia_limite_beneficio: int = 20
    valor_cota_salario_familia: float = 65.00
    calcula_periculosidade: bool = True
    calcula_insalubridade: bool = True
    usa_calc_inss: bool = True
    usa_calc_irrf: bool = True
    usa_calc_fgts: bool = True
    cod_salario_base: str = "11"
    cod_inss: str = "310"
    cod_irrf: str = "311"
    cod_he_50: str = "60"
    cod_he_100: str = "61"
    cod_dsr_he: str = "49"
    cod_adic_noturno: str = "12"
    cod_periculosidade: str = "13"
    cod_desconto_adiantamento: str = "300"
    cod_faltas: str = "321"  # Faltas em Dias
    cod_faltas_em_horas: str = "319"  # Faltas em Horas
    cod_dsr_desconto: str = "349"
    cod_vale_transporte: str = "320"
    cod_vale_refeicao: str = "319"
    # cod_salario_familia: str = "306" # Duplicado no original, mantendo o debaixo
    cod_salario_familia: str = "10"
    cod_salario_maternidade: str = "8"
    cod_reembolso_salarial: Optional[int] = None


COMPANY_CATALOG: Dict[str, FopagCompanyRule] = {
    "DEFAULT": FopagCompanyRule(),
    "JR": FopagCompanyRule(
        dia_limite_beneficio=15,
        calcula_insalubridade=False,
        valor_cota_salario_familia=65.00,
    ),
    # --- NOVA EMPRESA ADICIONADA ---
    # A CICLISTA (Código 2056)
    # Assumindo regras padrão. Se tiver algo diferente, altere aqui.
    "2056": FopagCompanyRule(),
    "CMD": FopagCompanyRule(percentual_vt=0.04),
}


def get_event_properties(code: str) -> Optional[EventProperties]:
    return EVENT_CATALOG.get(code)


def get_company_rule(company_code: str) -> FopagCompanyRule:
    return COMPANY_CATALOG.get(company_code, COMPANY_CATALOG["DEFAULT"])
