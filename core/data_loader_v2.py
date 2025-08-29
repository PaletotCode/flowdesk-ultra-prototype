# core/data_loader_v2.py - Versão com Análise Inteligente
import pandas as pd
import polars as pl
import time
import ezodf
from typing import Tuple, Optional, Callable
from core.logger_config import setup_logger
from core.smart_data_analyzer import SmartDataAnalyzer, DataStructure

def _extrair_valor_celula_seguro(cell):
    """
    Extrai o valor de uma célula do ezodf de forma segura
    """
    try:
        if cell is None or cell.value is None:
            return None
            
        valor = cell.value
        
        if isinstance(valor, str) and valor.strip() == '':
            return None
            
        return valor
        
    except (ValueError, TypeError, AttributeError):
        try:
            texto = str(cell.plaintext() if hasattr(cell, 'plaintext') else '')
            return texto.strip() if texto.strip() else None
        except:
            return None

def _ler_ods_robusto(uploaded_file, logger) -> Optional[pd.DataFrame]:
    """
    Leitura robusta de arquivo ODS
    """
    try:
        logger.info("Iniciando leitura robusta do arquivo ODS...")
        uploaded_file.seek(0)
        
        doc = ezodf.opendoc(uploaded_file)
        
        if not doc.sheets:
            logger.error("Arquivo ODS não contém planilhas.")
            return None
            
        sheet = doc.sheets[0]
        logger.info(f"Lendo planilha: {sheet.name}")

        data = []
        for i, row in enumerate(sheet.rows()):
            row_data = [_extrair_valor_celula_seguro(cell) for cell in row]
            data.append(row_data)
            
            if i % 5000 == 0 and i > 0:
                logger.info(f"Lidas {i} linhas...")

        df = pd.DataFrame(data)
        logger.info(f"Leitura concluída: {df.shape[0]} linhas × {df.shape[1]} colunas")
        return df

    except Exception as e:
        logger.error(f"Erro na leitura robusta: {e}")
        return None

def carregar_e_analisar_planilha(
    uploaded_file,
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> Tuple[Optional[pl.DataFrame], Optional[DataStructure], str]:
    """
    Carrega e analisa inteligentemente um arquivo ODS
    
    Returns:
        Tuple[DataFrame_limpo, Estrutura_identificada, Logs]
    """
    logger, log_stream = setup_logger()
    logger.info("================ INICIANDO ANÁLISE INTELIGENTE ================")
    start_time = time.time()

    def report_progress(percentage, message):
        logger.info(message)
        if progress_callback:
            progress_callback(percentage, message)

    try:
        # FASE 1: Leitura do arquivo
        report_progress(10, f"Lendo arquivo: {uploaded_file.name}")
        df_bruto = _ler_ods_robusto(uploaded_file, logger)
        
        if df_bruto is None:
            raise ValueError("Falha na leitura do arquivo ODS")

        report_progress(30, f"Arquivo lido: {df_bruto.shape[0]} linhas brutas")
        
        # FASE 2: Análise estrutural inteligente
        report_progress(40, "Iniciando análise estrutural inteligente...")
        analyzer = SmartDataAnalyzer(logger)
        
        estrutura = analyzer.analyze_structure(df_bruto)
        
        report_progress(60, f"Estrutura identificada: {len(estrutura.columns)} colunas válidas")
        
        # Log da estrutura identificada
        logger.info("=== ESTRUTURA IDENTIFICADA ===")
        logger.info(f"Linha de cabeçalho: {estrutura.header_row}")
        logger.info(f"Início dos dados: {estrutura.data_start_row}")
        logger.info(f"Linhas de dados: {estrutura.data_rows}")
        
        logger.info("=== COLUNAS IDENTIFICADAS ===")
        for col in estrutura.columns:
            logger.info(
                f"'{col.name}' (índice {col.original_index}) - "
                f"Tipo: {col.data_type}, "
                f"Confiança: {col.confidence_score:.2f}, "
                f"Nulos: {col.null_percentage:.1f}%, "
                f"Únicos: {col.unique_count}"
            )
        
        logger.info("=== PADRÕES DE NEGÓCIO ===")
        for pattern, cols in estrutura.patterns.items():
            if cols:
                col_names = [col.name for col in cols] if isinstance(cols, list) else str(cols)
                logger.info(f"{pattern}: {col_names}")
        
        # FASE 3: Criação do DataFrame limpo
        report_progress(80, "Criando DataFrame estruturado...")
        df_limpo = analyzer.create_clean_dataframe(df_bruto, estrutura)
        
        report_progress(100, f"Concluído! {df_limpo.height} linhas × {df_limpo.width} colunas")
        
        tempo_total = time.time() - start_time
        logger.info(f"Análise concluída em {tempo_total:.2f} segundos")
        logger.info("================ ANÁLISE CONCLUÍDA ================")
        
        return df_limpo, estrutura, log_stream.getvalue()
        
    except Exception as e:
        logger.error(f"ERRO na análise inteligente: {e}", exc_info=True)
        report_progress(100, f"Erro: {e}")
        return None, None, log_stream.getvalue()

def gerar_relatorio_estrutura(estrutura: DataStructure) -> str:
    """
    Gera um relatório detalhado da estrutura identificada
    """
    relatorio = []
    relatorio.append("# 📊 Relatório de Análise Estrutural\n")
    
    relatorio.append(f"**📋 Informações Gerais:**")
    relatorio.append(f"- Total de linhas no arquivo: {estrutura.total_rows:,}")
    relatorio.append(f"- Linha de cabeçalho: {estrutura.header_row + 1}")
    relatorio.append(f"- Início dos dados: {estrutura.data_start_row + 1}")
    relatorio.append(f"- Linhas com dados: {estrutura.data_rows:,}")
    relatorio.append(f"- Colunas identificadas: {len(estrutura.columns)}\n")
    
    relatorio.append("**🗂️ Colunas Identificadas:**")
    for i, col in enumerate(estrutura.columns, 1):
        relatorio.append(
            f"{i}. **{col.name}** "
            f"(Tipo: {col.data_type}, "
            f"Confiança: {col.confidence_score:.1%}, "
            f"Preenchimento: {100-col.null_percentage:.1f}%)"
        )
    
    relatorio.append("\n**🎯 Padrões de Negócio Detectados:**")
    
    patterns_map = {
        'vendedor_columns': '👤 Vendedores',
        'cliente_columns': '🏢 Clientes', 
        'valor_columns': '💰 Valores',
        'pedido_columns': '📝 Pedidos',
        'data_columns': '📅 Datas',
        'produto_columns': '📦 Produtos'
    }
    
    for pattern_key, pattern_label in patterns_map.items():
        cols = estrutura.patterns.get(pattern_key, [])
        if cols:
            col_names = [col.name for col in cols]
            relatorio.append(f"- {pattern_label}: {', '.join(col_names)}")
    
    relatorio.append("\n**🔍 Amostras de Dados:**")
    for col in estrutura.columns[:5]:  # Mostra apenas as primeiras 5 colunas
        if col.sample_values:
            samples = [str(v) for v in col.sample_values[:3] if v is not None]
            relatorio.append(f"- **{col.name}**: {', '.join(samples)}")
    
    return '\n'.join(relatorio)