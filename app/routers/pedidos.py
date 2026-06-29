from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List

from app.database import get_db
from app.models import Pedido, ItemPedido, Produto, Usuario, Cliente
from app.schemas import PedidoCreate, PedidoResponse
from app.dependencies import get_current_user

router = APIRouter(prefix="/pedidos", tags=["Pedidos"])

@router.get("", response_model=List[PedidoResponse])
async def list_pedidos(db: AsyncSession = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    query = select(Pedido).options(selectinload(Pedido.itens), selectinload(Pedido.cliente))
    if current_user.role != "master":
        query = query.where(Pedido.usuario_id == current_user.id)
        
    result = await db.execute(query)
    return result.scalars().all()

@router.post("", response_model=PedidoResponse, status_code=status.HTTP_201_CREATED)
async def create_pedido(
    pedido: PedidoCreate,
    db: AsyncSession = Depends(get_db)
):
    # 1. Buscar ou criar cliente
    result = await db.execute(select(Cliente).where(Cliente.whatsapp == pedido.cliente_whatsapp))
    cliente = result.scalar_one_or_none()
    
    if not cliente:
        cliente = Cliente(
            nome=pedido.cliente_nome,
            whatsapp=pedido.cliente_whatsapp,
            endereco=pedido.cliente_endereco
        )
        db.add(cliente)
        await db.flush()
    else:
        # Atualiza dados se necessário
        cliente.nome = pedido.cliente_nome
        cliente.endereco = pedido.cliente_endereco
        await db.flush()

    # 2. Criar pedido
    novo_pedido = Pedido(cliente_id=cliente.id, total=0.0)
    db.add(novo_pedido)
    await db.flush()
    
    total = 0.0
    for item in pedido.itens:
        # Busca o produto para validar e pegar preco atual
        prod_result = await db.execute(select(Produto).where(Produto.id == item.produto_id, Produto.is_active == True))
        produto_db = prod_result.scalar_one_or_none()
        
        if not produto_db:
            raise HTTPException(status_code=400, detail=f"Produto {item.produto_id} não encontrado ou inativo")
        
        if produto_db.estoque < item.quantidade:
            raise HTTPException(status_code=400, detail=f"Estoque insuficiente para {produto_db.nome}")
            
        produto_db.estoque -= item.quantidade
        
        novo_item = ItemPedido(
            pedido_id=novo_pedido.id,
            produto_id=produto_db.id,
            quantidade=item.quantidade,
            preco_unitario=produto_db.preco
        )
        db.add(novo_item)
        total += (produto_db.preco * item.quantidade)
        
    novo_pedido.total = total
    await db.commit()
    
    # Reload for response
    result = await db.execute(select(Pedido).options(selectinload(Pedido.itens), selectinload(Pedido.cliente)).where(Pedido.id == novo_pedido.id))
    return result.scalar_one()
