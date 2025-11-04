# teste_rpa_core.py
# Este script é um "Teste de Integração" para o nosso Músculo.
# Ele prova que todas as funções do rpa_core funcionam juntas.

import time
import rpa_core  # Importa nossa nova "Caixa de Ferramentas"

# --- CONFIGURAÇÕES DE TESTE ---
# (Coloque seus dados de login reais aqui)
TESTE_USER = "RYAN"
TESTE_PASS = "1234"
TESTE_EMPRESA_INICIAL = "9098"  # [Baseado no switch_company.py]
TESTE_EMPRESA_SEGUNDA = "9213"  # [Baseado no switch_company.py]
TESTE_COMPETENCIA = "11/2025"  # [Baseado no import_consignado.py]


def run_integration_test():
    app_session = None
    main_win_session = None

    print("=" * 70)
    print("INICIANDO TESTE DE INTEGRAÇÃO DO RPA CORE")
    print("=" * 70)

    try:
        # --- Teste da Função 1: iniciar_sessao_fortes ---
        print("\n--- TESTANDO: Função 1 (iniciar_sessao_fortes)... ---")
        app_session, main_win_session = rpa_core.iniciar_sessao_fortes(
            TESTE_USER, TESTE_PASS, TESTE_EMPRESA_INICIAL
        )
        if app_session is None or main_win_session is None:
            raise Exception("Falha ao iniciar a sessão. Teste abortado.")
        print("✓ SUCESSO: Sessão iniciada.")

        # --- Teste da Função 2: limpar_popups_iniciais ---
        print("\n--- TESTANDO: Função 2 (limpar_popups_iniciais)... ---")
        if not rpa_core.limpar_popups_iniciais(app_session, main_win_session):
            raise Exception("Falha ao limpar popups. Teste abortado.")
        print("✓ SUCESSO: Popups limpos.")

        # --- Teste da Função 3: trocar_empresa ---
        print("\n--- TESTANDO: Função 3 (trocar_empresa)... ---")
        if not rpa_core.trocar_empresa(
            app_session, main_win_session, TESTE_EMPRESA_SEGUNDA
        ):
            raise Exception("Falha ao trocar de empresa. Teste abortado.")
        print(f"✓ SUCESSO: Trocado para empresa {TESTE_EMPRESA_SEGUNDA}.")

        # --- Teste da Função 4: importar_consignado_empresa_ativa ---
        print("\n--- TESTANDO: Função 4 (importar_consignado_empresa_ativa)... ---")
        if not rpa_core.importar_consignado_empresa_ativa(
            main_win_session, TESTE_COMPETENCIA, TESTE_EMPRESA_SEGUNDA
        ):
            raise Exception("Falha ao importar consignado. Teste abortado.")
        print("✓ SUCESSO: Importação de consignado concluída.")

        print("\n" + "=" * 70)
        print("✓✓✓ TESTE DE INTEGRAÇÃO CONCLUÍDO COM SUCESSO! ✓✓✓")
        print("=" * 70)

    except Exception as e:
        print("\n" + "!" * 70)
        print(f"✗✗✗ TESTE FALHOU: {e}")
        print("!" * 70)

    finally:
        # Limpeza: Fecha o Fortes AC não importa o que aconteça
        if app_session and app_session.is_process_running():
            print("\nFinalizando sessão do Fortes AC...")
            app_session.kill()
        print("Teste finalizado.")


# --- Ponto de Entrada Padrão do Python ---
if __name__ == "__main__":
    print("Iniciando teste de integração em 3 segundos...")
    print("Por favor, não mexa no mouse ou teclado.")
    time.sleep(3)
    run_integration_test()
