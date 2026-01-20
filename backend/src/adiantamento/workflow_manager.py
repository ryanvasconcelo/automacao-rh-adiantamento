# src/workflow_manager.py
"""
Módulo de orquestração do fluxo de trabalho de adiantamento.
Gerencia o processo completo: cálculo -> comparação -> correção -> relatórios.
"""

import pandas as pd
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass
from enum import Enum

from .business_logic import processar_regras, aplicar_descontos_consignado
from .data_extraction import (
    fetch_employee_base_data,
    fetch_employee_leaves,
    fetch_employee_loans,
    get_latest_fol_seq,
)
from .fortes_integration.fortes_corrections import FortesCorrection
from .fortes_integration.fortes_pre_calculation import (
    FortesPreCalculation,
    calcular_parametros_correcao,
)
from .fortes_integration.fortes_auto_recalc import FortesAutoRecalc
from .report_generator import (
    gerar_relatorio_adiantamento_fortes,
    calcular_totais_dashboard,
)
from ..rules_catalog import get_company_rule
from config.logging_config import log


class WorkflowStatus(Enum):
    """Status do fluxo de trabalho."""

    INICIAL = "inicial"
    CALCULADO = "calculado"
    DIVERGENCIAS_ENCONTRADAS = "divergencias_encontradas"
    AGUARDANDO_CONFIRMACAO = "aguardando_confirmacao"
    CORRECOES_APLICADAS = "correcoes_aplicadas"
    RELATORIOS_GERADOS = "relatorios_gerados"
    ERRO = "erro"


@dataclass
class WorkflowResult:
    """Resultado do fluxo de trabalho."""

    status: WorkflowStatus
    mensagem: str
    df_calculado: Optional[pd.DataFrame] = None
    df_divergencias: Optional[pd.DataFrame] = None
    totais: Optional[Dict] = None
    correcoes_aplicadas: int = 0
    falhas_correcao: int = 0
    erros_correcao: List[str] = None
    caminho_pdf: Optional[str] = None
    caminho_csv: Optional[str] = None
    fol_seq: Optional[int] = None


class AdiantamentoWorkflow:
    """Gerencia o fluxo completo de processamento de adiantamento."""

    def __init__(self, empresa_codigo: str, ano: int, mes: int):
        """
        Inicializa o workflow.

        Args:
            empresa_codigo: Código do catálogo (ex: "PHY", "CMD")
            ano: Ano de referência
            mes: Mês de referência
        """
        self.catalog_code = str(empresa_codigo)
        self.rule = get_company_rule(empresa_codigo)

        # Busca o ID numérico da empresa para queries SQL
        if not self.rule.emp_id:
            raise ValueError(f"Empresa {empresa_codigo} não possui emp_id configurado")

        self.empresa_codigo = str(self.rule.emp_id)  # ID numérico para SQL
        self.ano = ano
        self.mes = mes
        self.df_calculado = None
        self.fol_seq = None

    def executar_calculo(self) -> WorkflowResult:
        """
        Executa o cálculo de adiantamento baseado nas regras.

        Returns:
            WorkflowResult com os dados calculados
        """
        try:
            log.info(
                f"Iniciando cálculo para {self.rule.name} - {self.mes:02d}/{self.ano}"
            )

            # 1. Busca dados base dos funcionários
            df_base = fetch_employee_base_data(self.empresa_codigo, self.ano, self.mes)

            if df_base.empty:
                return WorkflowResult(
                    status=WorkflowStatus.ERRO,
                    mensagem="Nenhum funcionário encontrado para o período",
                )

            log.info(f"Encontrados {len(df_base)} funcionários")

            # 2. Busca afastamentos
            employee_ids = df_base["Matricula"].tolist()
            df_licencas = fetch_employee_leaves(
                self.empresa_codigo, employee_ids, self.ano, self.mes
            )

            # 3. Busca empréstimos consignados
            df_consignados = fetch_employee_loans(
                self.empresa_codigo, employee_ids, self.ano, self.mes
            )

            # 4. Merge dos dados
            if not df_licencas.empty:
                df_base = pd.merge(df_base, df_licencas, on="Matricula", how="left")

            if not df_consignados.empty:
                df_base = pd.merge(df_base, df_consignados, on="Matricula", how="left")

            # 5. Processa regras de negócio
            df_processado = processar_regras(df_base, self.rule, self.ano, self.mes)

            # 6. Aplica descontos de consignado
            self.df_calculado = aplicar_descontos_consignado(df_processado, self.rule)

            # 7. Calcula totais
            totais = calcular_totais_dashboard(self.df_calculado)

            log.success(
                f"Cálculo concluído: {totais['total_funcionarios']} funcionários elegíveis, "
                f"R$ {totais['total_liquido']:,.2f}"
            )

            return WorkflowResult(
                status=WorkflowStatus.CALCULADO,
                mensagem="Cálculo realizado com sucesso",
                df_calculado=self.df_calculado,
                totais=totais,
            )

        except Exception as e:
            log.error(f"Erro no cálculo: {e}")
            return WorkflowResult(
                status=WorkflowStatus.ERRO, mensagem=f"Erro no cálculo: {str(e)}"
            )

    def comparar_com_fortes(self) -> WorkflowResult:
        """
        Compara valores calculados com valores no Fortes.

        Returns:
            WorkflowResult com as divergências encontradas
        """
        try:
            if self.df_calculado is None:
                return WorkflowResult(
                    status=WorkflowStatus.ERRO,
                    mensagem="Nenhum cálculo disponível. Execute executar_calculo() primeiro.",
                )

            # Busca o SEQ da folha no Fortes
            self.fol_seq = get_latest_fol_seq(self.empresa_codigo, self.ano, self.mes)

            if not self.fol_seq:
                return WorkflowResult(
                    status=WorkflowStatus.ERRO,
                    mensagem=f"Folha não encontrada no Fortes para {self.mes:02d}/{self.ano}",
                )

            log.info(f"Folha encontrada: SEQ {self.fol_seq}")

            # Cria o corretor
            corrector = FortesCorrection(self.empresa_codigo, self.fol_seq)

            # Verifica se a folha está aberta
            if not corrector.verificar_folha_aberta():
                return WorkflowResult(
                    status=WorkflowStatus.ERRO,
                    mensagem="A folha está encerrada ou em processamento no Fortes",
                    fol_seq=self.fol_seq,
                )

            # Gera relatório de diferenças
            df_divergencias = corrector.gerar_relatorio_diferencas(self.df_calculado)

            if df_divergencias.empty:
                log.info("Nenhuma divergência encontrada")
                return WorkflowResult(
                    status=WorkflowStatus.CALCULADO,
                    mensagem="Valores do Fortes estão corretos. Nenhuma correção necessária.",
                    df_calculado=self.df_calculado,
                    df_divergencias=df_divergencias,
                    totais=calcular_totais_dashboard(self.df_calculado),
                    fol_seq=self.fol_seq,
                )

            log.warning(f"Encontradas {len(df_divergencias)} divergências")

            return WorkflowResult(
                status=WorkflowStatus.DIVERGENCIAS_ENCONTRADAS,
                mensagem=f"Encontradas {len(df_divergencias)} divergências entre o calculado e o Fortes",
                df_calculado=self.df_calculado,
                df_divergencias=df_divergencias,
                totais=calcular_totais_dashboard(self.df_calculado),
                fol_seq=self.fol_seq,
            )

        except Exception as e:
            log.error(f"Erro na comparação: {e}")
            return WorkflowResult(
                status=WorkflowStatus.ERRO, mensagem=f"Erro na comparação: {str(e)}"
            )

    def aplicar_correcoes_fortes(
        self,
        confirmado: bool = False,
        fortes_user: Optional[str] = None,
        fortes_password_hash: Optional[int] = None,
        auto_recalc: bool = False,
    ) -> WorkflowResult:
        """
        ⚠️ APLICA CORREÇÕES REAIS NA TABELA SEP DO FORTES ⚠️

        Esta função ajusta os PARÂMETROS DE CÁLCULO na tabela SEP:
        - PercentualAdiant: Percentual de adiantamento
        - ValorAdiant: Valor fixo de adiantamento

        APÓS executar esta função, você DEVE:
        1. Ir no Fortes Pessoal
        2. RECALCULAR a folha de adiantamento
        3. Os valores serão calculados corretamente baseados nos novos parâmetros

        Args:
            confirmado: OBRIGATÓRIO ser True para executar
            fortes_user: Usuário do Fortes (opcional, para recálculo automático)
            fortes_password_hash: Hash numérico da senha do Fortes (opcional, para recálculo automático)
            auto_recalc: Se True, recalcula automaticamente após ajustar parâmetros

        Returns:
            WorkflowResult com o resultado
        """
        try:
            if self.df_calculado is None or self.fol_seq is None:
                return WorkflowResult(
                    status=WorkflowStatus.ERRO,
                    mensagem="Execute comparar_com_fortes() primeiro",
                )

            if not confirmado:
                return WorkflowResult(
                    status=WorkflowStatus.AGUARDANDO_CONFIRMACAO,
                    mensagem="⚠️ CONFIRMAÇÃO NECESSÁRIA: As correções serão aplicadas DIRETAMENTE no banco Fortes",
                    df_calculado=self.df_calculado,
                    totais=calcular_totais_dashboard(self.df_calculado),
                    fol_seq=self.fol_seq,
                )

            log.warning("=" * 80)
            log.warning("⚠️ AJUSTANDO PARÂMETROS NA TABELA SEP DO FORTES ⚠️")
            log.warning("Operações SQL: UPDATE na tabela SEP (cadastro do funcionário)")
            log.warning("Tabela afetada: SEP.PERCENTUALADIANT e SEP.VALORADIANT")
            log.warning(
                "APÓS estas alterações, você DEVE RECALCULAR a folha no Fortes!"
            )
            log.warning("=" * 80)

            # Calcula os parâmetros corretos
            try:
                df_parametros = calcular_parametros_correcao(self.df_calculado)
                log.info(f"Parâmetros calculados: {len(df_parametros)} registros")
            except Exception as e:
                log.error(f"Erro ao calcular parâmetros: {e}")
                import traceback

                traceback.print_exc()
                raise

            # Verifica se há parâmetros para ajustar
            if df_parametros.empty:
                return WorkflowResult(
                    status=WorkflowStatus.ERRO,
                    mensagem="Nenhum parâmetro para ajustar - todos os funcionários podem estar inelegíveis",
                    correcoes_aplicadas=0,
                    falhas_correcao=0,
                    erros_correcao=[],
                )

            # Aplica os ajustes na tabela SEP
            try:
                pre_calc = FortesPreCalculation(self.empresa_codigo)
                sucessos, falhas, erros = pre_calc.ajustar_lote(df_parametros)
                log.info(f"Resultado do lote: {sucessos} sucessos, {falhas} falhas")
            except Exception as e:
                log.error(f"Erro ao ajustar lote: {e}")
                import traceback

                traceback.print_exc()
                raise

            # Garante que erros é uma lista
            if not isinstance(erros, list):
                log.warning(f"erros não é uma lista: {type(erros)}")
                erros = []

            resultado = {
                "sucesso": sucessos > 0,
                "mensagem": f"{sucessos} parâmetros ajustados na SEP. RECALCULE a folha no Fortes!",
                "correcoes_aplicadas": sucessos,
                "falhas": falhas,
                "erros": erros,
            }

            if not resultado["sucesso"]:
                return WorkflowResult(
                    status=WorkflowStatus.ERRO,
                    mensagem=resultado["mensagem"],
                    correcoes_aplicadas=resultado["correcoes_aplicadas"],
                    falhas_correcao=resultado["falhas"],
                    erros_correcao=resultado.get("erros", []),
                )

            status = WorkflowStatus.CORRECOES_APLICADAS

            log.success(
                f"✅ PARÂMETROS AJUSTADOS NA TABELA SEP: "
                f"{resultado['correcoes_aplicadas']} sucessos, {resultado['falhas']} falhas"
            )

            # Se tem credenciais e auto_recalc, recalcula automaticamente
            if auto_recalc and fortes_user and fortes_password_hash:
                log.info("🔄 Recalculando folha automaticamente...")

                recalc = FortesAutoRecalc(
                    self.empresa_codigo, fortes_user, fortes_password_hash
                )
                result_recalc = recalc.recalcular_folha(self.fol_seq)

                if result_recalc["sucesso"]:
                    if result_recalc.get("requer_acao_manual"):
                        log.warning(result_recalc["mensagem"])
                    else:
                        log.success("✅ Folha recalculada automaticamente!")
                else:
                    log.error(f"Erro no recálculo: {result_recalc['mensagem']}")
                    log.warning(
                        "⚠️ AÇÃO NECESSÁRIA: Recalcule a folha manualmente no Fortes!"
                    )
            else:
                log.warning("⚠️ AÇÃO NECESSÁRIA: Recalcule a folha no Fortes Pessoal!")

            return WorkflowResult(
                status=status,
                mensagem=resultado["mensagem"],
                df_calculado=self.df_calculado,
                df_divergencias=resultado.get("diferencas"),
                totais=calcular_totais_dashboard(self.df_calculado),
                correcoes_aplicadas=resultado["correcoes_aplicadas"],
                falhas_correcao=resultado["falhas"],
                erros_correcao=resultado.get("erros", []),
                fol_seq=self.fol_seq,
            )

        except Exception as e:
            log.error(f"Erro ao aplicar correções: {e}")
            return WorkflowResult(
                status=WorkflowStatus.ERRO,
                mensagem=f"Erro ao aplicar correções: {str(e)}",
            )

    def gerar_relatorios(
        self, empresa_nome: Optional[str] = None, empresa_cnpj: Optional[str] = None
    ) -> WorkflowResult:
        """
        Gera os relatórios PDF e CSV.

        Args:
            empresa_nome: Nome da empresa (opcional)
            empresa_cnpj: CNPJ da empresa (opcional)

        Returns:
            WorkflowResult com os caminhos dos arquivos gerados
        """
        try:
            if self.df_calculado is None:
                return WorkflowResult(
                    status=WorkflowStatus.ERRO,
                    mensagem="Nenhum cálculo disponível. Execute executar_calculo() primeiro.",
                )

            log.info("Gerando relatórios...")

            # Usa valores padrão se não fornecidos
            if not empresa_nome:
                empresa_nome = self.rule.name
            if not empresa_cnpj:
                empresa_cnpj = "00.000.000/0000-00"  # Placeholder

            # Gera os relatórios
            caminho_pdf, caminho_csv = gerar_relatorio_adiantamento_fortes(
                self.df_calculado, empresa_nome, empresa_cnpj, self.ano, self.mes
            )

            if not caminho_pdf and not caminho_csv:
                return WorkflowResult(
                    status=WorkflowStatus.ERRO, mensagem="Falha ao gerar relatórios"
                )

            log.success("Relatórios gerados com sucesso")

            return WorkflowResult(
                status=WorkflowStatus.RELATORIOS_GERADOS,
                mensagem="Relatórios gerados com sucesso",
                df_calculado=self.df_calculado,
                totais=calcular_totais_dashboard(self.df_calculado),
                caminho_pdf=caminho_pdf,
                caminho_csv=caminho_csv,
                fol_seq=self.fol_seq,
            )

        except Exception as e:
            log.error(f"Erro ao gerar relatórios: {e}")
            return WorkflowResult(
                status=WorkflowStatus.ERRO,
                mensagem=f"Erro ao gerar relatórios: {str(e)}",
            )

    def executar_fluxo_completo(
        self,
        aplicar_correcoes: bool = True,
        confirmado: bool = False,
        empresa_nome: Optional[str] = None,
        empresa_cnpj: Optional[str] = None,
        fortes_user: Optional[str] = None,
        fortes_password_hash: Optional[int] = None,
        auto_recalc: bool = False,
    ) -> WorkflowResult:
        """
        Executa o fluxo completo de trabalho.

        Args:
            aplicar_correcoes: Se True, tenta aplicar correções no Fortes
            confirmado: Se True, aplica correções sem pedir confirmação
            empresa_nome: Nome da empresa para o relatório
            empresa_cnpj: CNPJ da empresa para o relatório
            fortes_user: Usuário do Fortes (para recálculo automático)
            fortes_password_hash: Hash numérico da senha do Fortes (para recálculo automático)
            auto_recalc: Se True, recalcula automaticamente após correções

        Returns:
            WorkflowResult final
        """
        # 1. Executa o cálculo
        result = self.executar_calculo()
        if result.status == WorkflowStatus.ERRO:
            return result

        # 2. Se não deve aplicar correções, gera relatórios direto
        if not aplicar_correcoes:
            log.info("Gerando relatórios SEM aplicar correções no Fortes")
            return self.gerar_relatorios(empresa_nome, empresa_cnpj)

        # 3. Compara com Fortes
        result = self.comparar_com_fortes()
        if result.status == WorkflowStatus.ERRO:
            return result

        # 4. Se não há divergências, gera relatórios
        if result.status == WorkflowStatus.CALCULADO:
            return self.gerar_relatorios(empresa_nome, empresa_cnpj)

        # 5. Aplica correções REAIS no banco Fortes (com recálculo opcional)
        result = self.aplicar_correcoes_fortes(
            confirmado=confirmado,
            fortes_user=fortes_user,
            fortes_password_hash=fortes_password_hash,
            auto_recalc=auto_recalc,
        )
        if result.status in [
            WorkflowStatus.AGUARDANDO_CONFIRMACAO,
            WorkflowStatus.ERRO,
        ]:
            return result

        # 6. ✅ APÓS APLICAR CORREÇÕES, GERA RELATÓRIOS AUTOMATICAMENTE
        log.info("Correções aplicadas com sucesso - gerando relatórios finais...")
        result_relatorios = self.gerar_relatorios(empresa_nome, empresa_cnpj)

        # Combina informações das correções com os relatórios
        return WorkflowResult(
            status=WorkflowStatus.RELATORIOS_GERADOS,
            mensagem=f"✅ Processo completo: {result.correcoes_aplicadas} correções aplicadas no banco Fortes + relatórios gerados",
            df_calculado=result_relatorios.df_calculado,
            totais=result_relatorios.totais,
            correcoes_aplicadas=result.correcoes_aplicadas,
            falhas_correcao=result.falhas_correcao,
            erros_correcao=result.erros_correcao,
            caminho_pdf=result_relatorios.caminho_pdf,
            caminho_csv=result_relatorios.caminho_csv,
            fol_seq=result.fol_seq,
        )


# Funções de conveniência para uso simples


def processar_adiantamento_simples(
    empresa_codigo: str,
    ano: int,
    mes: int,
    empresa_nome: Optional[str] = None,
    empresa_cnpj: Optional[str] = None,
) -> WorkflowResult:
    """
    Processa adiantamento SEM aplicar correções no Fortes.
    Apenas calcula e gera relatórios.

    Args:
        empresa_codigo: Código da empresa
        ano: Ano de referência
        mes: Mês de referência
        empresa_nome: Nome da empresa
        empresa_cnpj: CNPJ da empresa

    Returns:
        WorkflowResult com os relatórios gerados
    """
    workflow = AdiantamentoWorkflow(empresa_codigo, ano, mes)
    return workflow.executar_fluxo_completo(
        aplicar_correcoes=False, empresa_nome=empresa_nome, empresa_cnpj=empresa_cnpj
    )


def processar_adiantamento_com_correcoes(
    empresa_codigo: str,
    ano: int,
    mes: int,
    confirmado: bool = False,
    empresa_nome: Optional[str] = None,
    empresa_cnpj: Optional[str] = None,
) -> WorkflowResult:
    """
    ⚠️ Processa adiantamento COM CORREÇÕES REAIS no banco Fortes.

    ATENÇÃO: Esta função aplica alterações PERMANENTES no banco de dados.

    Args:
        empresa_codigo: Código da empresa
        ano: Ano de referência
        mes: Mês de referência
        confirmado: Se True, aplica correções sem pedir confirmação
        empresa_nome: Nome da empresa
        empresa_cnpj: CNPJ da empresa

    Returns:
        WorkflowResult com status do processo
    """
    workflow = AdiantamentoWorkflow(empresa_codigo, ano, mes)
    return workflow.executar_fluxo_completo(
        aplicar_correcoes=True,
        confirmado=confirmado,
        empresa_nome=empresa_nome,
        empresa_cnpj=empresa_cnpj,
    )
