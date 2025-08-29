# core/data_loader.py
import pandas as pd
import polars as pl
from typing import Tuple, List, Dict, Any
import streamlit as st

@st.cache_data
def carregar_planilha(uploaded_file) -> Tuple[pl.DataFrame, List[Dict[str, Any]]]:
    """
    Carrega, FAZ O PARSE CUSTOMIZADO de arquivos de relatório do ERP (XLS/HTML),
    injeta o ID de rastreabilidade e inicializa o log de auditoria.
    """
    log_auditoria = []
    df_pandas = None

    try:
        # --- ETAPA 1: TENTATIVA DE LEITURA INTELIGENTE ---
        # Primeiro, tentamos ler como um arquivo Excel/ODS padrão.
        try:
            df_pandas = pd.read_excel(uploaded_file, engine=None)
            log_auditoria.append({"passo": "Detecção de Formato", "detalhe": "Arquivo lido com sucesso como planilha padrão (Excel/ODS)."})
        except Exception:
            # Se a leitura padrão falhar, tentamos ler como um arquivo HTML.
            # O argumento 'header=0' é um palpite inicial que ajustaremos depois.
            # A codificação 'latin-1' é comum em sistemas legados no Brasil.
            uploaded_file.seek(0) # Reinicia o ponteiro do arquivo
            lista_de_dfs = pd.read_html(uploaded_file, header=0, encoding='latin-1')
            if lista_de_dfs:
                df_pandas = lista_de_dfs[0] # Pega a primeira tabela encontrada no HTML
                log_auditoria.append({"passo": "Detecção de Formato", "detalhe": "Arquivo lido com sucesso como Tabela HTML."})
            else:
                raise ValueError("Nenhuma tabela foi encontrada no arquivo.")

        if df_pandas is None:
            raise ValueError("Não foi possível carregar os dados da planilha.")

        df_polars = pl.from_pandas(df_pandas.copy())
        linhas_antes_limpeza = df_polars.height
        
        log_auditoria.append({
            "passo": "Carga de Dados Brutos",
            "detalhe": f"Carregadas {linhas_antes_limpeza} linhas brutas da planilha '{uploaded_file.name}'.",
        })

        # --- ETAPA 2: PARSER CUSTOMIZADO PARA O RELATÓRIO ---
        
        # 1. Renomear colunas para remover espaços e caracteres especiais (comuns em HTML)
        df_polars = df_polars.rename({col: col.strip().replace(':', '') for col in df_polars.columns})

        # 2. Remover linhas de total/resumo no final do arquivo.
        #    Esta é uma regra específica para o seu relatório.
        df_limpo = df_polars.filter(
            ~pl.col(df_polars.columns[2]).str.contains("Total", literal=True) # Ex: não contém "Total" na coluna de Cliente
        )
        
        # 3. Remover linhas completamente vazias que podem ter sido importadas.
        df_limpo = df_limpo.drop_nulls()

        # 4. Tenta encontrar a coluna de vendas para garantir que os tipos estão corretos
        possivel_vendas = ["Valor Venda", "valor_venda", "Vendas", "vendas", "Valor", "valor"]
        coluna_vendas_encontrada = None
        for col in possivel_vendas:
             if col in df_limpo.columns:
                coluna_vendas_encontrada = col
                break
        
        if coluna_vendas_encontrada:
             df_limpo = df_limpo.with_columns(
                 pl.col(coluna_vendas_encontrada).cast(pl.Float64, strict=False)
             )

        linhas_depois_limpeza = df_limpo.height
        linhas_removidas = linhas_antes_limpeza - linhas_depois_limpeza
        log_auditoria.append({
            "passo": "Limpeza Customizada",
            "detalhe": f"Foram removidas {linhas_removidas} linhas de totais ou vazias.",
        })

        # --- ETAPA 3: INJEÇÃO DE RASTREABILIDADE ---
        df_final = df_limpo.with_row_count(name="id_linha_original")
        
        return df_final, log_auditoria

    except Exception as e:
        log_auditoria.append({
            "passo": "Falha Crítica na Carga ou Limpeza",
            "detalhe": str(e),
            "linhas_afetadas": [],
            "resultado": None
        })
        return None, log_auditoria