# esse modulo do projeto visa garantir a tipagem correta dos dados, visando assim, que os dados da tabela requisitada estejam de acordo com o esperado pelo codigo, evitando assim erros de calculo ou processamento causado por tipo de dados incorretos, para fazer isso usamos o pydantic, ele é um molde de como a tabela deve ser, e o pydantic valida se os dados estao de acordo com o molde, caso nao estejam, ele gera um erro, que pode ser tratado pelo codigo

# src/data_validation.py

import pandas as pd
from pydantic import BaseModel, ValidationError, field_validator
from typing import Optional, Any
from datetime import date
from config.logging_config import log


class EmployeeModel(BaseModel):
    # Definimos nosso modelo de dados exatamente como antes.
    Matricula: str
    Nome: str
    AdmissaoData: Optional[date] = None
    DtRescisao: Optional[date] = None
    SalarioContratual: Optional[float] = None
    FlagAdiantamento: Optional[str] = None
    PercentualAdiant: Optional[float] = None
    ValorFixoAdiant: Optional[float] = None
    Cargo: Optional[str] = None
    DataInicioAfastamento: Optional[date] = None
    DataFimAfastamento: Optional[date] = None
    CodigoTipoLicenca: Optional[str] = None

    def clean_nan_values(cls, v: Any):
        """Converte qualquer valor 'nan' (float) em None."""
        # Se o valor for um float e for 'nan', ele se torna None.
        if isinstance(v, float) and pd.isna(v):
            return None
        # Para todos os outros casos, o valor original é mantido.
        return v


def validate_employee_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Valida cada linha do DataFrame. Se uma linha falhar, ela é marcada como
    inelegível e o erro é logado, sem quebrar o programa.
    """
    log.info("Iniciando validação da estrutura dos dados...")

    if "Status" not in df.columns:
        df["Status"] = ""
    if "Observacoes" not in df.columns:
        df["Observacoes"] = ""

    validated_rows = []
    for index, row in df.iterrows():
        row_data = row.to_dict()
        try:
            # Agora a validação está protegida pelo nosso validador universal.
            EmployeeModel(**row_data)
            validated_rows.append(row)
        except ValidationError as e:
            # Mantemos o log de erro para o caso de problemas de formato real.
            log.error(
                f"Erro de validação na Matrícula {row_data.get('Matricula', 'N/A')}: {e}"
            )
            row["Status"] = "Inelegível"
            row["Observacoes"] += "Dados com formato inválido (ValidationError); "
            validated_rows.append(row)
            continue

    log.success("Validação de dados concluída.")
    if not validated_rows:
        return pd.DataFrame(columns=df.columns)
    return pd.DataFrame(validated_rows)
