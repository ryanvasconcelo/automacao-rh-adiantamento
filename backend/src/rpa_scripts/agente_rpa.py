# agente_rpa.py
# O "Operário" - Fase 4
# Este script roda 24/7, lê a fila de jobs e chama o "Músculo" (rpa_core).

import time
import rpa_core  # Nosso Músculo (Fase 2)

# import backend.queue_db as queue_db  # Nossa conexão com a Ponte (Fase 3)
import backend.queue_db as queue_db  # Nossa conexão com a Ponte (Fase 3)
import traceback

# --- CONFIGURAÇÃO DO AGENTE ---
# (Coloque seus dados de login reais aqui)
USER = "RYAN"
PASS = "1234"
# O ID deste agente, para sabermos qual máquina executou
AGENT_ID = "WINDOWS_VM_01"
# ------------------------------


def processar_fila():
    """
    O loop principal do agente. Busca e processa um job.
    Retorna True se processou um job, False se a fila estava vazia.
    """
    conn = None
    job = None
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
        row = cursor.fetchone()  # Isto é uma tupla: (id, empresa_codigo, competencia)
        conn.commit()

        # Converte a tupla em um dicionário para o resto do código
        job = None
        if row:
            job = {"id": row[0], "empresa_codigo": row[1], "competencia": row[2]}

        # Se não há job, a fila está vazia
        if not job:
            return False  # Fila vazia

        print("\n--- NOVO JOB RECEBIDO ---")
        print(
            f"ID: {job['id']}, Empresa: {job['empresa_codigo']}, Comp: {job['competencia']}"
        )

        # 2. EXECUTAR JOB (Chamando o rpa_core)
        # (Esta função implementará a lógica de sessão)
        run_rpa_workflow(job)

        # 3. MARCAR COMO CONCLUÍDO
        sql_concluir = """
            UPDATE TB_RPA_JOBS
            SET status = 'CONCLUIDO', updated_at = GETDATE()
            WHERE id = %s
        """
        cursor.execute(sql_concluir, (job["id"],))
        conn.commit()
        print(f"✓ SUCESSO: Job {job['id']} marcado como CONCLUÍDO.")

    except Exception as e:
        # 4. MARCAR COMO ERRO
        print(f"!!! ERRO CRÍTICO no job {job['id'] if job else 'INDEFINIDO'}: {e}")
        if conn and job:
            try:
                sql_erro = """
                    UPDATE TB_RPA_JOBS
                    SET status = 'ERRO', error_message = %s, updated_at = GETDATE()
                    WHERE id = %s
                """
                cursor.execute(sql_erro, (traceback.format_exc(), job["id"]))
                conn.commit()
                print(f"✗ ERRO: Job {job['id']} marcado como ERRO no banco.")
            except Exception as db_e:
                print(f"!!! ERRO CRÍTICO NO BANCO: {db_e}")

        # Retorna True, pois processamos (e falhamos) um job
        return True

    finally:
        if conn:
            conn.close()

    # Se chegamos aqui, processamos um job
    return True


# --- GERENCIAMENTO DE SESSÃO (A "Inteligência" do Agente) ---
# Estas variáveis mantêm o estado do Fortes AC entre os loops
app_session = None
main_win_session = None
current_company_session = None


def run_rpa_workflow(job):
    """
    Orquestra o rpa_core mantendo a sessão aberta.
    """
    global app_session, main_win_session, current_company_session

    try:
        # --- PASSO 1: O Fortes está aberto? ---
        if app_session is None or not app_session.is_process_running():
            print("Sessão do Fortes não existe. Iniciando nova...")
            app_session, main_win_session = rpa_core.iniciar_sessao_fortes(
                USER, PASS, job["empresa_codigo"]
            )
            if app_session is None:
                raise Exception("Falha ao iniciar sessão (Função 1).")

            if not rpa_core.limpar_popups_iniciais(app_session, main_win_session):
                raise Exception("Falha ao limpar popups (Função 2).")

            current_company_session = job["empresa_codigo"]
            print(f"Sessão iniciada e logada na empresa {current_company_session}.")

        # --- PASSO 2: Estamos na empresa certa? ---
        if current_company_session != job["empresa_codigo"]:
            print(
                f"Sessão atual é {current_company_session}, trocando para {job['empresa_codigo']}..."
            )
            if not rpa_core.trocar_empresa(
                app_session, main_win_session, job["empresa_codigo"]
            ):
                raise Exception("Falha ao trocar de empresa (Função 3).")

            current_company_session = job["empresa_codigo"]
            print(f"Troca de empresa concluída.")

        # --- PASSO 3: Executar a Ação ---
        print(
            f"Executando importação para {current_company_session} (Comp: {job['competencia']})..."
        )
        if not rpa_core.importar_consignado_empresa_ativa(
            main_win_session, job["competencia"], job["empresa_codigo"]
        ):
            raise Exception("Falha ao importar consignado (Função 4).")

        print("Workflow do job concluído com sucesso.")

    except Exception as e:
        # Se algo der errado, matamos a sessão para forçar um
        # reinício limpo no próximo job.
        if app_session and app_session.is_process_running():
            app_session.kill()

        # Limpa nossas variáveis de sessão
        app_session, main_win_session, current_company_session = None, None, None

        print(f"!!! ERRO NO WORKFLOW: {e}. Sessão do Fortes foi finalizada.")
        # Propaga o erro para que o 'processar_fila' o marque no banco
        raise e


# --- O "Coração" do Agente ---
if __name__ == "__main__":
    print("=" * 70)
    print(f"Agente RPA (ID: {AGENT_ID}) iniciado. Ouvindo a fila de jobs...")
    print("Pressione Ctrl+C para parar.")
    print("=" * 70)

    while True:
        try:
            # Processa um job
            job_processado = processar_fila()

            if not job_processado:
                # Fila vazia, espera 10 segundos
                print("Fila vazia. Aguardando 10s...")
                time.sleep(10)
            else:
                # Processamos um job, verifica o próximo imediatamente
                time.sleep(1)  # Pausa curta

        except KeyboardInterrupt:
            print("\nParada solicitada. Finalizando agente...")
            # Garante que o Fortes feche ao sairmos
            if app_session and app_session.is_process_running():
                app_session.kill()
            break
        except Exception as e:
            # Erro na própria lógica do agente (ex: conexão com DB)
            print(f"!!! ERRO FATAL NO AGENTE: {e}")
            print("Aguardando 60s antes de tentar novamente...")
            time.sleep(60)
