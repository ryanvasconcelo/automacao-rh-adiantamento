# src/file_generator.py
import pandas as pd
from datetime import date
from config.logging_config import log


def gerar_arquivo_final(df_final: pd.DataFrame, empresa_codigo: str):
    """
    Gera o arquivo CSV final com os dados do adiantamento processado.
    """
    if df_final.empty:
        log.warning("Nenhum dado elegível para gerar o arquivo final.")
        return

    try:
        # Filtramos apenas os funcionários que de fato receberão algum valor.
        df_para_exportar = df_final[df_final["ValorLiquidoAdiantamento"] > 0].copy()

        # Selecionamos e renomeamos as colunas para o layout final.
        colunas_finais = {
            "Matricula": "MATRICULA",
            "Nome": "NOME_FUNCIONARIO",
            "SalarioContratual": "SALARIO_BASE",
            "ValorAdiantamentoBruto": "VALOR_BRUTO",
            "ValorDesconto": "DESCONTO_CONSIGNADO",
            "ValorLiquidoAdiantamento": "VALOR_LIQUIDO",
        }
        df_para_exportar = df_para_exportar[colunas_finais.keys()].rename(
            columns=colunas_finais
        )

        # Define o nome do arquivo com a data e o código da empresa.
        hoje = date.today().strftime("%Y-%m-%d")
        caminho_arquivo = f"data/adiantamento_{empresa_codigo}_{hoje}.csv"

        # Salva o DataFrame em um arquivo CSV.
        df_para_exportar.to_csv(caminho_arquivo, index=False, sep=";", decimal=",")

        log.success(f"Arquivo final gerado com sucesso em: {caminho_arquivo}")
    except Exception as e:
        log.error(f"Falha ao gerar o arquivo final: {e}")
