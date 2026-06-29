from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import uuid

from app.database import get_db
from app.models import Produto, Usuario
from app.schemas import ProdutoCreate, ProdutoResponse, ProdutoEstoqueUpdate, ProdutoUpdate
from app.dependencies import get_current_user
from pydantic import BaseModel

router = APIRouter(prefix="/produtos", tags=["Produtos"])

from sqlalchemy.orm import selectinload

class InstagramImportRequest(BaseModel):
    url: str

@router.post("/import-instagram")
async def import_from_instagram(
    body: InstagramImportRequest,
    current_user: Usuario = Depends(get_current_user)
):
    if current_user.role != "master":
        raise HTTPException(status_code=403, detail="Acesso restrito")
    try:
        from app.services.instagram import fetch_instagram_post
        data = fetch_instagram_post(body.url)
        return data
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Não foi possível buscar o post. Verifique se o link é de um perfil públíco. Detalhe: {str(e)}")

@router.get("", response_model=List[ProdutoResponse])
async def list_produtos(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Produto)
        .options(selectinload(Produto.categoria))
        .where(Produto.is_active == True)
        .order_by(Produto.data_criacao.desc())
    )
    return result.scalars().all()

@router.post("", response_model=ProdutoResponse, status_code=status.HTTP_201_CREATED)
async def create_produto(
    produto: ProdutoCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    if current_user.role != "master":
        raise HTTPException(status_code=403, detail="Acesso restrito")
        
    novo_produto = Produto(**produto.model_dump())
    db.add(novo_produto)
    await db.commit()
    
    # Recarrega o produto com a categoria para o response_model
    result = await db.execute(
        select(Produto)
        .options(selectinload(Produto.categoria))
        .where(Produto.id == novo_produto.id)
    )
    return result.scalar_one()

@router.patch("/{produto_id}", response_model=ProdutoResponse)
async def update_produto(
    produto_id: uuid.UUID,
    update_data: ProdutoUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    if current_user.role != "master":
        raise HTTPException(status_code=403, detail="Acesso restrito")
    result = await db.execute(select(Produto).where(Produto.id == produto_id))
    produto = result.scalar_one_or_none()
    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    data = update_data.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(produto, field, value)
    await db.commit()
    res = await db.execute(
        select(Produto)
        .options(selectinload(Produto.categoria))
        .where(Produto.id == produto_id)
    )
    return res.scalar_one()

@router.delete("/{produto_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_produto(
    produto_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    if current_user.role != "master":
        raise HTTPException(status_code=403, detail="Acesso restrito")
        
    result = await db.execute(select(Produto).where(Produto.id == produto_id))
    produto = result.scalar_one_or_none()
    
    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
        
    produto.is_active = False
    await db.commit()
    return None

@router.patch("/{produto_id}/estoque", response_model=ProdutoResponse)
async def update_estoque(
    produto_id: uuid.UUID,
    update_data: ProdutoEstoqueUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    if current_user.role != "master":
        raise HTTPException(status_code=403, detail="Acesso restrito")
        
    result = await db.execute(select(Produto).where(Produto.id == produto_id))
    produto = result.scalar_one_or_none()
    
    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
        
    produto.estoque = update_data.estoque
    await db.commit()
    
    # Recarrega para resposta
    res = await db.execute(
        select(Produto)
        .options(selectinload(Produto.categoria))
        .where(Produto.id == produto_id)
    )
    return res.scalar_one()

@router.patch("/{produto_id}/destaque", response_model=ProdutoResponse)
async def toggle_destaque(
    produto_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    if current_user.role != "master":
        raise HTTPException(status_code=403, detail="Acesso restrito")
    result = await db.execute(select(Produto).where(Produto.id == produto_id))
    produto = result.scalar_one_or_none()
    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    produto.destaque = not produto.destaque
    await db.commit()
    res = await db.execute(
        select(Produto)
        .options(selectinload(Produto.categoria))
        .where(Produto.id == produto_id)
    )
    return res.scalar_one()

@router.get("/destaques", response_model=List[ProdutoResponse])
async def get_destaques(db: AsyncSession = Depends(get_db)):
    """Retorna produtos em destaque (marcados individualmente ou por categoria destacada)."""
    from app.models import Configuracao
    config_result = await db.execute(select(Configuracao).where(Configuracao.id == 1))
    config = config_result.scalar_one_or_none()
    
    query = select(Produto).options(selectinload(Produto.categoria)).where(Produto.is_active == True)
    
    if config and config.categoria_destaque_id:
        from sqlalchemy import or_
        result = await db.execute(
            query.where(
                or_(Produto.destaque == True, Produto.categoria_id == config.categoria_destaque_id)
            ).order_by(Produto.destaque.desc(), Produto.data_criacao.desc())
        )
    else:
        result = await db.execute(
            query.where(Produto.destaque == True)
            .order_by(Produto.data_criacao.desc())
        )
    return result.scalars().all()
