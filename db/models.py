from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from db.database import Base

class Pedidos(Base):
    __tablename__ = "pedidos"
    
    id = Column(Integer, primary_key=True, index=True)
    pedido_id = Column(String, unique=True, index=True, nullable=False)
    tipo_pedido = Column(String)
    vendedor = Column(String)
    cliente = Column(String)
    data_cad_cliente = Column(String)
    origem_cliente = Column(String)
    telefone_cliente = Column(String)
    data_hora_fechamento = Column(String)
    data_hora_recebimento = Column(String)
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
    vendedor_externo = Column(String)
    dt_cad_cliente = Column(String)
    origem = Column(String)
    prazo_medio = Column(Float, default=0.0)
    desconto_geral = Column(Float, default=0.0)
    percent_desconto_geral = Column(Float, default=0.0)
    valor_impulso = Column(Float, default=0.0)
    valor_brinde = Column(Float, default=0.0)
    ent_agrupada = Column(String)
    usuario_insercao = Column(String)
    vlr_comis_emp_vda_direta = Column(Float, default=0.0)
    tab_preco = Column(String)
    pedido_da_devolucao = Column(String)
    dt_extracao = Column(String)
    
    # Relacionamento com itens
    itens = relationship("ItensPedido", back_populates="pedido")

class ItensPedido(Base):
    __tablename__ = "itens_pedido"
    
    id = Column(Integer, primary_key=True, index=True)
    pedido_id = Column(String, ForeignKey("pedidos.pedido_id"), nullable=False)
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
    
    # Relacionamento com pedido
    pedido = relationship("Pedidos", back_populates="itens")