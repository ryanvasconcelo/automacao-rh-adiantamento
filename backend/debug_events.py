# backend/debug_events.py
from src.database import get_connection
import pandas as pd
import warnings

# Silencia warnings do pandas/driver
warnings.filterwarnings("ignore")


def investigar_eventos(empresa_codigo, matricula, ano, mes):
    print(
        f"\n--- INVESTIGAÇÃO DETALHADA: {matricula} (Empresa {empresa_codigo} - {mes}/{ano}) ---"
    )

    ano_mes = f"{ano}{mes:02d}"

    # Query corrigida (Alias simples 'Tipo')
    query = """
        SELECT 
            EFP.EVE_CODIGO as Codigo,
            EVE.NOMEAPR as NomeEvento, -- Nome Abreviado geralmente é melhor
            EVE.ProvDesc as Tipo,      -- 1=Provento, 2=Desconto
            EFP.VALOR as Valor,
            EFP.REFERENCIA as Referencia
        FROM FOL
        INNER JOIN FPG ON FOL.EMP_Codigo = FPG.EMP_Codigo AND FOL.Seq = FPG.FOL_Seq
        INNER JOIN EFO ON FOL.EMP_Codigo = EFO.EMP_Codigo AND FOL.Seq = EFO.FOL_Seq
        INNER JOIN EFP ON EFO.EMP_Codigo = EFP.EMP_Codigo AND EFO.FOL_Seq = EFP.EFO_FOL_Seq AND EFO.EPG_Codigo = EFP.EFO_EPG_Codigo
        INNER JOIN EVE ON EFP.EMP_Codigo = EVE.EMP_Codigo AND EFP.EVE_Codigo = EVE.Codigo
        WHERE 
            FOL.EMP_Codigo = %s
            AND FPG.AnoMes = %s
            AND FOL.Folha = 1 -- Adiantamento
            AND EFO.EPG_CODIGO = %s
        ORDER BY EVE.ProvDesc, EFP.EVE_CODIGO
    """

    params = [empresa_codigo, ano_mes, matricula]

    try:
        with get_connection() as conn:
            df = pd.read_sql(query, conn, params=params)

        if df.empty:
            print("❌ NENHUM EVENTO ENCONTRADO!")
            print("Possíveis causas:")
            print("1. A folha não foi calculada para este funcionário.")
            print("2. A matrícula ou empresa estão erradas.")
        else:
            print(f"\nForam encontrados {len(df)} eventos na tabela EFP:\n")

            # Formatação bonita para leitura
            print(f"{'CÓDIGO':<8} | {'TIPO':<10} | {'VALOR (R$)':>12} | {'NOME'}")
            print("-" * 60)

            soma = 0.0

            for _, row in df.iterrows():
                tipo_cod = row["Tipo"]
                valor = float(row["Valor"])
                nome = row["NomeEvento"]
                codigo = row["Codigo"]

                tipo_desc = "Outro"
                sinal = ""

                if tipo_cod == 1:
                    tipo_desc = "PROVENTO"
                    sinal = "(+)"
                    soma += valor
                elif tipo_cod == 2:
                    tipo_desc = "DESCONTO"
                    sinal = "(-)"
                    soma -= valor
                else:
                    tipo_desc = f"TIPO {tipo_cod}"
                    sinal = "( )"
                    # Tipos 0, 3, 4 geralmente não somam no líquido

                print(f"{codigo:<8} | {tipo_desc:<10} | {sinal} {valor:>8.2f} | {nome}")

            print("-" * 60)
            print(f"SALDO LÍQUIDO FINAL (Simulado): R$ {soma:.2f}")
            print("-" * 60)

    except Exception as e:
        print(f"Erro ao executar query: {e}")


# EXECUÇÃO
if __name__ == "__main__":
    # Dados do Fábio (conforme seu print)
    investigar_eventos(empresa_codigo="9098", matricula="011802", ano=2025, mes=11)
