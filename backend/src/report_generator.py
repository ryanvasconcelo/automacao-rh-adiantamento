# src/report_generator.py
"""
Módulo para gerar relatórios de adiantamento no padrão Fortes.
"""

import pandas as pd
from datetime import date, datetime
from pathlib import Path
from typing import Optional, Tuple
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from config.logging_config import log


def formatar_valor(valor: float, com_sinal: bool = False) -> str:
    """Formata valor monetário no padrão brasileiro."""
    if pd.isna(valor) or valor == 0:
        return ""
    
    sinal = ""
    if com_sinal and valor < 0:
        sinal = "-"
        valor = abs(valor)
    elif com_sinal and valor > 0:
        sinal = ""
    
    return f"{sinal}{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def gerar_relatorio_adiantamento_fortes(
    df_final: pd.DataFrame,
    empresa_nome: str,
    empresa_cnpj: str,
    ano: int,
    mes: int,
    output_path: str = "data"
) -> Tuple[Optional[str], Optional[str]]:
    """
    Gera relatório de adiantamento no padrão Fortes (PDF e CSV).
    
    Args:
        df_final: DataFrame com dados processados
        empresa_nome: Nome da empresa
        empresa_cnpj: CNPJ da empresa
        ano: Ano de referência
        mes: Mês de referência
        output_path: Diretório de saída
        
    Returns:
        Tupla (caminho_pdf, caminho_csv)
    """
    if df_final.empty:
        log.warning("DataFrame vazio - nenhum relatório gerado")
        return None, None
    
    # Filtra apenas funcionários elegíveis com valor líquido > 0
    df_relatorio = df_final[
        (df_final["Status"] == "Elegível") & 
        (df_final["ValorLiquidoAdiantamento"] > 0)
    ].copy()
    
    if df_relatorio.empty:
        log.warning("Nenhum funcionário elegível com valor > 0")
        return None, None
    
    # Cria diretório se não existir
    Path(output_path).mkdir(exist_ok=True)
    
    # Data de emissão
    data_emissao = date.today().strftime("%d/%m/%Y")
    mes_ano = f"{mes:02d}/{ano}"
    
    # Gera PDF
    caminho_pdf = _gerar_pdf_fortes(
        df_relatorio, empresa_nome, empresa_cnpj, 
        data_emissao, mes_ano, output_path, ano, mes
    )
    
    # Gera CSV
    caminho_csv = _gerar_csv_fortes(
        df_relatorio, empresa_nome, empresa_cnpj,
        data_emissao, mes_ano, output_path, ano, mes
    )
    
    return caminho_pdf, caminho_csv


def _gerar_pdf_fortes(
    df: pd.DataFrame,
    empresa_nome: str,
    empresa_cnpj: str,
    data_emissao: str,
    mes_ano: str,
    output_path: str,
    ano: int,
    mes: int
) -> Optional[str]:
    """Gera PDF no formato Fortes."""
    try:
        hoje = date.today().strftime("%Y-%m-%d")
        caminho = f"{output_path}/adiantamento_folha_{ano}{mes:02d}_{hoje}.pdf"
        
        doc = SimpleDocTemplate(
            caminho,
            pagesize=A4,
            rightMargin=1.5*cm,
            leftMargin=1.5*cm,
            topMargin=2*cm,
            bottomMargin=2*cm,
        )
        
        elementos = []
        styles = getSampleStyleSheet()
        
        # Estilo customizado para título
        titulo_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=14,
            textColor=colors.black,
            spaceAfter=6,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        # Estilo para subtítulo
        subtitulo_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.black,
            spaceAfter=3,
            alignment=TA_LEFT,
        )
        
        # Cabeçalho
        titulo = Paragraph("<b>Adiantamento de Folha</b>", titulo_style)
        elementos.append(titulo)
        elementos.append(Spacer(1, 0.3*cm))
        
        # Informações da empresa
        info_empresa = f"Empresa: {empresa_nome} - CNPJ: {empresa_cnpj}"
        elementos.append(Paragraph(info_empresa, subtitulo_style))
        
        info_emissao = f"Emissão: {data_emissao} Mês/Ano: {mes_ano}"
        elementos.append(Paragraph(info_emissao, subtitulo_style))
        elementos.append(Spacer(1, 0.5*cm))
        
        # Cabeçalho da tabela
        dados_tabela = [[
            Paragraph("<b>Código</b>", styles['Normal']),
            Paragraph("<b>Empregado</b>", styles['Normal']),
            Paragraph("<b>Demonstrativo<br/>de cálculo</b>", styles['Normal']),
            Paragraph("<b>Referência</b>", styles['Normal']),
            Paragraph("<b>Valor</b>", styles['Normal'])
        ]]
        
        # Totalização
        total_bruto = 0
        total_descontos = 0
        total_liquido = 0
        
        # Adiciona linhas de funcionários
        for idx, row in df.iterrows():
            matricula = str(row['Matricula']).zfill(6)
            nome = row['Nome']
            salario = row['SalarioContratual']
            percentual = row.get('PercentualAdiant', 40)
            valor_bruto = row['ValorAdiantamentoBruto']
            valor_desconto = row.get('ValorDesconto', 0)
            valor_liquido = row['ValorLiquidoAdiantamento']
            
            # Linha principal do funcionário
            dados_tabela.append([
                matricula,
                nome,
                formatar_valor(salario),
                f"{int(percentual)}%",
                formatar_valor(valor_bruto)
            ])
            
            # Se tem desconto de consignado, adiciona linha
            if valor_desconto > 0:
                dados_tabela.append([
                    "",
                    "     301 Provisão Cred. Trab.- Desconto",
                    "",
                    f"{int(percentual)}%",
                    formatar_valor(-valor_desconto, com_sinal=True)
                ])
                
                # Linha com subtotal pontilhado
                dados_tabela.append([
                    "", "", "", "",
                    "- - - - - - - -"
                ])
                dados_tabela.append([
                    "", "", "", "",
                    formatar_valor(valor_liquido)
                ])
            
            # Linha vazia entre funcionários
            dados_tabela.append(["", "", "", "", ""])
            
            # Acumula totais
            total_bruto += valor_bruto
            total_descontos += valor_desconto
            total_liquido += valor_liquido
        
        # Total geral
        total_funcionarios = len(df)
        dados_tabela.append([
            "",
            Paragraph(f"<b>Total Geral ({total_funcionarios} empregados)</b>", styles['Normal']),
            "",
            "",
            ""
        ])
        dados_tabela.append([
            "", "", "", "",
            Paragraph(f"<b>{formatar_valor(total_bruto)}</b>", styles['Normal'])
        ])
        
        if total_descontos > 0:
            dados_tabela.append([
                "",
                "     301 Provisão Cred. Trab.- Desconto",
                "", "",
                Paragraph(f"<b>{formatar_valor(-total_descontos, com_sinal=True)}</b>", styles['Normal'])
            ])
            dados_tabela.append([
                "", "", "", "",
                "- - - - - - - -"
            ])
            dados_tabela.append([
                "", "", "", "",
                Paragraph(f"<b>{formatar_valor(total_liquido)}</b>", styles['Normal'])
            ])
        
        # Cria tabela
        tabela = Table(dados_tabela, colWidths=[2*cm, 7*cm, 3*cm, 2.5*cm, 2.5*cm])
        
        # Estilo da tabela
        estilo = TableStyle([
            # Cabeçalho
            ('BACKGROUND', (0, 0), (-1, 0), colors.white),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            ('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),
            
            # Dados
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),    # Código
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),    # Nome
            ('ALIGN', (2, 1), (2, -1), 'RIGHT'),   # Demo calc
            ('ALIGN', (3, 1), (3, -1), 'CENTER'),  # Ref
            ('ALIGN', (4, 1), (4, -1), 'RIGHT'),   # Valor
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ])
        
        tabela.setStyle(estilo)
        elementos.append(tabela)
        
        # Rodapé
        elementos.append(Spacer(1, 0.5*cm))
        rodape = Paragraph(
            f"<i>Gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')} - Fortes Pessoal</i>",
            ParagraphStyle(
                'Footer',
                parent=styles['Normal'],
                fontSize=7,
                textColor=colors.grey,
                alignment=TA_RIGHT
            )
        )
        elementos.append(rodape)
        
        # Gera o PDF
        doc.build(elementos)
        
        log.success(f"Relatório PDF gerado: {caminho}")
        return caminho
        
    except Exception as e:
        log.error(f"Erro ao gerar PDF: {e}")
        return None


def _gerar_csv_fortes(
    df: pd.DataFrame,
    empresa_nome: str,
    empresa_cnpj: str,
    data_emissao: str,
    mes_ano: str,
    output_path: str,
    ano: int,
    mes: int
) -> Optional[str]:
    """Gera CSV no formato Fortes."""
    try:
        hoje = date.today().strftime("%Y-%m-%d")
        caminho = f"{output_path}/adiantamento_folha_{ano}{mes:02d}_{hoje}.csv"
        
        # Prepara dados para CSV
        dados_csv = []
        
        for idx, row in df.iterrows():
            # Linha principal
            dados_csv.append({
                'Codigo': str(row['Matricula']).zfill(6),
                'Empregado': row['Nome'],
                'DemonstrativoCalculo': row['SalarioContratual'],
                'Referencia': f"{int(row.get('PercentualAdiant', 40))}%",
                'Valor': row['ValorAdiantamentoBruto'],
                'Tipo': 'ADIANTAMENTO'
            })
            
            # Se tem desconto
            if row.get('ValorDesconto', 0) > 0:
                dados_csv.append({
                    'Codigo': '',
                    'Empregado': '301 Provisão Cred. Trab.- Desconto',
                    'DemonstrativoCalculo': '',
                    'Referencia': f"{int(row.get('PercentualAdiant', 40))}%",
                    'Valor': -row['ValorDesconto'],
                    'Tipo': 'DESCONTO'
                })
                
                # Líquido
                dados_csv.append({
                    'Codigo': '',
                    'Empregado': 'Valor Líquido',
                    'DemonstrativoCalculo': '',
                    'Referencia': '',
                    'Valor': row['ValorLiquidoAdiantamento'],
                    'Tipo': 'LIQUIDO'
                })
        
        # Cria DataFrame e salva
        df_csv = pd.DataFrame(dados_csv)
        df_csv.to_csv(caminho, index=False, sep=";", decimal=",", encoding="utf-8-sig")
        
        log.success(f"Relatório CSV gerado: {caminho}")
        return caminho
        
    except Exception as e:
        log.error(f"Erro ao gerar CSV: {e}")
        return None


def calcular_totais_dashboard(df_final: pd.DataFrame) -> dict:
    """
    Calcula totais para exibição no dashboard.
    Todos os valores são arredondados para 2 casas decimais.
    
    Args:
        df_final: DataFrame com dados processados
        
    Returns:
        Dicionário com totais arredondados
    """
    # Filtra apenas funcionários elegíveis com valor > 0
    df_elegiveis = df_final[
        (df_final["Status"] == "Elegível") &
        (df_final["ValorLiquidoAdiantamento"] > 0)
    ]
    
    if df_elegiveis.empty:
        return {
            'total_bruto_regras': 0.00,
            'total_bruto_fortes': 0.00,
            'total_descontos': 0.00,
            'total_liquido': 0.00,
            'total_funcionarios': 0,
            'inconsistencias': 0
        }
    
    # Calcula totais com arredondamento para 2 casas decimais
    total_bruto_regras = round(df_elegiveis["ValorAdiantamentoBruto"].sum(), 2)
    total_descontos = round(df_elegiveis["ValorDesconto"].fillna(0).sum(), 2)
    total_liquido = round(df_elegiveis["ValorLiquidoAdiantamento"].sum(), 2)
    total_funcionarios = len(df_elegiveis)
    
    # Total bruto do Fortes (se existir coluna ValorBrutoFortes)
    if "ValorBrutoFortes" in df_elegiveis.columns:
        total_bruto_fortes = round(df_elegiveis["ValorBrutoFortes"].fillna(0).sum(), 2)
    else:
        total_bruto_fortes = total_bruto_regras
    
    # Conta inconsistências (funcionários inelegíveis ou com problemas)
    inconsistencias = len(df_final[df_final["Status"] != "Elegível"])
    
    return {
        'total_bruto_regras': total_bruto_regras,      # Valor calculado pelas regras
        'total_bruto_fortes': total_bruto_fortes,      # Valor do Fortes (se disponível)
        'total_descontos': total_descontos,            # Total de descontos consignado
        'total_liquido': total_liquido,                # Valor final (bruto - descontos)
        'total_funcionarios': total_funcionarios,      # Funcionários elegíveis
        'inconsistencias': inconsistencias             # Funcionários com problemas
    }