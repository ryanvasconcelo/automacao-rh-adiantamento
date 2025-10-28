"""
Módulo para ajustar parâmetros ANTES do cálculo do Fortes.
Modifica a tabela SEP (cadastro do funcionário) para que o Fortes calcule corretamente.
"""

import pandas as pd
import pymssql
from typing import Dict, List, Tuple, Optional
from .database import get_connection
from config.logging_config import log


class FortesPreCalculation:
    """Ajusta parâmetros na tabela SEP antes do cálculo."""

    def __init__(self, emp_codigo: str):
        self.emp_codigo = str(emp_codigo)
        self.has_update_permission = None  # Cache da verificação de permissão

    def verificar_permissao_update(self) -> bool:
        """
        Verifica se o usuário tem permissão de UPDATE na tabela SEP.
        Usa cache para evitar verificações repetidas.
        """
        if self.has_update_permission is not None:
            return self.has_update_permission

        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                # Tenta fazer um UPDATE dummy que não afeta nada
                query = """
                    UPDATE SEP 
                    SET PERCENTUALADIANT = PERCENTUALADIANT 
                    WHERE EMP_CODIGO = %s AND EPG_CODIGO = '-999999'
                """
                cursor.execute(query, [self.emp_codigo])
                conn.commit()

            self.has_update_permission = True
            log.info("✓ Permissão de UPDATE na tabela SEP confirmada")
            return True

        except Exception as e:
            error_msg = str(e)
            if (
                "UPDATE permission was denied" in error_msg
                or "permiss" in error_msg.lower()
            ):
                self.has_update_permission = False
                log.error("=" * 80)
                log.error("✗ SEM PERMISSÃO DE UPDATE NA TABELA SEP")
                log.error("=" * 80)
                log.error("Solução: Execute no SQL Server (como DBA):")
                log.error("")
                log.error("  USE AC;")
                log.error("  GO")
                log.error("  GRANT UPDATE ON dbo.SEP TO [seu_usuario];")
                log.error("  GO")
                log.error("")
                log.error("Ou configure um usuário com permissões adequadas.")
                log.error("=" * 80)
                return False
            else:
                log.error(f"Erro ao verificar permissão: {e}")
                raise

    def ajustar_parametros_funcionario(
        self,
        matricula: str,
        percentual_adiant: Optional[float] = None,
        valor_fixo_adiant: Optional[float] = None,
        flag_adiantamento: str = "S",
    ) -> bool:
        """
        ⚠️ ATUALIZA PARÂMETROS DO FUNCIONÁRIO NA TABELA SEP.

        Estes ajustes afetam o cálculo futuro do Fortes.

        Args:
            matricula: Matrícula do funcionário
            percentual_adiant: Percentual de adiantamento (ex: 40.0)
            valor_fixo_adiant: Valor fixo de adiantamento
            flag_adiantamento: 'S' para ativo, 'N' para inativo

        Returns:
            True se atualizado com sucesso
        """
        # Verificar permissão antes de tentar
        if not self.verificar_permissao_update():
            log.warning(f"Matrícula {matricula}: Ignorado (sem permissão UPDATE)")
            return False

        try:
            # Busca o registro mais recente do SEP
            query_select = """
                SELECT DATA, PERCENTUALADIANT, VALORADIANT, ADIANTAMENTO
                FROM SEP
                WHERE EMP_CODIGO = %s AND EPG_CODIGO = %s
                AND DATA = (
                    SELECT MAX(DATA) FROM SEP 
                    WHERE EMP_CODIGO = %s AND EPG_CODIGO = %s
                )
            """

            with get_connection() as conn:
                df = pd.read_sql(
                    query_select,
                    conn,
                    params=[self.emp_codigo, matricula, self.emp_codigo, matricula],
                )

                if df.empty:
                    log.error(f"Funcionário {matricula} não encontrado na SEP")
                    return False

                data_sep = df["DATA"].iloc[0]

                # Monta o UPDATE
                updates = []
                params = []

                if percentual_adiant is not None:
                    updates.append("PERCENTUALADIANT = %s")
                    params.append(percentual_adiant)

                if valor_fixo_adiant is not None:
                    updates.append("VALORADIANT = %s")
                    params.append(valor_fixo_adiant)

                if flag_adiantamento:
                    updates.append("ADIANTAMENTO = %s")
                    params.append(flag_adiantamento)

                if not updates:
                    log.warning("Nenhuma atualização especificada")
                    return False

                query_update = f"""
                    UPDATE SEP
                    SET {', '.join(updates)}
                    WHERE EMP_CODIGO = %s 
                        AND EPG_CODIGO = %s 
                        AND DATA = %s
                """

                params.extend([self.emp_codigo, matricula, data_sep])

                cursor = conn.cursor()
                cursor.execute(query_update, params)
                conn.commit()

                log.success(
                    f"✅ Matrícula {matricula}: PERCENTUAL={percentual_adiant or 'N/A'}%, "
                    f"VALOR=R${valor_fixo_adiant or 0:.2f}"
                )
                return True

        except Exception as e:
            error_msg = str(e)
            if (
                "UPDATE permission was denied" in error_msg
                or "permiss" in error_msg.lower()
            ):
                log.error(f"✗ Matrícula {matricula}: Permissão negada")
            else:
                log.error(f"✗ Matrícula {matricula}: Erro ao atualizar - {e}")
            return False

    def ajustar_lote(self, df_ajustes: pd.DataFrame) -> Tuple[int, int, List[Dict]]:
        """
        Ajusta parâmetros em lote para múltiplos funcionários.

        DataFrame deve conter:
        - Matricula
        - PercentualAdiant (opcional)
        - ValorFixoAdiant (opcional)

        Returns:
            (sucessos, falhas, detalhes_erros)
        """
        # Verificar permissão ANTES de processar o lote
        if not self.verificar_permissao_update():
            log.error("⚠️ Abortando lote: sem permissão de UPDATE na tabela SEP")

            # Retornar falha para todos
            erros = [
                {
                    "matricula": str(row["Matricula"]),
                    "erro": "Sem permissão UPDATE na tabela SEP",
                    "solucao": "GRANT UPDATE ON dbo.SEP TO [usuario]",
                }
                for _, row in df_ajustes.iterrows()
            ]
            return 0, len(df_ajustes), erros

        # Se tem permissão, processar normalmente
        sucessos = 0
        falhas = 0
        erros_detalhados = []

        log.info(f"Processando lote de {len(df_ajustes)} funcionários...")

        for idx, row in df_ajustes.iterrows():
            matricula = str(row["Matricula"])
            percentual = row.get("PercentualAdiant")
            valor_fixo = row.get("ValorFixoAdiant")

            try:
                if self.ajustar_parametros_funcionario(
                    matricula,
                    percentual_adiant=percentual if pd.notna(percentual) else None,
                    valor_fixo_adiant=valor_fixo if pd.notna(valor_fixo) else None,
                ):
                    sucessos += 1
                else:
                    falhas += 1
                    erros_detalhados.append(
                        {
                            "matricula": matricula,
                            "erro": "Falha ao atualizar parâmetros",
                        }
                    )
            except Exception as e:
                falhas += 1
                erros_detalhados.append({"matricula": matricula, "erro": str(e)})

        log.info(f"Ajustes aplicados: {sucessos} sucessos, {falhas} falhas")
        return sucessos, falhas, erros_detalhados


def calcular_parametros_correcao(df_calculado: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula os parâmetros corretos para cada funcionário ELEGÍVEL.

    Retorna um DataFrame com os parâmetros que devem ser ajustados na SEP
    para que o Fortes calcule corretamente.
    """
    df_params = []

    # Filtra apenas funcionários elegíveis com valor > 0
    df_elegiveis = df_calculado[
        (df_calculado["Status"] == "Elegível")
        & (df_calculado["ValorAdiantamentoBruto"] > 0)
    ].copy()

    log.info(f"Calculando parâmetros para {len(df_elegiveis)} funcionários elegíveis")

    for idx, row in df_elegiveis.iterrows():
        matricula = row["Matricula"]
        salario = row["SalarioContratual"]
        valor_bruto = row["ValorAdiantamentoBruto"]
        dias_trabalhados = row.get("DiasTrabalhados", 30)

        # Calcula o percentual correto considerando proporcionalidade
        if salario > 0 and dias_trabalhados >= 30:
            # Caso normal - calcula percentual direto
            percentual = (valor_bruto / salario) * 100
            df_params.append(
                {
                    "Matricula": matricula,
                    "PercentualAdiant": round(percentual, 2),
                    "ValorFixoAdiant": None,
                    "Metodo": "PERCENTUAL",
                }
            )
            log.debug(
                f"Matrícula {matricula}: {percentual:.2f}% ({dias_trabalhados} dias)"
            )
        elif salario > 0 and dias_trabalhados < 30:
            # Caso proporcional - usa valor fixo
            df_params.append(
                {
                    "Matricula": matricula,
                    "PercentualAdiant": None,
                    "ValorFixoAdiant": round(valor_bruto, 2),
                    "Metodo": "VALOR_FIXO",
                }
            )
            log.debug(
                f"Matrícula {matricula}: R$ {valor_bruto:.2f} fixo ({dias_trabalhados} dias)"
            )
        else:
            # Fallback - usa valor fixo
            if valor_bruto > 0:
                df_params.append(
                    {
                        "Matricula": matricula,
                        "PercentualAdiant": None,
                        "ValorFixoAdiant": round(valor_bruto, 2),
                        "Metodo": "VALOR_FIXO",
                    }
                )
                log.debug(
                    f"Matrícula {matricula}: R$ {valor_bruto:.2f} fixo (fallback)"
                )

    if not df_params:
        log.warning(
            "⚠️ Nenhum parâmetro calculado - todos os funcionários podem estar inelegíveis"
        )

    return pd.DataFrame(df_params)
