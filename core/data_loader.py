# core/data_loader.py
import pandas as pd
import polars as pl
from typing import Tuple, List, Dict, Any
import streamlit as st

@st.cache_data
def carregar_planilha(uploaded_file) -> Tuple[pl.DataFrame, List[Dict[str, Any]]]:
    """
    Carrega, LIMPA e prepara arquivos de planilha (ODS, XLS, XLSX), 
    injeta o ID de rastreabilidade e inicializa o log de auditoria.

    Args:
        uploaded_file: O objeto de arquivo carregado pelo Streamlit.

    Returns:
        Uma tupla contendo o DataFrame Polars limpo com id_linha_original 
        e o log de auditoria detalhado.
    """
    log_auditoria = []

    try:
        # --- ETAPA 1: CARGA DE DADOS BRUTOS (COM SUPORTE A MÚLTIPLOS MOTORES) ---
        # Removido 'engine="odf"' para que o pandas detecte o formato automaticamente
        df_pandas = pd.read_excel(uploaded_file, engine=None)
        df_polars = pl.from_pandas(df_pandas)
        linhas_antes_limpeza = df_polars.height

        log_auditoria.append({
            "passo": "Carga de Dados Brutos",
            "detalhe": f"Carregadas {linhas_antes_limpeza} linhas brutas da planilha '{uploaded_file.name}'.",
            "resultado": f"DataFrame bruto criado com shape: {df_polars.shape}"
        })

        # --- ETAPA 2: FILTRO DE LIMPEZA INTELIGENTE ---
        
        # Lista de nomes de coluna comuns para valores de vendas/receita
        possivel_vendas = [
            "Valor Venda", "valor_venda", "Vendas", "vendas", "Valor", "valor",
            "Total", "total", "Receita", "receita", "Revenue", "revenue"
        ]
        coluna_referencia = None
        for col in possivel_vendas:
            if col in df_polars.columns:
                coluna_referencia = col
                break
        
        df_limpo = df_polars

        if coluna_referencia:
            # Converte a coluna de referência para número. O argumento `strict=False` é a chave: 
            # tudo que não for um número válido (como textos de banners) se tornará 'null'.
            df_com_numeros = df_limpo.with_columns(
                pl.col(coluna_referencia).to_numeric(strict=False)
            )

            # Filtra o DataFrame, mantendo APENAS as linhas onde a coluna de referência
            # NÃO é nula. Isso efetivamente remove todas as linhas de banners e textos.
            df_limpo = df_com_numeros.filter(
                pl.col(coluna_referencia).is_not_null()
            )
            
            # Garante que a coluna final tenha o tipo numérico correto (ex: Float64)
            df_limpo = df_limpo.with_columns(
                pl.col(coluna_referencia).cast(pl.Float64)
            )

            linhas_depois_limpeza = df_limpo.height
            linhas_removidas = linhas_antes_limpeza - linhas_depois_limpeza

            log_auditoria.append({
                "passo": "Limpeza de Dados",
                "detalhe": f"Foram removidas {linhas_removidas} linhas que não continham dados numéricos na coluna de referência '{coluna_referencia}'.",
                "linhas_restantes": linhas_depois_limpeza,
            })
        else:
             log_auditoria.append({
                "passo": "Aviso de Limpeza",
                "detalhe": "Nenhuma coluna de referência de vendas foi encontrada para a limpeza. Os dados serão usados como estão, o que pode causar erros de cálculo se houver textos misturados.",
            })

        # --- ETAPA 3: INJEÇÃO DE RASTREABILIDADE ---
        # Adiciona a coluna 'id_linha_original' ao DataFrame JÁ LIMPO.
        df_final = df_limpo.with_row_count(name="id_linha_original")
        
        return df_final, log_auditoria

    except Exception as e:
        # Tratamento de erro robusto
        log_auditoria.append({
            "passo": "Falha Crítica na Carga ou Limpeza",
            "detalhe": str(e),
            "linhas_afetadas": [],
            "resultado": None
        })
        return None, log_auditoria