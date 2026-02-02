import sys
import os
from decimal import Decimal

# Setup path
sys.path.append(os.getcwd())
try:
    from src.database import get_connection
except ImportError:
    # Fallback se rodar fora da estrutura
    sys.path.append(os.path.join(os.getcwd(), "backend"))
    from src.database import get_connection


def D(valor):
    if valor is None:
        return Decimal("0.00")
    return Decimal(str(valor))


def fmt(val):
    return f"{val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def run_investigation():
    print("\n🕵️‍♂️ INVESTIGAÇÃO DE BASES E INCIDÊNCIAS (FOLHA 2 - MENSAL)")
    print("=" * 100)

    # ALVOS:
    # 000093 = Liliane
    # 000147 = Joao Paulo
    # 000287 = Aurino
    # 000146 = Luciana
    alvos = ["000093", "000147", "000287", "000146"]

    placeholders = ",".join(["%s"] * len(alvos))

    # OBS: Forçamos a busca na Folha Mensal (Folha = 2 no Fortes)
    sql = f"""
        SELECT 
            EPG.Codigo AS Mat,
            EPG.Nome,
            EFP.EVE_Codigo AS Cod,
            EVE.NomeApr AS Evento,
            EFP.Valor AS Valor,
            EVE.ProvDesc AS Tipo, -- 1=Prov, 2=Desc
            EVE.IndicativoCPMensalFerias AS Inc_INSS,
            EVE.IndicativoIRRFMensal AS Inc_IRRF
        FROM EFO (NOLOCK)
        INNER JOIN EPG (NOLOCK) ON EFO.EMP_Codigo = EPG.EMP_Codigo AND EFO.EPG_Codigo = EPG.Codigo
        INNER JOIN EFP (NOLOCK) ON EFO.EMP_Codigo = EFP.EMP_Codigo AND EFO.FOL_Seq = EFP.EFO_FOL_Seq AND EFO.EPG_Codigo = EFP.EFO_EPG_Codigo
        INNER JOIN EVE (NOLOCK) ON EFP.EMP_Codigo = EVE.EMP_Codigo AND EFP.EVE_CODIGO = EVE.CODIGO
        WHERE EFO.EMP_Codigo = '9189'
          -- Pega a última folha Tipo 2 (Mensal)
          AND EFO.FOL_Seq = (SELECT TOP 1 Seq FROM FOL WHERE EMP_Codigo = '9189' AND Folha = 2 ORDER BY Seq DESC)
          AND EPG.Codigo IN ({placeholders})
        ORDER BY EPG.Nome, EVE.ProvDesc, EFP.EVE_Codigo
    """

    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, alvos)
            rows = cursor.fetchall()

            curr_mat = None

            # Acumuladores
            base_inss_calc = Decimal(0)
            base_irrf_calc = Decimal(0)

            print(
                f"{'COD':<5} {'EVENTO':<30} {'TIPO':<4} {'VALOR':<12} {'INC.INSS':<8} {'INC.IRRF'}"
            )
            print("-" * 100)

            for row in rows:
                mat, nome, cod, evt, val, tipo, inc_inss, inc_irrf = row

                if mat != curr_mat:
                    if curr_mat:
                        print(
                            f"   >>> SOMA SIMULADA: INSS={fmt(base_inss_calc)} | IRRF={fmt(base_irrf_calc)}"
                        )
                        print("=" * 100)
                    print(f"\n👤 {nome} ({mat})")
                    curr_mat = mat
                    base_inss_calc = Decimal(0)
                    base_irrf_calc = Decimal(0)

                val_dec = D(val)
                inc_inss_bool = (
                    str(inc_inss).strip() not in ["0", "N", "None", ""]
                    if inc_inss
                    else False
                )
                inc_irrf_bool = (
                    str(inc_irrf).strip() not in ["0", "N", "None", ""]
                    if inc_irrf
                    else False
                )

                # Ignora bases informativas na soma
                if cod not in [
                    "600",
                    "601",
                    "602",
                    "603",
                    "604",
                    "605",
                    "606",
                    "607",
                    "608",
                    "310",
                    "311",
                ]:
                    if tipo == 1:  # Provento
                        if inc_inss_bool:
                            base_inss_calc += val_dec
                        if inc_irrf_bool:
                            base_irrf_calc += val_dec
                    elif tipo == 2:  # Desconto
                        if inc_inss_bool:
                            base_inss_calc -= val_dec
                        if inc_irrf_bool:
                            base_irrf_calc -= val_dec

                inc_inss_str = "SIM" if inc_inss_bool else "-"
                inc_irrf_str = "SIM" if inc_irrf_bool else "-"

                # Destaque
                if cod in ["602", "603", "310", "311"]:
                    print(
                        f"   👉 {cod:<5} {evt:<30} {tipo:<4} R$ {fmt(val):<9} {'[BASE/IMP]':<15}"
                    )
                else:
                    print(
                        f"      {cod:<5} {evt:<30} {tipo:<4} R$ {fmt(val):<9} {inc_inss_str:<8} {inc_irrf_str}"
                    )

            if curr_mat:
                print(
                    f"   >>> SOMA SIMULADA: INSS={fmt(base_inss_calc)} | IRRF={fmt(base_irrf_calc)}"
                )

    except Exception as e:
        print(f"Erro: {e}")


if __name__ == "__main__":
    run_investigation()
