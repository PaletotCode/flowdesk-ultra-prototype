from pydantic import BaseModel
from typing import Optional, List

class ProcessamentoResponse(BaseModel):
    status: str
    pedidos_processados: int
    itens_processados: int
    logs: Optional[List[str]] = None

class PedidoBase(BaseModel):
    pedido_id: str
    tipo_pedido: Optional[str] = None
    vendedor: Optional[str] = None
    cliente: Optional[str] = None
    data_cad_cliente: Optional[str] = None
    origem_cliente: Optional[str] = None
    telefone_cliente: Optional[str] = None
    data_hora_fechamento: Optional[str] = None
    data_hora_recebimento: Optional[str] = None
    vlr_produtos: Optional[float] = 0.0
    vlr_servicos: Optional[float] = 0.0
    frete: Optional[float] = 0.0
    out_desp: Optional[float] = 0.0
    juros: Optional[float] = 0.0
    tc: Optional[float] = 0.0
    desconto: Optional[float] = 0.0
    cred_man: Optional[float] = 0.0
    vlr_liquido: Optional[float] = 0.0
    custo: Optional[float] = 0.0
    percent_lucro: Optional[float] = 0.0
    juros_embutidos: Optional[float] = 0.0
    frete_cif_embutidos: Optional[float] = 0.0
    retencao_real: Optional[float] = 0.0
    base_lucro_pres: Optional[float] = 0.0
    percent_lucro_pres: Optional[float] = 0.0
    vlr_lucro_pres: Optional[float] = 0.0
    custo_compra: Optional[float] = 0.0
    vendedor_externo: Optional[str] = None
    dt_cad_cliente: Optional[str] = None
    origem: Optional[str] = None
    prazo_medio: Optional[float] = 0.0
    desconto_geral: Optional[float] = 0.0
    percent_desconto_geral: Optional[float] = 0.0
    valor_impulso: Optional[float] = 0.0
    valor_brinde: Optional[float] = 0.0
    ent_agrupada: Optional[str] = None
    usuario_insercao: Optional[str] = None
    vlr_comis_emp_vda_direta: Optional[float] = 0.0
    tab_preco: Optional[str] = None
    pedido_da_devolucao: Optional[str] = None
    dt_extracao: Optional[str] = None

class ItemPedidoBase(BaseModel):
    pedido_id: str
    codigo: str
    nome: Optional[str] = None
    marca: Optional[str] = None
    promocao: Optional[str] = None
    quantidade: Optional[float] = 0.0
    preco_venda: Optional[float] = 0.0
    juros_desc: Optional[float] = 0.0
    total_liquido: Optional[float] = 0.0
    valor_custo: Optional[float] = 0.0
    percent_lucro: Optional[float] = 0.0
    custo_compra: Optional[float] = 0.0
    linha_origem: Optional[int] = None
    subtotal_item: Optional[float] = 0.0

class Pedido(PedidoBase):
    id: int
    
    class Config:
        from_attributes = True

class ItemPedido(ItemPedidoBase):
    id: int
    
    class Config:
        from_attributes = True