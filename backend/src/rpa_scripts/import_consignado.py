# src/rpa_scripts/import_consignado.py (Versão 38.5 - O Xerife Win32)

import time
import os
import traceback

try:
    import pyautogui
except ImportError:
    print("ERRO: Biblioteca 'pyautogui' não encontrada.")
    exit()

from pywinauto.application import Application, WindowSpecification
from pywinauto import timings
from pywinauto.findwindows import ElementNotFoundError, ElementAmbiguousError
from pywinauto.application import ProcessNotFoundError
from pywinauto.keyboard import send_keys
from pywinauto import Desktop
from pywinauto import mouse

# --- Configurações ---
FORTES_EXE_PATH = r"C:\Fortes\Fortes\AC.exe"
DEFAULT_TIMEOUT = 15

# --- Identificadores ---
LOGIN_WINDOW_TITLE = "Logon"
OK_BUTTON_NAME = "Ok (F9)"
MAIN_WINDOW_TITLE = "Fortes AC 8.17.1.1 - Setor Pessoal"
POPUP_DICAS_TITLE = "Dicas - Versão 8 (Nova Tela)"
POPUP_SAIR_TITLE = "Confirmação"
POPUP_INTEGRACAO_TITLE = "Integração Fortes Pessoal"

# Nossos alvos principais
FILTER_WINDOW_TITLE = "Filtro de Consignado"
CONSIGNADO_WINDOW_TITLE = "Consignado - Crédito do Trabalhador"
# NOVOS ALVOS (das suas props v38.2)
PANEL_WINDOW_TITLE = "Painel Consignado - Crédito do Trabalhador"
PANEL_WINDOW_CLASS = "TfrmFrPainelConsignadoCreditoTrabalhador"
PANEL_BUTTON_NAME_REGEX = ".*Painel.*Consignado.*"
PANEL_COLETAR_BUTTON = "Coletar"


def login_v14_0(app: Application, username, password, company_code):
    """Executa o login robusto (Ordenação Vertical)"""
    print("Aguardando janela de Logon...")
    login_win = app.window(title=LOGIN_WINDOW_TITLE)
    login_win.wait("active", timeout=30)
    login_win.set_focus()
    print("Janela 'Logon' focada. Interagindo por ControlType e Posição Vertical...")

    all_edit_controls = login_win.descendants(control_type="Edit")
    sorted_edits = sorted(all_edit_controls, key=lambda ctrl: ctrl.rectangle().top)
    if len(sorted_edits) < 3:
        raise IndexError(f"Esperava 3 campos 'Edit', mas encontrei {len(sorted_edits)}")

    sorted_edits[0].set_text(username)
    sorted_edits[1].set_text(password)
    sorted_edits[2].set_text(company_code)
    time.sleep(1)
    ok_button = login_win.child_window(title=OK_BUTTON_NAME, control_type="Button")
    ok_button.wait("enabled", timeout=5)
    ok_button.click_input()
    print("Login enviado.")


def importar_consignado_rpa(username, password, company_code, competencia_mes_ano):
    """Função principal do RPA: Login, popups, navegação"""
    app_uia = None
    app_win32 = None
    main_win = None
    filtro_win = None
    consignado_win = None
    panel_win = None  # Variavel para a janela Painel

    try:
        # 1. Iniciar o Fortes AC com UIA
        print("Iniciando nova instância do Fortes AC...")
        app_uia = Application(backend="uia").start(FORTES_EXE_PATH)

        # 2. Executar Login
        login_v14_0(app_uia, username, password, company_code)

        # 3. Caçada de Popups (Plano v36.0 - A Força Bruta {ESC})
        print("\nIniciando 'Caçada Linear' de popups...")

        print("Aguardando 3s para TODOS os popups carregarem...")
        time.sleep(3)

        main_win_spec = app_uia.window(title=MAIN_WINDOW_TITLE)
        dicas_spec = app_uia.window(title=POPUP_DICAS_TITLE)

        try:
            if dicas_spec.exists(timeout=1):
                print("Caçada: Alvo 1 ('Dicas') encontrado. Fechando com {ESC}...")
                dicas_spec.set_focus()
                send_keys("{ESC}")
                time.sleep(0.5)
        except Exception:
            print(f"Caçada: Alvo 1 ('Dicas') não apareceu.")
            pass

        try:
            print("Caçada: Aplicando 'Força Bruta {ESC}' na Janela Principal...")
            main_win_spec.set_focus()
            print("Enviando {ESC} #1 (Alvo: FortesPay)...")
            send_keys("{ESC}")
            time.sleep(1)

            sair_popup = app_uia.window(title=POPUP_SAIR_TITLE)
            if sair_popup.exists(timeout=0.5):
                print("Caçada: Popup 'Sair?' apareceu. Clicando em 'Não'...")
                sair_popup.child_window(
                    title="Não", control_type="Button"
                ).click_input()
            else:
                print("Enviando {ESC} #2 (Alvo: Integração)...")
                main_win_spec.set_focus()
                send_keys("{ESC}")
                time.sleep(1)

        except Exception as e:
            print(f"!!! ERRO na Força Bruta {ESC}: {e}")
            pass

        print("Caçada Linear de popups concluída!\n")
        # --- FIM DO PASSO 3 ---

        # 4. Pegar Janela Principal (VERSÃO ROBUSTA "PLANO G")
        print("Verificando Janela Principal...")
        main_win = main_win_spec

        print(f"Aguardando '{MAIN_WINDOW_TITLE}' ficar VISÍVEL (timeout 30s)...")
        main_win.wait("visible", timeout=30)
        print("Janela principal está VISÍVEL.")

        main_win.set_focus()
        time.sleep(1)

        main_win.wait("active", timeout=5)
        print("Janela principal está FOCADA e ATIVA.")
        # --- FIM DO PASSO 4 ---

        # 5. CONECTAR win32
        print("\n--- PASSO 5: CONECTANDO backend win32 ---")
        pid = app_uia.process
        app_win32 = Application(backend="win32").connect(process=pid)
        print("✓ Backend 'win32' conectado com sucesso!")

        # 6. Clicar no Botão Hambúrguer
        print("\n--- PASSO 6: CLIQUE NO BOTÃO HAMBÚRGUER ---")
        main_win.click_input(coords=(25, 25))
        time.sleep(1)
        print("✓ Botão Hambúrgger clicado.")

        # 7. Encontrar Container do Menu
        MENU_PRINCIPAL_CLASSNAME = "TUiFinderTreeViewForFiltered"
        print(f"\n--- PASSO 7: ENCONTRAR E FOCAR NO CONTAINER DO MENU ---")

        uia_menu_container = main_win.child_window(class_name=MENU_PRINCIPAL_CLASSNAME)
        uia_menu_container.wait("visible", timeout=5)
        print("✓ Container do Menu encontrado (UIA). Focando...")
        uia_menu_container.set_focus()
        time.sleep(0.5)

        # 8, 9, 10. Navegar no Menu (Plano B - "Navegação por Busca")
        print("\n--- PASSO 8, 9, 10 (Navegação por Busca) ---")

        try:
            alvo = "Consignado - Crédito do Tr"
            print(f"Digitando '{alvo}' no campo de busca...")
            send_keys(alvo, with_spaces=True, pause=0.05)
            time.sleep(1)
            print("Enviando {ENTER} para abrir...")
            send_keys("{ENTER}")
            print("SUCESSO: Navegação por Busca concluída.")

        except Exception as e:
            print(f"!!! ERRO ao tentar navegar por Busca: {e}")
            traceback.print_exc()
            raise

        # 11. Aguardar Janela de Filtro (Plano F - "Xerife" com Título Correto)
        print(
            f"\n--- PASSO 11: AGUARDANDO JANELA '{FILTER_WINDOW_TITLE}' (via Desktop) ---"
        )

        try:
            desktop = Desktop(backend="uia")
            filtro_win = desktop.window(
                title=FILTER_WINDOW_TITLE, class_name="TfrmDgFiltroCOT_COE"
            )
            filtro_win.wait("active", timeout=15)
            filtro_win.set_focus()
            print(f"✓ SUCESSO! Janela '{FILTER_WINDOW_TITLE}' está ativa.")

        except Exception as e:
            print(f"!!! ERRO ao esperar ou focar na janela 'Filtro': {e}")
            traceback.print_exc()
            raise

        # 12. Preencher o Filtro (Plano F - "Seletores Exatos")
        print("\n--- PASSO 12: PREENCHENDO O FILTRO (Seletores Exatos) ---")
        try:
            print("Localizando campo 'Competência' (o 1º campo 'Edit' por posição)...")
            all_edits = filtro_win.descendants(control_type="Edit")
            if not all_edits:
                raise Exception("Nenhum campo 'Edit' encontrado no filtro.")

            sorted_edits = sorted(all_edits, key=lambda ctrl: ctrl.rectangle().top)
            competencia_field = sorted_edits[0]

            print(f"Digitando competência: {competencia_mes_ano}")
            competencia_field.set_text(competencia_mes_ano)
            time.sleep(0.5)

            print("Localizando botão 'Ok (F9)' pelo nome e classe...")
            ok_button = filtro_win.child_window(title="Ok (F9)", class_name="TDLBitBtn")
            ok_button.wait("enabled", timeout=5)

            print("Enviando clique para 'Ok (F9)'...")
            ok_button.click_input()

            filtro_win.wait_not("visible", timeout=10)
            print("✓ Filtro aplicado e janela fechada.")

        except Exception as e:
            print(f"!!! ERRO ao preencher o filtro com seletores exatos: {e}")
            traceback.print_exc()
            raise

        # 13. Aguardar Resultado (CORREÇÃO v38.1)
        print(
            f"\n--- PASSO 13: AGUARDANDO CONTROLE DE RESULTADO '{CONSIGNADO_WINDOW_TITLE}' ---"
        )

        try:
            consignado_win = main_win.child_window(title=CONSIGNADO_WINDOW_TITLE)
            consignado_win.wait("visible", timeout=15)
            main_win.set_focus()
            print("✓ SUCESSO! Janela de consignados está populada.")

        except Exception as e:
            print(f"!!! ERRO ao aguardar o controle de resultado: {e}")
            traceback.print_exc()
            raise

        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        # !!!   INÍCIO DO PASSO FINAL (v38.5) - O XERIFE WIN32    !!!
        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

        # 14. Clicar no Botão "Painel Consignado"
        print(f"\n--- PASSO 14: CLICANDO EM 'Painel Consignado' ---")
        try:
            panel_button = consignado_win.child_window(
                title_re=PANEL_BUTTON_NAME_REGEX, class_name="TDLBitBtn"
            )
            panel_button.wait("enabled", timeout=5)
            panel_button.click_input()
            print("✓ Botão 'Painel Consignado' clicado.")
            time.sleep(1.5)  # Pausa para a nova janela "nascer"
        except Exception as e:
            print(f"!!! ERRO ao clicar em 'Painel Consignado': {e}")
            traceback.print_exc()
            raise

        # 16. Preencher Painel de Importação (CORREÇÃO v38.5 - Teclado)
        print("\n--- PASSO 16: PREENCHENDO O PAINEL DE IMPORTAÇÃO (Teclado) ---")
        try:
            print("Enviando {TAB} para pular para 'Empresa'...")
            send_keys("{TAB}")
            time.sleep(0.5)

            print("Enviando {TAB} para pular para 'Empresa'...")
            send_keys("{TAB}")
            time.sleep(0.5)

            # Suas props confirmam que 'Competência' é o primeiro campo em foco
            print(f"Digitando competência: {competencia_mes_ano} (campo focado)")
            send_keys(competencia_mes_ano, with_spaces=True, pause=0.05)
            time.sleep(0.5)

            print("Enviando {TAB} para pular para 'Empresa'...")
            send_keys("{TAB}")
            time.sleep(0.5)

            print(f"Digitando empresa: {company_code}")
            send_keys(company_code, with_spaces=True, pause=0.05)
            time.sleep(0.5)
            print("✓ Campos 'Competência' e 'Empresa' preenchidos.")
        except Exception as e:
            print(f"!!! ERRO ao preencher os campos do painel com teclado: {e}")
            traceback.print_exc()
            raise

        send_keys("{TAB}")
        time.sleep(0.5)

        send_keys("{ENTER}")
        time.sleep(0.5)

        # 18. Sucesso Final
        print("\n✓✓✓ FASE FINAL CONCLUÍDA COM SUCESSO! ✓✓✓")
        return True

    except (ElementNotFoundError, ElementAmbiguousError, timings.TimeoutError) as e:
        print(f"\n✗ ERRO DE RPA (v38.5): {e}")
        return False
    except Exception as e:
        print(f"\n✗ ERRO INESPERADO NO RPA (v38.5): {e}")
        # Não imprimir o traceback inteiro se for a nossa parada forçada
        if "PARADA FORÇADA" not in str(e):
            traceback.print_exc()
        return False
    finally:
        if app_uia and app_uia.is_process_running():
            print("\nRPA (v38.5) concluído. Mantendo Fortes AC aberto.")


if __name__ == "__main__":
    teste_user = "RYAN"
    teste_pass = "1234"
    teste_empresa = "9213"
    teste_competencia = "11/25"  # Esta variável agora será usada em DOIS lugares

    print("Iniciando teste em 3 segundos... Mude para a máquina Windows agora.")
    time.sleep(3)

    print("=" * 70)
    print("TESTE MANUAL DO RPA (v38.5 - O Xerife Win32)")
    print("=" * 70)

    sucesso = importar_consignado_rpa(
        teste_user, teste_pass, teste_empresa, teste_competencia
    )

    print("\n" + "=" * 70)
    if sucesso:
        print("✓✓✓ TESTE CONCLÍDO COM SUCESSO! ✓✓✓")
    else:
        print("✗ TESTE FALHOU")
    print("=" * 70)
