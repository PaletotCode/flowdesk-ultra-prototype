# app.py
import streamlit as st
from core.data_loader import carregar_planilha
from ui.dashboard import render_dashboard, render_ai_assistant

# --- Configuração da Página e Estado da Sessão ---
st.set_page_config(
    page_title="FlowDesk Ultra Prototype",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Inicializa o estado da sessão de forma robusta
if 'df' not in st.session_state:
    st.session_state.df = None
if 'log' not in st.session_state:
    st.session_state.log = []
if 'file_name' not in st.session_state:
    st.session_state.file_name = None

# --- Header Principal ---
st.title("🔍 FlowDesk Ultra - The Traceable Engine")
st.markdown(
    """
    **O motor de análise de dados com rastreabilidade total.**  
    Cada número exibido na tela pode ser auditado até sua origem exata na planilha.
    
    ---
    """
)

# --- Seção de Upload ---
st.subheader("📁 Carregar Dados")
st.markdown("Faça o upload de uma planilha `.ods` para iniciar a análise rastreável.")

uploaded_file = st.file_uploader(
    "Selecione sua planilha ODS",
    type=["ods"],
    help="Formatos suportados: LibreOffice Calc (.ods)"
)

if uploaded_file:
    # Processa o arquivo apenas se for um novo arquivo
    if uploaded_file.name != st.session_state.file_name:
        with st.spinner("🚀 Processando sua planilha com motor Polars..."):
            df, log = carregar_planilha(uploaded_file)
            if df is not None:
                st.session_state.df = df
                st.session_state.log = log
                st.session_state.file_name = uploaded_file.name
                st.success(
                    f"✅ **Planilha '{uploaded_file.name}' carregada com sucesso!**\n\n"
                    f"📊 {df.height:,} linhas × {df.width} colunas processadas\n"
                    f"🔑 Coluna 'id_linha_original' injetada para rastreabilidade total"
                )
            else:
                st.error("❌ **Falha ao carregar a planilha.** Verifique o log de erros abaixo:")
                st.json(log[-1] if log else {"erro": "Log vazio"})
    else:
        st.info(f"📁 Planilha '{uploaded_file.name}' já está carregada na sessão.")

# --- Renderização Condicional do Conteúdo ---
if st.session_state.df is not None:
    st.divider()
    
    # Renderiza o dashboard a partir do módulo de UI
    render_dashboard(st.session_state.df, st.session_state.log)

    render_ai_assistant(st.session_state.df, st.session_state.log)

    st.divider()
    
    # Seção de Auditoria
    st.subheader("🔍 Sistema de Auditoria")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Resumo da Sessão:**")
        st.info(
            f"📝 **{len(st.session_state.log)}** operações registradas\n\n"
            f"📊 **{st.session_state.df.height:,}** linhas sendo rastreadas\n\n"
            f"🔑 IDs de linha: 0 → {st.session_state.df.height - 1}"
        )
    
    with col2:
        st.markdown("**Última Operação:**")
        if st.session_state.log:
            ultimo_log = st.session_state.log[-1]
            st.json({
                "passo": ultimo_log.get("passo", "N/A"),
                "linhas_afetadas": len(ultimo_log.get("linhas_originais_afetadas", [])),
                "resultado": ultimo_log.get("resultado", "N/A")
            })
        else:
            st.write("Nenhuma operação registrada ainda.")
    
    # Log completo expansível
    with st.expander("📋 Ver Log de Auditoria Completo da Sessão"):
        st.markdown("**Todas as operações realizadas desde o carregamento:**")
        for i, entrada in enumerate(st.session_state.log):
            st.write(f"**{i+1}. {entrada.get('passo', 'Operação desconhecida')}**")
            st.json(entrada)
            if i < len(st.session_state.log) - 1:
                st.divider()

else:
    # Estado inicial - sem dados carregados
    st.info(
        """
        👆 **Para começar, carregue uma planilha ODS acima.**
        
        ### 🎯 O que o FlowDesk Ultra faz:
        
        - **🔍 Rastreabilidade Total**: Cada métrica mostra exatamente quais linhas da planilha original foram usadas
        - **⚡ Performance Extrema**: Motor Polars otimizado para datasets grandes (70k+ linhas)
        - **🧮 Cálculos Auditáveis**: Log detalhado de cada operação matemática realizada
        - **🎛️ Interface Intuitiva**: Dashboards interativos com validadores integrados
        
        ### 📋 Formato esperado da planilha:
        - Arquivo `.ods` (LibreOffice Calc)
        - Colunas com dados numéricos para análise
        - Preferencialmente com colunas como 'Valor Venda', 'Vendas', ou similares
        """
    )

# --- Footer ---
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666; font-size: 0.8em;'>
        FlowDesk Ultra Prototype | Powered by Polars + Streamlit + Rastreabilidade Total
    </div>
    """, 
    unsafe_allow_html=True
)