# Arquivo: backend/debug_sql.py
from src.database import get_connection
from src.emp_ids import CODE_TO_EMP_ID

# --- CONFIGURAÇÃO ---
CODIGO_EMPRESA_CATALOGO = "JR"  # Tente "JR" ou o código que você está usando
ANO = 2025
# --------------------


def debug_folhas():
    fortes_id = CODE_TO_EMP_ID.get(CODIGO_EMPRESA_CATALOGO)
    print(f"--- DIAGNÓSTICO SQL ---")
    print(f"Empresa Catálogo: {CODIGO_EMPRESA_CATALOGO}")
    print(f"ID Fortes (SQL): {fortes_id}")

    if not fortes_id:
        print("ERRO: Empresa não encontrada no emp_ids.py")
        return

    conn = get_connection()
    cursor = conn.cursor(as_dict=True)

    sql = """
        SELECT TOP 20
            FPG.AnoMes,
            FOL.Seq,
            FOL.Folha as TipoFolha,  -- 1=Adiant, 2=Mensal, etc.
            FPG.Tipo as TipoProcessamento, -- 1=Normal, etc.
            FOL.Encerrada,
            FOL.DtCalculo
        FROM FOL (NOLOCK)
        INNER JOIN FPG (NOLOCK) 
            ON FOL.EMP_Codigo = FPG.EMP_Codigo 
            AND FOL.Seq = FPG.FOL_Seq
        WHERE 
            FOL.EMP_Codigo = %s
            AND FPG.AnoMes LIKE %s
        ORDER BY FPG.AnoMes DESC, FOL.Seq DESC
    """

    # Busca qualquer coisa de 2025 (2025%)
    param_ano = f"{ANO}%"

    print(f"\nBuscando folhas no banco para EMP_Codigo={fortes_id} e Ano={ANO}...")
    try:
        cursor.execute(sql, (str(fortes_id), param_ano))
        rows = cursor.fetchall()

        if not rows:
            print(
                "NENHUM REGISTRO ENCONTRADO! Verifique se o ID da empresa está correto."
            )
        else:
            print(
                f"{'AnoMes':<8} | {'Seq':<6} | {'TipoFolha':<10} | {'TipoProc':<8} | {'Encerrada':<10} | {'DtCalculo'}"
            )
            print("-" * 70)
            for row in rows:
                # TipoFolha: 1=Adiant, 2=Mensal
                tipo_folha = row["TipoFolha"]
                desc_tipo = "MENSAL (2)" if tipo_folha == 2 else f"OUTRO ({tipo_folha})"

                print(
                    f"{row['AnoMes']:<8} | {row['Seq']:<6} | {desc_tipo:<10} | {row['TipoProcessamento']:<8} | {row['Encerrada']:<10} | {row['DtCalculo']}"
                )

    except Exception as e:
        print(f"Erro SQL: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    debug_folhas()
