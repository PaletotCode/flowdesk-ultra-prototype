# Use Python 3.11 slim como base
FROM python:3.11-slim

# Define variáveis de ambiente
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Define o diretório de trabalho
WORKDIR /app

# Instala dependências do sistema necessárias
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copia o arquivo de requirements
COPY requirements.txt .

# Instala as dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Cria diretórios necessários
RUN mkdir -p /app/core /app/db /app/api

# Copia os arquivos da aplicação
COPY main.py .
COPY core/ ./core/
COPY db/ ./db/
COPY api/ ./api/

# Cria arquivos __init__.py se não existirem
RUN touch /app/core/__init__.py /app/db/__init__.py /app/api/__init__.py

# Cria um usuário não-root para executar a aplicação
RUN groupadd -r appuser && useradd -r -g appuser appuser
RUN chown -R appuser:appuser /app
USER appuser

# Expõe a porta da aplicação
EXPOSE 8000

# Define o health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Comando para iniciar a aplicação
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]