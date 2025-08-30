"""
Arquivo principal da aplicação FastAPI.
"""
import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Importações dos módulos da aplicação
from db.database import create_tables
from api.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gerencia o ciclo de vida da aplicação.
    Cria as tabelas do banco de dados na inicialização.
    """
    logger.info("Iniciando aplicação...")
    
    try:
        # Cria as tabelas do banco de dados
        create_tables()
        logger.info("Banco de dados configurado com sucesso")
    except Exception as e:
        logger.error(f"Erro ao configurar banco de dados: {str(e)}")
        raise
    
    yield
    
    logger.info("Finalizando aplicação...")


# Cria a aplicação FastAPI
app = FastAPI(
    title="Pedidos Parser API",
    description="API para processamento de planilhas de pedidos usando o parser otimizado",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configuração de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, especificar os domínios permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclui as rotas da API
app.include_router(router)


@app.get("/", include_in_schema=False)
async def root():
    """
    Redireciona a raiz para a documentação da API.
    """
    return RedirectResponse(url="/docs")


@app.get("/ping")
async def ping():
    """
    Endpoint simples para verificar se a API está respondendo.
    """
    return {"message": "pong"}


# Handler global de exceções
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    Handler global para capturar exceções não tratadas.
    """
    logger.error(f"Erro não tratado na rota {request.url}: {str(exc)}", exc_info=True)
    return HTTPException(
        status_code=500,
        detail="Erro interno do servidor"
    )


if __name__ == "__main__":
    import uvicorn
    
    # Configurações do servidor
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    
    logger.info(f"Iniciando servidor em {host}:{port} (debug={debug})")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info"
    )