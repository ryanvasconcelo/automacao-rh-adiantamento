# src/rpa_scripts/import_consignado.py (Versão 31.0 - UIA + Busca Flexível Corrigida)

import time
from pywinauto.application import Application, WindowSpecification
from pywinauto import timings
from pywinauto.findwindows import ElementNotFoundError, ElementAmbiguousError
from pywinauto.application import ProcessNotFoundError
from pywinauto.keyboard import send_keys

# --- Configurações ---
FORTES_EXE_PATH = r"C:\Fortes\Fortes\AC.exe"  # Verifique se este caminho está correto
DEFAULT_TIMEOUT = 15

# --- Identificadores ---
LOGIN_WINDOW_TITLE = "Logon"
OK_BUTTON_NAME = "Ok (F9)"
MAIN_WINDOW_TITLE = "Fortes AC 8.17.0.3 - Setor Pessoal"  # Verifique se o título da janela principal é sempre este

# --- Identificadores de Popups ---
# Alvo 1
POPUP_DICAS_TITLE = "Dicas - Versão 8 (Nova Tela)"
POPUP_DICAS_BUTTON = "OK"
# Alvo 2 (Condicional)
POPUP_INTEGRACOES_TITLE = "Controle de Integrações"
POPUP_INTEGRACOES_BUTTON = "Fechar"
# Alvo 2.5 ("Bobo")
POPUP_INTEGRACOES_BOBO_TITLE = "Integração Fortes Pessoal"
POPUP_INTEGRACOES_BOBO_BUTTON = "Fechar"
# Alvo 4 (Notificações)
NOTIFICATION_AREA_CLASSNAME = "TDLNotificationArea"

# --- Filtro (Nosso Alvo Final) ---
FILTER_WINDOW_TITLE = "Filtro"  # Título da janela que deve abrir após a navegação


def login_v14_0(app: Application, username, password, company_code):
    """
    Executa o login robusto (Ordenação Vertical v12.2) com backend UIA.
    """
    print("Aguardando janela de Logon...")
    login_win = app.window(title=LOGIN_WINDOW_TITLE)
    login_win.wait("active", timeout=30)
    login_win.set_focus()
    print("Janela 'Logon' focada. Interagindo por ControlType e Posição Vertical...")

    print("Identificando todos os campos 'Edit' na janela...")
    all_edit_controls = login_win.descendants(control_type="Edit")

    print(
        f"Encontrados {len(all_edit_controls)} campos 'Edit'. Ordenando por posição vertical..."
    )
    sorted_edits = sorted(all_edit_controls, key=lambda ctrl: ctrl.rectangle().top)

    if len(sorted_edits) < 3:
        raise IndexError(
            f"Esperava 3 campos 'Edit' (User, Pass, Empresa), mas encontrei {len(sorted_edits)}"
        )

    print("Inserindo Usuário...")
    sorted_edits[0].set_text(username)

    print("Inserindo Senha...")
    sorted_edits[1].set_text(password)

    print(f"Inserindo Código da Empresa: {company_code}")
    sorted_edits[2].set_text(company_code)

    print("Ignorando 'Subsistema' (confiando no padrão 'Setor Pessoal').")
    time.sleep(1)

    print(f"Procurando botão pelo nome: '{OK_BUTTON_NAME}'...")
    ok_button = login_win.child_window(title=OK_BUTTON_NAME, control_type="Button")
    ok_button.wait("enabled", timeout=5)

    print("Clicando no botão OK...")
    ok_button.click_input()
    print("Login enviado.")


def importar_consignado_rpa(username, password, company_code, competencia_mes_ano):
    """
    Função principal do RPA: Loga (uia), limpa popups, e navega (uia) até o menu.
    """
    app = None
    main_win = None
    app_uia = None
    app_win32 = None
    main_win = None

    try:
        # 1. Iniciar o Fortes AC com UIA (backend que estava funcionando para login)
        print("Iniciando nova instância do Fortes AC...")
        app = Application(backend="uia").start(FORTES_EXE_PATH)

        # 2. Executar Login
        login_v14_0(app, username, password, company_code)

        # 3. Caçada Linear de Popups (mantida a lógica original)
        print("\nIniciando 'Caçada Linear' de popups...")

        # --- Alvo 1: Dicas (Obrigatório) ---
        try:
            print("Caçada Linear: Procurando Alvo 1 ('Dicas')...")
            dicas_popup = app.window(title=POPUP_DICAS_TITLE)
            dicas_popup.wait("visible", timeout=15)
            print("Caçada Linear: Alvo 1 ('Dicas') encontrado. Fechando...")
            dicas_popup.child_window(
                title=POPUP_DICAS_BUTTON, control_type="Button"
            ).click_input()
            dicas_popup.wait_not("visible", timeout=5)
            print("Caçada Linear: Alvo 1 abatido.")
        except (ElementNotFoundError, timings.TimeoutError):
            print("Caçada Linear: Alvo 1 ('Dicas') não apareceu. Continuando...")
            pass

        # --- Alvo 2: Controle de Integrações (Condicional) ---
        try:
            print("Caçada Linear: Procurando Alvo 2 ('Controle de Integrações')...")
            integ_popup = app.window(title=POPUP_INTEGRACOES_TITLE)
            integ_popup.wait("visible", timeout=3)
            print("Caçada Linear: Alvo 2 ('Controle...') encontrado. Fechando...")
            integ_popup.child_window(
                title=POPUP_INTEGRACOES_BUTTON, control_type="Button"
            ).click_input()
            integ_popup.wait_not("visible", timeout=5)
            print("Caçada Linear: Alvo 2 abatido.")
        except (ElementNotFoundError, timings.TimeoutError):
            print("Caçada Linear: Alvo 2 ('Controle...') não apareceu. OK.")
            pass

        # --- Alvo 2.5: Integração Pessoal ("Bobo") ---
        try:
            print("Caçada Linear: Procurando Alvo 2.5 ('Integração Pessoal')...")
            bobo_popup = app.window(title=POPUP_INTEGRACOES_BOBO_TITLE)
            bobo_popup.wait("visible", timeout=3)
            print("Caçada Linear: Alvo 2.5 ('Integração...') encontrado. Fechando...")
            bobo_popup.child_window(
                title=POPUP_INTEGRACOES_BOBO_BUTTON, control_type="Button"
            ).click_input()
            bobo_popup.wait_not("visible", timeout=5)
            print("Caçada Linear: Alvo 2.5 abatido.")
        except (ElementNotFoundError, timings.TimeoutError):
            print("Caçada Linear: Alvo 2.5 ('Integração...') não apareceu. OK.")
            pass

        # --- Alvo 3 (Propaganda) - IGNORADO ---
        print("Caçada Linear: Ignorando Alvo 3 (Propaganda FortesPay).")

        # --- Alvo 4 (Área de Notificações) ---
        try:
            print("Caçada Linear: Procurando Alvo 4 ('Área de Notificações')...")
            if not main_win:
                main_win = app.window(title=MAIN_WINDOW_TITLE)
            main_win.wait("visible", timeout=10)

            notification_area_list = main_win.descendants(
                class_name=NOTIFICATION_AREA_CLASSNAME
            )
            if notification_area_list:
                print("Caçada Linear: Alvo 4 encontrado. Tentando fechar...")
                notification_area = notification_area_list[0]

                # Plano A: Clicar no botão "Fechar" (se existir)
                try:
                    fechar_btn = notification_area.child_window(
                        title="Fechar", control_type="Button"
                    )
                    if fechar_btn.exists(timeout=1):
                        print("Plano A: Botão 'Fechar' encontrado. Clicando...")
                        fechar_btn.click_input()
                        time.sleep(1)
                except:
                    print("Plano A: Botão 'Fechar' não encontrado.")
                    pass

                # Plano B: Tentar ESC (se o Plano A falhou)
                if notification_area.is_visible():
                    print("Plano B: Tentando fechar com ESC...")
                    main_win.set_focus()
                    send_keys("{ESC}")
                    time.sleep(1)

                if notification_area.is_visible():
                    print(
                        "⚠️ AVISO: Alvo 4 (Notificações) ainda visível. Continuando..."
                    )
                else:
                    print("✓ Caçada Linear: Alvo 4 abatido.")
            else:
                print("Caçada Linear: Alvo 4 não apareceu. OK.")
        except (ElementNotFoundError, timings.TimeoutError):
            print("Caçada Linear: Alvo 4 não apareceu. OK.")
            pass

        print("Caçada Linear de popups concluída!\n")

        # 4. Verificar Janela Principal e Focar
        print("Verificando se a Janela Principal está disponível...")
        if not main_win:
            main_win = app.window(title=MAIN_WINDOW_TITLE)

        try:
            main_win.wait("active", timeout=15)
            print("Janela principal está visível e ativa.")
        except timings.TimeoutError as e:
            print(
                f"AVISO: Janela principal não ficou ativa no timeout ({e}). Tentando focar e continuar..."
            )

        main_win.set_focus()
        time.sleep(1)
        print("Janela principal focada.")

        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        # !!!           INÍCIO DA LÓGICA DE NAVEGAÇÃO (v31.0)              !!!
        # !!!           UIA + Busca Flexível Corrigida                     !!!
        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

        # 5. Clicar no Botão Hambúrguer (Menu Principal) por Coordenadas
        print("\n--- PASSO 1: CLIQUE NO BOTÃO HAMBÚRGUER (Coordenadas) ---")
        try:
            main_win.click_input(coords=(25, 25))
            time.sleep(1)
            print("SUCESSO: Botão Hambúrguer clicado.")
        except Exception as e:
            print(f"ERRO ao tentar clicar no botão Hambúrguer: {e}")
            raise
        # ... (código anterior) ...
        # ... (código anterior) ...

        # 6. Encontrar o Container do Menu Principal
        MENU_PRINCIPAL_CLASSNAME = "TUiFinderTreeViewForFiltered"
        print(
            f"\n--- PASSO 2: ENCONTRAR CONTAINER DO MENU ('{MENU_PRINCIPAL_CLASSNAME}') ---"
        )
        try:
            # 6a. USAR app_uia para encontrar o container
            uia_menu_container = main_win.child_window(
                class_name=MENU_PRINCIPAL_CLASSNAME
            )
            uia_menu_container.wait("visible", timeout=5)
            print("SUCESSO: Container do Menu encontrado com UIA.")

            # Pegamos o handle da janela que o UIA encontrou
            menu_container_hwnd = uia_menu_container.handle

            # 6b. CORREÇÃO: Usamos o app_win32 (que já está conectado) para criar a referência WIN32
            # Usando o handle (hwnd) do container que o UIA nos deu.
            win32_menu_container = app_win32.window(handle=menu_container_hwnd)

        except Exception as e:
            print(f"ERRO: Container do Menu não encontrado: {e}")
            raise

        # 7. Navegar: Movimentos
        print("\n--- PASSO 3: CLICAR EM 'MOVIMENTOS' ---")
        try:
            # USANDO O OBJETO WIN32 (win32_menu_container)
            movimentos_item = win32_menu_container.child_window(
                title="MOVIMENTOS", found_index=0
            )
            movimentos_item.click_input()
            time.sleep(0.5)
            print("SUCESSO: 'MOVIMENTOS' clicado e expandido.")
        except Exception as e:
            print(f"ERRO ao clicar em 'MOVIMENTOS': {e}")
            raise

        # ... (Passos 8 e 9 permanecem os mesmos) ...

        # 8. Navegar: Empregados
        print("\n--- PASSO 4: CLICAR EM 'Empregados' ---")
        try:
            # USANDO O NOVO OBJETO WIN32
            empregados_item = win32_menu_container.child_window(
                title="Empregados", found_index=0
            )
            empregados_item.click_input()
            time.sleep(0.5)
            print("SUCESSO: 'Empregados' clicado e expandido.")
        except Exception as e:
            print(f"ERRO ao clicar em 'Empregados': {e}")
            raise

        # 9. Navegar: Consignado - Crédito Trabalhador (Ação Final)
        print("\n--- PASSO 5: CLICAR EM 'Consignado - Crédito do Trab' ---")
        try:
            # USANDO O NOVO OBJETO WIN32
            consignado_item = win32_menu_container.child_window(
                title="Consignado - Crédito do Trab", found_index=0
            )
            consignado_item.click_input()
            print("SUCESSO: 'Consignado - Crédito do Trab' clicado.")
        except Exception as e:
            print(f"ERRO ao clicar em 'Consignado - Crédito do Trab': {e}")
            raise

        # ... (restante do código) ...

        # 10. Aguardar Janela de Filtro (Ponto de Continuação da Automação)
        print(f"\nAguardando janela de '{FILTER_WINDOW_TITLE}' aparecer...")
        filtro_win = app.window(title=FILTER_WINDOW_TITLE)
        filtro_win.wait("active", timeout=15)
        print(f"SUCESSO! Janela de '{FILTER_WINDOW_TITLE}' está ativa.")

        # 11. Sucesso
        print("\n✓ FASE 1 CONCLUÍDA!")
        return True

    except (ElementNotFoundError, ElementAmbiguousError, timings.TimeoutError) as e:
        print(f"\n✗ ERRO DE RPA (v31.0): {e}")
        return False
    except Exception as e:
        print(f"\n✗ ERRO INESPERADO NO RPA (v31.0): {e}")
        import traceback

        traceback.print_exc()
        return False
    finally:
        if app and app.is_process_running():
            print("\nRPA (v31.0) concluído. Mantendo Fortes AC aberto.")


# --- Bloco de Teste Manual ---
if __name__ == "__main__":
    # Substitua com suas credenciais de teste
    teste_user = "RYAN"
    teste_pass = "1234"
    teste_empresa = "9098"
    teste_competencia = "10/25"

    print("=" * 70)
    print("TESTE MANUAL DO RPA (v31.0 - UIA + Busca Flexível Corrigida)")
    print("=" * 70)

    sucesso = importar_consignado_rpa(
        teste_user, teste_pass, teste_empresa, teste_competencia
    )

    print("\n" + "=" * 70)
    if sucesso:
        print("✓ TESTE CONCLUÍDO COM SUCESSO!")
    else:
        print("✗ TESTE FALHOU")
    print("=" * 70)
