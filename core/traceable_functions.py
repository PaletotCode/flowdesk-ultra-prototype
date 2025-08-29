# core/traceable_functions.py
import polars as pl
from typing import List, Dict, Any, Union

def calcular_metrica(
    df: pl.DataFrame,
    log_auditoria: List[Dict[str, Any]],
    nome_metrica: str,
    expressao_polars: pl.Expr,
    filtros_aplicados: Dict[str, Any] = None
) -> Union[float, int, str, None]:
    """
    Calcula uma métrica aplicando uma expressão Polars a um DataFrame filtrado
    e registra um log detalhado da operação.

    Args:
        df: O DataFrame Polars de origem (com id_linha_original).
        log_auditoria: A lista de log de auditoria para ser atualizada.
        nome_metrica: Um nome amigável para a métrica (ex: "Vendas Totais").
        expressao_polars: A expressão Polars a ser executada (ex: pl.sum("valor_venda")).
        filtros_aplicados: Um dicionário descrevendo os filtros para o log.

    Returns:
        O resultado da métrica calculada.
    """
    # Aplica filtros se existirem
    if filtros_aplicados:
        # Constrói expressões de filtro dinâmicamente
        filtros_expr = []
        for coluna, valor in filtros_aplicados.items():
            if isinstance(valor, (list, tuple)):
                filtros_expr.append(pl.col(coluna).is_in(valor))
            else:
                filtros_expr.append(pl.col(coluna) == valor)
        
        df_filtrado = df.filter(pl.all_horizontal(filtros_expr)) if filtros_expr else df
    else:
        df_filtrado = df

    # Captura os IDs das linhas que contribuíram para o cálculo
    ids_originais_afetados = df_filtrado['id_linha_original'].to_list()

    if not ids_originais_afetados:
        resultado = 0  # ou None, dependendo da regra de negócio
    else:
        try:
            resultado = df_filtrado.select(expressao_polars).item()
        except Exception as e:
            resultado = None
            log_entry = {
                "passo": f"Erro no Cálculo Métrica: {nome_metrica}",
                "detalhe": f"Erro na expressão Polars: {str(e)} | Filtros: {filtros_aplicados}",
                "linhas_originais_afetadas": ids_originais_afetados,
                "numero_linhas_usadas": len(ids_originais_afetados),
                "resultado": None,
                "erro": str(e)
            }
            log_auditoria.append(log_entry)
            return resultado

    log_entry = {
        "passo": f"Cálculo Métrica: {nome_metrica}",
        "detalhe": f"Expressão Polars: {str(expressao_polars)} | Filtros: {filtros_aplicados or 'Nenhum'}",
        "linhas_originais_afetadas": ids_originais_afetados,
        "numero_linhas_usadas": len(ids_originais_afetados),
        "resultado": resultado
    }
    
    log_auditoria.append(log_entry)
    
    return resultado