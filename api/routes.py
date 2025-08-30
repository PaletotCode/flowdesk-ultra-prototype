"""
Definição das rotas da API FastAPI.
"""
import uuid
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
import math

from ..db.database import get_db
from ..db.models import Upload, Pedido, ItemPedido, TotalPedido
from ..core.parser import parse, load_sheet
from ..core.gcs_utils import download_file_from_gcs
from .schemas import (
    ProcessFileRequest, ProcessFileResponse, UploadStatusResponse,
    PedidoSchema, PaginatedPedidosResponse, ErrorResponse
)

logger = logging.getLogger(__name__)

# Cria o router da API
router = APIRouter(prefix="/v1", tags=["api"])


async def process_file_background(upload_id: str, file_url: str):
    """
    Processa o arquivo em background usando o parser original.
    """
    from ..db.database import get_db_session
    
    db = get_db_session()
    try:
        # Atualiza status para processando
        upload = db.query(Upload).filter(Upload.id == upload_id).first()
        if not upload:
            logger.error(f"Upload {upload_id} não encontrado")
            return
        
        upload.status = "processing"
        db.commit()
        
        logger.info(f"Iniciando processamento do arquivo {file_url}")
        
        # Baixa o arquivo do GCS
        file_content, filename = await download_file_from_gcs(file_url)
        
        # Carrega a planilha usando a função original
        df_raw = load_sheet(file_content, filename)
        
        # Processa usando o parser original
        df_pedidos, df_itens, df_totais, logs = parse(df_raw, debug=True)
        
        logger.info(f"Parser concluído: {len(df_pedidos)} pedidos, {len(df_itens)} itens")
        
        # Salva os pedidos no banco
        pedidos_salvos = []
        for _, pedido_row in df_pedidos.iterrows():
            pedido_db = Pedido(
                upload_id=upload_id,
                **pedido_row.to_dict()
            )
            db.add(pedido_db)
            db.flush()  # Para obter o ID
            pedidos_salvos.append(pedido_db)
        
        # Salva os itens no banco
        itens_count = 0
        for _, item_row in df_itens.iterrows():
            # Encontra o pedido correspondente
            pedido_db = None
            for p in pedidos_salvos:
                if p.pedido_id == item_row['pedido_id']:
                    pedido_db = p
                    break
            
            if pedido_db:
                item_dict = item_row.to_dict()
                item_dict['pedido_db_id'] = pedido_db.id
                
                item_db = ItemPedido(**item_dict)
                db.add(item_db)
                itens_count += 1
        
        # Salva os totais no banco
        for _, total_row in df_totais.iterrows():
            total_db = TotalPedido(**total_row.to_dict())
            db.add(total_db)
        
        # Atualiza o status do upload
        upload.status = "completed"
        upload.completed_at = func.now()
        upload.total_pedidos = len(df_pedidos)
        upload.total_itens = itens_count
        
        db.commit()
        logger.info(f"Processamento do upload {upload_id} concluído com sucesso")
        
    except Exception as e:
        logger.error(f"Erro no processamento do upload {upload_id}: {str(e)}")
        
        # Atualiza status para erro
        try:
            upload = db.query(Upload).filter(Upload.id == upload_id).first()
            if upload:
                upload.status = "failed"
                upload.error_message = str(e)
                upload.completed_at = func.now()
                db.commit()
        except Exception as commit_error:
            logger.error(f"Erro ao salvar status de erro: {commit_error}")
    
    finally:
        db.close()


@router.post("/uploads/process", response_model=ProcessFileResponse)
async def process_file(
    request: ProcessFileRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Inicia o processamento de um arquivo do GCS em background.
    """
    try:
        # Gera um ID único para o upload
        upload_id = str(uuid.uuid4())
        
        # Extrai o nome do arquivo da URL
        filename = request.file_url.split("/")[-1]
        
        # Cria o registro de upload
        upload = Upload(
            id=upload_id,
            file_url=request.file_url,
            filename=filename,
            status="processing"
        )
        
        db.add(upload)
        db.commit()
        
        # Inicia o processamento em background
        background_tasks.add_task(process_file_background, upload_id, request.file_url)
        
        logger.info(f"Processamento iniciado para {request.file_url} (ID: {upload_id})")
        
        return ProcessFileResponse(
            status="processing_started",
            upload_id=upload_id
        )
        
    except Exception as e:
        logger.error(f"Erro ao iniciar processamento: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")


@router.get("/uploads/{upload_id}/status", response_model=UploadStatusResponse)
async def get_upload_status(upload_id: str, db: Session = Depends(get_db)):
    """
    Verifica o status de um processamento.
    """
    upload = db.query(Upload).filter(Upload.id == upload_id).first()
    
    if not upload:
        raise HTTPException(status_code=404, detail="Upload não encontrado")
    
    return UploadStatusResponse(
        status=upload.status,
        item_count=upload.total_itens or 0,
        pedido_count=upload.total_pedidos or 0,
        created_at=upload.created_at,
        completed_at=upload.completed_at,
        error_message=upload.error_message,
        filename=upload.filename
    )


@router.get("/pedidos", response_model=PaginatedPedidosResponse)
async def list_pedidos(
    page: int = Query(1, ge=1, description="Número da página"),
    per_page: int = Query(50, ge=1, le=200, description="Itens por página"),
    upload_id: Optional[str] = Query(None, description="Filtrar por upload específico"),
    db: Session = Depends(get_db)
):
    """
    Lista os pedidos processados com paginação.
    """
    try:
        # Query base
        query = db.query(Pedido)
        
        # Filtro por upload se especificado
        if upload_id:
            query = query.filter(Pedido.upload_id == upload_id)
        
        # Conta total
        total = query.count()
        
        # Calcula paginação
        offset = (page - 1) * per_page
        pages = math.ceil(total / per_page)
        
        # Busca os pedidos da página
        pedidos = query.offset(offset).limit(per_page).all()
        
        return PaginatedPedidosResponse(
            pedidos=pedidos,
            total=total,
            page=page,
            per_page=per_page,
            pages=pages
        )
        
    except Exception as e:
        logger.error(f"Erro ao listar pedidos: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")


@router.get("/pedidos/{pedido_id}")
async def get_pedido_details(pedido_id: str, db: Session = Depends(get_db)):
    """
    Obtém detalhes de um pedido específico incluindo seus itens.
    """
    try:
        # Busca o pedido
        pedido = db.query(Pedido).filter(Pedido.pedido_id == pedido_id).first()
        
        if not pedido:
            raise HTTPException(status_code=404, detail="Pedido não encontrado")
        
        # Busca os itens do pedido
        itens = db.query(ItemPedido).filter(ItemPedido.pedido_id == pedido_id).all()
        
        # Busca o total do pedido
        total = db.query(TotalPedido).filter(TotalPedido.pedido_id == pedido_id).first()
        
        return {
            "pedido": pedido,
            "itens": itens,
            "total": total
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar pedido {pedido_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")


@router.get("/uploads")
async def list_uploads(
    page: int = Query(1, ge=1, description="Número da página"),
    per_page: int = Query(20, ge=1, le=100, description="Itens por página"),
    db: Session = Depends(get_db)
):
    """
    Lista todos os uploads realizados com paginação.
    """
    try:
        # Query base ordenada por data de criação (mais recente primeiro)
        query = db.query(Upload).order_by(Upload.created_at.desc())
        
        # Conta total
        total = query.count()
        
        # Calcula paginação
        offset = (page - 1) * per_page
        pages = math.ceil(total / per_page)
        
        # Busca os uploads da página
        uploads = query.offset(offset).limit(per_page).all()
        
        return {
            "uploads": uploads,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": pages
        }
        
    except Exception as e:
        logger.error(f"Erro ao listar uploads: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")


@router.get("/health")
async def health_check():
    """
    Endpoint de health check para verificar se a API está funcionando.
    """
    return {"status": "healthy", "service": "pedidos-parser-api"}