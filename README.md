# Parser de Pedidos - API Backend

Esta API FastAPI processa planilhas de pedidos (.ods, .xls, .xlsx) e extrai dados estruturados para armazenamento em PostgreSQL.

## 🚀 Funcionalidades

- **Processamento de Planilhas**: Suporte para formatos .ods, .xls e .xlsx
- **Extração Inteligente**: Parser robusto que identifica pedidos e itens automaticamente
- **Persistência**: Dados salvos em PostgreSQL com SQLAlchemy ORM
- **API RESTful**: Endpoints bem documentados com FastAPI
- **Cloud Ready**: Configurado para deploy no Railway

## 📁 Estrutura do Projeto

```
/
├── main.py              # Entrypoint da API
├── requirements.txt     # Dependências Python
├── railway.toml         # Configuração Railway
├── core/
│   └── parser.py        # Lógica de parsing (preservada do original)
├── db/
│   ├── database.py      # Configuração do banco
│   └── models.py        # Modelos SQLAlchemy
└── api/
    ├── routes.py        # Endpoints da API  
    └── schemas.py       # Schemas Pydantic
```

## 🛠️ Instalação e Execução

### Pré-requisitos
- Python 3.8+
- PostgreSQL

### 1. Instalar Dependências
```bash
pip install -r requirements.txt
```

### 2. Configurar Banco de Dados
Defina a variável de ambiente `DATABASE_URL`:
```bash
export DATABASE_URL="postgresql://username:password@localhost/parser_db"
```

### 3. Executar a API
```bash
python main.py
```

A API estará disponível em: `http://localhost:8000`

## 📚 Documentação da API

### Endpoints Principais

#### `POST /api/v1/processar-planilha/`
Processa uma planilha e salva os dados no banco.

**Parâmetros:**
- `arquivo`: Arquivo da planilha (form-data)
- `debug`: Boolean opcional para logs detalhados

**Resposta:**
```json
{
  "status": "sucesso",
  "pedidos_processados": 1250,
  "itens_processados": 8500,
  "logs": ["..."] // apenas se debug=true
}
```

#### `GET /api/v1/status/`
Verifica se a API está funcionando.

#### `GET /api/v1/pedidos/count/`
Retorna o número total de pedidos no banco.

#### `GET /api/v1/itens/count/`
Retorna o número total de itens no banco.

### Documentação Interativa
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## 🗄️ Estrutura do Banco de Dados

### Tabela `pedidos`
Armazena informações dos pedidos:
- `pedido_id` (string, único)
- `tipo_pedido`, `vendedor`, `cliente`
- Valores financeiros: `vlr_produtos`, `vlr_liquido`, `desconto`, etc.
- Metadados: `dt_extracao`, timestamps, etc.

### Tabela `itens_pedido`
Armazena itens de cada pedido:
- `pedido_id` (FK para pedidos)
- `codigo`, `nome`, `marca`
- `quantidade`, `preco_venda`, `subtotal_item`
- Custos e margens de lucro

## 🚀 Deploy no Railway

### 1. Conectar ao GitHub
Conecte seu repositório ao Railway.

### 2. Adicionar PostgreSQL
No dashboard do Railway, adicione um serviço PostgreSQL.

### 3. Deploy Automático
O Railway detectará o `railway.toml` e fará o deploy automaticamente.

### 4. Configurar Domínio
Configure um domínio personalizado no dashboard do Railway.

## 🔧 Variáveis de Ambiente

| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| `DATABASE_URL` | URL de conexão PostgreSQL | `postgresql://user:pass@host:5432/db` |
| `PORT` | Porta da aplicação | `8000` (Railway define automaticamente) |

## 🧪 Testando a API

### Usando curl
```bash
curl -X POST "http://localhost:8000/api/v1/processar-planilha/" \
  -H "Content-Type: multipart/form-data" \
  -F "arquivo=@sua_planilha.xlsx" \
  -F "debug=true"
```

### Usando Python
```python
import requests

url = "http://localhost:8000/api/v1/processar-planilha/"
files = {"arquivo": open("sua_planilha.xlsx", "rb")}
data = {"debug": True}

response = requests.post(url, files=files, data=data)
print(response.json())
```

## ⚡ Performance e Escalabilidade

- **Processamento Assíncrono**: Endpoints FastAPI assíncronos
- **Connection Pooling**: SQLAlchemy com pool de conexões
- **Indexação**: Índices em `pedido_id` para consultas rápidas
- **Deduplicação**: Lógica para evitar registros duplicados

## 🔒 Considerações de Segurança

Para produção, considere:
- Autenticação e autorização
- Rate limiting
- Validação rigorosa de arquivos
- HTTPS obrigatório
- Configuração específica de CORS

## 🐛 Troubleshooting

### Erro de Conexão com Banco
Verifique se `DATABASE_URL` está correta e o PostgreSQL está rodando.

### Erro no Parsing
A lógica de parsing foi preservada do código original testado. Se houver erros, verifique o formato da planilha.

### Deploy no Railway
Certifique-se de que:
- O serviço PostgreSQL está ativo
- As variáveis de ambiente estão configuradas
- O `railway.toml` está no root do projeto

## 📈 Próximos Passos

1. **Frontend**: Construir interface em Next.js
2. **Cache**: Implementar Redis para performance
3. **Filas**: Processamento assíncrono com Celery
4. **Monitoramento**: Logs estruturados e métricas
5. **Testes**: Suite de testes automatizados