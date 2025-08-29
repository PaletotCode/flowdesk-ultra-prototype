# core/data_loader.py (Refatoração Final)
import polars as pl
from typing import Tuple, List, Dict, Any
import streamlit as st

@st.cache_data
def carregar_planilha(uploaded_file) -> Tuple[pl.DataFrame, List[Dict[str, Any]]]:
    """
    Carrega e faz o PARSE de um arquivo CSV, com detecção inteligente de cabeçalho
    e limpeza de rodapés de resumo.
    """
    log_auditoria = []
    
    try:
        # --- ETAPA 1: LER O ARQUIVO CSV DE FORMA BRUTA ---
        # Tenta ler com ';' (padrão Brasil) e depois com ',' (padrão universal)
        try:
            df_bruto = pl.read_csv(uploaded_file, has_header=False, encoding='latin-1', separator=';')
        except:
            uploaded_file.seek(0)
            df_bruto = pl.read_csv(uploaded_file, has_header=False, encoding='latin-1', separator=',')

        # --- ETAPA 2: DETECÇÃO INTELIGENTE DE CABEÇALHO ---
        header_keywords = ['data', 'nota', 'cliente', 'vendedor', 'produto', 'valor', 'quant', 'total']
        best_match_score = 0
        header_row_index = -1

        # Procura o cabeçalho nas primeiras 20 linhas
        for i, row in enumerate(df_bruto.head(20).iter_rows()):
            current_score = 0
            row_str = " ".join(str(cell) for cell in row).lower()
            for keyword in header_keywords:
                if keyword in row_str:
                    current_score += 1
            
            if current_score > best_match_score:
                best_match_score = current_score
                header_row_index = i

        # Se a melhor pontuação for muito baixa (ex: < 3), o cabeçalho não foi encontrado
        if best_match_score < 3:
            raise ValueError("Não foi possível identificar uma linha de cabeçalho válida. Verifique se o arquivo CSV contém colunas como 'Data', 'Cliente', 'Valor', etc.")

        # --- ETAPA 3: RECARREGAR O CSV USANDO O CABEÇALHO ENCONTRADO ---
        header_names = [str(col).strip() for col in df_bruto.row(header_row_index)]
        uploaded_file.seek(0)
        
        try:
             df_polars = pl.read_csv(
                uploaded_file, 
                skip_rows=header_row_index + 1,
                has_header=False, # Nós definiremos o cabeçalho manualmente
                encoding='latin-1',
                separator=';'
            )
        except:
            uploaded_file.seek(0)
            df_polars = pl.read_csv(
                uploaded_file, 
                skip_rows=header_row_index + 1,
                has_header=False,
                encoding='latin-1',
                separator=','
            )
        
        # Garante que o número de colunas corresponde ao cabeçalho encontrado
        if len(df_polars.columns) == len(header_names):
            df_polars.columns = header_names
        else:
            # Se houver uma incompatibilidade, usa um método seguro
            df_polars = df_polars.select(pl.all().prefix("col_"))


        linhas_antes_limpeza = df_polars.height
        log_auditoria.append({
            "passo": "Carga de Dados CSV",
            "detalhe": f"Carregadas {linhas_antes_limpeza} linhas brutas do arquivo '{uploaded_file.name}'. Cabeçalho encontrado na linha {header_row_index + 1}.",
        })

        # --- ETAPA 4: LIMPEZA PÓS-CARGA ---
        # Remove linhas de total/resumo (ex: onde a 3a coluna contém 'Total')
        # E remove linhas onde a primeira coluna está totalmente nula (linhas vazias)
        df_limpo = df_polars.filter(
            ~pl.col(df_polars.columns[2]).str.contains("Total", literal=True) &
            pl.col(df_polars.columns[0]).is_not_null()
        )

        linhas_depois_limpeza = df_limpo.height
        linhas_removidas = linhas_antes_limpeza - linhas_depois_limpeza
        log_auditoria.append({
            "passo": "Limpeza Pós-Carga",
            "detalhe": f"Foram removidas {linhas_removidas} linhas de totais ou vazias.",
        })

        # --- ETAPA 5: INJEÇÃO DE RASTREABILIDADE ---
        df_final = df_limpo.with_row_count(name="id_linha_original")
        return df_final, log_auditoria

    except Exception as e:
        log_auditoria.append({"passo": "Falha Crítica na Carga ou Limpeza", "detalhe": str(e)})
        return None, log_auditoria