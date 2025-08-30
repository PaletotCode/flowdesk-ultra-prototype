"""
Utilitários para interagir com Google Cloud Storage.
"""
import os
from typing import Tuple
from google.cloud import storage
import tempfile
import logging

logger = logging.getLogger(__name__)


def parse_gcs_url(gcs_url: str) -> Tuple[str, str]:
    """
    Parse uma URL do GCS no formato gs://bucket-name/path/to/file
    Retorna (bucket_name, file_path)
    """
    if not gcs_url.startswith("gs://"):
        raise ValueError("URL deve começar com 'gs://'")
    
    path_part = gcs_url[5:]  # Remove 'gs://'
    parts = path_part.split("/", 1)
    
    if len(parts) != 2:
        raise ValueError("URL GCS deve ter formato gs://bucket-name/path/to/file")
    
    return parts[0], parts[1]


async def download_file_from_gcs(gcs_url: str) -> Tuple[bytes, str]:
    """
    Baixa um arquivo do Google Cloud Storage.
    
    Args:
        gcs_url: URL do arquivo no formato gs://bucket-name/path/to/file
        
    Returns:
        Tuple contendo (conteúdo_do_arquivo_em_bytes, nome_do_arquivo)
        
    Raises:
        Exception: Se não conseguir baixar o arquivo
    """
    try:
        bucket_name, file_path = parse_gcs_url(gcs_url)
        
        # Inicializa o cliente GCS
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(file_path)
        
        if not blob.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {gcs_url}")
        
        # Baixa o conteúdo do arquivo
        file_content = blob.download_as_bytes()
        
        # Extrai o nome do arquivo
        filename = os.path.basename(file_path)
        
        logger.info(f"Arquivo baixado com sucesso: {gcs_url} ({len(file_content)} bytes)")
        
        return file_content, filename
        
    except Exception as e:
        logger.error(f"Erro ao baixar arquivo do GCS {gcs_url}: {str(e)}")
        raise


def get_gcs_client():
    """
    Retorna um cliente do Google Cloud Storage configurado.
    As credenciais devem ser configuradas via variável de ambiente GOOGLE_APPLICATION_CREDENTIALS
    ou através do mecanismo padrão do GCP.
    """
    return storage.Client()