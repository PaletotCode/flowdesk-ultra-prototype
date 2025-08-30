import streamlit as st
import pandas as pd
from parser import load_sheet, parse

st.set_page_config(page_title="Parser de Pedidos", layout="wide")

st.title("Parser de Pedidos → DataFrame")

uploaded = st.file_uploader("Carregue o arquivo (.ods, .xls, .xlsx)", type=["ods","xls","xlsx"])
debug = st.checkbox("Modo debug", value=True)

prog = st.progress(0, text="Aguardando arquivo…")

if uploaded:
    try:
        prog.progress(10, text="Lendo planilha…")
        df_raw = load_sheet(uploaded)

        prog.progress(30, text="Processando…")
        df_pedidos, df_itens, df_totais, logs = parse(df_raw, debug=debug)

        prog.progress(90, text="Renderizando UI…")
        tabs = st.tabs(["Pedidos", "Itens", "Totais", "Logs de Parsing", "Dados Crus"])

        with tabs[0]:
            st.caption(f"Extraídos {len(df_pedidos)} pedidos.")
            st.dataframe(df_pedidos, use_container_width=True)
            st.download_button(
                "Baixar pedidos (CSV)", 
                df_pedidos.to_csv(index=False).encode("utf-8"), 
                "pedidos.csv", 
                "text/csv"
            )

        with tabs[1]:
            st.caption(f"Extraídos {len(df_itens)} itens únicos de pedido.")
            st.dataframe(df_itens, use_container_width=True)
            st.download_button(
                "Baixar itens (CSV)", 
                df_itens.to_csv(index=False).encode("utf-8"), 
                "itens.csv", 
                "text/csv"
            )

        with tabs[2]:
            st.caption("Totais calculados por pedido.")
            st.dataframe(df_totais, use_container_width=True)
            st.download_button(
                "Baixar totais (CSV)", 
                df_totais.to_csv(index=False).encode("utf-8"), 
                "totais.csv", 
                "text/csv"
            )

        with tabs[3]:
            st.caption("Eventos de parsing e avisos.")
            st.code("\n".join(logs), language=None)

        with tabs[4]:
            st.caption("Prévia da planilha como lida inicialmente (dados crus).")
            st.dataframe(df_raw.head(200), use_container_width=True)

        prog.progress(100, text="Concluído.")
        st.success("Arquivo processado com sucesso!")

    except Exception as e:
        st.error(f"Falha ao processar o arquivo: {e}")
        prog.progress(100, text="Erro.")
        st.exception(e)

else:
    st.info("Importe um arquivo para iniciar o processamento.")