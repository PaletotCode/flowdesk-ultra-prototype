import pandas as pd
import polars as pl
from typing import Tuple, List, Dict, Any
import streamlit as st

@st.cache_data(show_spinner=False)
def carregar_planilha(uploaded_file) -> Tuple[pl.DataFrame, List[Dict[str, Any]]]:
    """
    Faz o parse de um relatório ODS estruturado em blocos, extraindo
    pedidos, itens e o tipo de cada transação (PED, ACU, DEV).
    """
    log_auditoria = []
    
    try:
        # --- ETAPA 1: LEITURA DO ARQUIVO ODS ---
        # Usamos o engine 'odf' para garantir a leitura de arquivos .ods
        df_bruto = pd.read_excel(uploaded_file, engine='odf', header=None)
        
        log_auditoria.append({
            "passo": "Carga de Dados Brutos",
            "detalhe": f"Carregadas {len(df_bruto)} linhas brutas do arquivo ODS '{uploaded_file.name}'."
        })

        # --- ETAPA 2: PARSING COM MÁQUINA DE ESTADOS ROBUSTA ---
        dados_processados = []
        estado_atual = "procurando_secao"
        tipo_pedido_atual = "INDEFINIDO"
        dados_pedido_atual = {}
        cabecalho_itens = []

        for index, row in df_bruto.iterrows():
            # Converte a linha para uma lista de strings, tratando valores nulos
            primeira_celula = str(row.iloc[0] if pd.notna(row.iloc[0]) else "").strip()

            # --- Lógica de Transição de Estado ---
            if "PEDIDOS EM CARTEIRA" in primeira_celula:
                tipo_pedido_atual = "PED"
                continue
            elif "PEDIDOS ACUMULATIVO" in primeira_celula:
                tipo_pedido_atual = "ACU"
                continue
            elif "DEVOLUÇÃO DE PEDIDOS" in primeira_celula:
                tipo_pedido_atual = "DEV"
                continue

            if "Pedido" in primeira_celula:
                estado_atual = "lendo_cabecalho_pedido"
                dados_pedido_atual = {
                    'Pedido': row.iloc[1],
                    'Data': row.iloc[2],
                    'Cód. Cliente': row.iloc[3],
                    'Nome Cliente': row.iloc[4],
                    'Cód. Vendedor': row.iloc[5],
                    'Nome Vendedor': row.iloc[6],
                    'Tipo_Pedido': tipo_pedido_atual
                }
                continue
            
            if "Cód. Int." in primeira_celula:
                estado_atual = "lendo_itens"
                # Captura os nomes das colunas dos itens dinamicamente
                cabecalho_itens = [str(h).strip() for h in row]
                continue

            if "Total do Pedido:" in primeira_celula:
                estado_atual = "procurando_secao"
                dados_pedido_atual = {}
                cabecalho_itens = []
                continue

            # --- Lógica de Processamento de Estado ---
            if estado_atual == "lendo_itens":
                # Verifica se a linha parece ser uma linha de item válida (não vazia)
                if pd.notna(row.iloc[0]) and pd.notna(row.iloc[1]):
                    item_dict = {}
                    for i, header in enumerate(cabecalho_itens):
                        item_dict[header] = row.iloc[i]
                    
                    # Combina os dados do cabeçalho do pedido com os dados do item
                    linha_completa = {**dados_pedido_atual, **item_dict}
                    dados_processados.append(linha_completa)

        log_auditoria.append({
            "passo": "Parsing de Blocos",
            "detalhe": f"Processadas {len(dados_processados)} linhas de itens de pedidos com sucesso."
        })

        # --- ETAPA 3: CONSTRUÇÃO DO DATAFRAME FINAL ---
        if not dados_processados:
            raise ValueError("Nenhum item de pedido foi encontrado na planilha. Verifique o formato.")

        df_pandas_limpo = pd.DataFrame(dados_processados)
        df_final_polars = pl.from_pandas(df_pandas_limpo)
        
        # Injeção da coluna de rastreabilidade
        df_final = df_final_polars.with_row_count(name="id_linha_original")

        return df_final, log_auditoria

    except Exception as e:
        log_auditoria.append({"passo": "Falha Crítica na Carga ou Parsing", "detalhe": str(e)})
        return None, log_auditoria