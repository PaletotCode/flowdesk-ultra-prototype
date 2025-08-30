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
    # Normaliza o nome da coluna para uma chave de dicionário consistente
    return _strip_accents(col).lower().replace("  ", " ").replace("\n", " ").replace("\t", " ").replace(".", "").replace("/", "").replace(" ", "_").strip()

def _is_blank_row(row: pd.Series) -> bool:
    return all((str(x).strip() == "" or pd.isna(x)) for x in row)

def _to_float(x) -> float:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return 0.0
    s = str(x).strip().lower()
    if s == "" or s == 'nan':
        return 0.0
    
    if ',' in s and '.' in s:
        if s.rfind('.') > s.rfind(','):
            s = s.replace(',', '')
        else:
            s = s.replace('.', '').replace(',', '.')
    elif ',' in s:
        s = s.replace(',', '.')
        
    try:
        return float(s)
    except (ValueError, TypeError):
        return 0.0

def _to_percent_float(x) -> float:
    # Converte uma string de percentual (ex: '38,70%') para um float (ex: 0.387)
    if x is None:
        return 0.0
    s = str(x).strip().replace('%', '')
    return _to_float(s) / 100.0 if s else 0.0
    
def _get_str_val(data: dict, key: str) -> str:
    # Obtém um valor de dicionário normalizado como string
    return str(data.get(key, "") or "").strip()

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
        # Usa um subconjunto chave para identificar o cabeçalho
        row_values = [str(v) for v in row.values]
        if "Tipo" in row_values and "Id" in row_values and "Vendedor" in row_values:
            main_header_row = row
            logs.append(f"Cabeçalho principal de referência encontrado no índice relativo {idx}.")
            break
            
    if main_header_row is None:
        raise ValueError("Nenhum cabeçalho principal ('Tipo', 'Id', 'Vendedor') foi encontrado.")

    # Normaliza os nomes do cabeçalho principal para usar como chaves
    main_header_keys = [_norm_col(h) for h in main_header_row]
    
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
            # Mapeia os valores da linha para as chaves normalizadas do cabeçalho
            order_data = dict(zip(main_header_keys, order_row))

            pedido_id = _get_str_val(order_data, 'id')
            if not pedido_id:
                pedido_id = f"UNKNOWN_{order_data_row_index}"
            
            # --- CAPTURA DE TODAS AS COLUNAS DO PEDIDO ---
            pedidos_rows.append({
                "pedido_id": pedido_id,
                "tipo_pedido": _get_str_val(order_data, 'tipo'),
                "vendedor": _get_str_val(order_data, 'vendedor'),
                "cliente": _get_str_val(order_data, 'cliente'),
                "data_cad_cliente": _get_str_val(order_data, 'data_cad_cliente'),
                "origem_cliente": _get_str_val(order_data, 'origem_cliente'),
                "telefone_cliente": _get_str_val(order_data, 'telefone_cliente'),
                "data_hora_fechamento": _get_str_val(order_data, 'datahora_fechamento'),
                "data_hora_recebimento": _get_str_val(order_data, 'datahora_recebimento'),
                "vlr_produtos": _to_float(_get_str_val(order_data, 'vlr_produtos')),
                "vlr_servicos": _to_float(_get_str_val(order_data, 'vlr_servicos')),
                "frete": _to_float(_get_str_val(order_data, 'frete')),
                "out_desp": _to_float(_get_str_val(order_data, 'out_desp')),
                "juros": _to_float(_get_str_val(order_data, 'juros')),
                "tc": _to_float(_get_str_val(order_data, 'tc')),
                "desconto": _to_float(_get_str_val(order_data, 'desconto')),
                "cred_man": _to_float(_get_str_val(order_data, 'cred_man')),
                "vlr_liquido": _to_float(_get_str_val(order_data, 'vlr_liquido')),
                "custo": _to_float(_get_str_val(order_data, 'custo')),
                "percent_lucro": _to_percent_float(_get_str_val(order_data, '%lucro')),
                "juros_embutidos": _to_float(_get_str_val(order_data, 'juros_embutidos')),
                "frete_cif_embutidos": _to_float(_get_str_val(order_data, 'frete_cif_embutidos')),
                "retencao_real": _to_float(_get_str_val(order_data, 'retencao_real')),
                "base_lucro_pres": _to_float(_get_str_val(order_data, 'base_lucro_pres')),
                "percent_lucro_pres": _to_percent_float(_get_str_val(order_data, '%lucro_pres')),
                "vlr_lucro_pres": _to_float(_get_str_val(order_data, 'vlr_lucro_pres')),
                "custo_compra": _to_float(_get_str_val(order_data, 'custo_compra')),
                "vendedor_externo": _get_str_val(order_data, 'vendedor_externo'),
                "dt_cad_cliente": _get_str_val(order_data, 'dt_cad_cliente'),
                "origem": _get_str_val(order_data, 'origem'),
                "prazo_medio": _to_float(_get_str_val(order_data, 'prazo_medio')),
                "desconto_geral": _to_float(_get_str_val(order_data, 'desconto_geral')),
                "percent_desconto_geral": _to_percent_float(_get_str_val(order_data, '%_desconto_geral')),
                "valor_impulso": _to_float(_get_str_val(order_data, 'valor_impulso')),
                "valor_brinde": _to_float(_get_str_val(order_data, 'valor_brinde')),
                "ent_agrupada": _get_str_val(order_data, 'ent_agrupada'),
                "usuario_insercao": _get_str_val(order_data, 'usuario_insercao'),
                "vlr_comis_emp_vda_direta": _to_float(_get_str_val(order_data, 'vlr_comis_emp_vda_direta')),
                "tab_preco": _get_str_val(order_data, 'tab_preco'),
                "pedido_da_devolucao": _get_str_val(order_data, 'pedido_da_devolucao'),
            })

            i = order_data_row_index + 1
            if not (i < n and _is_blank_row(df.iloc[i])): i -= 1 # Volta se não achou linha em branco
            i += 1
            if i < n and not _is_blank_row(df.iloc[i]): i += 1
            
            if i < n and not _is_blank_row(df.iloc[i]):
                item_header_raw = df.iloc[i]
                # Corrige a duplicação de "preço venda"
                seen = {}; item_header_dedup = []
                for item in item_header_raw:
                    item_str = str(item)
                    if item_str in seen: seen[item_str] += 1; item_header_dedup.append(f"{item_str}_{seen[item_str]}")
                    else: seen[item_str] = 0; item_header_dedup.append(item_str)
                
                item_cols_norm = [_norm_col(h) for h in item_header_dedup]
                
                if 'codigo' in item_cols_norm:
                    i += 1
                    blanks = 0
                    while i < n:
                        item_row = df.iloc[i]
                        if "Tipo" in item_row.values and "Id" in item_row.values: break
                        if _is_blank_row(item_row):
                            blanks += 1
                            if blanks >= 2: i += 1; break
                            i += 1
                            continue
                        blanks = 0
                        
                        item_data = dict(zip(item_cols_norm, item_row))
                        
                        codigo = _get_str_val(item_data, 'codigo')
                        if not codigo: i += 1; continue
                        
                        q = _to_float(_get_str_val(item_data, 'quantidade'))
                        p = _to_float(_get_str_val(item_data, 'preco_venda'))
                        d = _to_float(_get_str_val(item_data, 'jurosdesc'))
                        
                        key = (pedido_id, codigo)
                        if key not in itens_rows:
                            itens_rows[key] = {
                                "pedido_id": pedido_id,
                                "codigo": codigo,
                                "nome": _get_str_val(item_data, 'nome'),
                                "marca": _get_str_val(item_data, 'marca'),
                                "promocao": _get_str_val(item_data, 'promocao'),
                                "quantidade": q,
                                "preco_venda": p,
                                "juros_desc": d,
                                "total_liquido": _to_float(_get_str_val(item_data, 'total_liquido')),
                                "valor_custo": _to_float(_get_str_val(item_data, 'valor_custo')),
                                "percent_lucro": _to_percent_float(_get_str_val(item_data, '%_lucro')),
                                "custo_compra": _to_float(_get_str_val(item_data, 'custo_compra')),
                                "linha_origem": i,
                            }
                        else:
                            itens_rows[key]['quantidade'] += q
                            itens_rows[key]['juros_desc'] += d
                        i += 1
                    continue
            i += 1
        else:
            i += 1
            
    df_pedidos = pd.DataFrame(pedidos_rows)
    if not df_pedidos.empty:
        df_pedidos["dt_extracao"] = pd.Timestamp.utcnow().isoformat()

    df_itens = pd.DataFrame(list(itens_rows.values()))
    
    # Recalcula o subtotal do item após agregação
    if not df_itens.empty:
        df_itens["subtotal_item"] = (df_itens["quantidade"] * df_itens["preco_venda"]) + df_itens["juros_desc"]

    if df_itens.empty:
        df_totais = pd.DataFrame(columns=["pedido_id", "qtd_itens", "valor_bruto", "valor_descontos", "valor_liquido"])
    else:
        df_itens["_bruto"] = df_itens["quantidade"] * df_itens["preco_venda"]
        grp = df_itens.groupby("pedido_id")
        df_totais = grp.agg(
            qtd_itens=("codigo", "nunique"),
            valor_bruto=("_bruto", "sum"),
            valor_descontos=("juros_desc", "sum"),
            valor_liquido=("subtotal_item", "sum"),
        ).reset_index()
        df_itens.drop(columns=["_bruto"], inplace=True, errors='ignore')

    return df_pedidos, df_itens, df_totais, logs

# ==============================================================================
# INTERFACE DO STREAMLIT
# ==============================================================================

st.set_page_config(page_title="Parser de Pedidos", layout="wide")
st.title("📄 Parser de Pedidos para DataFrame Estruturado")
st.markdown("Faça o upload de sua planilha de vendas (`.ods`, `.xls`, `.xlsx`) para extrair os pedidos e itens de forma organizada.")

uploaded = st.file_uploader("Selecione o arquivo", type=["ods","xls","xlsx"])
debug = st.sidebar.checkbox("Exibir logs de debug", value=False)

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
            st.dataframe(df_pedidos, hide_index=True, use_container_width=True)
            st.download_button("Baixar Pedidos (CSV)", df_pedidos.to_csv(index=False).encode("utf-8"), "pedidos.csv", "text/csv", key="download_pedidos", use_container_width=True)
        with tabs[1]:
            st.dataframe(df_itens, hide_index=True, use_container_width=True)
            st.download_button("Baixar Itens (CSV)", df_itens.to_csv(index=False).encode("utf-8"), "itens.csv", "text/csv", key="download_itens", use_container_width=True)
        with tabs[2]:
            st.dataframe(df_totais, hide_index=True, use_container_width=True)
            st.download_button("Baixar Totais (CSV)", df_totais.to_csv(index=False).encode("utf-8"), "totais.csv", "text/csv", key="download_totais", use_container_width=True)

        if debug:
            with st.sidebar.expander("📝 Logs de Parsing", expanded=True):
                MAX_LOG_LINES = 1000
                if len(logs) > MAX_LOG_LINES:
                    log_display = logs[:500] + [f"\n... (log truncado, {len(logs) - 1000} linhas omitidas) ...\n"] + logs[-500:]
                    st.code("\n".join(log_display), language='log')
                    st.download_button(label=" baixar log completo", data="\n".join(logs).encode('utf-8'), file_name="parsing_log.txt", mime="text/plain")
                else:
                    st.code("\n".join(logs), language='log')
        prog.progress(100, text="Finalizado.")
    except Exception as e:
        st.error(f"Ocorreu um erro durante o processamento: {e}")
        st.exception(e) 
        prog.progress(100, text="Erro!")
else:
    st.info("Aguardando o upload de um arquivo para iniciar.")