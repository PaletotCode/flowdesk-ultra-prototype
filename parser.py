from __future__ import annotations
import pandas as pd
import numpy as np
import unicodedata
from typing import Tuple, Dict, List, Optional

REQUIRED_HEADER_KEYS = ["tipo", "id", "vendedor", "cliente", "evolucao"]
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
    # Primeiro, removemos os pontos de milhar e depois trocamos a vírgula por ponto decimal
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None

def load_sheet(file, sheet_name: Optional[str] = None) -> pd.DataFrame:
    name = getattr(file, "name", "") if not isinstance(file, str) else file
    suffix = name.lower().split(".")[-1]
    engine = None
    if suffix == "ods":
        engine = "odf"
    elif suffix == "xlsx":
        engine = "openpyxl"
    elif suffix == "xls":
        engine = "xlrd" 
    
    # Lê todos os dados como string para evitar conversões automáticas
    df = pd.read_excel(file, sheet_name=sheet_name, header=None, dtype=str, engine=engine)
    return df

def find_header_index(df_raw: pd.DataFrame) -> int:
    """Encontra o índice da primeira linha que parece ser o cabeçalho do pedido."""
    for idx in range(min(30, len(df_raw))):
        row = df_raw.iloc[idx].astype(str).fillna("")
        normalized = [_norm_col(x) for x in row]
        # Verifica se as colunas essenciais estão presentes
        if all(key in normalized for key in REQUIRED_HEADER_KEYS):
            return idx
    raise ValueError("Linha de cabeçalho com ['Tipo','Id','Vendedor','Cliente','Evolução'] não encontrada.")

def normalize_columns(df: pd.DataFrame, header_idx: int) -> pd.DataFrame:
    """Aplica os nomes de colunas normalizados ao DataFrame."""
    headers = df.iloc[header_idx].tolist()
    cols = [_norm_col(h) for h in headers]
    
    # Corrige nomes duplicados adicionando um sufixo
    seen = {}
    final_cols = []
    for col in cols:
        if col in seen:
            seen[col] += 1
            final_cols.append(f"{col}_{seen[col]}")
        else:
            seen[col] = 0
            final_cols.append(col)

    df2 = df.iloc[header_idx + 1:].reset_index(drop=True).copy()
    df2.columns = final_cols
    return df2

def parse(df_raw: pd.DataFrame, debug: bool = False) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, List[str]]:
    logs: List[str] = []
    
    # 1) remover 3 linhas iniciais
    df = df_raw.iloc[3:].reset_index(drop=True)
    logs.append("Removidas as 3 primeiras linhas (banner).")

    # 2) localizar cabeçalho
    header_idx = find_header_index(df)
    logs.append(f"Cabeçalho encontrado em df_raw.iloc[3 + {header_idx}] (índice relativo {header_idx}).")

    # 3) normalizar colunas
    df_norm = normalize_columns(df, header_idx)
    logs.append(f"Colunas normalizadas: {list(df_norm.columns)}")

    # Atalhos para nomes de colunas críticos
    col_tipo = "tipo"
    col_id = "id"
    col_vendedor = "vendedor"
    col_cliente = "cliente"
    col_evolucao = "evolucao"
    col_nome = ITEM_NAME_KEY
    col_codigo = ITEM_CODE_KEY

    # 4) iterar com máquina de estados
    pedidos_rows: List[Dict] = []
    itens_rows: Dict[Tuple[str, str], Dict] = {}  # (pedido_id, codigo) -> item acumulado

    i = 0
    n = len(df_norm)

    while i < n:
        row = df_norm.iloc[i]
        
        # Detecta um novo bloco se a linha atual for um cabeçalho repetido ou se contiver um tipo de pedido válido
        tipo_pedido_val = str(row.get(col_tipo, "")).strip().upper()
        if tipo_pedido_val in {"PED", "ACU", "DEV"}:
            
            # linha de valores do pedido
            rv = row
            tipo_pedido = tipo_pedido_val
            pedido_id = str(rv.get(col_id, "")).strip()
            vendedor = str(rv.get(col_vendedor, "")).strip()
            cliente = str(rv.get(col_cliente, "")).strip()
            evolucao = str(rv.get(col_evolucao, "")).strip() if col_evolucao in df_norm.columns else ""

            if not pedido_id:
                pedido_id = f"UNKNOWN_{i}"

            pedidos_rows.append({
                "pedido_id": pedido_id,
                "tipo_pedido": tipo_pedido,
                "vendedor": vendedor,
                "cliente": cliente,
                "evolucao": evolucao,
            })
            logs.append(f"Pedido '{pedido_id}' capturado (linha {i}).")

            # 1 linha vazia (flag início itens)
            i += 1
            if i < n and not _is_blank_row(df_norm.iloc[i]):
                logs.append(f"[WARN] Esperado linha vazia antes de itens em {i}, mas não estava vazia. Tolerando.")
            i += 1 # Consumir a linha que deveria ser vazia

            # Consumir itens até 2 vazias ou novo cabeçalho/pedido
            blanks = 0
            while i < n:
                r = df_norm.iloc[i]
                
                if str(r.get(col_tipo, "")).strip().upper() in {"PED", "ACU", "DEV"}:
                    logs.append(f"Novo pedido encontrado na linha {i}. Fim dos itens do pedido '{pedido_id}'.")
                    break
                
                if _is_blank_row(r):
                    blanks += 1
                    if blanks >= 2:
                        logs.append(f"Duas linhas vazias em {i}. Fim dos itens do pedido '{pedido_id}'.")
                        i += 1
                        break
                    i += 1
                    continue
                blanks = 0

                # Ignorar linhas de cabeçalho de itens ou totais
                val_codigo = str(r.get(col_codigo, "")).strip()
                if val_codigo.lower() == 'codigo' or 'totais de' in val_codigo.lower():
                    logs.append(f"Ignorando linha de cabeçalho/total de itens em {i}.")
                    i+=1
                    continue
                
                nome = str(r.get(col_nome, "")).strip()
                marca = str(r.get("marca", "")).strip()
                promocao = str(r.get("promocao?", "")).strip() # O '?' pode ser normalizado
                quantidade = _to_float(r.get("quantidade", 0))
                preco_venda = _to_float(r.get("preco venda", 0))
                desconto = _to_float(r.get("juros/desc.", 0)) # Nome da coluna na planilha

                # Subtotal
                q = quantidade or 0.0
                p = preco_venda or 0.0
                d = desconto or 0.0
                subtotal = q * p + d
                
                if not val_codigo and not nome:
                    i+=1
                    continue

                key = (pedido_id, val_codigo or f"NO_CODE_{i}")
                if key not in itens_rows:
                    itens_rows[key] = {
                        "pedido_id": pedido_id, "codigo": val_codigo, "nome": nome,
                        "marca": marca, "promocao": promocao, "quantidade": q,
                        "preco_venda": p, "desconto": d, "subtotal_item": subtotal,
                        "linha_origem": int(i),
                    }
                else:
                    # Agrega itens repetidos
                    it = itens_rows[key]
                    it["quantidade"] += q
                    it["desconto"] += d
                    it["subtotal_item"] += subtotal

                i += 1
            continue

        i += 1  # Nenhuma condição especial, avança para a próxima linha

    df_pedidos = pd.DataFrame(pedidos_rows)
    if not df_pedidos.empty:
        df_pedidos["dt_extracao"] = pd.Timestamp.utcnow().tz_localize("UTC").isoformat()

    df_itens = pd.DataFrame(list(itens_rows.values()))

    # Totais por pedido
    if df_itens.empty:
        df_totais = pd.DataFrame(columns=["pedido_id", "qtd_itens", "valor_bruto", "valor_descontos", "valor_liquido"])
    else:
        df_itens["_bruto"] = df_itens["quantidade"].fillna(0) * df_itens["preco_venda"].fillna(0)
        grp = df_itens.groupby("pedido_id", dropna=False)
        df_totais = grp.agg(
            qtd_itens=("codigo", "nunique"),
            valor_bruto=("_bruto", "sum"),
            valor_descontos=("desconto", "sum"),
            valor_liquido=("subtotal_item", "sum"),
        ).reset_index()
        df_itens = df_itens.drop(columns=["_bruto"])

    for d in (df_pedidos, df_itens, df_totais):
        if not d.empty and "pedido_id" in d.columns:
            d.sort_values(["pedido_id"], inplace=True, kind="stable")

    return df_pedidos, df_itens, df_totais, logs