# Pedidos Parser API

API robusta e escalável para processamento de planilhas de pedidos (.ods, .xls, .xlsx), construída com FastAPI, PostgreSQL e Google Cloud Storage.

## 🚀 Características

- **Parser Otimizado**: Lógica de parsing extremamente precisa preservada do sistema original
- **Processamento Assíncrono**: Arquivos são processados em background usando FastAPI BackgroundTasks
- **Armazenamento Robusto**: PostgreSQL para dados estruturados + Google Cloud Storage para arquivos
- **API RESTful**: Endpoints bem documentados com validação automática (Pydantic)
- **Containerizado**: Pronto para deploy com Docker
- **Escalável**: Arquitetura preparada para alta demanda

## 📁 Estrutura do Projeto

```
/
├── main.py                 # Arquivo principal da API FastAPI
├── requirements.txt        # Dependências do projeto
├── Dockerfile             # Container da aplicação
├── .env.example           # Exemplo de variáveis de ambiente
├── README.md              # Documentação
│
├── core/                  # Lógica de negócio
│   ├── __init__.py
│   ├── parser.py          # Parser original (PRESERVADO)
│   └── gcs_utils.py       # Utilitários Google Cloud Storage
│
├── db/                    # Banco de dados
│   ├── __init__.py
│   ├── models.py          # Modelos SQLAlchemy
│   └── database.py        # Configuração do banco
│
└── api/                   # API REST
    ├── __init__.py
    ├── routes.py          # Endpoints da API
    └── schemas.py         # Modelos Pydantic
```

## 🛠️ Configuração

### 1. Variáveis de Ambiente

Copie o arquivo `.env.example` para `.env` e configure:

```bash
# Banco de dados (Railway PostgreSQL)
DATABASE_URL=postgresql://usuario:senha@host:porta/banco

# Google Cloud Storage
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json

# Servidor
HOST=0.0.0.0
PORT=8000
DEBUG=false
```

### 2. Instalação Local

```bash
# Clone o repositório
git clone <seu-repo>
cd pedidos-parser-api

# Instale as dependências
pip install -r requirements.txt

# Execute a aplicação
python main.py
```

### 3. Docker

```bash
# Build da imagem
docker build -t pedidos-parser-api .

# Execute o container
docker run -p 8000:8000 --env-file .env pedidos-parser-api
```

## 📚 Endpoints da API

### Processamento de Arquivos

**POST /v1/uploads/process**
```json
{
  "file_url": "gs://meu-bucket/planilha.ods"
}
```
Resposta:
```json
{
  "status": "processing_started",
  "upload_id": "uuid-do-upload"
}
```

**GET /v1/uploads/{upload_id}/status**
```json
{
  "status": "completed",
  "item_count": 1234,
  "pedido_count": 56,
  "created_at": "2024-01-01T10:00:00Z",
  "completed_at": "2024-01-01T10:01:30Z",
  "filename": "