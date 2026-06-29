from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List

from app.database import get_db
from app.models import Pedido, ItemPedido, Produto, Usuario, Cliente, Configuracao
from app.schemas import PedidoCreate, PedidoResponse
from app.dependencies import get_current_user
from app.services.whatsapp import whatsapp_service
from app.utils.pix import generate_pix_brcode

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
    background_tasks: BackgroundTasks,
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
    pedido_completo = result.scalar_one()

    # Buscar configuração do PIX
    conf_result = await db.execute(select(Configuracao).where(Configuracao.id == 1))
    config = conf_result.scalar_one_or_none()

    if config and config.pix_chave and config.pix_nome_recebedor and config.pix_cidade_recebedor:
        br_code = generate_pix_brcode(
            chave=config.pix_chave,
            tipo=config.pix_tipo,
            nome=config.pix_nome_recebedor,
            cidade=config.pix_cidade_recebedor,
            valor=total,
            txid=str(novo_pedido.id)[:10]
        )
    else:
        br_code = "CHAVE PIX NÃO CONFIGURADA NO PAINEL ADMIN"
    
    # Injeta na resposta da API
    pedido_completo.pix_copia_cola = br_code

    msg = f"🛍️ *Olá {cliente.nome.split()[0]}! Seu pedido foi gerado com sucesso.*\n\n"
    msg += f"📦 *Pedido:* #{str(novo_pedido.id)[:8]}\n"
    msg += f"💰 *Total:* R$ {total:.2f}\n\n"
    msg += f"Para confirmar e validarmos a sua compra para separação, realize o pagamento via *PIX Copia e Cola* abaixo:\n\n"
    msg += f"```{br_code}```\n\n"
    msg += f"Assim que o pagamento for efetuado, já autorizamos o seu pacote para envio! 💖"
    
    # Enviar mensagem em background
    background_tasks.add_task(whatsapp_service.send_text_message, cliente.whatsapp, msg)

    return pedido_completo
