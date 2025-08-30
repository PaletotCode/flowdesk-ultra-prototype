from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from db.database import engine
from db.models import Base
from api.routes import router

# Criar as tabelas no banco de dados
Base.metadata.create_all(bind=engine)

# Inicializar a aplicação FastAPI
app = FastAPI(
    title="Parser de Pedidos API",
    description="API para processamento de planilhas de pedidos e extração de dados estruturados",
    version="1.0.0"
)

# Configurar CORS para permitir requisições do frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, especificar os domínios permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir as rotas
app.include_router(router, prefix="/api/v1", tags=["parser"])

@app.get("/")
async def root():
    """
    Endpoint raiz da API
    """
    return {
        "message": "Parser de Pedidos API",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "online"
    }

@app.get("/health")
async def health_check():
    """
    Endpoint de verificação de saúde da aplicação
    """
    return {"status": "healthy", "message": "API está funcionando corretamente"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)