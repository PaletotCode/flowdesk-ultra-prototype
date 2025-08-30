import pandas as pd
import numpy as np
import unicodedata
from typing import Tuple, Dict, List, Optional

def parse(df_raw: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, List[str]]:
    
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

    logs: List[str] = []
    df = df_raw.iloc[3:].reset_index(drop=True)
    logs.append("Removidas as 3 primeiras linhas (banner).")

    pedidos_rows: List[Dict] = []
    itens_rows: Dict[Tuple[str, str], Dict] = {}

    i = 0
    n = len(df)
    
    main_header_found = False
    
    while i < n:
        row = df.iloc[i]
        
        # Detecta um cabeçalho de bloco (Tipo, Id, Vendedor...)
        if "Tipo" in row.values and "Id" in row.values and "Vendedor" in row.values:
            if not main_header_found:
                 logs.append(f"Cabeçalho principal encontrado no índice relativo {i}.")
                 main_header_found = True
            
            i += 1
            if i >= n: break
            
            # A linha seguinte contém os valores do pedido
            order_row = df.iloc[i]
            order_data = dict(zip(row, order_row))
            
            pedido_id = str(order_data.get("Id", "")).strip()
            if not pedido_id:
                pedido_id = f"UNKNOWN_{i}"
                logs.append(f"[WARN] Pedido com ID ausente na linha {i}. Usando '{pedido_id}'.")
            
            pedidos_rows.append({
                "pedido_id": pedido_id,
                "tipo_pedido": str(order_data.get("Tipo", "")).strip().upper(),
                "vendedor": str(order_data.get("Vendedor", "")).strip(),
                "cliente": str(order_data.get("Cliente", "")).strip(),
                "evolucao": str(order_data.get("Evolução", "")).strip(),
            })
            logs.append(f"Pedido '{pedido_id}' capturado (linha {i}).")
            
            i += 1 # Avança para a próxima linha (espera-se que seja vazia)
            
            # Pula linhas vazias até encontrar o cabeçalho dos itens
            while i < n and _is_blank_row(df.iloc[i]):
                i += 1

            if i >= n: continue
            
            # Linha atual é o cabeçalho dos itens (B:M => 1:13)
            item_header_row = df.iloc[i, 1:13]
            item_cols_norm = [_norm_col(h) for h in item_header_row]
            
            if 'codigo' not in item_cols_norm:
                logs.append(f"[ERROR] Cabeçalho de itens para o pedido '{pedido_id}' não contém 'Código' na faixa B:M. Itens ignorados.")
                # Continua a busca por um novo bloco de pedido
                while i < n:
                    if "Tipo" in df.iloc[i].values and "Id" in df.iloc[i].values:
                        break
                    i += 1
                continue

            i += 1 # Avança para a primeira linha de item

            # Processa as linhas de item
            blanks = 0
            while i < n:
                current_row = df.iloc[i]
                
                # Condição de término: novo cabeçalho principal
                if "Tipo" in current_row.values and "Id" in current_row.values:
                    logs.append(f"Novo cabeçalho principal detectado em {i}. Fim dos itens para '{pedido_id}'.")
                    break

                if _is_blank_row(current_row):
                    blanks += 1
                    if blanks >= 2:
                        logs.append(f"Duas linhas vazias em {i}. Fim dos itens para '{pedido_id}'.")
                        i += 1
                        break
                    i += 1
                    continue
                blanks = 0
                
                item_data_raw = dict(zip(item_cols_norm, current_row[1:13]))
                
                nome = str(item_data_raw.get('nome', '')).strip()
                if nome.lower() == 'totais de pedidos':
                    logs.append(f"Linha 'Totais de pedidos' ignorada em {i}.")
                    i += 1
                    continue
                
                codigo = str(item_data_raw.get('codigo', '')).strip()
                if not codigo: # Pula linhas sem código de item
                    i += 1
                    continue

                q = _to_float(item_data_raw.get('quantidade', 0)) or 0.0
                p = _to_float(item_data_raw.get('preco venda', 0)) or 0.0
                d = _to_float(item_data_raw.get('juros/desc.', 0)) or _to_float(item_data_raw.get('desconto', 0)) or 0.0
                subtotal = q * p + d
                
                key = (pedido_id, codigo)

                if key not in itens_rows:
                    itens_rows[key] = {
                        "pedido_id": pedido_id,
                        "codigo": codigo,
                        "nome": nome,
                        "marca": str(item_data_raw.get('marca', '')).strip(),
                        "promocao": str(item_data_raw.get('promocao?', '')).strip(),
                        "quantidade": q,
                        "preco_venda": p,
                        "desconto": d,
                        "subtotal_item": subtotal,
                        "linha_origem": i,
                    }
                else:
                    itens_rows[key]['quantidade'] += q
                    itens_rows[key]['desconto'] += d
                    itens_rows[key]['subtotal_item'] += subtotal
                
                i += 1
            continue
        
        i += 1

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