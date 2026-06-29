from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import uuid

from app.database import get_db
from app.models import Categoria, Usuario
from app.schemas import CategoriaCreate, CategoriaResponse
from app.dependencies import get_current_user

router = APIRouter(prefix="/categorias", tags=["Categorias"])

@router.get("", response_model=List[CategoriaResponse])
async def listar_categorias(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Categoria).order_by(Categoria.nome))
    return result.scalars().all()

@router.post("", response_model=CategoriaResponse, status_code=status.HTTP_201_CREATED)
async def criar_categoria(
    categoria: CategoriaCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    # Verifica se já existe
    result = await db.execute(select(Categoria).where(Categoria.nome == categoria.nome))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Categoria já existe")
    
    nova_cat = Categoria(nome=categoria.nome)
    db.add(nova_cat)
    await db.commit()
    await db.refresh(nova_cat)
    return nova_cat

@router.delete("/{categoria_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deletar_categoria(
    categoria_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    result = await db.execute(select(Categoria).where(Categoria.id == categoria_id))
    cat = result.scalar_one_or_none()
    if not cat:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    
    await db.delete(cat)
    await db.commit()
    return None
