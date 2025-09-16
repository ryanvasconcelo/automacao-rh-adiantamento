# src/emp_ids.py

# Mapeia EMP.NOME (Fortes) -> EMP_CODIGO (int)
# Use nomes exatamente como retornam no Fortes (sua listagem).
EMP_ID_MAP = {
    # DIA 20 / JR
    "JR RODRIGUES DP": 9098,
    "J R RODRIGUES": 4826,

    # DIA 15 (principais do seu catálogo)
    "S A ALIMENTOS E PRODUTOS REGIONAIS LTDA": None,    # preencha se quiser por nome completo
    "AMM SERVICOS": 4844,
    "RIO NEGRO CERVE": 9179,
    "CM DISTRIBUIDOR": 9200,
    "MA DE O PINHEIR": 9135,
    "REAL PROTEINA": 9255,
    "REMBRAZ": 16,
    "ROLL PET": 9100,
    "GONCALES INDUST": 9141,
    "INGRID MAIA EIR": 2047,
    "PHYSIO VIDA": 2021,
    "SUPPORT NORT": 4780,
    "CSR REFEIÇÕES": 4809,
    "LUBRINORTE": 9130,
    "UNIMAR EIRELI": 2069,
    "UNIMAR": 10,
    "ABF DISTRIBUIDO": 130,
    "MARINARA PIZZAR": 2088,

    # Extras úteis do seu dump (exemplos)
    "PROJECONT": 18,
    "PROJECONT SERVI": 4810,
    "PROJECONT RT": 4817,
    "PROJECONT RT SC": 4841,
    "JR RODRIGUES": 9096,  # se existir com esse nome, manteremos também
}

# Overrides diretos por CÓDIGO do catálogo (quando o nome “amigável” difere do EMP.NOME):
# Ex.: "JR" no catálogo = 9098 no Fortes (JR RODRIGUES DP)
CODE_TO_EMP_ID = {
    "JR":   9098,
    "MTZ":  None,   # preencha se tiver o ID exato; senão deixa para casar por nome
    "AMM":  4844,
    "RIO":  9179,
    "CMD":  9200,
    "MAP":  9135,
    "RPC":  9255,
    "REM":  16,
    "ROL":  9100,
    "GON":  9141,
    "IMI":  2047,
    "PHY":  2021,
    "SUP":  4780,
    "CSR":  4809,
    "LUB":  9130,
    "UNI1": 2069,
    "UNI2": 10,
    "ABF":  130,
    "MAR":  2088,
}
