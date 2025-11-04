# rpa_core.py
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
import pyautogui
import os

# --- Constantes do Fortes ---
FORTES_EXE_PATH = r"C:\Fortes\Fortes\AC.exe"
LOGIN_WINDOW_TITLE = "Logon"
OK_BUTTON_NAME = "Ok (F9)"
MAIN_WINDOW_TITLE = "Fortes AC 8.17.1.1 - Setor Pessoal"  # atentar para a versao que pode ser motivo de quebra da aplicacao no futuro
POPUP_DICAS_TITLE = "Dicas - Versão 8 (Nova Tela)"
POPUP_SAIR_TITLE = "Confirmação"
POPUP_RELATORIO_TEMPO = "Assistente de Gestão do Tempo"  #
POPUP_AVALIACAO = "Avaliação"  # (Suposição, confirme se puder)
POPUP_INTEGRACOES = "Controle de Integrações"  #
POPUP_ATENCAO = "Atenção!"  #
POPUP_INFORMACAO = "Informação"  #


# --- FUNÇÃO 1: LOGIN (Baseada na sua login_v14_0) ---
def iniciar_sessao_fortes(username, password, initial_company_code):
    """
    Inicia uma nova instância do Fortes AC e executa o login.
    Retorna os objetos 'app' e 'main_win' para controle futuro.
    """
    print("Iniciando nova instância do Fortes AC...")
    try:
        app = Application(backend="uia").start(FORTES_EXE_PATH)

        print("Aguardando janela de Logon...")
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

        # Aguarda a janela principal carregar
        main_win = app.window(title=MAIN_WINDOW_TITLE)
        main_win.wait("visible", timeout=30)
        print("Janela principal carregada.")

        return app, main_win

    except Exception as e:
        print(f"!!! ERRO CRÍTICO ao iniciar sessão: {e}")
        # Se falhar, tenta matar o processo para não deixar lixo
        if "app" in locals() and app.is_process_running():
            app.kill()
        return None, None


# Pega o caminho absoluto da pasta onde este script está
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


# --- FUNÇÃO 2: LIMPEZA DE POPUPS (Versão 5.0 - O "Firewall Visual") ---
def limpar_popups_iniciais(app: Application, main_win: WindowSpecification):
    """
    Implementa a sua estratégia de "Firewall Visual".
    1. Músculo (pywinauto) envia {ESC} em loop.
    2. Olhos (pyautogui) procuram *apenas* pelo "Não" do popup "Sair?".
    3. Músculo (pywinauto) clica em "Não" para finalizar.
    """
    print("\nIniciando 'Loop de Caçada v5.0' (O Firewall Visual)...")

    # O alvo visual para o *Firewall*
    target_path = os.path.join(SCRIPT_DIR, "target_btn_nao.png")  #

    if not os.path.exists(target_path):
        raise FileNotFoundError(
            f"Arquivo do Firewall Visual não encontrado: {target_path}"
        )
    print(f"Alvo do Firewall Visual carregado: {target_path}")

    limite_tempo = 30
    tempo_inicio = time.time()

    # Especificação do popup "Sair?", que caçaremos com pywinauto
    sair_popup_spec = app.window(title=POPUP_SAIR_TITLE)

    while (time.time() - tempo_inicio) < limite_tempo:
        try:
            # 1. CONDIÇÃO DE SUCESSO: A Janela Principal está ativa?
            if main_win.is_active():
                main_win.set_focus()
                time.sleep(0.1)  # Pausa de estabilização
                if main_win.is_active():
                    print("✓ SUCESSO: Janela principal está limpa e ativa!")
                    return True  # O trabalho acabou

            # 2. OS "OLHOS" (O Firewall): O pyautogui procura pelo "Não"
            #
            location = pyautogui.locateOnScreen(
                target_path, confidence=0.8, grayscale=True, region=None
            )

            if location:
                # 3. AÇÃO DO FIREWALL (Músculo)
                print("Caçada (Visual): Firewall 'Não' detectado!")
                print("Acionando 'Músculo' (pywinauto) para clicar em 'Não'...")

                # Usamos pywinauto (confiável) para clicar
                if sair_popup_spec.exists(timeout=0.5):
                    sair_popup_spec.child_window(
                        title="Não", control_type="Button"
                    ).click_input()
                    time.sleep(0.5)
                    print(
                        "Firewall clicado. Reiniciando loop para verificação final..."
                    )
                    continue  # Volta ao início para verificar se main_win está ativa
                else:
                    print(
                        "AVISO: Olhos viram 'Não', mas Músculo não achou popup 'Confirmação'."
                    )

            else:
                # 4. AÇÃO CEGA (Músculo): Nenhum "Não" encontrado.
                # Isso significa que um popup cego (ou nenhum) está na tela.
                # Enviamos {ESC} para matar o que quer que esteja lá.
                print("Caçada (Cega): Nenhum firewall. Enviando {ESC}...")
                main_win.set_focus()
                send_keys("{ESC}")  # <-- CORREÇÃO: Com aspas
                time.sleep(1.0)  # Pausa para o popup fechar

        except pyautogui.ImageNotFoundException:
            # Isso é normal, significa apenas que o botão "Não" não está na tela.
            # Continuamos para a Ação Cega ({ESC}).
            print("Caçada (Olhos): Botão 'Não' não encontrado. Enviando {ESC}...")
            main_win.set_focus()
            send_keys("{ESC}")  # <-- CORREÇÃO: Com aspas
            time.sleep(1.0)

        except Exception as e:
            print(
                f"!!! Erro inesperado durante a caçada: {e} (Tipo: {type(e)}). Continuando..."
            )
            time.sleep(1)

    # Se saiu do loop (passou 30s), é porque estourou o tempo
    raise timings.TimeoutError("Loop de Caçada v5.0 (Firewall Visual) falhou (30s).")


# --- Constantes para Troca de Empresa ---
MENU_PRINCIPAL_CLASSNAME = "TUiFinderTreeViewForFiltered"
TROCA_WINDOW_TITLE = "Outra Empresa"
TROCA_WINDOW_CLASS = "TfrmLgAC"


# --- FUNÇÃO 3: TROCA DE EMPRESA (Baseada no seu switch_company.py v36.1) ---
def trocar_empresa(
    app: Application,
    main_win: WindowSpecification,
    novo_codigo_empresa: str,
):
    """
    Executa o fluxo de "Outra Empresa" usando a navegação por busca.
    Assume que a janela principal está limpa e ativa.
    """
    print(f"\nIniciando troca para Empresa: {novo_codigo_empresa}...")
    try:
        # PASSO 1: Clicar no Hambúrguer (Baseado no Passo 6 do v36.1)
        # Usamos coordenadas fixas porque provamos que é estável
        main_win.click_input(coords=(25, 25))
        time.sleep(1)
        print("✓ Botão Hambúrguer clicado.")

        # PASSO 2: Navegar via Busca (Baseado nos Passos 7 e 8 do v36.1)
        uia_menu_container = main_win.child_window(class_name=MENU_PRINCIPAL_CLASSNAME)
        uia_menu_container.wait("visible", timeout=5)
        uia_menu_container.set_focus()

        time.sleep(0.5)

        alvo = "Outra Empresa"
        print(f"Digitando '{alvo}' no campo de busca...")
        send_keys(alvo, with_spaces=True, pause=0.05)
        time.sleep(1)  # Pausa para a UI filtrar
        send_keys("{ENTER}")
        print("✓ Navegação por Busca concluída.")

        # PASSO 3: Preencher Janela de Troca (Baseado nos Passos 9 e 10 do v36.1)
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

        print("Enviando {ENTER} para confirmar (clicar em 'Ok (F9)')...")
        time.sleep(1)
        send_keys("{TAB}")
        send_keys("{ENTER}")

        troca_win.wait_not("visible", timeout=10)
        print("✓ Janela de Troca fechada.")

        # PASSO 4: Limpeza PÓS-TROCA (O seu 'Passo 11' - Crítico!)
        # Como você observou, a troca de empresa gera NOVOS popups.
        # Usamos a mesma lógica da Função 2.
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
        return False


# --- Constantes para Importação de Consignado ---
FILTER_WINDOW_TITLE = "Filtro de Consignado"
FILTER_WINDOW_CLASS = "TfrmDgFiltroCOT_COE"  #
CONSIGNADO_WINDOW_TITLE = "Consignado - Crédito do Trabalhador"
PANEL_BUTTON_NAME_REGEX = ".*Painel.*Consignado.*"  #


# rpa_core.py (continuação)

# rpa_core.py (continuação)

# rpa_core.py (continuação)


# --- FUNÇÃO 4: IMPORTAR CONSIGNADO (Versão 1.5 - O "Mapa de 4 Tabs") ---
def importar_consignado_empresa_ativa(
    main_win: WindowSpecification, competencia_mes_ano: str, company_code: str
):
    """
    Executa o fluxo de "Importar Consignado".
    Usa o "mapa de 4 tabs" para o Filtro.
    """
    print(
        f"\nIniciando importação de consignado para {company_code} (Comp: {competencia_mes_ano})..."
    )
    try:
        # PASSO 1: Clicar no Hambúrguer
        main_win.click_input(coords=(25, 25))
        time.sleep(1)
        print("✓ Botão Hambúrguer clicado.")

        # PASSO 2: Navegar via Busca
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
        time.sleep(1.5)  # "Suspiro" da v1.3

        # PASSO 3: Preencher Janela de Filtro (COM CORREÇÃO "4 Tabs")
        desktop = Desktop(backend="uia")
        filtro_win = desktop.window(
            title=FILTER_WINDOW_TITLE, class_name=FILTER_WINDOW_CLASS
        )
        filtro_win.wait("active", timeout=15)
        filtro_win.set_focus()
        print(f"✓ Janela '{FILTER_WINDOW_TITLE}' está ativa.")

        all_edits = filtro_win.descendants(control_type="Edit")
        sorted_edits = sorted(all_edits, key=lambda ctrl: ctrl.rectangle().top)
        competencia_field = sorted_edits[0]

        print(f"Digitando competência: {competencia_mes_ano}")
        competencia_field.set_text(competencia_mes_ano)
        time.sleep(5)

        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        # !!!           INÍCIO DA CORREÇÃO (v1.5 - 4 Tabs)           !!!
        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

        # Baseado na sua "Missão de Reconhecimento"
        print("Enviando {TAB 4} para mover o foco para o botão 'Ok'...")
        send_keys("{TAB}")  #
        time.sleep(1)
        send_keys("{TAB}")  #
        time.sleep(1)
        send_keys("{TAB}")  #
        time.sleep(1)
        send_keys("{TAB}")  #
        time.sleep(1)

        print("Enviando {ENTER} para ativar o botão 'Ok' (focado)...")
        send_keys("{ENTER}")

        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        # !!!             FIM DA CORREÇÃO (v1.5 - 4 Tabs)            !!!
        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

        filtro_win.wait_not("visible", timeout=10)
        print("✓ Filtro aplicado e janela fechada.")

        print("Dando 2s para o Fortes 'respirar' e popular a grade...")
        time.sleep(2.0)

        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        # !!!           INÍCIO DA CORREÇÃO (v1.6 - Foco)             !!!
        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

        # PASSO 4: Clicar em "Painel Consignado"
        send_keys("{TAB}")  #
        time.sleep(1)
        send_keys("{TAB}")  #
        time.sleep(1)

        print("Enviando {ENTER} para ativar o botão 'Ok' (focado)...")
        send_keys("{ENTER}")

        print("✓ Botão 'Painel Consignado' clicado.")
        time.sleep(1.5)

        # PASSO 5: Preencher Painel (O "Plano T: Tabs" - LÓGICA CORRIGIDA)
        print("Preenchendo painel via teclado (Plano T)...")

        # Lógica baseada no seu v38.5 / v40.0
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

        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        # !!!             FIM DA CORREÇÃO (v1.6 - Foco)              !!!
        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

        print("Enviando {ENTER} para Coletar...")
        send_keys("{ENTER}")
        print("Aguardando 15s pela coleta...")
        time.sleep(15)

        print("✓✓✓ Importação de Consignado CONCLUÍDA.")
        return True

    except Exception as e:
        print(f"!!! ERRO ao importar consignado: {e} (Tipo: {type(e)})")
        import traceback

        traceback.print_exc()
        return False
