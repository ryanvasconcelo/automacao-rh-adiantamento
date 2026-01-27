#!/usr/bin/env python3
"""
Debug: Comparar fontes de dados
- O que data_fetcher.fetch_payroll_data traz?
- O que map_table traz da FOLHA 2?
"""

import sys
import os
from decimal import Decimal

sys.path.append(os.getcwd())

try:
    from src.database import get_connection
    from src.fopag import data_fetcher
except ImportError:
    sys.path.append(os.path.join(os.getcwd(), "backend"))
    from src.database import get_connection
    from src.fopag import data_fetcher


def D(valor):
    if valor is None:
        return Decimal("0.00")
    return Decimal(str(valor))


def fmt(val):
    return f"{val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def main():
    print("\n" + "="*120)
    print("🔍 COMPARAÇÃO DE FONTES DE DADOS")
    print("="*120)
    
    # Alvos
    alvos = ["000093", "000287"]
    
    # 1. O que data_fetcher traz?
    print("\n📦 FONTE 1: data_fetcher.fetch_payroll_data() [FPG.Tipo IN (1,4)]")
    print("-" * 120)
    
    empresa_codigo = "9189"
    folha_seq = data_fetcher.get_folha_id(empresa_codigo, mes=9, ano=2025)
    print(f"Folha Seq: {folha_seq}")
    
    if folha_seq:
        dados = data_fetcher.fetch_payroll_data(empresa_codigo, folha_seq)
        for func in dados:
            if func["matricula"] in alvos:
                print(f"\n👤 {func['nome']} ({func['matricula']})")
                base_inss_data_fetcher = Decimal("0")
                base_irrf_data_fetcher = Decimal("0")
                
                for evt in func["eventos"]:
                    cod = evt["codigo"]
                    val = D(evt["valor"])
                    inc_inss = evt["incidencias"]["inss"]
                    inc_irrf = evt["incidencias"]["irrf"]
                    
                    print(f"  {cod:5} {evt['descricao']:30} R$ {fmt(val):>10} INSS={inc_inss} IRRF={inc_irrf}")
                    
                    if cod not in ["600", "601", "602", "603", "604", "605", "606", "607", "608", "310", "311"]:
                        if evt["tipo"] == 1:  # provento
                            if inc_inss:
                                base_inss_data_fetcher += val
                            if inc_irrf:
                                base_irrf_data_fetcher += val
                        elif evt["tipo"] == 2:  # desconto
                            if inc_inss:
                                base_inss_data_fetcher -= val
                            if inc_irrf:
                                base_irrf_data_fetcher -= val
                
                print(f"  >>> BASE CALCULADA: INSS={fmt(base_inss_data_fetcher)} | IRRF={fmt(base_irrf_data_fetcher)}")
    
    # 2. O que FOLHA 2 traz?
    print("\n\n📦 FONTE 2: map_table [FOL.Folha = 2]")
    print("-" * 120)
    
    placeholders = ",".join(["%s"] * len(alvos))
    sql_folha2 = f"""
        SELECT 
            EPG.Codigo AS Mat,
            EPG.Nome,
            EFP.EVE_Codigo AS Cod,
            EVE.NomeApr AS Evento,
            EFP.Valor AS Valor,
            EVE.ProvDesc AS Tipo,
            EVE.IndicativoCPMensalFerias AS Inc_INSS,
            EVE.IndicativoIRRFMensal AS Inc_IRRF
        FROM EFO (NOLOCK)
        INNER JOIN EPG (NOLOCK) ON EFO.EMP_Codigo = EPG.EMP_Codigo AND EFO.EPG_Codigo = EPG.Codigo
        INNER JOIN EFP (NOLOCK) ON EFO.EMP_Codigo = EFP.EMP_Codigo AND EFO.FOL_Seq = EFP.EFO_FOL_Seq AND EFO.EPG_Codigo = EFP.EFO_EPG_Codigo
        INNER JOIN EVE (NOLOCK) ON EFP.EMP_Codigo = EVE.EMP_Codigo AND EFP.EVE_CODIGO = EVE.CODIGO
        WHERE EFO.EMP_Codigo = '9189'
          AND EFO.FOL_Seq = (SELECT TOP 1 Seq FROM FOL WHERE EMP_Codigo = '9189' AND Folha = 2 ORDER BY Seq DESC)
          AND EPG.Codigo IN ({placeholders})
        ORDER BY EPG.Nome, EVE.ProvDesc, EFP.EVE_Codigo
    """
    
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql_folha2, alvos)
            rows = cursor.fetchall()
            
            curr_mat = None
            base_inss_folha2 = Decimal("0")
            base_irrf_folha2 = Decimal("0")
            
            for row in rows:
                mat, nome, cod, evt, val, tipo, inc_inss, inc_irrf = row
                
                if mat != curr_mat:
                    if curr_mat:
                        print(f"  >>> BASE CALCULADA: INSS={fmt(base_inss_folha2)} | IRRF={fmt(base_irrf_folha2)}")
                    print(f"\n👤 {nome} ({mat})")
                    curr_mat = mat
                    base_inss_folha2 = Decimal("0")
                    base_irrf_folha2 = Decimal("0")
                
                val_dec = D(val)
                inc_inss_bool = str(inc_inss).strip() not in ["0", "N", "None", ""] if inc_inss else False
                inc_irrf_bool = str(inc_irrf).strip() not in ["0", "N", "None", ""] if inc_irrf else False
                
                print(f"  {cod:5} {evt:30} R$ {fmt(val_dec):>10} INSS={inc_inss_bool} IRRF={inc_irrf_bool}")
                
                if cod not in ["600", "601", "602", "603", "604", "605", "606", "607", "608", "310", "311"]:
                    if tipo == 1:  # provento
                        if inc_inss_bool:
                            base_inss_folha2 += val_dec
                        if inc_irrf_bool:
                            base_irrf_folha2 += val_dec
                    elif tipo == 2:  # desconto
                        if inc_inss_bool:
                            base_inss_folha2 -= val_dec
                        if inc_irrf_bool:
                            base_irrf_folha2 -= val_dec
            
            if curr_mat:
                print(f"  >>> BASE CALCULADA: INSS={fmt(base_inss_folha2)} | IRRF={fmt(base_irrf_folha2)}")
    
    except Exception as e:
        print(f"Erro: {e}")
    
    print("\n" + "="*120)


if __name__ == "__main__":
    main()
