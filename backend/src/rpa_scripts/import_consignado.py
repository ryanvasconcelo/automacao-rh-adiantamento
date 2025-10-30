# src/rpa_scripts/import_consignado.py (Versão 23.0 - Produção Limpa)

import time
from pywinauto.application import Application, WindowSpecification
from pywinauto import timings
from pywinauto.findwindows import ElementNotFoundError, ElementAmbiguousError
from pywinauto.application import ProcessNotFoundError
from pywinauto.keyboard import send_keys

# --- Configurações ---
FORTES_EXE_PATH = r"C:\Fortes\Fortes\AC.exe"
DEFAULT_TIMEOUT = 15

# --- Identificadores ---
LOGIN_WINDOW_TITLE = "Logon"
OK_BUTTON_NAME = "Ok (F9)"
MAIN_WINDOW_TITLE = "Fortes AC 8.17.0.3 - Setor Pessoal"

# --- Identificadores de Popups ---
POPUP_DICAS_TITLE = "Dicas - Versão 8 (Nova Tela)"
POPUP_DICAS_BUTTON = "OK"
POPUP_INTEGRACOES_TITLE = "Controle de Integrações"
POPUP_INTEGRACOES_BUTTON = "Fechar"
POPUP_INTEGRACOES_BOBO_TITLE = "Integração Fortes Pessoal"
POPUP_INTEGRACOES_BOBO_BUTTON = "Fechar"
POPUP_SAIR_SISTEMA_TITLE = "Confirmação"
POPUP_PROPAGANDA_CLASSNAME = "TDLPanel"

# --- Filtro ---
FILTER_WINDOW_TITLE = "Filtro"


def login_v14_0(app: Application, username, password, company_code):
    """Executa o login robusto (Ordenação Vertical)"""
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
        raise IndexError(f"Esperava 3 campos 'Edit', mas encontrei {len(sorted_edits)}")

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


def navigate_text_menu_v14_1(main_win: WindowSpecification):
    """Navega no 'Menu' lateral clicando nos itens de TEXTO."""
    print("Iniciando navegação no Menu de Texto...")
    try:
        # Etapa 1: Clicar em MOVIMENTOS
        print("Procurando 'MOVIMENTOS'...")
        mov_item = main_win.child_window(title="MOVIMENTOS", control_type="Text")
        mov_item.wait("visible", timeout=10)
        mov_item.click_input()
        print("Clicou em 'MOVIMENTOS'.")
        time.sleep(0.5)

        # Etapa 2: Clicar em Empregados
        print("Procurando 'Empregados'...")
        emp_item = main_win.child_window(title="Empregados", control_type="Text")
        emp_item.wait("visible", timeout=10)
        emp_item.click_input()
        print("Clicou em 'Empregados'.")
        time.sleep(0.5)

        # Etapa 3: Duplo-clique em Consignado
        print("Procurando 'Consignado - Crédito Trabalhador'...")
        consignado_item = main_win.child_window(
            title="Consignado - Crédito Trabalhador", control_type="Text"
        )
        consignado_item.wait("visible", timeout=10)
        print("Item final encontrado. Executando Double-Click...")
        consignado_item.double_click_input()

        print("Navegação no menu de texto concluída.")

    except (ElementNotFoundError, timings.TimeoutError) as e:
        print(f"ERRO DE NAVEGAÇÃO: Não foi possível encontrar um item do menu: {e}")
        raise
    except Exception as e:
        print(f"ERRO INESPERADO NA NAVEGAÇÃO: {e}")
        raise


def importar_consignado_rpa(username, password, company_code, competencia_mes_ano):
    app = None
    main_win = None

    try:
        # 1. Iniciar o Fortes AC
        print("Iniciando nova instância do Fortes AC...")
        app = Application(backend="uia").start(FORTES_EXE_PATH)

        # 2. Executar Login
        login_v14_0(app, username, password, company_code)

        # 3. Caçada Linear de Popups
        print("\nIniciando 'Caçada Linear' de popups...")

        # --- Alvo 1: Dicas ---
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

        # --- Alvo 2: Controle de Integrações ---
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

        # --- Alvo 2.5: Integração Pessoal ---
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

        print("Caçada Linear: Ignorando Alvo 3 (não é um popup a ser fechado).")

        # --- Alvo 4: Área de Notificações ---
        try:
            print("Caçada Linear: Procurando Alvo 4 ('Área de Notificações')...")

            if not main_win:
                main_win = app.window(title=MAIN_WINDOW_TITLE)
            main_win.wait("visible", timeout=10)

            notification_area = main_win.child_window(class_name="TDLNotificationArea")

            if notification_area.exists(timeout=3):
                print("Caçada Linear: Alvo 4 (Área de Notificações) encontrada.")
                print("Tentando fechar a área de notificações...")

                # Procurar botão "Fechar"
                try:
                    print("Procurando botão 'Fechar' na interface...")
                    fechar_btn = main_win.child_window(
                        title="Fechar", control_type="Button"
                    )
                    if fechar_btn.exists(timeout=2):
                        print("Botão 'Fechar' encontrado! Clicando...")
                        fechar_btn.click_input()
                        time.sleep(1)
                        if not notification_area.exists(timeout=1):
                            print(
                                "✓ Caçada Linear: Alvo 4 abatido (via botão 'Fechar')!"
                            )
                except Exception as e:
                    print(f"Erro ao procurar botão 'Fechar': {e}")

                # Tentar ESC múltiplas vezes
                if notification_area.exists(timeout=1):
                    print("Tentando fechar com ESC (3 tentativas)...")
                    for i in range(3):
                        try:
                            send_keys("{ESC}")
                            time.sleep(0.5)
                            if not notification_area.exists(timeout=1):
                                print(
                                    f"✓ Caçada Linear: Alvo 4 abatido (via ESC na tentativa {i+1})."
                                )
                                break
                        except Exception as e:
                            print(f"Erro com ESC na tentativa {i+1}: {e}")

                if notification_area.exists(timeout=1):
                    print(
                        "⚠️ AVISO: Área de notificações AINDA VISÍVEL. Tentando continuar..."
                    )
                else:
                    print("✓ Área de notificações fechada com sucesso!")

            else:
                print("Caçada Linear: Alvo 4 não apareceu. OK.")

        except (ElementNotFoundError, timings.TimeoutError):
            print("Caçada Linear: Alvo 4 não apareceu. OK.")

        # --- Alvo 4.5: Popup Confirmação (Loop) ---
        for tentativa in range(3):
            try:
                print(
                    f"Caçada Linear: Procurando Alvo 4.5 ('Sair do sistema?') - tentativa {tentativa + 1}..."
                )
                confirmacao_popup = app.window(title=POPUP_SAIR_SISTEMA_TITLE)

                if confirmacao_popup.exists(timeout=2):
                    print(
                        f"Caçada Linear: Alvo 4.5 DETECTADO (tentativa {tentativa + 1})!"
                    )
                    nao_button = confirmacao_popup.child_window(
                        title_re=".*[Nn]ão.*", control_type="Button"
                    )

                    if nao_button.exists(timeout=2):
                        print("Botão 'Não' encontrado. Clicando...")
                        nao_button.click_input()
                        time.sleep(1)
                        print(
                            f"Caçada Linear: Alvo 4.5 abatido (tentativa {tentativa + 1})."
                        )
                    else:
                        confirmacao_popup.type_keys("{ESC}")
                        time.sleep(1)
                else:
                    print(
                        f"Caçada Linear: Nenhum popup de confirmação na tentativa {tentativa + 1}."
                    )
                    break

            except (ElementNotFoundError, timings.TimeoutError):
                print(
                    f"Caçada Linear: Alvo 4.5 não apareceu na tentativa {tentativa + 1}."
                )
                break

        # --- Alvo 5: Propaganda Fortes Pay ---
        try:
            print("Caçada Linear: Procurando Alvo 5 ('Propaganda Fortes Pay')...")

            # Estratégia A: Janela independente
            all_windows = app.windows()
            for win in all_windows:
                try:
                    if win.window_text() == MAIN_WINDOW_TITLE:
                        continue
                    if win.class_name() == "TDLPanel" and win.is_visible():
                        rect = win.rectangle()
                        width = rect.right - rect.left
                        height = rect.bottom - rect.top

                        if 400 < width < 800 and 250 < height < 600:
                            print(
                                f"    -> Possível propaganda encontrada! Tentando fechar..."
                            )
                            try:
                                win.type_keys("{ESC}")
                                time.sleep(1)
                            except:
                                pass
                            break
                except:
                    continue

            print("Caçada Linear: Processamento do Alvo 5 concluído.")

        except Exception as e:
            print(f"Caçada Linear: Erro ao processar Alvo 5: {e}")

        print("Caçada Linear de popups concluída!\n")

        # 4. Verificar Janela Principal
        print("Verificando se a Janela Principal está disponível...")
        if not main_win:
            main_win = app.window(title=MAIN_WINDOW_TITLE)

        try:
            main_win.wait("visible", timeout=15)
            print("Janela principal está visível.")
        except timings.TimeoutError:
            print(
                "AVISO: Janela principal não ficou visível no timeout. Tentando continuar..."
            )

        try:
            main_win.set_focus()
            time.sleep(1)
            print("Janela principal focada.")
        except Exception as e:
            print(f"AVISO: Não foi possível focar a janela principal: {e}")

        # 5. Navegar no Menu
        print("\n--- INICIANDO NAVEGAÇÃO NO MENU ---")

        # INSPEÇÃO TEMPORÁRIA: Ver estrutura do menu
        print("INSPEÇÃO: Procurando TreeView do menu...")
        try:
            tree_view = main_win.child_window(class_name="TUiTreeViewScroller")
            if tree_view.exists(timeout=3):
                print("TreeView encontrado!")

                # Procurar TreeItems
                tree_items = tree_view.descendants(control_type="TreeItem")
                print(f"Total de TreeItems encontrados: {len(tree_items)}")

                print("\nPrimeiros 20 TreeItems:")
                for i, item in enumerate(tree_items[:20]):
                    try:
                        name = item.window_text()
                        visible = item.is_visible()
                        rect = item.rectangle()
                        print(
                            f"  TreeItem[{i}]: '{name}' | Visible: {visible} | Rect: {rect}"
                        )
                    except Exception as e:
                        print(f"  TreeItem[{i}]: erro - {e}")

                # Também procurar por Text dentro do TreeView
                text_controls = tree_view.descendants(control_type="Text")
                print(
                    f"\nTotal de controles 'Text' dentro do TreeView: {len(text_controls)}"
                )

                for i, txt in enumerate(text_controls[:20]):
                    try:
                        name = txt.window_text()
                        visible = txt.is_visible()
                        print(f"  Text[{i}]: '{name}' | Visible: {visible}")
                    except:
                        pass
            else:
                print("TreeView NÃO encontrado!")
        except Exception as e:
            print(f"Erro na inspeção: {e}")

        print("\n--- FIM DA INSPEÇÃO ---")
        print("PARANDO AQUI. Copie as informações acima.")
        return False

        # navigate_text_menu_v14_1(main_win)

        # 6. Aguardar Janela de Filtro
        print(f"\nAguardando janela de '{FILTER_WINDOW_TITLE}' aparecer...")
        filtro_win = app.window(title=FILTER_WINDOW_TITLE)
        filtro_win.wait("active", timeout=15)
        print(f"SUCESSO! Janela de '{FILTER_WINDOW_TITLE}' está ativa.")
        print("AVISO: Preenchimento do filtro ainda não implementado.")

        # 7. Sucesso
        print("\n✓ Navegação concluída com sucesso!")
        return True

    except (ElementNotFoundError, ElementAmbiguousError, timings.TimeoutError) as e:
        print(f"\n✗ ERRO DE RPA (v23.0): {e}")
        return False
    except Exception as e:
        print(f"\n✗ ERRO INESPERADO NO RPA (v23.0): {e}")
        import traceback

        traceback.print_exc()
        return False
    finally:
        if app and app.is_process_running():
            print("\nRPA (v23.0) concluído. Mantendo Fortes AC aberto.")


if __name__ == "__main__":
    teste_user = "RYAN"
    teste_pass = "1234"
    teste_empresa = "9098"
    teste_competencia = "10/2025"

    print("=" * 70)
    print("TESTE MANUAL DO RPA (v23.0 - Produção Limpa)")
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
