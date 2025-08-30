from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import io
import pandas as pd

from db.database import get_db
from db.models import Pedidos, ItensPedido
from api.schemas import ProcessamentoResponse
from core.parser import load_sheet, parse

router = APIRouter()

@router.post("/processar-planilha/", response_model=ProcessamentoResponse)
async def processar_planilha(
    arquivo: UploadFile = File(...),
    debug: bool = False,
    db: Session = Depends(get_db)
):
    """
    Processa uma planilha de pedidos (.ods, .xls, .xlsx) e salva no banco de dados.
    
    - **arquivo**: Arquivo da planilha para processar
    - **debug**: Se True, retorna os logs detalhados do processamento
    """
    
    # Verificar se o arquivo tem uma extensão válida
    if not arquivo.filename or not arquivo.filename.lower().endswith(('.ods', '.xls', '.xlsx')):
        raise HTTPException(
            status_code=400, 
            detail="Arquivo deve ser uma planilha (.ods, .xls, .xlsx)"
        )
    
    try:
        # Ler o conteúdo do arquivo
        contents = await arquivo.read()
        file_obj = io.BytesIO(contents)
        file_obj.name = arquivo.filename
        
        # Processar a planilha usando o parser
        df_raw = load_sheet(file_obj)
        df_pedidos, df_itens, df_totais, logs = parse(df_raw, debug=debug)
        
        # Salvar pedidos no banco de dados
        pedidos_salvos = 0
        for _, row in df_pedidos.iterrows():
            try:
                pedido = Pedidos(**row.to_dict())
                
                # Verificar se o pedido já existe
                existing_pedido = db.query(Pedidos).filter(Pedidos.pedido_id == pedido.pedido_id).first()
                if existing_pedido:
                    # Atualizar pedido existente
                    for key, value in row.to_dict().items():
                        setattr(existing_pedido, key, value)
                else:
                    # Adicionar novo pedido
                    db.add(pedido)
                    
                pedidos_salvos += 1
            except Exception as e:
                logs.append(f"Erro ao salvar pedido {row.get('pedido_id', 'N/A')}: {str(e)}")
                continue
        
        # Salvar itens no banco de dados
        itens_salvos = 0
        for _, row in df_itens.iterrows():
            try:
                item = ItensPedido(**row.to_dict())
                
                # Verificar se o item já existe (mesmo pedido_id e codigo)
                existing_item = db.query(ItensPedido).filter(
                    ItensPedido.pedido_id == item.pedido_id,
                    ItensPedido.codigo == item.codigo
                ).first()
                
                if existing_item:
                    # Atualizar item existente
                    for key, value in row.to_dict().items():
                        setattr(existing_item, key, value)
                else:
                    # Adicionar novo item
                    db.add(item)
                    
                itens_salvos += 1
            except Exception as e:
                logs.append(f"Erro ao salvar item {row.get('codigo', 'N/A')} do pedido {row.get('pedido_id', 'N/A')}: {str(e)}")
                continue
        
        # Commit das mudanças
        try:
            db.commit()
        except IntegrityError as e:
            db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Erro de integridade do banco de dados: {str(e)}"
            )
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Erro ao salvar no banco de dados: {str(e)}"
            )
        
        # Preparar resposta
        response = ProcessamentoResponse(
            status="sucesso",
            pedidos_processados=pedidos_salvos,
            itens_processados=itens_salvos,
            logs=logs if debug else None
        )
        
        return response
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Erro no formato da planilha: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")


@router.get("/status/")
async def status():
    """
    Endpoint simples para verificar se a API está funcionando
    """
    return {"status": "API funcionando", "message": "Parser de Pedidos Online"}


@router.get("/pedidos/count/")
async def contar_pedidos(db: Session = Depends(get_db)):
    """
    Retorna o número total de pedidos no banco de dados
    """
    try:
        total = db.query(Pedidos).count()
        return {"total_pedidos": total}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao contar pedidos: {str(e)}")


@router.get("/itens/count/")
async def contar_itens(db: Session = Depends(get_db)):
    """
    Retorna o número total de itens no banco de dados
    """
    try:
        total = db.query(ItensPedido).count()
        return {"total_itens": total}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao contar itens: {str(e)}")