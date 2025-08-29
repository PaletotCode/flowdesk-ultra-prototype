# core/data_loader.py (completamente refatorado)
import polars as pl
from typing import Tuple, List, Dict, Any
import streamlit as st

@st.cache_data
def carregar_planilha(uploaded_file) -> Tuple[pl.DataFrame, List[Dict[str, Any]]]:
    """
    Carrega e faz o PARSE de um arquivo CSV, esperando um cabeçalho de múltiplas linhas
    e rodapés de resumo, típicos de relatórios de ERP.
    """
    log_auditoria = []
    
    try:
        # --- ETAPA 1: LER O ARQUIVO CSV ---
        # A codificação 'latin-1' é comum em arquivos gerados por sistemas Windows no Brasil.
        # O separador pode ser ',' ou ';', vamos deixar o Polars tentar detectar.
        df_bruto = pl.read_csv(
            uploaded_file, 
            has_header=False, # Lemos sem cabeçalho para podermos encontrá-lo
            encoding='latin-1',
            separator=';' # Forçar o uso de ponto e vírgula, comum no Brasil
        )
        
        # --- ETAPA 2: PARSER CUSTOMIZADO PARA ENCONTRAR O CABEÇALHO REAL ---
        # Encontra o número da linha onde o cabeçalho real começa (ex: procurando por 'Núm. Nota')
        header_row_index = -1
        for i, row in enumerate(df_bruto.iter_rows()):
            if any("Núm. Nota" in str(cell) for cell in row):
                header_row_index = i
                break
        
        if header_row_index == -1:
            raise ValueError("Não foi possível encontrar a linha de cabeçalho no arquivo CSV. Verifique se a coluna 'Núm. Nota' existe.")

        # Recarrega o CSV, pulando as linhas de lixo e usando o cabeçalho correto
        uploaded_file.seek(0) # Reinicia o ponteiro do arquivo
        df_com_header = pl.read_csv(
            uploaded_file, 
            skip_rows=header_row_index + 1,
            has_header=True,
            encoding='latin-1',
            separator=';'
        )
        # Define os nomes das colunas com base na linha que encontramos
        df_com_header.columns = [str(col).strip() for col in df_bruto.row(header_row_index)]
        
        df_polars = df_com_header
        linhas_antes_limpeza = df_polars.height
        log_auditoria.append({
            "passo": "Carga de Dados CSV",
            "detalhe": f"Carregadas {linhas_antes_limpeza} linhas brutas do arquivo '{uploaded_file.name}'.",
        })

        # --- ETAPA 3: LIMPEZA PÓS-CARGA ---
        # Remove linhas de total/resumo no final do arquivo
        df_limpo = df_polars.filter(
            ~pl.col(df_polars.columns[2]).str.contains("Total", literal=True)
        ).drop_nulls()

        linhas_depois_limpeza = df_limpo.height
        linhas_removidas = linhas_antes_limpeza - linhas_depois_limpeza
        log_auditoria.append({
            "passo": "Limpeza Pós-Carga",
            "detalhe": f"Foram removidas {linhas_removidas} linhas de totais ou vazias.",
        })

        # --- ETAPA 4: INJEÇÃO DE RASTREABILIDADE ---
        df_final = df_limpo.with_row_count(name="id_linha_original")
        return df_final, log_auditoria

    except Exception as e:
        log_auditoria.append({"passo": "Falha Crítica na Carga ou Limpeza", "detalhe": str(e)})
        return None, log_auditoria