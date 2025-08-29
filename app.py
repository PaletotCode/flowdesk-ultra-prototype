# app.py - Aplicação Principal do FlowDesk Ultra com Análise Inteligente
import streamlit as st
import polars as pl

# Importa as novas funções dos módulos inteligentes
from core.data_loader_v2 import carregar_e_analisar_planilha, gerar_relatorio_estrutura
from core.smart_data_analyzer import DataStructure
from ui.smart_dashboard import (
    render_structure_report, render_smart_dashboard,
    render_column_explorer, render_business_insights
)
from core.ai_functions import perguntar_ia

# Configuração da página
st.set_page_config(
    page_title="FlowDesk Ultra - Análise Inteligente",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

def gerar_sugestoes_ia(estrutura: DataStructure) -> list:
    """
    Gera sugestões de perguntas baseadas na estrutura identificada.
    """
    sugestoes = []
    patterns = estrutura.patterns if hasattr(estrutura, 'patterns') else {}

    if patterns.get('vendedor_columns'):
        sugestoes.append("Quais são os top 5 vendedores por volume de vendas?")
        sugestoes.append("Qual vendedor tem o melhor ticket médio?")

    if patterns.get('cliente_columns') and patterns.get('valor_columns'):
        sugestoes.append("Quais são os 10 clientes que mais compram?")

    if patterns.get('produto_columns'):
        sugestoes.append("Quais produtos são mais vendidos?")

    if patterns.get('data_columns'):
        sugestoes.append("Como está a tendência de vendas ao longo do tempo?")
        sugestoes.append("Qual mês teve a melhor performance?")

    sugestoes.extend([
        "Faça um resumo executivo dos dados",
        "Identifique anomalias ou padrões interessantes",
    ])

    return sugestoes[:6]

def render_ai_assistant_smart(df: pl.DataFrame, estrutura: DataStructure, log: list):
    """
    Renderiza o assistente de IA com contexto inteligente da estrutura.
    """
    st.header("🤖 Assistente IA Inteligente")
    st.markdown("*O assistente agora entende a estrutura dos seus dados automaticamente.*")

    with st.expander("🧠 Contexto Inteligente Disponível para a IA"):
        st.write("**Padrões Identificados:**")
        patterns = estrutura.patterns if hasattr(estrutura, 'patterns') else {}
        for pattern, cols in patterns.items():
            if cols:
                # Trata o caso de ser uma lista de objetos Column ou apenas uma string/lista de strings
                if isinstance(cols, list) and all(hasattr(c, 'name') for c in cols):
                    col_names = [c.name for c in cols]
                else:
                    col_names = cols
                st.write(f"- {pattern.replace('_columns', '').title()}: `{col_names}`")

        st.write("**Colunas com Alta Confiança:**")
        colunas_confiaveis = [col for col in estrutura.columns if col.confidence_score > 0.7]
        for col in colunas_confiaveis:
            st.write(f"- `{col.name}` (Tipo: {col.data_type}) - Confiança: {col.confidence_score:.1%}")

    st.markdown("---")
    st.markdown("**💬 Faça perguntas específicas sobre seus dados:**")

    sugestoes = gerar_sugestoes_ia(estrutura)
    if sugestoes:
        st.write("**💡 Sugestões:**")
        cols = st.columns(len(sugestoes))
        for i, sugestao in enumerate(sugestoes):
            if cols[i].button(sugestao, key=f"sugestao_{i}"):
                st.session_state.pergunta_ia = sugestao
                st.rerun()

    pergunta_usuario = st.text_area(
        "Ou digite sua própria pergunta:",
        value=st.session_state.get('pergunta_ia', ''),
        key="input_pergunta_ia",
        height=100
    )

    if st.button("🧠 Perguntar ao FlowDesk AI", type="primary"):
        if not pergunta_usuario:
            st.warning("Por favor, digite uma pergunta ou selecione uma sugestão.")
        else:
            with st.spinner("🧠 IA analisando com contexto estrutural..."):
                # Futuramente, a função perguntar_ia pode ser otimizada para receber o objeto 'estrutura'
                resposta = perguntar_ia(df, log, pergunta_usuario, estrutura)
                st.session_state.ultima_resposta_ia = resposta

    if "ultima_resposta_ia" in st.session_state and st.session_state.ultima_resposta_ia:
        st.markdown("#### 🎯 Resposta da IA:")
        st.markdown(st.session_state.ultima_resposta_ia)
        with st.expander("🔬 Ver Contexto Enviado para IA"):
            if log:
                st.json(log[-1])

def render_welcome_screen():
    """
    Renderiza a tela de boas-vindas aprimorada.
    """
    st.markdown("""
    ## 🧠 Bem-vindo ao FlowDesk Ultra Inteligente!

    Esta versão utiliza um motor de análise para entender automaticamente a estrutura da sua planilha.

    ### 🚀 **Como funciona:**
    1.  **Upload na Barra Lateral**: Carregue seu arquivo ODS.
    2.  **Análise Inteligente**: Clique no botão para o sistema identificar:
        -   Onde estão seus cabeçalhos e dados reais.
        -   Quais colunas representam vendedores, clientes, produtos, valores e datas.
        -   A qualidade e o tipo de dado em cada coluna.
    3.  **Explore os Resultados**: Navegue pelas abas para ver o dashboard adaptativo, a estrutura dos dados, insights e interagir com a IA que agora *entende* seus dados.
    """)
    st.info("""
    💡 **Exemplo do que o sistema identifica automaticamente:**
    -   👤 **Vendedor**: "Vendedor", "Rep", "Seller"
    -   🏢 **Cliente**: "Cliente", "Razão Social", "Company"
    -   💰 **Valor**: "Valor Total", "Preço", "Amount"
    -   📦 **Produto**: "Produto", "Item", "Descrição"
    -   📅 **Data**: "Data", "DateTime", "Dt_Pedido"
    """)

def main():
    """Função principal da aplicação Streamlit."""
    st.title("🧠 FlowDesk Ultra - Análise Inteligente de Dados")
    st.markdown("""
        **Uma nova abordagem que analisa e estrutura seus dados automaticamente.**
        Faça o upload de um arquivo ODS na barra lateral para começar.
    """)

    # Inicialização do session state
    if 'df' not in st.session_state:
        st.session_state.df = None
        st.session_state.estrutura = None
        st.session_state.log_auditoria = []
        st.session_state.processing_logs = ""

    # --- BARRA LATERAL ---
    with st.sidebar:
        st.header("📁 Upload e Análise")
        uploaded_file = st.file_uploader(
            "Escolha um arquivo ODS",
            type=['ods'],
            help="O sistema identificará automaticamente a estrutura e os padrões de negócio."
        )

        if uploaded_file:
            if st.button("🧠 Analisar Inteligentemente", type="primary", use_container_width=True):
                with st.spinner("🔍 Mapeando estrutura e padrões... Isso pode levar um minuto."):
                    progress_bar = st.progress(0, text="Iniciando análise...")

                    def progress_callback(percentage, message):
                        progress_bar.progress(percentage / 100, text=message)

                    df_res, est_res, logs_res = carregar_e_analisar_planilha(
                        uploaded_file, progress_callback=progress_callback
                    )

                    st.session_state.df = df_res
                    st.session_state.estrutura = est_res
                    st.session_state.processing_logs = logs_res
                    st.session_state.log_auditoria = [] # Reseta o log de auditoria
                    
                    if df_res is not None and est_res is not None:
                         st.success(f"✅ Análise concluída! {df_res.height:,} linhas estruturadas.")
                    else:
                         st.error("❌ Falha na análise. Verifique os logs.")
                    
                    st.rerun()

        if st.session_state.df is not None and st.session_state.estrutura is not None:
            st.markdown("---")
            st.subheader("📊 Dados Carregados")
            df = st.session_state.df
            estrutura = st.session_state.estrutura
            st.metric("Linhas de Dados", f"{df.height:,}")
            st.metric("Colunas Válidas", f"{len(estrutura.columns)}")

        if st.session_state.processing_logs:
            with st.expander("📋 Logs de Análise da Estrutura"):
                st.text(st.session_state.processing_logs)

    # --- CONTEÚDO PRINCIPAL ---
    if st.session_state.df is not None and st.session_state.estrutura is not None:
        df = st.session_state.df
        estrutura = st.session_state.estrutura
        log = st.session_state.log_auditoria
        relatorio = gerar_relatorio_estrutura(estrutura)

        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📊 Dashboard Inteligente",
            "📋 Estrutura Detectada",
            "🔍 Explorador de Colunas",
            "💡 Business Insights",
            "🤖 Assistente IA"
        ])

        with tab1:
            render_smart_dashboard(df, estrutura, log)
        with tab2:
            render_structure_report(estrutura, relatorio)
            st.subheader("👀 Prévia dos Dados Estruturados")
            st.dataframe(df.head(20), use_container_width=True)
        with tab3:
            render_column_explorer(df, estrutura)
        with tab4:
            render_business_insights(df, estrutura, log)
        with tab5:
            render_ai_assistant_smart(df, estrutura, log)

    else:
        render_welcome_screen()

if __name__ == "__main__":
    main()