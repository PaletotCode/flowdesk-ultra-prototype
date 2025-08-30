# main.py - Versão Atualizada
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config.database import engine
from modules.relatorio_vend_dev_com_itens import models as relatorio_models
from modules.relatorio_vend_dev_com_itens.routes import router as relatorio_router

# Criar as tabelas no banco de dados a partir do módulo específico
relatorio_models.Base.metadata.create_all(bind=engine)

# Inicializar a aplicação FastAPI
app = FastAPI(
    title="FlowDesk Ultra API",
    description="API para processamento e consulta de planilhas de relatórios",
    version="1.0.0"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir as rotas do módulo de relatório com um prefixo
app.include_router(
    relatorio_router, 
    prefix="/api/v1/relatorio-vend-dev-com-itens", 
    tags=["Relatório Vendas/Devoluções com Itens"]
)

@app.get("/")
async def root():
    return {"message": "FlowDesk Ultra API está online"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}