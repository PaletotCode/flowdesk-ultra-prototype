import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# URL de conexão do PostgreSQL
# Formato: postgresql://username:password@localhost/database_name
# Para Railway ou outros serviços cloud, use a variável de ambiente DATABASE_URL
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/parser_db")

# Para compatibilidade com algumas versões do PostgreSQL no Railway
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """Dependency para obter uma sessão do banco de dados"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()