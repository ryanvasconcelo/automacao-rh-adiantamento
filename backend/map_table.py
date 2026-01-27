import sys
import os
import itertools
from decimal import Decimal, ROUND_HALF_UP

# Configuração de ambiente
sys.path.append(os.getcwd())
try:
    from src.database import get_connection
except ImportError:
    sys.path.append(os.path.join(os.getcwd(), "backend"))
    from src.database import get_connection


def D(valor):
    if valor is None:
        return Decimal("0.00")
    return Decimal(str(valor))


def reverse_engineer_he_base(valor_pago, horas, percentual, carga_horaria=220):
    """
    Fórmula HE: Base / 220 * (1 + %) * Horas = Valor
    Base = (Valor * 220) / ((1 + %) * Horas)
    """
    valor = D(valor_pago)
    h = D(horas)
    if h == 0:
        return D(0)
    perc = D(percentual) / 100

    # Base = (Valor * Carga) / (Fator * Horas)
    fator = 1 + perc
    base = (valor * D(carga_horaria)) / (D(fator) * h)
    return base.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def find_combination(proventos, target_base):
    eventos = list(proventos.items())  # [(Nome, Valor), ...]
    matches = []

    # Testa combinações de 1 a 5 eventos (aumentei o range)
    for r in range(1, len(eventos) + 1):
        if r > 5:
            break  # Limita para não explodir
        for combo in itertools.combinations(eventos, r):
            soma = sum(item[1] for item in combo)
            if abs(soma - target_base) < Decimal("0.05"):
                matches.append([item[0] for item in combo])
    return matches


def run_investigation():
    print("🕵️‍♂️ INICIANDO INVESTIGAÇÃO DE BASES - TRANSFORMAR (9189)")

    # Matriculas do PDF
    matriculas_alvo = [
        "000284",
        "000283",
        "000282",
        "000293",
        "000279",
        "000146",
        "000195",
    ]

    placeholders = ",".join(["%s"] * len(matriculas_alvo))

    sql = f"""
        SELECT 
            EPG.Codigo,       -- 0
            EPG.Nome,         -- 1
            EFP.EVE_Codigo,   -- 2
            EVE.NomeApr,      -- 3
            EFP.Valor,        -- 4
            EFP.Referencia,   -- 5
            EVE.ProvDesc      -- 6
        FROM EFO (NOLOCK)
        INNER JOIN EPG (NOLOCK) ON EFO.EMP_Codigo = EPG.EMP_Codigo AND EFO.EPG_Codigo = EPG.Codigo
        INNER JOIN EFP (NOLOCK) ON EFO.EMP_Codigo = EFP.EMP_Codigo AND EFO.FOL_Seq = EFP.EFO_FOL_Seq AND EFO.EPG_Codigo = EFP.EFO_EPG_Codigo
        INNER JOIN EVE (NOLOCK) ON EFP.EMP_Codigo = EVE.EMP_Codigo AND EFP.EVE_CODIGO = EVE.CODIGO
        WHERE EFO.EMP_Codigo = '9189'
          AND EFO.FOL_Seq = (
              SELECT TOP 1 Seq FROM FOL WHERE EMP_Codigo = '9189' AND Folha = 2 ORDER BY Seq DESC
          )
          AND EPG.Codigo IN ({placeholders})
        ORDER BY EPG.Nome
    """

    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, matriculas_alvo)
            rows = cursor.fetchall()

            data = {}
            # Processa usando ÍNDICES da tupla
            for row in rows:
                mat = row[0]
                nome = row[1]

                if mat not in data:
                    data[mat] = {"nome": nome, "eventos": [], "proventos": {}}

                cod_evento = str(row[2])
                desc_evento = row[3]
                val = D(row[4])
                ref = D(row[5]) if row[5] else D(0)
                tipo = row[6]

                data[mat]["eventos"].append(
                    {
                        "cod": cod_evento,
                        "desc": desc_evento,
                        "val": val,
                        "ref": ref,
                        "tipo": tipo,
                    }
                )

                # Guarda proventos para combinação (exceto HE)
                if tipo == 1 and "HORA EXTRA" not in desc_evento.upper():
                    data[mat]["proventos"][f"{desc_evento} ({val})"] = val

            # Analisa
            for mat, info in data.items():
                print(f"\n👤 {info['nome']} (Mat: {mat})")

                he_events = [
                    e for e in info["eventos"] if "HORA EXTRA" in e["desc"].upper()
                ]

                if not he_events:
                    print("   ⚠️ Nenhuma Hora Extra encontrada.")
                    continue

                for he in he_events:
                    percentual = 50
                    desc = he["desc"].upper()
                    if "60" in desc:
                        percentual = 60
                    elif "100" in desc:
                        percentual = 100

                    horas = float(he["ref"])

                    # Engenharia Reversa
                    base_reversa = reverse_engineer_he_base(
                        he["val"], horas, percentual
                    )

                    print(f"   🎯 Evento: {he['desc']}")
                    print(
                        f"      Valor: R$ {he['val']} | Ref: {horas}h | %: {percentual}"
                    )
                    print(f"      🔎 BASE EFETIVA (Reversa): R$ {base_reversa}")

                    matches = find_combination(info["proventos"], base_reversa)

                    if matches:
                        print(f"      ✅ COMPOSIÇÃO:")
                        for m in matches:
                            print(f"         ➜ {' + '.join(m)}")
                    else:
                        print(
                            f"      ❌ Sem match exato. Proventos disp: {list(info['proventos'].keys())}"
                        )
                        # Tenta adicionar Adic Noturno se não tiver
                        pool_noturno = sum(
                            p["val"]
                            for p in info["eventos"]
                            if "NOTURNO" in p["desc"].upper()
                        )
                        if pool_noturno > 0:
                            print(
                                f"         (Obs: Adic. Noturno total é R$ {pool_noturno})"
                            )

    except Exception as e:
        print(f"Erro fatal: {e}")


if __name__ == "__main__":
    run_investigation()
