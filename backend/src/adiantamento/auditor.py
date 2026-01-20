# Este arquivo substitui o antigo 'business_logic.py' para uso na WEB
from src.shared.utils import safe_decimal
from datetime import datetime


class AdiantamentoAuditor:
    def processar_folha(self, dados_sql: list):
        divergencias = []

        for row in dados_sql:
            # 1. Sanitização (Blindagem)
            salario = safe_decimal(row.get("Salario_Bruto"))
            dias_trabalhados = safe_decimal(row.get("Dias_Trabalhados"))

            # 2. Lógica de Negócio (Replicar a lógica do business_logic.py aqui)
            # Exemplo hipotético de regra de adiantamento (40%):
            proventos_esperados = salario * Decimal("0.40")

            # ... lógica de comparação ...

        return divergencias
