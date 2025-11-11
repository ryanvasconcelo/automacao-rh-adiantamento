# rpa_core.py (Versão 2.1 - Fecha a Janela do Painel)
# tool box de functions
import time
import pywinauto
from pywinauto.keyboard import send_keys
from pywinauto import timings
from pywinauto import Desktop
from pywinauto.application import Application, WindowSpecification
from pywinauto.findwindows import ElementNotFoundError, ElementAmbiguousError
from pywinauto.application import ProcessNotFoundError
from pywinauto import mouse
import traceback

# --- Constantes do Fortes ---
FORTES_EXE_PATH = r"C:\Fortes\Fortes\AC.exe"
LOGIN_WINDOW_TITLE = "Logon"
OK_BUTTON_NAME = "Ok (F9)"
MAIN_WINDOW_TITLE = "Fortes AC 8.17.1.1 - Setor Pessoal"
POPUP_SAIR_TITLE = "Confirmação"  # O popup "Sair?"

# --- Popups de Limpeza (v6.0) ---
POPUP_DICAS_TITLE = "Dicas - Versão 8 (Nova Tela)"
POPUP_RELATORIO_TEMPO = "Assistente de Gestão do Tempo"
POPUP_AVALIACAO = "Avaliação"
POPUP_INTEGRACOES = "Controle de Integrações"
POPUP_ATENCAO_CONECTA = "Atenção!"
POPUP_INFORMACAO_ATIVIDADES = "Informação"

# --- Constantes para Troca de Empresa ---
MENU_PRINCIPAL_CLASSNAME = "TUiFinderTreeViewForFiltered"
TROCA_WINDOW_TITLE = "Outra Empresa"
TROCA_WINDOW_CLASS = "TfrmLgAC"

# --- Constantes para Importação de Consignado ---
FILTER_WINDOW_TITLE = "Filtro de Consignado"
FILTER_WINDOW_CLASS = "TfrmDgFiltroCOT_COE"
CONSIGNADO_WINDOW_TITLE = "Consignado - Crédito do Trabalhador"
PANEL_BUTTON_NAME_REGEX = ".*Painel.*Consignado.*"
# --- INÍCIO DA ALTERAÇÃO (v2.1) ---
PANEL_WINDOW_TITLE = "Painel Consignado - Crédito do Trabalhador"  #
# --- FIM DA ALTERAÇÃO ---

# --- Constantes dos Popups Finais (Baseado nas suas Props) ---
POPUP_CONFIRMACAO_REIMPORTAR = "Confirmação"
POPUP_INFORMACAO_SUCESSO = "Informação"
POPUP_FINAL_CLASS = "TDlMessageForm"


# --- FUNÇÃO 1: LOGIN (Estável) ---
def iniciar_sessao_fortes(username, password, initial_company_code):
    # (Código da v2.0... Sem alterações)
    print("Iniciando nova instância do Fortes AC...")
    try:
        app = Application(backend="uia").start(FORTES_EXE_PATH)
        login_win = app.window(title=LOGIN_WINDOW_TITLE)
        login_win.wait("active", timeout=30)
        login_win.set_focus()
        print("Janela 'Logon' focada. Interagindo...")
        all_edit_controls = login_win.descendants(control_type="Edit")
        sorted_edits = sorted(all_edit_controls, key=lambda ctrl: ctrl.rectangle().top)
        if len(sorted_edits) < 3:
            raise IndexError(
                f"Esperava 3 campos 'Edit', mas encontrei {len(sorted_edits)}"
            )
        sorted_edits[0].set_text(username)
        sorted_edits[1].set_text(password)
        sorted_edits[2].set_text(initial_company_code)
        time.sleep(1)
        ok_button = login_win.child_window(title=OK_BUTTON_NAME, control_type="Button")
        ok_button.wait("enabled", timeout=5)
        ok_button.click_input()
        print("Login enviado.")
        main_win = app.window(title=MAIN_WINDOW_TITLE)
        main_win.wait("visible", timeout=30)
        print("Janela principal carregada.")
        return app, main_win
    except Exception as e:
        print(f"!!! ERRO CRÍTICO ao iniciar sessão: {e}")
        if "app" in locals() and app.is_process_running():
            app.kill()
        return None, None


# --- FUNÇÃO 2: LIMPEZA DE POPUPS (v6.0 - 100% Músculo Estável) ---
def limpar_popups_iniciais(app: Application, main_win: WindowSpecification):
    # (Código da v2.0... Sem alterações)
    print("\nIniciando 'Loop de Caçada 100% Músculo' (v6.0)...")
    titulos_conhecidos = [
        POPUP_DICAS_TITLE,
        POPUP_RELATORIO_TEMPO,
        POPUP_AVALIACAO,
        POPUP_INTEGRACOES,
        POPUP_ATENCAO_CONECTA,
        POPUP_INFORMACAO_ATIVIDADES,
    ]
    limite_tempo = 30
    tempo_inicio = time.time()
    ciclos_sem_alvo = 0
    sair_popup_spec = app.window(title=POPUP_SAIR_TITLE)

    while (time.time() - tempo_inicio) < limite_tempo:
        try:
            if main_win.is_active():
                main_win.set_focus()
                time.sleep(0.1)
                if main_win.is_active():
                    print("✓ SUCESSO: Janela principal está limpa e ativa!")
                    return True

            alvo_encontrado = None
            for titulo in titulos_conhecidos:
                popup_spec = app.window(title_re=f".*{titulo}.*")
                if popup_spec.exists(timeout=0.2):
                    alvo_encontrado = titulo
                    break

            if alvo_encontrado:
                ciclos_sem_alvo = 0
                print(
                    f"Caçada (Título): Alvo '{alvo_encontrado}' detectado. Enviando {{ESC}}..."
                )
                popup_spec.set_focus().send_keys("{ESC}")
                time.sleep(1.0)
                continue

            ciclos_sem_alvo += 1
            if ciclos_sem_alvo % 3 == 0:
                print(
                    f"Caçada (Cega): Nenhum alvo por título. Aplicando 'Força Bruta {{ESC}}'..."
                )
                main_win.set_focus()
                send_keys("{ESC}")
                time.sleep(1.0)

                if sair_popup_spec.exists(timeout=0.2):
                    print("Caçada: Firewall acionado! Clicando em 'Não'...")
                    sair_popup_spec.child_window(
                        title="Não", control_type="Button"
                    ).click_input()
                    time.sleep(0.5)
                continue

            print(f"Caçada: Nada detectado (Ciclo {ciclos_sem_alvo}). Aguardando 1s...")
            time.sleep(1)

        except Exception as e:
            print(
                f"!!! Erro inesperado durante a caçada: {e} (Tipo: {type(e)}). Continuando..."
            )
            time.sleep(1)

    raise timings.TimeoutError("Loop de Caçada (v6.0) falhou (30s).")


# --- FUNÇÃO 3: TROCA DE EMPRESA (Estável) ---
def trocar_empresa(
    app: Application, main_win: WindowSpecification, novo_codigo_empresa: str
):
    # (Código da v2.0... Sem alterações)
    print(f"\nIniciando troca para Empresa: {novo_codigo_empresa}...")
    try:
        main_win.click_input(coords=(25, 25))
        time.sleep(1)
        print("✓ Botão Hambúrguer clicado.")

        uia_menu_container = main_win.child_window(class_name=MENU_PRINCIPAL_CLASSNAME)
        uia_menu_container.wait("visible", timeout=5)
        uia_menu_container.set_focus()
        time.sleep(0.5)
        alvo = "Outra Empresa"
        print(f"Digitando '{alvo}' no campo de busca...")
        send_keys(alvo, with_spaces=True, pause=0.05)
        time.sleep(1)
        send_keys("{ENTER}")
        print("✓ Navegação por Busca concluída.")

        desktop = Desktop(backend="uia")
        troca_win = desktop.window(
            title=TROCA_WINDOW_TITLE, class_name=TROCA_WINDOW_CLASS
        )
        troca_win.wait("active", timeout=15)
        troca_win.set_focus()
        print(f"✓ Janela '{TROCA_WINDOW_TITLE}' está ativa.")

        print(f"Digitando novo código: {novo_codigo_empresa} (campo focado)")
        send_keys(novo_codigo_empresa, with_spaces=True, pause=0.05)
        time.sleep(0.5)

        print("Enviando {TAB} e {ENTER} para confirmar...")
        time.sleep(1)
        send_keys("{TAB}")
        send_keys("{ENTER}")

        troca_win.wait_not("visible", timeout=10)
        print("✓ Janela de Troca fechada.")

        print(
            f"Aguardando 3s para NOVOS popups (da empresa {novo_codigo_empresa}) carregarem..."
        )
        time.sleep(3)
        print("Caçada Pós-Troca: Aplicando 'Força Bruta {ESC}'...")
        main_win.set_focus()
        print("Enviando {ESC} #1 (Alvo: FortesPay)...")
        send_keys("{ESC}")
        time.sleep(1)

        sair_popup = app.window(title=POPUP_SAIR_TITLE)
        if sair_popup.exists(timeout=0.5):
            print("Caçada Pós-Troca: Firewall acionado. Clicando 'Não'...")
            sair_popup.child_window(title="Não", control_type="Button").click_input()
        else:
            print("Enviando {ESC} #2 (Alvo: Integração)...")
            main_win.set_focus()
            send_keys("{ESC}")
            time.sleep(1)

        main_win.wait("active", timeout=10)
        print(f"✓ Popups Pós-Troca limpos. Empresa {novo_codigo_empresa} está ativa.")
        return True
    except Exception as e:
        print(f"!!! ERRO ao trocar de empresa: {e}")
        traceback.print_exc()
        return False


# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# !!!               INÍCIO DA MUDANÇA (v2.1)                 !!!
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!


# --- FUNÇÃO-AUXILIAR ATUALIZADA: Limpeza Pós-Importação (v2.1 - Fecha Painel) ---
def _limpar_popups_finais(app: Application):
    """
    Caça os popups FINAIS (Confirmação e Sucesso) e FECHA o painel.
    Usa 100% pywinauto ("Músculo") baseado nas suas props.
    """
    print("Iniciando 'Caçada Final' (v2.1 - Fecha Painel)...")

    popup_confirmacao = app.window(
        title=POPUP_CONFIRMACAO_REIMPORTAR, class_name=POPUP_FINAL_CLASS
    )
    popup_sucesso = app.window(
        title=POPUP_INFORMACAO_SUCESSO, class_name=POPUP_FINAL_CLASS
    )

    limite_tempo = 20
    tempo_inicio = time.time()

    sucesso_tratado = False  # O popup de Sucesso é obrigatório

    while (time.time() - tempo_inicio) < limite_tempo:
        try:
            # --- ALVO 1 (Condicional): A Reimportação "Sim?" ---
            if popup_confirmacao.exists(timeout=0.2):
                print("Caçada Final (Músculo): Janela 'Confirmação' detectada.")
                popup_confirmacao.child_window(
                    title="Sim", class_name="TDLBitBtn"
                ).click_input()
                print("Caçada Final (Músculo): Clicou em 'Sim'.")
                time.sleep(1.0)
                continue

            # --- ALVO 2 (Final): O "Ok" de Sucesso ---
            if popup_sucesso.exists(timeout=0.2):
                print("Caçada Final (Músculo): Janela 'Informação' detectada.")
                popup_sucesso.child_window(
                    title="Ok", class_name="TDLBitBtn"
                ).click_input()
                print("Caçada Final (Músculo): Clicou em 'Ok'.")
                sucesso_tratado = True
                break  # <-- O "Ok" é o fim. Saímos do loop.

            print("Caçada Final: Aguardando popups de confirmação/sucesso...")
            time.sleep(1)

        except Exception as e:
            print(f"!!! Erro inesperado na Caçada Final: {e} (Tipo: {type(e)}).")
            try:
                if popup_confirmacao.exists(timeout=0.2):
                    popup_confirmacao.send_keys("{ESC}")
                elif popup_sucesso.exists(timeout=0.2):
                    popup_sucesso.send_keys("{ESC}")
            except:
                pass
            time.sleep(1)

    if not sucesso_tratado:
        raise timings.TimeoutError(
            "Caçada Final falhou (20s). Popup de 'Sucesso' NUNCA foi encontrado."
        )

    # --- PASSO FINAL (A CORREÇÃO v2.1) ---
    # Agora que clicamos em "Ok", o foco está na janela "Painel Consignado"
    #
    # Precisamos fechá-la para devolver o foco à MAIN_WINDOW.
    try:
        print("Limpando a janela 'Painel Consignado'...")
        # (Usamos title_re para sermos robustos, como no v38.5)
        painel_win = app.window(title_re=f".*{PANEL_WINDOW_TITLE}.*")

        if painel_win.exists(timeout=1.0):
            painel_win.close()  # Pede para fechar educadamente
            print("✓ Janela 'Painel Consignado' fechada.")
        else:
            print("AVISO: Janela 'Painel Consignado' não encontrada para fechar.")
    except Exception as e:
        print(f"AVISO: Erro ao tentar fechar o 'Painel Consignado': {e}")
        # (Não falha o robô, apenas avisa)

    return True


# --- FUNÇÃO 4: IMPORTAR CONSIGNADO (Versão 2.1 - Estável) ---
def importar_consignado_empresa_ativa(
    app: Application,
    main_win: WindowSpecification,
    competencia_mes_ano: str,
    company_code: str,
):
    """
    Executa o fluxo de "Importar Consignado" (v1.5)
    E agora chama a função de limpeza final (v2.1).
    """
    print(
        f"\nIniciando importação de consignado para {company_code} (Comp: {competencia_mes_ano})..."
    )
    try:
        # PASSO 1, 2, 3 (Estáveis)
        main_win.click_input(coords=(25, 25))
        time.sleep(1)
        print("✓ Botão Hambúrguer clicado.")
        uia_menu_container = main_win.child_window(class_name=MENU_PRINCIPAL_CLASSNAME)
        uia_menu_container.wait("visible", timeout=5)
        uia_menu_container.set_focus()
        time.sleep(1)
        alvo = "Consignado - Crédito do Trabalhador"
        print(f"Digitando '{alvo}' no campo de busca...")
        send_keys(alvo, with_spaces=True, pause=0.05)
        time.sleep(1)
        send_keys("{ENTER}")
        print("✓ Navegação por Busca concluída.")
        print("Dando 1.5s para o Fortes 'respirar' e abrir o Filtro...")
        time.sleep(1.5)

        desktop = Desktop(backend="uia")
        filtro_win = desktop.window(
            title=FILTER_WINDOW_TITLE, class_name=FILTER_WINDOW_CLASS
        )
        filtro_win.wait("active", timeout=15)
        filtro_win.set_focus()
        print(f"✓ Janela '{FILTER_WINDOW_TITLE}' está ativa.")

        competencia_field = filtro_win.descendants(control_type="Edit")[0]
        print(f"Digitando competência: {competencia_mes_ano}")
        competencia_field.set_text(competencia_mes_ano)
        time.sleep(1)
        print("Enviando {TAB 4} para mover o foco para o botão 'Ok'...")
        send_keys("{TAB 4}")
        time.sleep(0.5)
        print("Enviando {ENTER} para ativar o botão 'Ok' (focado)...")
        send_keys("{ENTER}")
        filtro_win.wait_not("visible", timeout=10)
        print("✓ Filtro aplicado e janela fechada.")
        print("Dando 2s para o Fortes 'respirar' e popular a grade...")
        time.sleep(2.0)

        # PASSO 4 (Estável - Lógica "Cega" v1.6)
        print("Navegando 'às cegas' para o botão 'Painel Consignado'...")
        send_keys("{TAB}")
        time.sleep(0.3)
        send_keys("{TAB}")
        time.sleep(0.5)
        print("Enviando {ENTER} para ativar o botão 'Painel Consignado'...")
        send_keys("{ENTER}")
        print("✓ Botão 'Painel Consignado' clicado.")
        time.sleep(1.5)

        # PASSO 5 (Estável - "Plano T: Tabs" v1.6)
        print("Preenchendo painel via teclado (Plano T)...")
        print("Enviando {TAB 2} para 'Competência'...")
        send_keys("{TAB 2}")
        time.sleep(0.5)
        print(f"Digitando competência: {competencia_mes_ano}")
        send_keys(competencia_mes_ano, with_spaces=True, pause=0.05)
        time.sleep(0.5)
        print(f"Enviando {{TAB}} para Empresa...")
        send_keys("{TAB}")
        time.sleep(0.5)
        print(f"Digitando empresa: {company_code}")
        send_keys(company_code, with_spaces=True, pause=0.05)
        time.sleep(0.5)
        print("Enviando {TAB} para Coletar...")
        send_keys("{TAB}")
        time.sleep(0.5)
        print("Enviando {ENTER} para Coletar...")
        send_keys("{ENTER}")
        print("Aguardando 15s pela coleta...")
        time.sleep(15)

        # PASSO 6: Limpar popups FINAIS (v2.1)
        print("Coleta enviada. Iniciando limpeza final de popups...")
        _limpar_popups_finais(app)  # <--- AQUI ESTÁ A CHAVE

        print("✓✓✓ Importação de Consignado CONCLUÍDA.")
        return True

    except Exception as e:
        print(f"!!! ERRO ao importar consignado: {e} (Tipo: {type(e)})")
        traceback.print_exc()
        return False
