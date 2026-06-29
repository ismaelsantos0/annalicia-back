from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import uuid

from app.database import get_db
from app.models import Produto, Usuario
from app.schemas import ProdutoCreate, ProdutoResponse
from app.dependencies import get_current_user

router = APIRouter(prefix="/produtos", tags=["Produtos"])

@router.get("", response_model=List[ProdutoResponse])
async def list_produtos(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Produto).where(Produto.is_active == True))
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
    await db.refresh(novo_produto)
    return novo_produto

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
