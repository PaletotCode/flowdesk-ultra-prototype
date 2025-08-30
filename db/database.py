"""
Configuração da conexão com o banco de dados PostgreSQL.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from .models import Base
import logging

logger = logging.getLogger(__name__)

# URL de conexão com o banco (deve vir da variável de ambiente)
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL não está definida nas variáveis de ambiente")

# Cria o engine do SQLAlchemy
engine = create_engine(
    DATABASE_URL,
    poolclass=StaticPool,
    pool_pre_ping=True,  # Verifica conexões antes de usar
    echo=os.getenv("SQL_ECHO", "false").lower() == "true"  # Log das queries SQL se SQL_ECHO=true
)

# Configura o sessionmaker
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_tables():
    """
    Cria todas as tabelas no banco de dados.
    """
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Tabelas criadas/verificadas com sucesso")
    except Exception as e:
        logger.error(f"Erro ao criar tabelas: {str(e)}")
        raise


def get_db() -> Session:
    """
    Dependency para obter uma sessão do banco de dados.
    Para usar com FastAPI Depends().
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_session() -> Session:
    """
    Retorna uma nova sessão do banco de dados.
    Para uso direto fora dos endpoints da API.
    """
    return SessionLocal()