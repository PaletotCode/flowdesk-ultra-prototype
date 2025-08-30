import streamlit as st
import pandas as pd
import numpy as np
import unicodedata
from typing import Tuple, Dict, List, Optional

# ==============================================================================
# LÓGICA DE PARSING (INTEGRADA DIRETAMENTE NO APP)
# ==============================================================================

def _strip_accents(s: str) -> str:
    if s is None or (isinstance(s, float) and np.isnan(s)):
        return ""
    s = str(s).strip()
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

def _norm_col(col: str) -> str:
    return _strip_accents(col).lower().replace("  ", " ").replace("\n", " ").replace("\t", " ").strip()

def _is_blank_row(row: pd.Series) -> bool:
    return all((str(x).strip() == "" or pd.isna(x)) for x in row)

def _to_float(x) -> Optional[float]:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return None
    s = str(x).strip()
    if s == "":
        return None
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except (ValueError, TypeError):
        return None

def load_sheet(file) -> pd.DataFrame:
    name = getattr(file, "name", "") if not isinstance(file, str) else file
    suffix = name.lower().split(".")[-1]
    engine = None
    if suffix == "ods":
        engine = "odf"
    elif suffix == "xlsx":
        engine = "openpyxl"
    elif suffix == "xls":
        engine = "xlrd"
    
    df = pd.read_excel(file, sheet_name=0, header=None, dtype=str, engine=engine)
    return df

def parse(df_raw: pd.DataFrame, debug: bool = False) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, List[str]]:
    logs: List[str] = []
    logs.append("Iniciando o processo de parsing.")
    df = df_raw.iloc[3:].reset_index(drop=True)
    logs.append("Removidas as 3 primeiras linhas (banner).")

    main_header_row = None
    for idx, row in df.iterrows():
        if "Tipo" in row.values and "Id" in row.values and "Vendedor" in row.values:
            main_header_row = row
            logs.append(f"Cabeçalho principal de referência encontrado no índice relativo {idx}.")
            break
            
    if main_header_row is None:
        raise ValueError("Nenhum cabeçalho principal ('Tipo', 'Id', 'Vendedor') foi encontrado.")

    pedidos_rows: List[Dict] = []
    itens_rows: Dict[Tuple[str, str], Dict] = {}
    
    i = 0
    n = len(df)
    
    while i < n:
        row = df.iloc[i]
        
        is_header = "Tipo" in row.values and "Id" in row.values
        order_data_row_index = -1
        if is_header:
            order_data_row_index = i + 1
        elif str(row.iloc[0]).strip().upper() in {"PED", "ACU", "DEV"}:
            order_data_row_index = i
        
        if order_data_row_index != -1 and order_data_row_index < n:
            order_row = df.iloc[order_data_row_index]
            order_data = dict(zip(main_header_row, order_row))

            pedido_id = str(order_data.get("Id", "")).strip()
            if not pedido_id:
                pedido_id = f"UNKNOWN_{order_data_row_index}"
                logs.append(f"[WARN] Pedido com ID ausente na linha {order_data_row_index}. Usando '{pedido_id}'.")

            logs.append(f"--- Novo Bloco Encontrado ---")
            logs.append(f"Pedido '{pedido_id}' capturado a partir da linha {order_data_row_index}.")
            
            pedidos_rows.append({
                "pedido_id": pedido_id,
                "tipo_pedido": str(order_data.get("Tipo", "")).strip().upper(),
                "vendedor": str(order_data.get("Vendedor", "")).strip(),
                "cliente": str(order_data.get("Cliente", "")).strip(),
                "evolucao": str(order_data.get("Evolução", "")).strip(),
            })

            i = order_data_row_index + 1
            
            if i < n and _is_blank_row(df.iloc[i]):
                logs.append(f"  -> Linha vazia (flag de itens) encontrada em {i}.")
                i += 1
            else:
                logs.append(f"  -> [WARN] Nenhuma linha vazia encontrada após os dados do pedido em {i-1}.")

            if i < n and not _is_blank_row(df.iloc[i]):
                item_header_raw = df.iloc[i, 1:13]
                item_cols_norm = [_norm_col(h) for h in item_header_raw]
                logs.append(f"  -> Potencial cabeçalho de itens encontrado em {i}. Colunas: {item_cols_norm}")

                if 'codigo' in item_cols_norm:
                    i += 1
                    logs.append(f"  -> Inciando busca por itens para o pedido '{pedido_id}' a partir da linha {i}...")
                    blanks = 0
                    while i < n:
                        item_row = df.iloc[i]
                        
                        if "Tipo" in item_row.values and "Id" in item_row.values:
                            logs.append(f"  -> FIM DOS ITENS: Novo cabeçalho principal encontrado em {i}.")
                            break
                        
                        if _is_blank_row(item_row):
                            blanks += 1
                            if blanks >= 2:
                                logs.append(f"  -> FIM DOS ITENS: Duas linhas vazias consecutivas encontradas em {i}.")
                                i += 1
                                break
                            i += 1
                            continue
                        blanks = 0
                        
                        item_data_raw = dict(zip(item_cols_norm, item_row[1:13]))
                        
                        nome = str(item_data_raw.get('nome', '')).strip()
                        if nome.lower().startswith('totais de'):
                            logs.append(f"    - Linha de total ignorada em {i}.")
                            i += 1
                            continue

                        codigo = str(item_data_raw.get('codigo', '')).strip()
                        if not codigo:
                            i += 1
                            continue

                        logs.append(f"    - Item encontrado em {i}: Código='{codigo}', Nome='{nome}'")

                        q = _to_float(item_data_raw.get('quantidade', 0)) or 0.0
                        p = _to_float(item_data_raw.get('preco venda', 0)) or 0.0
                        desconto_val = item_data_raw.get('juros/desc.') or item_data_raw.get('desconto')
                        d = _to_float(desconto_val) or 0.0
                        subtotal = q * p + d
                        
                        key = (pedido_id, codigo)
                        if key not in itens_rows:
                            itens_rows[key] = {
                                "pedido_id": pedido_id, "codigo": codigo, "nome": nome,
                                "marca": str(item_data_raw.get('marca', '')).strip(),
                                "promocao": str(item_data_raw.get('promocao?', '')).strip(),
                                "quantidade": q, "preco_venda": p, "desconto": d,
                                "subtotal_item": subtotal, "linha_origem": i,
                            }
                        else:
                            logs.append(f"      -> Agregando item repetido: Código='{codigo}'")
                            itens_rows[key]['quantidade'] += q
                            itens_rows[key]['desconto'] += d
                            itens_rows[key]['subtotal_item'] += subtotal
                        
                        i += 1
                    continue
                else:
                    logs.append(f"  -> [ERROR] Cabeçalho de itens inválido para o pedido '{pedido_id}' em {i}. 'código' não encontrado.")
                    i += 1
            else:
                logs.append(f"  -> [WARN] Nenhuma linha de cabeçalho de itens encontrada para o pedido '{pedido_id}'.")
                i += 1
        else:
            i += 1
            
    logs.append("Fim do processo de parsing.")

    df_pedidos = pd.DataFrame(pedidos_rows)
    if not df_pedidos.empty:
        df_pedidos["dt_extracao"] = pd.Timestamp.utcnow().isoformat()

    df_itens = pd.DataFrame(list(itens_rows.values()))

    if df_itens.empty:
        df_totais = pd.DataFrame(columns=["pedido_id", "qtd_itens", "valor_bruto", "valor_descontos", "valor_liquido"])
    else:
        df_itens["_bruto"] = df_itens["quantidade"] * df_itens["preco_venda"]
        grp = df_itens.groupby("pedido_id")
        df_totais = grp.agg(
            qtd_itens=("codigo", "nunique"),
            valor_bruto=("_bruto", "sum"),
            valor_descontos=("desconto", "sum"),
            valor_liquido=("subtotal_item", "sum"),
        ).reset_index()
        df_itens.drop(columns=["_bruto"], inplace=True)

    return df_pedidos, df_itens, df_totais, logs

# ==============================================================================
# INTERFACE DO STREAMLIT
# ==============================================================================

st.set_page_config(page_title="Parser de Pedidos", layout="wide")

st.title("📄 Parser de Pedidos para DataFrame Estruturado")
st.markdown("Faça o upload de sua planilha de vendas (`.ods`, `.xls`, `.xlsx`) para extrair os pedidos e itens de forma organizada.")

uploaded = st.file_uploader("Selecione o arquivo", type=["ods","xls","xlsx"])
debug = st.sidebar.checkbox("Exibir logs de debug", value=True)

if uploaded:
    prog = st.progress(0, text="Aguardando processamento…")
    try:
        prog.progress(10, text=f"Lendo o arquivo '{uploaded.name}'…")
        df_raw = load_sheet(uploaded)

        prog.progress(30, text="Analisando e extraindo dados…")
        df_pedidos, df_itens, df_totais, logs = parse(df_raw, debug=debug)

        prog.progress(90, text="Renderizando resultados…")
        
        st.success(f"🎉 Processamento concluído! Foram encontrados **{len(df_pedidos)}** pedidos e **{len(df_itens)}** itens únicos.")

        tabs = st.tabs(["🛒 Pedidos", "📦 Itens", "📊 Totais por Pedido"])

        with tabs[0]:
            st.dataframe(df_pedidos, use_container_width=True, hide_index=True)
            st.download_button("Baixar Pedidos (CSV)", df_pedidos.to_csv(index=False).encode("utf-8"), "pedidos.csv", "text/csv", key="download_pedidos")

        with tabs[1]:
            st.dataframe(df_itens, use_container_width=True, hide_index=True)
            st.download_button("Baixar Itens (CSV)", df_itens.to_csv(index=False).encode("utf-8"), "itens.csv", "text/csv", key="download_itens")

        with tabs[2]:
            st.dataframe(df_totais, use_container_width=True, hide_index=True)
            st.download_button("Baixar Totais (CSV)", df_totais.to_csv(index=False).encode("utf-8"), "totais.csv", "text/csv", key="download_totais")

        if debug:
            with st.sidebar.expander("📝 Logs de Parsing", expanded=True):
                st.code("\n".join(logs), language='log')

        prog.progress(100, text="Finalizado.")

    except Exception as e:
        st.error(f"Ocorreu um erro durante o processamento: {e}")
        st.exception(e) 
        prog.progress(100, text="Erro!")
else:
    st.info("Aguardando o upload de um arquivo para iniciar.")