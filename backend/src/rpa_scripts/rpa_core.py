# rpa_core.py (Versão 1.7 - Blindado contra popups finais)
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
import traceback  # <-- Import para o traceback completo

# --- Constantes do Fortes ---
FORTES_EXE_PATH = r"C:\Fortes\Fortes\AC.exe"
LOGIN_WINDOW_TITLE = "Logon"
OK_BUTTON_NAME = "Ok (F9)"
MAIN_WINDOW_TITLE = "Fortes AC 8.17.1.1 - Setor Pessoal"
POPUP_DICAS_TITLE = "Dicas - Versão 8 (Nova Tela)"
POPUP_SAIR_TITLE = "Confirmação"

# --- Constantes para Troca de Empresa ---
MENU_PRINCIPAL_CLASSNAME = "TUiFinderTreeViewForFiltered"
TROCA_WINDOW_TITLE = "Outra Empresa"
TROCA_WINDOW_CLASS = "TfrmLgAC"

# --- Constantes para Importação de Consignado ---
FILTER_WINDOW_TITLE = "Filtro de Consignado"
FILTER_WINDOW_CLASS = "TfrmDgFiltroCOT_COE"
CONSIGNADO_WINDOW_TITLE = "Consignado - Crédito do Trabalhador"
PANEL_BUTTON_NAME_REGEX = ".*Painel.*Consignado.*"

# --- Constantes dos Popups Finais (Novos Alvos) ---
POPUP_CONFIRMACAO_REIMPORTAR = "Confirmação"  #
POPUP_INFORMACAO_SUCESSO = "Informação"  #


# Pega o caminho absoluto da pasta onde este script está
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


# --- FUNÇÃO 1: LOGIN (Estável) ---
def iniciar_sessao_fortes(username, password, initial_company_code):
    """
    Inicia uma nova instância do Fortes AC e executa o login.
    """
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


# --- FUNÇÃO 2: LIMPEZA DE POPUPS (v5.0 - Estável) ---
def limpar_popups_iniciais(app: Application, main_win: WindowSpecification):
    """
    Implementa a estratégia "Firewall Visual" (v5.0).
    """
    print("\nIniciando 'Loop de Caçada v5.0' (O Firewall Visual)...")
    target_path = os.path.join(SCRIPT_DIR, "target_btn_nao.png")  #

    if not os.path.exists(target_path):
        raise FileNotFoundError(
            f"Arquivo do Firewall Visual não encontrado: {target_path}"
        )
    print(f"Alvo do Firewall Visual carregado: {target_path}")

    limite_tempo = 30
    tempo_inicio = time.time()
    sair_popup_spec = app.window(title=POPUP_SAIR_TITLE)

    while (time.time() - tempo_inicio) < limite_tempo:
        try:
            if main_win.is_active():
                main_win.set_focus()
                time.sleep(0.1)
                if main_win.is_active():
                    print("✓ SUCESSO: Janela principal está limpa e ativa!")
                    return True

            location = pyautogui.locateOnScreen(
                target_path, confidence=0.8, grayscale=True, region=None
            )

            if location:
                print("Caçada (Visual): Firewall 'Não' detectado!")
                print("Acionando 'Músculo' (pywinauto) para clicar em 'Não'...")
                if sair_popup_spec.exists(timeout=0.5):
                    sair_popup_spec.child_window(
                        title="Não", control_type="Button"
                    ).click_input()
                    time.sleep(0.5)
                    print(
                        "Firewall clicado. Reiniciando loop para verificação final..."
                    )
                    continue
                else:
                    print(
                        "AVISO: Olhos viram 'Não', mas Músculo não achou popup 'Confirmação'."
                    )
            else:
                print("Caçada (Cega): Nenhum firewall. Enviando {ESC}...")
                main_win.set_focus()
                send_keys("{ESC}")
                time.sleep(1.0)

        except pyautogui.ImageNotFoundException:
            print("Caçada (Olhos): Botão 'Não' não encontrado. Enviando {ESC}...")
            main_win.set_focus()
            send_keys("{ESC}")
            time.sleep(1.0)
        except Exception as e:
            print(
                f"!!! Erro inesperado durante a caçada: {e} (Tipo: {type(e)}). Continuando..."
            )
            time.sleep(1)

    raise timings.TimeoutError("Loop de Caçada v5.0 (Firewall Visual) falhou (30s).")


# --- FUNÇÃO 3: TROCA DE EMPRESA (Estável) ---
def trocar_empresa(
    app: Application, main_win: WindowSpecification, novo_codigo_empresa: str
):
    """
    Executa o fluxo de "Outra Empresa" usando a navegação por busca.
    """
    print(f"\nIniciando troca para Empresa: {novo_codigo_empresa}...")
    try:
        # PASSO 1: Clicar no Hambúrguer
        main_win.click_input(coords=(25, 25))
        time.sleep(1)
        print("✓ Botão Hambúrguer clicado.")

        # PASSO 2: Navegar via Busca
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

        # PASSO 3: Preencher Janela de Troca
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

        # PASSO 4: Limpeza PÓS-TROCA (Crítico!)
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
        traceback.print_exc()  # Adiciona traceback para debug
        return False


# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# !!!               INÍCIO DA MUDANÇA (Ajuste 2)             !!!
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!


# --- NOVA FUNÇÃO-AUXILIAR: Limpeza Pós-Importação ---
def _limpar_popups_finais(app: Application):
    """
    Caça os popups FINAIS (Confirmação e Sucesso) após a coleta.
    Usa uma estratégia Híbrida (Olhos + Músculo).
    """
    print("Iniciando 'Caçada Final' por popups de Reimportação/Sucesso...")

    # Nossos novos alvos visuais
    target_sim = os.path.join(SCRIPT_DIR, "target_btn_sim_reimportar.png")
    target_ok = os.path.join(SCRIPT_DIR, "target_btn_ok_final.png")

    # Nossos alvos por título (pywinauto)
    popup_confirmacao = app.window(title=POPUP_CONFIRMACAO_REIMPORTAR)  #
    popup_sucesso = app.window(title=POPUP_INFORMACAO_SUCESSO)  #

    limite_tempo = 20  # 20 segundos de limite
    tempo_inicio = time.time()

    # Flags para garantir que lidamos com os popups
    confirmacao_tratada = False
    sucesso_tratado = False

    while (time.time() - tempo_inicio) < limite_tempo:
        try:
            # CONDIÇÃO DE SUCESSO: Ambos os popups foram tratados
            if confirmacao_tratada and sucesso_tratado:
                print("✓ Caçada Final: Popups de Sucesso e Confirmação tratados.")
                return True

            # --- ALVO 1 (Condicional): A Reimportação "Sim?" ---
            if not confirmacao_tratada:
                # OLHOS (pyautogui): Vê o botão "Sim"
                if os.path.exists(target_sim) and pyautogui.locateOnScreen(
                    target_sim, confidence=0.8, grayscale=True, region=None
                ):
                    print("Caçada Final (Olhos): Botão 'Sim' detectado!")
                    # MÚSCULO (pywinauto): Clica no "Sim"
                    if popup_confirmacao.exists(timeout=0.5):
                        popup_confirmacao.child_window(
                            title="Sim", control_type="Button"
                        ).click_input()
                        print("Caçada Final (Músculo): Clicou em 'Sim'.")
                        confirmacao_tratada = True
                        time.sleep(1.0)  # Pausa para o próximo popup
                        continue

                # Fallback: Se os Olhos falharem, mas a janela existir, envia {ENTER}
                elif popup_confirmacao.exists(timeout=0.2):
                    print(
                        "Caçada Final (Músculo): Janela 'Confirmação' detectada. Enviando {ENTER}..."
                    )
                    popup_confirmacao.set_focus().send_keys("{ENTER}")
                    confirmacao_tratada = True
                    time.sleep(1.0)
                    continue

            # --- ALVO 2 (Final): O "Ok" de Sucesso ---
            # (Só procuramos por ele se a confirmação já foi tratada ou não apareceu)

            # OLHOS (pyautogui): Vê o botão "Ok"
            if os.path.exists(target_ok) and pyautogui.locateOnScreen(
                target_ok, confidence=0.8, grayscale=True, region=None
            ):
                print("Caçada Final (Olhos): Botão 'Ok' detectado!")
                # MÚSCULO (pywinauto): Clica no "Ok"
                if popup_sucesso.exists(timeout=0.5):
                    popup_sucesso.child_window(
                        title="Ok", control_type="Button"
                    ).click_input()
                    print("Caçada Final (Músculo): Clicou em 'Ok'.")
                    sucesso_tratado = True
                    # Se tratamos o OK, provavelmente a confirmação não era necessária
                    confirmacao_tratada = True
                    continue

            # Fallback: Se os Olhos falharem, mas a janela existir, envia {ENTER}
            elif popup_sucesso.exists(timeout=0.2):
                print(
                    "Caçada Final (Músculo): Janela 'Informação' detectada. Enviando {ENTER}..."
                )
                popup_sucesso.set_focus().send_keys("{ENTER}")
                sucesso_tratado = True
                confirmacao_tratada = True
                continue

            # Se nenhum popup foi encontrado ainda
            print("Caçada Final: Aguardando popups de confirmação/sucesso...")
            time.sleep(1)

        except pyautogui.ImageNotFoundException:
            # Normal, os botões não estão na tela
            print("Caçada Final (Olhos): Nenhum alvo visual. Verificando títulos...")
            # (O loop continuará e tentará o fallback por título)
            time.sleep(1)
        except Exception as e:
            print(f"!!! Erro inesperado na Caçada Final: {e} (Tipo: {type(e)}).")
            time.sleep(1)

    # Se saímos do loop, algo deu errado
    if not sucesso_tratado:
        raise timings.TimeoutError(
            "Caçada Final falhou (20s). Popup de 'Sucesso' nunca foi encontrado."
        )
    return True


# --- FUNÇÃO 4: IMPORTAR CONSIGNADO (Versão 1.7 - Blindada) ---
def importar_consignado_empresa_ativa(
    app: Application,  # <-- MUDANÇA: Precisa do 'app' para a nova limpeza
    main_win: WindowSpecification,
    competencia_mes_ano: str,
    company_code: str,
):
    """
    Executa o fluxo de "Importar Consignado" (v1.5)
    E agora chama a função de limpeza final (v1.7).
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
        time.sleep(1.5)

        # PASSO 3: Preencher Janela de Filtro (v1.5 - "4 Tabs")
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
        time.sleep(1)  # Pausa maior, como no seu código

        print("Enviando {TAB 4} para mover o foco para o botão 'Ok'...")
        # Lógica de 4 tabs separada (mais robusta)
        send_keys("{TAB}")
        time.sleep(0.3)
        send_keys("{TAB}")
        time.sleep(0.3)
        send_keys("{TAB}")
        time.sleep(0.3)
        send_keys("{TAB}")
        time.sleep(0.5)

        print("Enviando {ENTER} para ativar o botão 'Ok' (focado)...")
        send_keys("{ENTER}")

        filtro_win.wait_not("visible", timeout=10)
        print("✓ Filtro aplicado e janela fechada.")

        print("Dando 2s para o Fortes 'respirar' e popular a grade...")
        time.sleep(2.0)

        # PASSO 4: Clicar em "Painel Consignado" (Lógica "Cega" vitoriosa)
        # Sua lógica "cega" (sem .wait()) foi a vencedora.
        print("Navegando 'às cegas' para o botão 'Painel Consignado'...")
        send_keys("{TAB}")  # 1. Foco na grade
        time.sleep(0.3)
        send_keys("{TAB}")  # 2. Foco no botão
        time.sleep(0.5)

        print("Enviando {ENTER} para ativar o botão 'Painel Consignado'...")
        send_keys("{ENTER}")

        print("✓ Botão 'Painel Consignado' clicado.")
        time.sleep(1.5)

        # PASSO 5: Preencher Painel (O "Plano T: Tabs" - v1.6)
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
        time.sleep(15)  # O tempo da coleta

        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        # !!!             INÍCIO DA MUDANÇA (Ajuste 2)               !!!
        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

        # PASSO 6: Limpar popups FINAIS
        print("Coleta enviada. Iniciando limpeza final de popups...")
        if not _limpar_popups_finais(app):
            raise Exception("Falha ao limpar popups de Confirmação/Sucesso.")

        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        # !!!               FIM DA MUDANÇA (Ajuste 2)                !!!
        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

        print("✓✓✓ Importação de Consignado CONCLUÍDA.")
        return True

    except Exception as e:
        print(f"!!! ERRO ao importar consignado: {e} (Tipo: {type(e)})")
        traceback.print_exc()
        return False
