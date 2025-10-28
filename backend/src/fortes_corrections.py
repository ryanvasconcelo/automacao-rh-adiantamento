# src/fortes_corrections.py
"""
Módulo para aplicar correções diretas no banco de dados Fortes.
Permite ajustar valores de adiantamento já calculados na folha.
"""

import pandas as pd
from typing import Dict, List, Optional, Tuple
from .database import get_connection
from config.logging_config import log


class FortesCorrection:
    """Classe para gerenciar correções na folha do Fortes."""
    
    # Códigos de eventos padrão do Fortes
    EVE_ADIANTAMENTO = '001'
    EVE_BASE_CALCULO = '608'
    EVE_CONSIGNADO = '901'  # Ajustar conforme o sistema
    
    def __init__(self, emp_codigo: str, fol_seq: int):
        """
        Inicializa o módulo de correções.
        
        Args:
            emp_codigo: Código da empresa
            fol_seq: Sequencial da folha de pagamento
        """
        self.emp_codigo = str(emp_codigo)
        self.fol_seq = int(fol_seq)
        
    def verificar_folha_aberta(self) -> bool:
        """Verifica se a folha está aberta para edição."""
        query = """
            SELECT ENCERRADA, CALCULANDO 
            FROM FOL 
            WHERE EMP_CODIGO = %s AND SEQ = %s
        """
        with get_connection() as conn:
            df = pd.read_sql(query, conn, params=[self.emp_codigo, self.fol_seq])
            
        if df.empty:
            log.error(f"Folha {self.fol_seq} não encontrada para empresa {self.emp_codigo}")
            return False
            
        if df['ENCERRADA'].iloc[0] == 'S':
            log.error(f"Folha {self.fol_seq} está encerrada")
            return False
            
        if df['CALCULANDO'].iloc[0] == 'S':
            log.warning(f"Folha {self.fol_seq} está em processo de cálculo")
            return False
            
        return True
    
    def buscar_funcionario_na_folha(self, matricula: str) -> Optional[Dict]:
        """
        Busca dados do funcionário na folha atual.
        
        Args:
            matricula: Matrícula do funcionário
            
        Returns:
            Dicionário com dados ou None se não encontrado
        """
        query = """
            SELECT 
                EFO.EPG_CODIGO,
                EFO.SEP_DATA,
                EPG.NOME
            FROM EFO
            INNER JOIN EPG ON EFO.EMP_CODIGO = EPG.EMP_CODIGO 
                AND EFO.EPG_CODIGO = EPG.CODIGO
            WHERE EFO.EMP_CODIGO = %s 
                AND EFO.FOL_SEQ = %s 
                AND EFO.EPG_CODIGO = %s
        """
        with get_connection() as conn:
            df = pd.read_sql(query, conn, params=[self.emp_codigo, self.fol_seq, matricula])
            
        if df.empty:
            return None
            
        return df.iloc[0].to_dict()
    
    def buscar_evento_funcionario(self, matricula: str, eve_codigo: str) -> Optional[Dict]:
        """
        Busca evento específico do funcionário na folha.
        
        Args:
            matricula: Matrícula do funcionário
            eve_codigo: Código do evento
            
        Returns:
            Dicionário com dados do evento ou None
        """
        query = """
            SELECT 
                EFP.EVE_CODIGO,
                EFP.VALOR,
                EFP.REFERENCIA,
                EVE.NOME as EVE_NOME,
                EVE.PROVDESC
            FROM EFP
            INNER JOIN EVE ON EFP.EMP_CODIGO = EVE.EMP_CODIGO 
                AND EFP.EVE_CODIGO = EVE.CODIGO
            WHERE EFP.EMP_CODIGO = %s 
                AND EFP.EFO_FOL_SEQ = %s 
                AND EFP.EFO_EPG_CODIGO = %s 
                AND EFP.EVE_CODIGO = %s
        """
        with get_connection() as conn:
            df = pd.read_sql(
                query, 
                conn, 
                params=[self.emp_codigo, self.fol_seq, matricula, eve_codigo]
            )
            
        if df.empty:
            return None
            
        return df.iloc[0].to_dict()
    
    def atualizar_evento(
        self,
        matricula: str,
        eve_codigo: str,
        novo_valor: float,
        nova_referencia: Optional[float] = None
    ) -> bool:
        """
        ⚠️ ATENÇÃO: Esta função executa UPDATE REAL no banco de dados do Fortes.
        A operação é irreversível sem backup.
        
        Atualiza o valor de um evento existente na tabela EFP.
        
        Args:
            matricula: Matrícula do funcionário
            eve_codigo: Código do evento
            novo_valor: Novo valor do evento
            nova_referencia: Nova referência (opcional)
            
        Returns:
            True se atualizado com sucesso
        """
        # Verifica se o evento existe
        evento = self.buscar_evento_funcionario(matricula, eve_codigo)
        if not evento:
            log.warning(f"Evento {eve_codigo} não encontrado para matrícula {matricula}")
            return False
        
        try:
            query = """
                UPDATE EFP 
                SET VALOR = %s
                    {referencia_clause}
                WHERE EMP_CODIGO = %s 
                    AND EFO_FOL_SEQ = %s 
                    AND EFO_EPG_CODIGO = %s 
                    AND EVE_CODIGO = %s
            """
            
            params = [novo_valor]
            ref_clause = ""
            
            if nova_referencia is not None:
                ref_clause = ", REFERENCIA = %s"
                params.append(nova_referencia)
            
            query = query.format(referencia_clause=ref_clause)
            params.extend([self.emp_codigo, self.fol_seq, matricula, eve_codigo])
            
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
                
            log.success(
                f"Evento {eve_codigo} atualizado para matrícula {matricula}: "
                f"R$ {evento['VALOR']:.2f} → R$ {novo_valor:.2f}"
            )
            return True
            
        except Exception as e:
            log.error(f"Erro ao atualizar evento: {e}")
            return False
    
    def inserir_evento(
        self,
        matricula: str,
        eve_codigo: str,
        valor: float,
        referencia: Optional[float] = None
    ) -> bool:
        """
        ⚠️ ATENÇÃO: Esta função executa INSERT REAL no banco de dados do Fortes.
        A operação é irreversível sem backup.
        
        Insere um novo evento para o funcionário na tabela EFP.
        
        Args:
            matricula: Matrícula do funcionário
            eve_codigo: Código do evento
            valor: Valor do evento
            referencia: Referência do evento (opcional)
            
        Returns:
            True se inserido com sucesso
        """
        # Verifica se o funcionário está na folha
        func = self.buscar_funcionario_na_folha(matricula)
        if not func:
            log.error(f"Funcionário {matricula} não encontrado na folha {self.fol_seq}")
            return False
        
        # Verifica se o evento já existe
        if self.buscar_evento_funcionario(matricula, eve_codigo):
            log.warning(f"Evento {eve_codigo} já existe para matrícula {matricula}")
            return self.atualizar_evento(matricula, eve_codigo, valor, referencia)
        
        try:
            query = """
                INSERT INTO EFP (
                    EMP_CODIGO, EFO_FOL_SEQ, EFO_EPG_CODIGO, EVE_CODIGO, 
                    VALOR, REFERENCIA
                )
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            
            params = [
                self.emp_codigo,
                self.fol_seq,
                matricula,
                eve_codigo,
                valor,
                referencia or 0.0
            ]
            
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
                
            log.success(
                f"Evento {eve_codigo} inserido para matrícula {matricula}: R$ {valor:.2f}"
            )
            return True
            
        except Exception as e:
            log.error(f"Erro ao inserir evento: {e}")
            return False
    
    def aplicar_correcoes_lote(
        self,
        df_correcoes: pd.DataFrame
    ) -> Tuple[int, int, List[str]]:
        """
        ⚠️ ATENÇÃO: Esta função executa operações REAIS no banco de dados do Fortes.
        Executa UPDATE e INSERT nas tabelas EFP (eventos da folha).
        As operações são irreversíveis sem backup do banco.
        
        Aplica correções em lote a partir de um DataFrame.
        
        O DataFrame deve conter as colunas:
        - Matricula: matrícula do funcionário
        - ValorAdiantamentoBruto: novo valor do adiantamento
        - ValorDesconto: novo valor do desconto (opcional)
        
        Args:
            df_correcoes: DataFrame com as correções
            
        Returns:
            Tupla (sucesso, falhas, erros)
        """
        if not self.verificar_folha_aberta():
            return 0, 0, ["Folha não está aberta para edição"]
        
        sucessos = 0
        falhas = 0
        erros = []
        
        for idx, row in df_correcoes.iterrows():
            matricula = str(row['Matricula'])
            
            try:
                # Atualiza o valor do adiantamento
                if 'ValorAdiantamentoBruto' in row:
                    valor_adiant = float(row['ValorAdiantamentoBruto'])
                    if self.atualizar_evento(matricula, self.EVE_ADIANTAMENTO, valor_adiant):
                        sucessos += 1
                    else:
                        falhas += 1
                        erros.append(f"Matrícula {matricula}: falha ao atualizar adiantamento")
                
                # Atualiza o desconto se fornecido
                if 'ValorDesconto' in row and pd.notna(row['ValorDesconto']):
                    valor_desconto = float(row['ValorDesconto'])
                    if valor_desconto > 0:
                        # Tenta atualizar ou inserir o evento de desconto
                        if not self.atualizar_evento(matricula, self.EVE_CONSIGNADO, valor_desconto):
                            self.inserir_evento(matricula, self.EVE_CONSIGNADO, valor_desconto)
                            
            except Exception as e:
                falhas += 1
                erros.append(f"Matrícula {matricula}: {str(e)}")
        
        log.info(f"Correções aplicadas: {sucessos} sucessos, {falhas} falhas")
        return sucessos, falhas, erros
    
    def gerar_relatorio_diferencas(
        self, 
        df_calculado: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Compara valores calculados com valores no Fortes e gera relatório.
        
        Args:
            df_calculado: DataFrame com valores calculados pelo sistema
            
        Returns:
            DataFrame com as diferenças encontradas
        """
        diferencas = []
        
        for idx, row in df_calculado.iterrows():
            matricula = str(row['Matricula'])
            valor_calculado = float(row.get('ValorAdiantamentoBruto', 0))
            
            # Busca o valor atual no Fortes
            evento = self.buscar_evento_funcionario(matricula, self.EVE_ADIANTAMENTO)
            
            if not evento:
                diferencas.append({
                    'Matricula': matricula,
                    'Nome': row.get('Nome', ''),
                    'ValorFortes': 0.0,
                    'ValorCalculado': valor_calculado,
                    'Diferenca': valor_calculado,
                    'Status': 'NÃO ENCONTRADO NO FORTES'
                })
                continue
            
            valor_fortes = float(evento['VALOR'])
            diferenca = valor_calculado - valor_fortes
            
            if abs(diferenca) > 0.01:  # Considera diferenças > 1 centavo
                diferencas.append({
                    'Matricula': matricula,
                    'Nome': row.get('Nome', ''),
                    'ValorFortes': valor_fortes,
                    'ValorCalculado': valor_calculado,
                    'Diferenca': diferenca,
                    'Status': 'DIVERGÊNCIA'
                })
        
        return pd.DataFrame(diferencas)


def aplicar_correcoes_fortes(
    emp_codigo: str,
    fol_seq: int,
    df_correcoes: pd.DataFrame,
    apenas_comparar: bool = True
) -> Dict:
    """
    ⚠️ ATENÇÃO: Esta função executa operações REAIS no banco de dados do Fortes.
    
    Aplica correções diretas nas tabelas EFP e EFO do banco Fortes.
    As operações são permanentes e irreversíveis sem backup.
    
    Args:
        emp_codigo: Código da empresa
        fol_seq: Sequencial da folha
        df_correcoes: DataFrame com correções
        apenas_comparar: Se True, apenas gera relatório de diferenças (padrão: True)
                        Se False, APLICA AS CORREÇÕES REAIS no banco
        
    Returns:
        Dicionário com resultado da operação
    """
    corrector = FortesCorrection(emp_codigo, fol_seq)
    
    # Verifica se a folha está aberta
    if not corrector.verificar_folha_aberta():
        return {
            'sucesso': False,
            'mensagem': 'Folha não está disponível para correção',
            'correcoes_aplicadas': 0,
            'falhas': 0
        }
    
    # Gera relatório de diferenças
    df_diferencas = corrector.gerar_relatorio_diferencas(df_correcoes)
    
    if df_diferencas.empty:
        return {
            'sucesso': True,
            'mensagem': 'Nenhuma diferença encontrada',
            'correcoes_aplicadas': 0,
            'falhas': 0,
            'diferencas': df_diferencas
        }
    
    log.info(f"Encontradas {len(df_diferencas)} diferenças")
    
    # Se apenas comparar, retorna as diferenças sem aplicar
    if apenas_comparar:
        return {
            'sucesso': True,
            'mensagem': 'Comparação realizada - correções NÃO aplicadas no banco',
            'correcoes_aplicadas': 0,
            'falhas': 0,
            'diferencas': df_diferencas
        }
    
    # ⚠️ EXECUTA AS CORREÇÕES REAIS NO BANCO DE DADOS FORTES
    log.warning("=" * 80)
    log.warning("APLICANDO CORREÇÕES REAIS NO BANCO DE DADOS DO FORTES")
    log.warning("Tabelas afetadas: EFP (eventos da folha)")
    log.warning("Operações: UPDATE e INSERT diretos no SQL Server")
    log.warning("=" * 80)
    sucessos, falhas, erros = corrector.aplicar_correcoes_lote(df_correcoes)
    
    return {
        'sucesso': sucessos > 0,
        'mensagem': f'{sucessos} correções aplicadas, {falhas} falhas',
        'correcoes_aplicadas': sucessos,
        'falhas': falhas,
        'erros': erros,
        'diferencas': df_diferencas
    }