# src/rpa_scripts/import_consignado.py (Versão 36.1 - O Teste de "Troca de Empresa")

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
POPUP_SAIR_TITLE = "Confirmação"  # O popup "Sair do sistema?"

# Nossos novos alvos (das suas props)
TROCA_WINDOW_TITLE = "Outra Empresa"
TROCA_WINDOW_CLASS = "TfrmLgAC"


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
    """
    Função principal do RPA (v36.1):
    Testa o fluxo de "Troca de Empresa" usando o "Plano de Busca".
    """
    app_uia = None
    app_win32 = None
    main_win = None

    # --- DADOS DE TESTE PARA TROCA ---
    # Vamos logar na 9098 e tentar trocar para a 9200
    NOVA_EMPRESA_CODIGO = "9200"
    # -----------------------------------

    try:
        # 1. Iniciar o Fortes AC com UIA
        print("Iniciando nova instância do Fortes AC...")
        app_uia = Application(backend="uia").start(FORTES_EXE_PATH)

        # 2. Executar Login
        login_v14_0(
            app_uia, username, password, company_code
        )  # Loga na empresa INICIAL (9098)

        # 3. Caçada de Popups (Plano v36.0 - A Força Bruta {ESC})
        # Esta é a lógica que PROVAMOS que funciona.
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
        except Exception as e:
            print(f"Caçada: Alvo 1 ('Dicas') falhou ou não apareceu. {e}")
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

        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        # !!!   INÍCIO DA NOVA LÓGICA (v36.1) - TROCA DE EMPRESA   !!!
        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

        # 6. Clicar no Botão Hambúrguer
        print("\n--- PASSO 6: CLIQUE NO BOTÃO HAMBÚRGUER ---")
        main_win.click_input(coords=(25, 25))
        time.sleep(1)
        print("✓ Botão Hambúrgger clicado.")

        # 7. Encontrar Container do Menu e Focar
        MENU_PRINCIPAL_CLASSNAME = "TUiFinderTreeViewForFiltered"
        print(f"\n--- PASSO 7: ENCONTRAR E FOCAR NO CONTAINER DO MENU ---")

        uia_menu_container = main_win.child_window(class_name=MENU_PRINCIPAL_CLASSNAME)
        uia_menu_container.wait("visible", timeout=5)
        print("✓ Container do Menu encontrado (UIA). Focando...")
        uia_menu_container.set_focus()
        time.sleep(0.5)

        # 8. Navegar para "Outra Empresa" (O Seu Plano de Busca)
        print("\n--- PASSO 8: NAVEGAÇÃO POR BUSCA (Plano 'Outra Empresa') ---")

        try:
            alvo = "Outra Empresa"
            print(f"Digitando '{alvo}' no campo de busca...")
            send_keys(alvo, with_spaces=True, pause=0.05)
            time.sleep(1)  # Dar 1s para a UI filtrar
            print("Enviando {ENTER} para abrir...")
            send_keys("{ENTER}")
            print("SUCESSO: Navegação por Busca concluída.")

        except Exception as e:
            print(f"!!! ERRO ao tentar navegar por Busca: {e}")
            traceback.print_exc()
            raise

        # 9. Aguardar Janela de Troca (O "Xerife" UIA)
        print(
            f"\n--- PASSO 9: AGUARDANDO JANELA '{TROCA_WINDOW_TITLE}' (via Desktop) ---"
        )

        try:
            # Usar o "Xerife" UIA (que funcionou para o "Filtro" no v38.x)
            desktop = Desktop(backend="uia")
            troca_win = desktop.window(
                title=TROCA_WINDOW_TITLE, class_name=TROCA_WINDOW_CLASS
            )
            troca_win.wait("active", timeout=15)
            troca_win.set_focus()
            print(f"✓ SUCESSO! Janela '{TROCA_WINDOW_TITLE}' está ativa.")

        except Exception as e:
            print(f"!!! ERRO ao esperar ou focar na janela 'Outra Empresa': {e}")
            traceback.print_exc()
            raise

        # 10. Preencher a Troca (O "Foco Cego" com Teclado)
        print("\n--- PASSO 10: PREENCHENDO A TROCA DE EMPRESA ---")
        try:
            # Suas props confirmam que o campo de código já está focado
            print(f"Digitando novo código: {NOVA_EMPRESA_CODIGO} (campo focado)")
            send_keys(NOVA_EMPRESA_CODIGO, with_spaces=True, pause=0.05)
            time.sleep(0.5)

            print("Enviando {ENTER} para confirmar (clicar em 'Ok (F9)')...")
            send_keys("{ENTER}")

            troca_win.wait_not("visible", timeout=10)
            print("✓ Janela de Troca fechada.")

        except Exception as e:
            print(f"!!! ERRO ao preencher a troca: {e}")
            traceback.print_exc()
            raise

        # 11. Limpeza Pós-Troca (Sua Observação Crítica)
        print(
            f"\n--- PASSO 11: LIMPANDO POPUPS PÓS-TROCA (Empresa {NOVA_EMPRESA_CODIGO}) ---"
        )

        print("Aguardando 3s para NOVOS popups carregarem...")
        time.sleep(3)

        try:
            # Re-executar a "Força Bruta {ESC}"
            print("Caçada Pós-Troca: Aplicando 'Força Bruta {ESC}'...")
            main_win.set_focus()
            print("Enviando {ESC} #1 (Alvo: FortesPay)...")
            send_keys("{ESC}")
            time.sleep(1)

            sair_popup = app_uia.window(title=POPUP_SAIR_TITLE)
            if sair_popup.exists(timeout=0.5):
                print("Caçada Pós-Troca: Popup 'Sair?' apareceu. Clicando 'Não'...")
                sair_popup.child_window(
                    title="Não", control_type="Button"
                ).click_input()
            else:
                print("Enviando {ESC} #2 (Alvo: Integração)...")
                main_win.set_focus()
                send_keys("{ESC}")
                time.sleep(1)

            main_win.wait("active", timeout=10)
            print("✓ Popups Pós-Troca limpos. Nova empresa está ativa.")

        except Exception as e:
            print(f"!!! ERRO na Limpeza Pós-Troca: {e}")
            pass

        # 12. Sucesso
        print("\n✓✓✓ TESTE DE TROCA DE EMPRESA CONCLUÍDO COM SUCESSO! ✓✓✓")
        return True

    except (ElementNotFoundError, ElementAmbiguousError, timings.TimeoutError) as e:
        print(f"\n✗ ERRO DE RPA (v36.1): {e}")
        return False
    except Exception as e:
        print(f"\n✗ ERRO INESPERADO NO RPA (v36.1): {e}")
        # Não imprimir o traceback inteiro se for a nossa parada forçada
        if "PARADA FORÇADA" not in str(e):
            traceback.print_exc()
        return False
    finally:
        if app_uia and app_uia.is_process_running():
            print("\nRPA (v36.1) concluído. Mantendo Fortes AC aberto.")


if __name__ == "__main__":
    teste_user = "RYAN"
    teste_pass = "1234"
    teste_empresa = "9098"  # Empresa inicial
    teste_competencia = "10/25"

    print("Iniciando teste em 3 segundos... Mude para a máquina Windows agora.")
    time.sleep(3)

    print("=" * 70)
    print("TESTE MANUAL DO RPA (v36.1 - O Teste de 'Troca de Empresa')")
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
