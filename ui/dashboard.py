# ui/dashboard.py
import streamlit as st
import polars as pl
from core.traceable_functions import calcular_metrica
from core.ai_functions import perguntar_ia

def render_dashboard(df: pl.DataFrame, log: list):
    """
    Renderiza o dashboard principal com KPIs e seus validadores.
    
    Args:
        df: DataFrame Polars com os dados carregados
        log: Lista de log de auditoria da sessão
    """
    st.header("📊 Dashboard de Vendas")
    
    # Exibe informações básicas sobre os dados
    st.info(f"📈 Dataset carregado: {df.height:,} linhas × {df.width} colunas")
    
    # Mostra as colunas disponíveis para debugging
    with st.expander("🔍 Colunas Disponíveis"):
        colunas = [col for col in df.columns if col != "id_linha_original"]
        st.write(colunas)
    
    # Tenta diferentes variações de nomes de colunas para vendas
    possivel_vendas = [
        "Valor Venda", "valor_venda", "Vendas", "vendas", "Valor", "valor",
        "Total", "total", "Receita", "receita", "Revenue", "revenue"
    ]
    
    coluna_vendas = None
    for col in possivel_vendas:
        if col in df.columns:
            coluna_vendas = col
            break
    
    if coluna_vendas:
        # Dashboard principal com métricas
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Vendas Totais
            vendas_totais = calcular_metrica(
                df=df,
                log_auditoria=log,
                nome_metrica="Vendas Totais",
                expressao_polars=pl.sum(coluna_vendas),
                filtros_aplicados=None
            )
            
            if vendas_totais is not None:
                st.metric("💰 Vendas Totais", f"R$ {vendas_totais:,.2f}")
            else:
                st.metric("💰 Vendas Totais", "Erro no cálculo")
            
            # Validador do cálculo
            with st.expander("🔬 Validar Cálculo - Vendas Totais"):
                if log:
                    st.json(log[-1])
        
        with col2:
            # Ticket Médio
            ticket_medio = calcular_metrica(
                df=df,
                log_auditoria=log,
                nome_metrica="Ticket Médio",
                expressao_polars=pl.mean(coluna_vendas),
                filtros_aplicados=None
            )
            
            if ticket_medio is not None:
                st.metric("🎯 Ticket Médio", f"R$ {ticket_medio:,.2f}")
            else:
                st.metric("🎯 Ticket Médio", "Erro no cálculo")
            
            # Validador do cálculo
            with st.expander("🔬 Validar Cálculo - Ticket Médio"):
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
                st.metric("📊 Transações", f"{num_transacoes:,}")
            else:
                st.metric("📊 Transações", "Erro no cálculo")
            
            # Validador do cálculo
            with st.expander("🔬 Validar Cálculo - Transações"):
                if log:
                    st.json(log[-1])
        
        st.divider()
        
        # Seção de análise por filtros (exemplo com uma coluna categórica)
        colunas_categoricas = []
        for col in df.columns:
            if col != "id_linha_original" and col != coluna_vendas:
                try:
                    # Verifica se a coluna tem poucos valores únicos (categórica)
                    unique_count = df.select(pl.col(col).n_unique()).item()
                    if unique_count <= 20:  # Limite arbitrário para categórica
                        colunas_categoricas.append(col)
                except:
                    continue
        
        if colunas_categoricas:
            st.subheader("🎛️ Análise por Categoria")
            
            coluna_selecionada = st.selectbox(
                "Selecione uma coluna para análise:",
                options=colunas_categoricas,
                key="filtro_categoria"
            )
            
            if coluna_selecionada:
                # Obtém valores únicos da coluna
                valores_unicos = df.select(pl.col(coluna_selecionada).unique()).to_series().to_list()
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Vendas por {coluna_selecionada}:**")
                    
                    # Calcula vendas para cada categoria
                    for valor in valores_unicos[:10]:  # Limita a 10 valores
                        vendas_categoria = calcular_metrica(
                            df=df,
                            log_auditoria=log,
                            nome_metrica=f"Vendas - {coluna_selecionada}: {valor}",
                            expressao_polars=pl.sum(coluna_vendas),
                            filtros_aplicados={coluna_selecionada: valor}
                        )
                        
                        if vendas_categoria is not None:
                            st.write(f"• **{valor}**: R$ {vendas_categoria:,.2f}")
                        else:
                            st.write(f"• **{valor}**: Erro no cálculo")
                
                with col2:
                    # Mostra o último cálculo detalhado
                    with st.expander("🔬 Último Cálculo Detalhado"):
                        if log:
                            st.json(log[-1])
    
    else:
        st.warning(
            "❌ **Coluna de vendas não encontrada!**\n\n"
            f"Procurei por: {', '.join(possivel_vendas)}\n\n"
            "Por favor, verifique se sua planilha contém uma dessas colunas ou "
            "ajuste os nomes das colunas conforme esperado."
        )
        
        # Mostra uma prévia dos dados para ajudar na identificação
        st.subheader("👀 Prévia dos Dados")
        st.dataframe(df.head(10), use_container_width=True)

def render_ai_assistant(df: pl.DataFrame, log: list):
    """
    Renderiza a seção de interação com a IA.
    """
    st.divider()
    st.header("🧠 Assistente de Análise com IA")
    st.markdown("Faça uma pergunta em linguagem natural sobre seus dados.")

    prompt_usuario = st.text_area(
        "Exemplo: 'Qual o valor total de vendas e o ticket médio?' ou 'Existe alguma correlação entre as colunas numéricas?'",
        key="prompt_usuario_ia"
    )

    if st.button("Perguntar ao FlowDesk AI", type="primary"):
        if not prompt_usuario:
            st.warning("Por favor, digite uma pergunta.")
        else:
            with st.spinner("🧠 A IA está analisando os dados e elaborando uma resposta..."):
                resposta = perguntar_ia(df, log, prompt_usuario)
                st.session_state.ultima_resposta_ia = resposta

    if "ultima_resposta_ia" in st.session_state and st.session_state.ultima_resposta_ia:
        st.markdown("#### Resposta da IA:")
        st.markdown(st.session_state.ultima_resposta_ia)
        
        with st.expander("🔬 Validar Análise da IA"):
            st.markdown("**Contexto e Prompt Exatos Enviados para a IA:**")
            # Pega o último log, que deve ser o da consulta à IA
            st.json(log[-1])