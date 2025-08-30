"""
Modelos SQLAlchemy para o banco de dados PostgreSQL.
Define as tabelas baseadas na estrutura extraída pelo parser.
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()


class Upload(Base):
    """
    Tabela para controlar o status dos uploads e processamentos.
    """
    __tablename__ = "uploads"
    
    id = Column(String, primary_key=True)  # UUID gerado
    file_url = Column(String, nullable=False)  # URL do arquivo no GCS
    filename = Column(String, nullable=False)  # Nome original do arquivo
    status = Column(String, nullable=False, default="processing")  # processing, completed, failed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    total_pedidos = Column(Integer, default=0)
    total_itens = Column(Integer, default=0)
    
    # Relacionamento com pedidos
    pedidos = relationship("Pedido", back_populates="upload", cascade="all, delete-orphan")


class Pedido(Base):
    """
    Tabela de pedidos - baseada na estrutura extraída pelo parser.
    """
    __tablename__ = "pedidos"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    upload_id = Column(String, ForeignKey("uploads.id"), nullable=False)
    
    # Campos do pedido (conforme extraído pelo parser)
    pedido_id = Column(String, nullable=False)
    tipo_pedido = Column(String)
    vendedor = Column(String)
    cliente = Column(String)
    data_cad_cliente = Column(String)
    origem_cliente = Column(String)
    telefone_cliente = Column(String)
    data_hora_fechamento = Column(String)
    data_hora_recebimento = Column(String)
    
    # Valores monetários
    vlr_produtos = Column(Float, default=0.0)
    vlr_servicos = Column(Float, default=0.0)
    frete = Column(Float, default=0.0)
    out_desp = Column(Float, default=0.0)
    juros = Column(Float, default=0.0)
    tc = Column(Float, default=0.0)
    desconto = Column(Float, default=0.0)
    cred_man = Column(Float, default=0.0)
    vlr_liquido = Column(Float, default=0.0)
    custo = Column(Float, default=0.0)
    percent_lucro = Column(Float, default=0.0)
    juros_embutidos = Column(Float, default=0.0)
    frete_cif_embutidos = Column(Float, default=0.0)
    retencao_real = Column(Float, default=0.0)
    base_lucro_pres = Column(Float, default=0.0)
    percent_lucro_pres = Column(Float, default=0.0)
    vlr_lucro_pres = Column(Float, default=0.0)
    custo_compra = Column(Float, default=0.0)
    prazo_medio = Column(Float, default=0.0)
    desconto_geral = Column(Float, default=0.0)
    percent_desconto_geral = Column(Float, default=0.0)
    valor_impulso = Column(Float, default=0.0)
    valor_brinde = Column(Float, default=0.0)
    vlr_comis_emp_vda_direta = Column(Float, default=0.0)
    
    # Campos adicionais
    vendedor_externo = Column(String)
    dt_cad_cliente = Column(String)
    origem = Column(String)
    ent_agrupada = Column(String)
    usuario_insercao = Column(String)
    tab_preco = Column(String)
    pedido_da_devolucao = Column(String)
    dt_extracao = Column(String)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relacionamentos
    upload = relationship("Upload", back_populates="pedidos")
    itens = relationship("ItemPedido", back_populates="pedido", cascade="all, delete-orphan")


class ItemPedido(Base):
    """
    Tabela de itens dos pedidos.
    """
    __tablename__ = "itens_pedido"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    pedido_id = Column(String, nullable=False)  # ID do pedido (não FK para a tabela pedidos)
    pedido_db_id = Column(Integer, ForeignKey("pedidos.id"), nullable=False)  # FK para o registro na tabela pedidos
    
    # Dados do item
    codigo = Column(String, nullable=False)
    nome = Column(String)
    marca = Column(String)
    promocao = Column(String)
    quantidade = Column(Float, default=0.0)
    preco_venda = Column(Float, default=0.0)
    juros_desc = Column(Float, default=0.0)
    total_liquido = Column(Float, default=0.0)
    valor_custo = Column(Float, default=0.0)
    percent_lucro = Column(Float, default=0.0)
    custo_compra = Column(Float, default=0.0)
    linha_origem = Column(Integer)
    subtotal_item = Column(Float, default=0.0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relacionamento
    pedido = relationship("Pedido", back_populates="itens")


class TotalPedido(Base):
    """
    Tabela com totais agregados por pedido.
    """
    __tablename__ = "totais_pedido"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    pedido_id = Column(String, nullable=False)
    qtd_itens = Column(Integer, default=0)
    valor_bruto = Column(Float, default=0.0)
    valor_descontos = Column(Float, default=0.0)
    valor_liquido = Column(Float, default=0.0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())