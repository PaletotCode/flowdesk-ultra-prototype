"""
Schemas Pydantic para validação de entrada e saída da API.
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from enum import Enum


class UploadStatus(str, Enum):
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ProcessFileRequest(BaseModel):
    """Schema para requisição de processamento de arquivo."""
    file_url: str = Field(..., description="URL do arquivo no Google Cloud Storage (gs://bucket/path)")
    
    @validator('file_url')
    def validate_gcs_url(cls, v):
        if not v.startswith('gs://'):
            raise ValueError('file_url deve ser uma URL válida do GCS (gs://bucket/path)')
        return v


class ProcessFileResponse(BaseModel):
    """Schema para resposta de início de processamento."""
    status: str = Field(default="processing_started", description="Status do processamento")
    upload_id: str = Field(..., description="ID único do upload para acompanhamento")


class UploadStatusResponse(BaseModel):
    """Schema para resposta do status de processamento."""
    status: UploadStatus = Field(..., description="Status atual do processamento")
    item_count: int = Field(default=0, description="Quantidade de itens processados")
    pedido_count: int = Field(default=0, description="Quantidade de pedidos processados")
    created_at: Optional[datetime] = Field(None, description="Data/hora de início do processamento")
    completed_at: Optional[datetime] = Field(None, description="Data/hora de conclusão")
    error_message: Optional[str] = Field(None, description="Mensagem de erro caso falhe")
    filename: Optional[str] = Field(None, description="Nome original do arquivo")


class PedidoSchema(BaseModel):
    """Schema para um pedido."""
    id: int
    pedido_id: str
    tipo_pedido: Optional[str] = None
    vendedor: Optional[str] = None
    cliente: Optional[str] = None
    data_cad_cliente: Optional[str] = None
    origem_cliente: Optional[str] = None
    telefone_cliente: Optional[str] = None
    data_hora_fechamento: Optional[str] = None
    data_hora_recebimento: Optional[str] = None
    vlr_produtos: float = 0.0
    vlr_servicos: float = 0.0
    frete: float = 0.0
    out_desp: float = 0.0
    juros: float = 0.0
    tc: float = 0.0
    desconto: float = 0.0
    cred_man: float = 0.0
    vlr_liquido: float = 0.0
    custo: float = 0.0
    percent_lucro: float = 0.0
    juros_embutidos: float = 0.0
    frete_cif_embutidos: float = 0.0
    retencao_real: float = 0.0
    base_lucro_pres: float = 0.0
    percent_lucro_pres: float = 0.0
    vlr_lucro_pres: float = 0.0
    custo_compra: float = 0.0
    vendedor_externo: Optional[str] = None
    dt_cad_cliente: Optional[str] = None
    origem: Optional[str] = None
    prazo_medio: float = 0.0
    desconto_geral: float = 0.0
    percent_desconto_geral: float = 0.0
    valor_impulso: float = 0.0
    valor_brinde: float = 0.0
    ent_agrupada: Optional[str] = None
    usuario_insercao: Optional[str] = None
    vlr_comis_emp_vda_direta: float = 0.0
    tab_preco: Optional[str] = None
    pedido_da_devolucao: Optional[str] = None
    dt_extracao: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ItemPedidoSchema(BaseModel):
    """Schema para um item de pedido."""
    id: int
    pedido_id: str
    codigo: str
    nome: Optional[str] = None
    marca: Optional[str] = None
    promocao: Optional[str] = None
    quantidade: float = 0.0
    preco_venda: float = 0.0
    juros_desc: float = 0.0
    total_liquido: float = 0.0
    valor_custo: float = 0.0
    percent_lucro: float = 0.0
    custo_compra: float = 0.0
    linha_origem: Optional[int] = None
    subtotal_item: float = 0.0
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TotalPedidoSchema(BaseModel):
    """Schema para totais de um pedido."""
    id: int
    pedido_id: str
    qtd_itens: int = 0
    valor_bruto: float = 0.0
    valor_descontos: float = 0.0
    valor_liquido: float = 0.0
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PaginatedPedidosResponse(BaseModel):
    """Schema para resposta paginada de pedidos."""
    pedidos: List[PedidoSchema]
    total: int = Field(..., description="Total de pedidos disponíveis")
    page: int = Field(..., description="Página atual")
    per_page: int = Field(..., description="Itens por página")
    pages: int = Field(..., description="Total de páginas")


class PaginatedItensResponse(BaseModel):
    """Schema para resposta paginada de itens."""
    itens: List[ItemPedidoSchema]
    total: int = Field(..., description="Total de itens disponíveis")
    page: int = Field(..., description="Página atual")
    per_page: int = Field(..., description="Itens por página")
    pages: int = Field(..., description="Total de páginas")


class ErrorResponse(BaseModel):
    """Schema para respostas de erro."""
    error: str = Field(..., description="Mensagem de erro")
    detail: Optional[str] = Field(None, description="Detalhes adicionais do erro")