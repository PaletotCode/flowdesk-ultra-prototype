import streamlit as st
import pandas as pd
from parser import load_sheet, parse

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
            st.download_button("Baixar Pedidos (CSV)", df_pedidos.to_csv(index=False).encode("utf-8"), "pedidos.csv", "text/csv", use_container_width=True)

        with tabs[1]:
            st.dataframe(df_itens, use_container_width=True, hide_index=True)
            st.download_button("Baixar Itens (CSV)", df_itens.to_csv(index=False).encode("utf-8"), "itens.csv", "text/csv", use_container_width=True)

        with tabs[2]:
            st.dataframe(df_totais, use_container_width=True, hide_index=True)
            st.download_button("Baixar Totais (CSV)", df_totais.to_csv(index=False).encode("utf-8"), "totais.csv", "text/csv", use_container_width=True)

        if debug:
            with st.sidebar.expander("📝 Logs de Parsing", expanded=True):
                st.code("\n".join(logs))

        prog.progress(100, text="Finalizado.")

    except Exception as e:
        st.error(f"Ocorreu um erro durante o processamento: {e}")
        st.exception(e) 
        prog.progress(100, text="Erro!")
else:
    st.info("Aguardando o upload de um arquivo para iniciar.")