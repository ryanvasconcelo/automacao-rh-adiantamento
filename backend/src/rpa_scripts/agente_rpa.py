# agente_rpa.py (Versão 1.4 - Lógica Condicional e Foco Corrigido)
# O "Operário" - Fase 4

import time
import rpa_core  # Nosso Músculo (Fase 2)
import queue_db  # Nossa conexão com a Ponte (Fase 3)
import traceback
import pyodbc
from pywinauto.application import Application

# --- CONFIGURAÇÃO DO AGENTE ---
USER = "RYAN"
PASS = "1234"
AGENT_ID = "WINDOWS_VM_01"
# ------------------------------


def processar_fila():
    """
    O loop principal do agente. Busca e processa um job.
    Retorna True se processou um job, False se a fila estava vazia.
    """
    conn = None
    job_id = None

    try:
        conn = queue_db.get_queue_connection()
        cursor = conn.cursor()

        # 1. PEGAR JOB: Busca o job PENDENTE mais antigo
        sql_pegar_job = """
            UPDATE TOP (1) TB_RPA_JOBS
            SET status = 'EM_PROCESSAMENTO', updated_at = GETDATE()
            OUTPUT inserted.id, inserted.empresa_codigo, inserted.competencia
            WHERE status = 'PENDENTE'
        """
        cursor.execute(sql_pegar_job)

        row = cursor.fetchone()  # (id, empresa_codigo, competencia)

        job = None
        if row:
            job = {"id": row[0], "empresa_codigo": row[1], "competencia": row[2]}
            job_id = job["id"]

        if not job:
            return False  # Fila vazia

        print("\n--- NOVO JOB RECEBIDO ---")
        print(
            f"ID: {job['id']}, Empresa: {job['empresa_codigo']}, Comp: {job['competencia']}"
        )

        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        # !!!           INÍCIO DA MUDANÇA (v1.4 - Condicional)       !!!
        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

        # 2. VERIFICAR SE HÁ MAIS JOBS (Sua lógica condicional)
        sql_check_next = "SELECT COUNT(*) FROM TB_RPA_JOBS WHERE status = 'PENDENTE'"
        cursor.execute(sql_check_next)
        has_next_job = cursor.fetchone()[0] > 0
        print(f"Jobs pendentes restantes: {has_next_job}")

        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        # !!!             FIM DA MUDANÇA (v1.4 - Condicional)        !!!
        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

        # 3. EXECUTAR JOB (Chamando o rpa_core)
        run_rpa_workflow(job, has_next_job)  # Passa a flag condicional

        # 4. MARCAR COMO CONCLUÍDO
        sql_concluir = "UPDATE TB_RPA_JOBS SET status = 'CONCLUIDO', updated_at = GETDATE() WHERE id = ?"
        cursor.execute(sql_concluir, (job["id"],))
        print(f"✓ SUCESSO: Job {job['id']} marcado como CONCLUÍDO.")

    except Exception as e:
        # 5. MARCAR COMO ERRO
        print(f"!!! ERRO CRÍTICO no job {job_id if job_id else 'INDEFINIDO'}: {e}")

        if conn and job_id:
            try:
                sql_erro = "UPDATE TB_RPA_JOBS SET status = 'ERRO', error_message = ? WHERE id = ? AND status != 'ERRO'"
                cursor.execute(sql_erro, (traceback.format_exc(), job_id))
                print(f"✗ ERRO: Job {job_id} marcado como ERRO no banco.")
            except Exception as db_e:
                print(
                    f"!!! ERRO CRÍTICO NO BANCO (não foi possível marcar o job como erro): {db_e}"
                )

        return True

    finally:
        if conn:
            conn.close()

    return True


# --- GERENCIAMENTO DE SESSÃO (A "Inteligência" do Agente) ---
app_session: Application | None = None
current_company_session: str | None = None

# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# !!!           INÍCIO DA MUDANÇA (v1.4 - Foco/Condicional)    !!!
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!


def run_rpa_workflow(job_dict, has_next_job: bool):  # Recebe o dicionário E a flag
    """
    Orquestra o rpa_core mantendo a sessão aberta.
    (v1.4) Limpa popups CADA VEZ e implementa lógica condicional de saída.
    """
    global app_session, current_company_session

    job_id = job_dict["id"]
    empresa_codigo = job_dict["empresa_codigo"]
    competencia = job_dict["competencia"]

    try:
        # --- PASSO 1: O Fortes está aberto? ---
        if app_session is None or not app_session.is_process_running():
            print("Sessão do Fortes não existe. Iniciando nova...")
            # Funções 1
            app_session, main_win = rpa_core.iniciar_sessao_fortes(
                USER, PASS, empresa_codigo
            )
            if app_session is None:
                raise Exception("Falha ao iniciar sessão (Função 1).")

            # Função 2 (Limpeza Inicial)
            if not rpa_core.limpar_popups_iniciais(app_session, main_win):
                raise Exception("Falha ao limpar popups (Função 2).")

            current_company_session = empresa_codigo
            print(f"Sessão iniciada e logada na empresa {current_company_session}.")

        # --- CORREÇÃO DE FOCO (v1.4) ---
        # (Resolve o bug do 'timed out')
        # Pega um "ponteiro fresco" E limpa quaisquer popups "entre jobs"
        print("Pegando 'ponteiro fresco' e limpando a janela principal...")
        main_win_fresca = app_session.window(title=rpa_core.MAIN_WINDOW_TITLE)

        # Chama a Função 2 (Limpeza) de novo. Isso garante que a main_win
        # está 100% ativa e limpa ANTES de tentarmos usá-la.
        if not rpa_core.limpar_popups_iniciais(app_session, main_win_fresca):
            raise Exception("Falha ao limpar popups 'entre jobs' (Função 2).")
        print("✓ Ponteiro fresco obtido e janela limpa.")

        # --- PASSO 2: Estamos na empresa certa? ---
        if current_company_session != empresa_codigo:
            print(
                f"Sessão atual é {current_company_session}, trocando para {empresa_codigo}..."
            )
            # Função 3
            if not rpa_core.trocar_empresa(
                app_session, main_win_fresca, empresa_codigo
            ):
                raise Exception("Falha ao trocar de empresa (Função 3).")

            current_company_session = empresa_codigo
            print(f"Troca de empresa concluída.")

        # --- PASSO 3: Executar a Ação ---
        print(
            f"Executando importação para {current_company_session} (Comp: {competencia})..."
        )

        # Função 4
        if not rpa_core.importar_consignado_empresa_ativa(
            app_session, main_win_fresca, competencia, empresa_codigo
        ):
            raise Exception("Falha ao importar consignado (Função 4).")

        print(f"Workflow do job {job_id} concluído com sucesso.")

        # --- PASSO 4: LÓGICA CONDICIONAL DE SAÍDA ---
        #
        if not has_next_job:
            print("Este foi o último job da fila. Encerrando a sessão do Fortes...")
            if app_session and app_session.is_process_running():
                app_session.kill()
            app_session, current_company_session = None, None
            print("Sessão do Fortes finalizada.")
        else:
            print("Ainda há jobs na fila. Mantendo a sessão aberta para o próximo job.")

    except Exception as e:
        # Se algo der errado, matamos a sessão para forçar um
        # reinício limpo no próximo job.
        if app_session and app_session.is_process_running():
            app_session.kill()
        app_session, current_company_session = None, None

        print(
            f"!!! ERRO NO WORKFLOW (Job {job_id}): {e}. Sessão do Fortes foi finalizada."
        )
        raise e


# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# !!!             FIM DAS MUDANÇAS (v1.4)                    !!!
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

# --- O "Coração" do Agente ---
if __name__ == "__main__":
    print("=" * 70)
    print(f"Agente RPA (ID: {AGENT_ID}) iniciado. Ouvindo a fila de jobs...")
    print("Pressione Ctrl+C para parar.")
    print("=" * 70)

    while True:
        try:
            job_processado = processar_fila()

            if not job_processado:
                print("Fila vazia. Aguardando 10s...")
                time.sleep(10)
            else:
                time.sleep(1)

        except KeyboardInterrupt:
            print("\nParada solicitada. Finalizando agente...")
            if app_session and app_session.is_process_running():
                app_session.kill()
            break
        except Exception as e:
            print(f"!!! ERRO FATAL NO AGENTE: {e}")
            print("Aguardando 60s antes de tentar novamente...")
            time.sleep(60)
