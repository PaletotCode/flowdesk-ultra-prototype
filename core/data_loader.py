# core/data_loader.py (com Modo de Depuração)
import polars as pl
from typing import Tuple, List, Dict, Any
import streamlit as st

@st.cache_data(show_spinner=False) # Desativamos o spinner do cache para não sobrepor o nosso
def carregar_planilha(uploaded_file, debug_mode: bool = False) -> Tuple[pl.DataFrame, List[Dict[str, Any]]]:
    """
    Carrega e faz o PARSE de um arquivo CSV. Inclui um modo de depuração
    para diagnosticar arquivos com formatos inesperados.
    """
    log_auditoria = []
    
    try:
        # --- ETAPA 1: LER O ARQUIVO CSV DE FORMA BRUTA ---
        df_bruto = None
        try:
            # Tentativa com ponto e vírgula
            df_bruto = pl.read_csv(uploaded_file, has_header=False, encoding='latin-1', separator=';')
        except:
            try:
                # Tentativa com vírgula
                uploaded_file.seek(0)
                df_bruto = pl.read_csv(uploaded_file, has_header=False, encoding='latin-1', separator=',')
            except Exception as e:
                raise ValueError(f"Não foi possível ler o CSV nem com ';' nem com ','. Erro: {e}")
        
        # --- ETAPA 2: MODO DE DEPURAÇÃO ---
        # Se o modo de depuração estiver ativo, mostramos os dados brutos e paramos.
        if debug_mode:
            st.warning(" MODO DE DEPURAÇÃO ATIVADO ")
            st.markdown("A execução foi pausada para análise. As informações abaixo mostram como o programa está 'enxergando' seu arquivo.")
            
            st.subheader("1. Estrutura do DataFrame Bruto")
            st.write(f"**Shape (Linhas, Colunas):** `{df_bruto.shape}`")
            st.markdown(f"**Observação:** Se o número de colunas for 1, o separador (`;` ou `,`) provavelmente está incorreto para este arquivo.")

            st.subheader("2. Prévia das 10 Primeiras Linhas Brutas")
            st.dataframe(df_bruto.head(10))

            log_auditoria.append({"passo": "Modo de Depuração", "detalhe": "Execução pausada para análise do arquivo."})
            return None, log_auditoria # Para a execução aqui

        # --- SE O MODO DE DEPURAÇÃO ESTIVER DESATIVADO, CONTINUA O PROCESSO NORMAL ---

        # (O resto do código é o mesmo da última versão)
        
        header_keywords = ['data', 'nota', 'cliente', 'vendedor', 'produto', 'valor', 'quant', 'total']
        best_match_score = 0
        header_row_index = -1

        for i, row in enumerate(df_bruto.head(20).iter_rows()):
            current_score = 0
            row_str = " ".join(str(cell) for cell in row).lower()
            for keyword in header_keywords:
                if keyword in row_str:
                    current_score += 1
            if current_score > best_match_score:
                best_match_score = current_score
                header_row_index = i

        if best_match_score < 3:
            raise ValueError("Não foi possível identificar uma linha de cabeçalho válida. Verifique se o arquivo CSV contém colunas como 'Data', 'Cliente', 'Valor', etc.")

        header_names = [str(col).strip() for col in df_bruto.row(header_row_index)]
        uploaded_file.seek(0)
        
        df_polars = pl.read_csv(uploaded_file, skip_rows=header_row_index + 1, has_header=False, encoding='latin-1', separator=';')
        try:
             df_polars = pl.read_csv(uploaded_file, skip_rows=header_row_index + 1, has_header=False, encoding='latin-1', separator=';')
        except:
            uploaded_file.seek(0)
            df_polars = pl.read_csv(uploaded_file, skip_rows=header_row_index + 1, has_header=False, encoding='latin-1', separator=',')
        
        if len(df_polars.columns) == len(header_names):
            df_polars.columns = header_names
        else:
            df_polars = df_polars.select(pl.all().prefix("col_"))

        linhas_antes_limpeza = df_polars.height
        log_auditoria.append({"passo": "Carga de Dados CSV", "detalhe": f"Carregadas {linhas_antes_limpeza} linhas. Cabeçalho na linha {header_row_index + 1}."})

        df_limpo = df_polars.filter(
            ~pl.col(df_polars.columns[2]).str.contains("Total", literal=True) &
            pl.col(df_polars.columns[0]).is_not_null()
        )

        linhas_depois_limpeza = df_limpo.height
        linhas_removidas = linhas_antes_limpeza - linhas_depois_limpeza
        log_auditoria.append({"passo": "Limpeza Pós-Carga", "detalhe": f"Removidas {linhas_removidas} linhas de totais ou vazias."})

        df_final = df_limpo.with_row_count(name="id_linha_original")
        return df_final, log_auditoria

    except Exception as e:
        log_auditoria.append({"passo": "Falha Crítica na Carga ou Limpeza", "detalhe": str(e)})
        return None, log_auditoria