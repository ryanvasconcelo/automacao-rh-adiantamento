# src/fortes_auto_recalc.py
"""
Módulo para recalcular folha no Fortes automaticamente.
Usa credenciais de usuário do Fortes para autenticar e recalcular.
"""

import pyodbc
from typing import Optional, Dict
from .database import get_connection
from config.logging_config import log


class FortesAutoRecalc:
    """Recalcula folha no Fortes automaticamente com autenticação."""
    
    def __init__(self, emp_codigo: str, fortes_user: str, fortes_password_hash: int):
        """
        Inicializa com credenciais do Fortes.
        
        Args:
            emp_codigo: Código da empresa
            fortes_user: Usuário do Fortes Pessoal
            fortes_password_hash: Hash numérico da senha do usuário
        """
        self.emp_codigo = str(emp_codigo)
        self.fortes_user = fortes_user
        self.fortes_password_hash = fortes_password_hash
    
    def validar_credenciais(self) -> bool:
        """
        Valida as credenciais do usuário no Fortes.
        
        NOTA: A senha no Fortes é armazenada como hash numérico na coluna Senha.
        Por segurança, vamos apenas verificar se o usuário existe e está ativo.
        
        Returns:
            True se as credenciais são válidas
        """
        try:
            query = """
                SELECT Codigo, NOME, Senha, Bloqueado
                FROM USU
                WHERE Codigo = %s
                    AND Bloqueado = 0
            """
            
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, [self.fortes_user])
                result = cursor.fetchone()
                
            if result:
                codigo, nome, senha_hash, bloqueado = result
                
                # Validar o hash da senha
                if senha_hash != self.fortes_password_hash:
                    log.error(
                        f"❌ Hash de senha incorreto para usuário {self.fortes_user}. "
                        f"Esperado: {self.fortes_password_hash}, Encontrado: {senha_hash}"
                    )
                    return False
                
                log.success(f"✅ Usuário autenticado: {codigo} ({nome or 'Sem nome'})")
                return True
            else:
                log.error(f"❌ Usuário {self.fortes_user} não encontrado ou bloqueado")
                return False
                
        except Exception as e:
            log.error(f"Erro ao validar credenciais: {e}")
            return False
    
    def recalcular_folha(self, fol_seq: int, tipo_folha: int = 1) -> Dict:
        """
        Recalcula a folha de adiantamento no Fortes.
        
        ATENÇÃO: Esta função executa o recálculo da folha.
        Os valores na tabela EFP serão recalculados baseados nos parâmetros da SEP.
        
        Args:
            fol_seq: Sequencial da folha
            tipo_folha: Tipo da folha (1 = Adiantamento, 2 = Mensal, etc.)
        
        Returns:
            Dicionário com resultado da operação
        """
        if not self.validar_credenciais():
            return {
                'sucesso': False,
                'mensagem': 'Credenciais inválidas'
            }
        
        try:
            # Marca a folha como "A Calcular"
            query_marcar = """
                UPDATE FOL 
                SET ACALCULAR = 'S',
                    CALCULANDO = 'N',
                    ENCERRADA = 'N'
                WHERE EMP_CODIGO = %s 
                    AND SEQ = %s
                    AND FOLHA = %s
            """
            
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query_marcar, [self.emp_codigo, fol_seq, tipo_folha])
                conn.commit()
            
            log.info(f"Folha {fol_seq} marcada para recálculo")
            
            # NOTA: O recálculo real é feito por stored procedures do Fortes
            # Vamos chamar a procedure de cálculo se existir
            try:
                with get_connection() as conn:
                    cursor = conn.cursor()
                    
                    # Tenta chamar a procedure de cálculo do Fortes
                    # O nome pode variar dependendo da versão
                    cursor.execute(
                        "EXEC sp_CalcularFolha @EmpCodigo = ?, @FolSeq = ?, @Tipo = ?",
                        [self.emp_codigo, fol_seq, tipo_folha]
                    )
                    conn.commit()
                    
                    log.success(f"✅ Folha {fol_seq} recalculada automaticamente")
                    
                    return {
                        'sucesso': True,
                        'mensagem': f'Folha {fol_seq} recalculada com sucesso'
                    }
                    
            except Exception as proc_error:
                # Se a procedure não existir, marca para recálculo manual
                log.warning(f"Procedure de cálculo não encontrada: {proc_error}")
                log.info("Folha marcada para recálculo manual no Fortes")
                
                return {
                    'sucesso': True,
                    'mensagem': (
                        f'Folha {fol_seq} marcada para recálculo. '
                        'Abra o Fortes e confirme o cálculo.'
                    ),
                    'requer_acao_manual': True
                }
                
        except Exception as e:
            log.error(f"Erro ao recalcular folha: {e}")
            return {
                'sucesso': False,
                'mensagem': f'Erro ao recalcular: {str(e)}'
            }


def recalcular_folha_automatico(
    emp_codigo: str,
    fol_seq: int,
    fortes_user: str,
    fortes_password_hash: int
) -> Dict:
    """
    Função de conveniência para recalcular folha.
    
    Args:
        emp_codigo: Código da empresa
        fol_seq: Sequencial da folha
        fortes_user: Usuário do Fortes
        fortes_password_hash: Hash numérico da senha do Fortes
        
    Returns:
        Resultado da operação
    """
    recalc = FortesAutoRecalc(emp_codigo, fortes_user, fortes_password_hash)
    return recalc.recalcular_folha(fol_seq)