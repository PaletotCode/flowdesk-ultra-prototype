# ui/smart_dashboard.py - Dashboard que trabalha com estrutura identificada
import streamlit as st
import polars as pl
from typing import List, Dict, Any
from core.smart_data_analyzer import DataStructure, ColumnInfo
from core.traceable_functions import calcular_metrica

def render_structure_report(estrutura: DataStructure, relatorio: str):
    """
    Renderiza o relatório de estrutura identificada
    """
    with st.expander("📋 Relatório de Estrutura Identificada", expanded=True):
        st.markdown(relatorio)

def render_smart_dashboard(df: pl.DataFrame, estrutura: DataStructure, log: List[Dict[str, Any]]):
    """
    Renderiza dashboard baseado na estrutura identificada automaticamente
    """
    st.header("🧠 Dashboard Inteligente")
    st.markdown("*Dashboard gerado automaticamente baseado na estrutura dos seus dados*")
    
    # Informações básicas
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📊 Total de Linhas", f"{df.height:,}")
    with col2:
        st.metric("🗂️ Colunas Válidas", f"{len(estrutura.columns)}")
    with col3:
        st.metric("📈 Taxa de Preenchimento", f"{_calcular_taxa_preenchimento(df):.1f}%")
    with col4:
        st.metric("🎯 Confiança Média", f"{_calcular_confianca_media(estrutura):.1f}%")
    
    st.divider()
    
    # Dashboard por padrões identificados
    _render_vendas_dashboard(df, estrutura, log)
    _render_vendedores_dashboard(df, estrutura, log)
    _render_clientes_dashboard(df, estrutura, log)
    _render_produtos_dashboard(df, estrutura, log)

def _calcular_taxa_preenchimento(df: pl.DataFrame) -> float:
    """Calcula a taxa de preenchimento geral do DataFrame."""
    if df.is_empty():
        return 0.0
    
    total_cells = df.height * df.width
    if total_cells == 0:
        return 100.0
    
    # Linha corrigida com a expressão Polars idiomática
    null_count = df.null_count().select(pl.sum_horizontal("*")).item()
    
    filled_cells = total_cells - null_count
    return (filled_cells / total_cells) * 100

def _calcular_confianca_media(estrutura: DataStructure) -> float:
    """
    Calcula a confiança média das colunas identificadas
    """
    if not estrutura.columns:
        return 0.0
    
    return sum(col.confidence_score for col in estrutura.columns) / len(estrutura.columns) * 100

def _render_vendas_dashboard(df: pl.DataFrame, estrutura: DataStructure, log: List):
    """
    Renderiza métricas de vendas baseadas nas colunas identificadas
    """
    valor_cols = estrutura.patterns.get('valor_columns', [])
    if not valor_cols:
        st.warning("💰 **Colunas de valores não identificadas automaticamente**")
        return
    
    st.subheader("💰 Análise de Vendas")
    
    # Usa a primeira coluna de valor identificada
    coluna_principal = valor_cols[0]
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Valor Total
        valor_total = calcular_metrica(
            df=df,
            log_auditoria=log,
            nome_metrica=f"Valor Total ({coluna_principal.name})",
            expressao_polars=pl.col(coluna_principal.name).cast(pl.Float64, strict=False).sum(),
            filtros_aplicados=None
        )
        
        if valor_total is not None:
            st.metric("💵 Valor Total", f"R$ {valor_total:,.2f}")
        else:
            st.metric("💵 Valor Total", "Erro no cálculo")
        
        with st.expander("🔍 Detalhes do Cálculo"):
            if log:
                st.json(log[-1])
    
    with col2:
        # Ticket Médio
        ticket_medio = calcular_metrica(
            df=df,
            log_auditoria=log,
            nome_metrica=f"Ticket Médio ({coluna_principal.name})",
            expressao_polars=pl.col(coluna_principal.name).cast(pl.Float64, strict=False).mean(),
            filtros_aplicados=None
        )
        
        if ticket_medio is not None:
            st.metric("📊 Ticket Médio", f"R$ {ticket_medio:,.2f}")
        else:
            st.metric("📊 Ticket Médio", "Erro no cálculo")
            
        with st.expander("🔍 Detalhes do Cálculo"):
            if log:
                st.json(log[-1])
    
    with col3:
        # Número de Transações
        num_transacoes = calcular_metrica(
            df=df,
            log_auditoria=log,
            nome_metrica="Número de Transações",
            expressao_polars=pl.count(),
            filtros_aplicados=None
        )
        
        if num_transacoes is not None:
            st.metric("🧾 Transações", f"{num_transacoes:,}")
        else:
            st.metric("🧾 Transações", "Erro no cálculo")
            
        with st.expander("🔍 Detalhes do Cálculo"):
            if log:
                st.json(log[-1])
    
    # Gráfico de distribuição de valores se houver dados suficientes
    try:
        valores_sample = df.select(
            pl.col(coluna_principal.name).cast(pl.Float64, strict=False)
        ).drop_nulls().head(1000)
        
        if valores_sample.height > 0:
            st.subheader(f"📈 Distribuição de {coluna_principal.name}")
            hist_data = valores_sample.to_pandas().iloc[:, 0].tolist()
            st.bar_chart(hist_data[:50])  # Mostra apenas os primeiros 50 para performance
            
    except Exception as e:
        st.warning(f"Não foi possível gerar gráfico de distribuição: {e}")

def _render_vendedores_dashboard(df: pl.DataFrame, estrutura: DataStructure, log: List):
    """
    Renderiza análise por vendedores
    """
    vendedor_cols = estrutura.patterns.get('vendedor_columns', [])
    valor_cols = estrutura.patterns.get('valor_columns', [])
    
    if not vendedor_cols or not valor_cols:
        st.info("👤 **Análise por vendedores**: Colunas de vendedor ou valor não identificadas")
        return
    
    st.subheader("👤 Análise por Vendedores")
    
    vendedor_col = vendedor_cols[0]
    valor_col = valor_cols[0]
    
    # Top 10 vendedores
    try:
        top_vendedores = df.group_by(vendedor_col.name).agg([
            pl.col(valor_col.name).cast(pl.Float64, strict=False).sum().alias("total_vendas"),
            pl.count().alias("num_transacoes")
        ]).sort("total_vendas", descending=True).head(10)
        
        st.write("**🏆 Top 10 Vendedores por Valor Total:**")
        
        for i, row in enumerate(top_vendedores.to_dicts(), 1):
            vendedor = row[vendedor_col.name]
            total = row["total_vendas"]
            transacoes = row["num_transacoes"]
            
            if total is not None:
                st.write(f"{i}. **{vendedor}**: R$ {total:,.2f} ({transacoes} transações)")
            
    except Exception as e:
        st.error(f"Erro na análise de vendedores: {e}")

def _render_clientes_dashboard(df: pl.DataFrame, estrutura: DataStructure, log: List):
    """
    Renderiza análise por clientes
    """
    cliente_cols = estrutura.patterns.get('cliente_columns', [])
    valor_cols = estrutura.patterns.get('valor_columns', [])
    
    if not cliente_cols or not valor_cols:
        st.info("🏢 **Análise por clientes**: Colunas de cliente ou valor não identificadas")
        return
    
    st.subheader("🏢 Análise por Clientes")
    
    cliente_col = cliente_cols[0]
    valor_col = valor_cols[0]
    
    # Top 10 clientes
    try:
        top_clientes = df.group_by(cliente_col.name).agg([
            pl.col(valor_col.name).cast(pl.Float64, strict=False).sum().alias("total_compras"),
            pl.count().alias("num_pedidos")
        ]).sort("total_compras", descending=True).head(10)
        
        st.write("**🎯 Top 10 Clientes por Valor de Compras:**")
        
        for i, row in enumerate(top_clientes.to_dicts(), 1):
            cliente = row[cliente_col.name]
            total = row["total_compras"]
            pedidos = row["num_pedidos"]
            
            if total is not None:
                st.write(f"{i}. **{cliente}**: R$ {total:,.2f} ({pedidos} pedidos)")
                
    except Exception as e:
        st.error(f"Erro na análise de clientes: {e}")

def _render_produtos_dashboard(df: pl.DataFrame, estrutura: DataStructure, log: List):
    """
    Renderiza análise por produtos
    """
    produto_cols = estrutura.patterns.get('produto_columns', [])
    valor_cols = estrutura.patterns.get('valor_columns', [])
    quantidade_cols = estrutura.patterns.get('quantidade_columns', [])
    
    if not produto_cols:
        st.info("📦 **Análise por produtos**: Colunas de produto não identificadas")
        return
    
    st.subheader("📦 Análise por Produtos")
    
    produto_col = produto_cols[0]
    
    # Produtos mais vendidos (por quantidade se disponível, senão por frequência)
    try:
        if quantidade_cols and valor_cols:
            # Análise completa com quantidade e valor
            qtd_col = quantidade_cols[0]
            valor_col = valor_cols[0]
            
            top_produtos = df.group_by(produto_col.name).agg([
                pl.col(qtd_col.name).cast(pl.Float64, strict=False).sum().alias("total_quantidade"),
                pl.col(valor_col.name).cast(pl.Float64, strict=False).sum().alias("total_valor"),
                pl.count().alias("num_vendas")
            ]).sort("total_quantidade", descending=True).head(10)
            
            st.write("**📈 Top 10 Produtos por Quantidade Vendida:**")
            
            for i, row in enumerate(top_produtos.to_dicts(), 1):
                produto = row[produto_col.name]
                quantidade = row["total_quantidade"]
                valor = row["total_valor"]
                vendas = row["num_vendas"]
                
                if quantidade is not None:
                    st.write(f"{i}. **{produto}**: {quantidade:,.0f} unidades, R$ {valor:,.2f} ({vendas} vendas)")
        
        else:
            # Análise simples por frequência
            top_produtos_freq = df.group_by(produto_col.name).agg([
                pl.count().alias("frequencia")
            ]).sort("frequencia", descending=True).head(10)
            
            st.write("**🔥 Top 10 Produtos por Frequência de Vendas:**")
            
            for i, row in enumerate(top_produtos_freq.to_dicts(), 1):
                produto = row[produto_col.name]
                freq = row["frequencia"]
                st.write(f"{i}. **{produto}**: {freq} vendas")
                
    except Exception as e:
        st.error(f"Erro na análise de produtos: {e}")

def render_column_explorer(df: pl.DataFrame, estrutura: DataStructure):
    """
    Renderiza explorador interativo de colunas
    """
    st.subheader("🔍 Explorador de Colunas")
    st.markdown("*Explore individualmente cada coluna identificada*")
    
    # Seletor de coluna
    colunas_disponiveis = [col.name for col in estrutura.columns]
    coluna_selecionada = st.selectbox(
        "Selecione uma coluna para explorar:",
        options=colunas_disponiveis,
        key="explorador_coluna"
    )
    
    if coluna_selecionada:
        # Encontra informações da coluna
        col_info = next((col for col in estrutura.columns if col.name == coluna_selecionada), None)
        
        if col_info:
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.write("**📊 Informações da Coluna:**")
                st.write(f"• **Tipo**: {col_info.data_type}")
                st.write(f"• **Confiança**: {col_info.confidence_score:.1%}")
                st.write(f"• **Valores únicos**: {col_info.unique_count:,}")
                st.write(f"• **Taxa de preenchimento**: {100-col_info.null_percentage:.1f}%")
                
                st.write("**🔍 Amostras:**")
                for valor in col_info.sample_values[:5]:
                    if valor is not None:
                        st.code(str(valor))
            
            with col2:
                # Estatísticas da coluna no DataFrame atual
                try:
                    coluna_data = df.select(pl.col(coluna_selecionada)).drop_nulls()
                    
                    if coluna_data.height > 0:
                        st.write("**📈 Estatísticas Atuais:**")
                        
                        if col_info.data_type == 'numeric':
                            try:
                                stats = coluna_data.select(
                                    pl.col(coluna_selecionada).cast(pl.Float64, strict=False)
                                ).describe()
                                st.dataframe(stats, use_container_width=True)
                            except:
                                st.write("Não foi possível calcular estatísticas numéricas")
                        
                        # Valores mais frequentes
                        try:
                            freq = coluna_data.group_by(coluna_selecionada).count().sort("count", descending=True).head(10)
                            st.write("**🏆 Valores Mais Frequentes:**")
                            st.dataframe(freq, use_container_width=True)
                        except Exception as e:
                            st.write(f"Erro ao calcular frequências: {e}")
                            
                except Exception as e:
                    st.error(f"Erro ao analisar coluna: {e}")

def render_business_insights(df: pl.DataFrame, estrutura: DataStructure):
    """
    Renderiza insights automáticos de negócio
    """
    st.subheader("💡 Insights Automáticos")
    st.markdown("*Insights gerados automaticamente baseados nos padrões identificados*")
    
    insights = []
    
    # Insight sobre completude dos dados
    taxa_preenchimento = _calcular_taxa_preenchimento(df)
    if taxa_preenchimento > 90:
        insights.append(f"✅ **Excelente qualidade de dados**: {taxa_preenchimento:.1f}% de preenchimento")
    elif taxa_preenchimento > 70:
        insights.append(f"⚠️ **Boa qualidade de dados**: {taxa_preenchimento:.1f}% de preenchimento")
    else:
        insights.append(f"❌ **Atenção à qualidade**: Apenas {taxa_preenchimento:.1f}% de preenchimento")
    
    # Insight sobre tipos de colunas identificadas
    tipos_identificados = {}
    for col in estrutura.columns:
        tipos_identificados[col.data_type] = tipos_identificados.get(col.data_type, 0) + 1
    
    if tipos_identificados.get('numeric', 0) > 0:
        insights.append(f"📊 **{tipos_identificados['numeric']} colunas numéricas** identificadas para análise")
    
    if tipos_identificados.get('date', 0) > 0:
        insights.append(f"📅 **{tipos_identificados['date']} colunas de data** identificadas para análise temporal")
    
    # Insight sobre padrões de negócio
    if estrutura.patterns.get('vendedor_columns'):
        insights.append("👤 **Análise por vendedor** disponível")
    
    if estrutura.patterns.get('cliente_columns'):
        insights.append("🏢 **Análise por cliente** disponível")
    
    if estrutura.patterns.get('produto_columns'):
        insights.append("📦 **Análise por produto** disponível")
    
    # Exibe insights
    for insight in insights:
        st.markdown(f"- {insight}")
    
    if not insights:
        st.info("Nenhum insight automático gerado. Dados podem precisar de mais estruturação.")