from __future__ import annotations
import pandas as pd
import numpy as np
import unicodedata
from typing import Tuple, Dict, List, Optional

REQUIRED_HEADER_KEYS = ["tipo", "id", "vendedor", "cliente"]
ITEM_NAME_KEY = "nome"
ITEM_CODE_KEY = "codigo"

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
    except ValueError:
        return None

def load_sheet(file) -> pd.DataFrame:
    """Carrega a primeira planilha de um arquivo ODS, XLS ou XLSX como um DataFrame."""
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

def find_header_index(df_raw: pd.DataFrame) -> int:
    """Encontra o índice da primeira linha que contém as colunas essenciais."""
    for idx in range(min(30, len(df_raw))):
        row = df_raw.iloc[idx].astype(str).fillna("")
        normalized = [_norm_col(x) for x in row]
        if all(key in normalized for key in REQUIRED_HEADER_KEYS):
            return idx
    raise ValueError(f"Linha de cabeçalho com {REQUIRED_HEADER_KEYS} não encontrada.")

def normalize_columns(df: pd.DataFrame, header_idx: int) -> pd.DataFrame:
    """Aplica os nomes de colunas normalizados e retorna o DataFrame a partir dos dados."""
    headers = df.iloc[header_idx].tolist()
    
    cols_seen = {}
    normalized_cols = []
    for h in headers:
        norm_h = _norm_col(h)
        if norm_h in cols_seen:
            cols_seen[norm_h] += 1
            normalized_cols.append(f"{norm_h}_{cols_seen[norm_h]}")
        else:
            cols_seen[norm_h] = 0
            normalized_cols.append(norm_h)

    df2 = df.iloc[header_idx + 1:].reset_index(drop=True).copy()
    df2.columns = normalized_cols
    return df2

def parse(df_raw: pd.DataFrame, debug: bool = False) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, List[str]]:
    logs: List[str] = []
    
    df = df_raw.iloc[3:].reset_index(drop=True)
    logs.append("Removidas as 3 primeiras linhas (banner).")

    header_idx = find_header_index(df)
    logs.append(f"Cabeçalho principal encontrado no índice relativo {header_idx}.")

    df_norm = normalize_columns(df, header_idx)
    logs.append(f"Colunas normalizadas: {list(df_norm.columns)}")

    col_tipo, col_id, col_vendedor, col_cliente = "tipo", "id", "vendedor", "cliente"
    col_evolucao = "evolucao"
    col_nome, col_codigo = ITEM_NAME_KEY, ITEM_CODE_KEY
    
    pedidos_rows: List[Dict] = []
    itens_rows: Dict[Tuple[str, str], Dict] = {}

    i = 0
    n = len(df_norm)
    while i < n:
        row = df_norm.iloc[i]
        tipo_pedido = str(row.get(col_tipo, "")).strip().upper()

        if tipo_pedido in {"PED", "ACU", "DEV"}:
            pedido_id = str(row.get(col_id, f"UNKNOWN_{i}")).strip()
            
            pedidos_rows.append({
                "pedido_id": pedido_id,
                "tipo_pedido": tipo_pedido,
                "vendedor": str(row.get(col_vendedor, "")).strip(),
                "cliente": str(row.get(col_cliente, "")).strip(),
                "evolucao": str(row.get(col_evolucao, "")).strip() if col_evolucao in df_norm.columns else "",
            })
            logs.append(f"Pedido '{pedido_id}' capturado (linha {i}).")

            i += 1
            if i < n and not _is_blank_row(df_norm.iloc[i]):
                logs.append(f"[WARN] Esperava-se uma linha vazia após os dados do pedido em {i}, mas não foi encontrada. Continuando.")
            i += 1

            blanks = 0
            while i < n:
                r = df_norm.iloc[i]
                
                if str(r.get(col_tipo, "")).strip().upper() in {"PED", "ACU", "DEV"}:
                    logs.append(f"Novo pedido detectado em {i}. Fim dos itens para '{pedido_id}'.")
                    break
                
                if _is_blank_row(r):
                    blanks += 1
                    if blanks >= 2:
                        logs.append(f"Duas linhas vazias em {i}. Fim dos itens para '{pedido_id}'.")
                        i += 1
                        break
                    i += 1
                    continue
                blanks = 0

                val_nome = str(r.get(col_nome, "")).strip()
                if val_nome.lower().startswith("totais de"):
                    logs.append(f"Linha de total ignorada em {i}: '{val_nome}'.")
                    i += 1
                    continue
                
                codigo = str(r.get(col_codigo, "")).strip()
                if not codigo and not val_nome:
                    i+=1
                    continue
                
                key = (pedido_id, codigo or f"NO_CODE_{i}")
                
                q = _to_float(r.get("quantidade", 0)) or 0.0
                p = _to_float(r.get("preco venda", 0)) or 0.0
                d = _to_float(r.get("juros/desc.", 0)) or _to_float(r.get("desconto", 0)) or 0.0

                if key not in itens_rows:
                    itens_rows[key] = {
                        "pedido_id": pedido_id, "codigo": codigo, "nome": val_nome,
                        "marca": str(r.get("marca", "")).strip(),
                        "promocao": str(r.get("promocao?", "")).strip(),
                        "quantidade": q, "preco_venda": p, "desconto": d,
                        "subtotal_item": q * p + d, "linha_origem": i,
                    }
                else:
                    itens_rows[key]["quantidade"] += q
                    itens_rows[key]["desconto"] += d
                    itens_rows[key]["subtotal_item"] += (q * p + d)
                
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
            qtd_itens=("codigo", "nunique"), valor_bruto=("_bruto", "sum"),
            valor_descontos=("desconto", "sum"), valor_liquido=("subtotal_item", "sum"),
        ).reset_index()
        df_itens.drop(columns=["_bruto"], inplace=True)

    for d in (df_pedidos, df_itens, df_totais):
        if not d.empty and "pedido_id" in d.columns:
            d.sort_values("pedido_id", inplace=True, kind="stable")

    return df_pedidos, df_itens, df_totais, logs