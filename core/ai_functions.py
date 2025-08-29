# core/ai_functions.py
import streamlit as st
import polars as pl
import google.generativeai as genai
from typing import Dict, Any, List

# Configura a API Key do Gemini a partir dos segredos do Streamlit
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

def perguntar_ia(
    df: pl.DataFrame, 
    log_auditoria: List[Dict[str, Any]], 
    pergunta_usuario: str
) -> str:
    """
    Prepara um contexto, envia uma pergunta do usuário para a API do Gemini
    e registra a interação completa no log de auditoria.

    Args:
        df: O DataFrame Polars com os dados.
        log_auditoria: A lista de log para ser atualizada.
        pergunta_usuario: A pergunta feita pelo usuário.

    Returns:
        A resposta da IA em formato de texto.
    """
    # --- Passo 1: Preparar o Contexto ---
    # A IA não pode processar 70k linhas. Enviamos um resumo estatístico.
    resumo_estatistico = df.describe().to_pandas().to_markdown()
    schema_dados = str(df.schema)
    
    # CRÍTICO: Engenharia de Prompt
    prompt_completo = f"""
    Você é o "FlowDesk AI", um analista de dados especialista em planilhas financeiras e de vendas. 
    Sua tarefa é responder perguntas do usuário com base em um resumo dos dados fornecidos.

    **Contexto dos Dados Fornecidos:**

    1.  **Schema (Estrutura das Colunas):**
        ```
        {schema_dados}
        ```

    2.  **Resumo Estatístico (describe):**
        ```
        {resumo_estatistico}
        ```

    **Instruções:**
    - Analise o schema e o resumo estatístico para entender os dados disponíveis.
    - Responda à pergunta do usuário de forma clara e objetiva.
    - Baseie sua resposta APENAS no contexto fornecido. Não invente dados.
    - Se a pergunta não puder ser respondida com o resumo, explique por que (ex: "Para responder sobre o desempenho mensal, eu precisaria dos dados agregados por mês, o que não está neste resumo.").
    - Formate sua resposta usando Markdown para melhor legibilidade.

    **Pergunta do Usuário:**
    "{pergunta_usuario}"
    """

    # --- Passo 2: Chamar a API do Gemini ---
    try:
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        resposta_ia_bruta = model.generate_content(prompt_completo)
        resposta_ia_texto = resposta_ia_bruta.text
    
    except Exception as e:
        resposta_ia_texto = f"Ocorreu um erro ao contatar a IA: {str(e)}"

    # --- Passo 3: Registrar no Log de Auditoria ---
    # Para o resumo, consideramos que todas as linhas contribuíram
    ids_originais_contexto = df['id_linha_original'].to_list()
    
    log_entry = {
        "passo": "Consulta à IA (Gemini)",
        "pergunta_usuario": pergunta_usuario,
        "prompt_completo_enviado": prompt_completo,
        "dados_contexto_enviados": {
            "schema": schema_dados,
            "resumo_estatistico": df.describe().to_dict(as_series=False)
        },
        "linhas_originais_contexto": ids_originais_contexto,
        "numero_linhas_contexto": len(ids_originais_contexto),
        "resposta_ia": resposta_ia_texto
    }
    log_auditoria.append(log_entry)

    return resposta_ia_texto