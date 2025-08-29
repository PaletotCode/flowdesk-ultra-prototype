# core/logger_config.py
import logging
import io

def setup_logger():
    """
    Configura e retorna um logger que escreve para um stream em memória (StringIO).
    Isso permite capturar os logs para exibição na interface do Streamlit.
    """
    # Cria um stream em memória para armazenar os logs
    log_stream = io.StringIO()

    # Pega o logger raiz
    logger = logging.getLogger('FlowDeskLogger')
    
    # Evita adicionar múltiplos handlers se a função for chamada mais de uma vez
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        # Cria um handler que escreve no stream em memória
        stream_handler = logging.StreamHandler(log_stream)
        
        # Cria um formato para as mensagens de log
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        stream_handler.setFormatter(formatter)
        
        # Adiciona o handler ao logger
        logger.addHandler(stream_handler)

    return logger, log_stream