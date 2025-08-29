# core/data_loader.py
import pandas as pd
import polars as pl
from typing import Tuple, List, Dict, Any
import streamlit as st

@st.cache_data
def carregar_planilha(uploaded_file) -> Tuple[pl.DataFrame, List[Dict[str, Any]]]:
    """
    Carrega um arquivo ODS, converte para Polars, injeta o ID de rastreabilidade
    e inicializa o log de auditoria.

    Args:
        uploaded_file: O objeto de arquivo carregado pelo Streamlit.

    Returns:
        Uma tupla contendo o DataFrame Polars com id_linha_original e 
        o log de auditoria inicial.
    """
    log_auditoria = []

    try:
        # Use pandas apenas como ponte de leitura
        df_pandas = pd.read_excel(uploaded_file, engine='odf')
        df_polars = pl.from_pandas(df_pandas)

        # Injeção da coluna de rastreabilidade
        df_com_id = df_polars.with_row_count(name="id_linha_original")

        log_auditoria.append({
            "passo": "Carga de Dados",
            "detalhe": f"Carregadas {df_com_id.height} linhas e {df_com_id.width} colunas da planilha '{uploaded_file.name}'.",
            "linhas_afetadas": list(range(df_com_id.height)),
            "resultado": f"DataFrame criado com shape: {df_com_id.shape}"
        })
        
        return df_com_id, log_auditoria

    except Exception as e:
        # Tratamento de erro robusto
        log_auditoria.append({
            "passo": "Falha na Carga de Dados",
            "detalhe": str(e),
            "linhas_afetadas": [],
            "resultado": None
        })
        return None, log_auditoria