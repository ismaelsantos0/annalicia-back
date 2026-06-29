from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from uuid import UUID

from app.database import get_db
from app.models import ZonaEntrega, Usuario
from app.schemas import ZonaEntregaResponse, ZonaEntregaCreate, ZonaEntregaUpdate
from app.dependencies import get_current_user

router = APIRouter(prefix="/zonas-entrega", tags=["Zonas de Entrega"])

@router.get("", response_model=List[ZonaEntregaResponse])
async def list_zonas(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ZonaEntrega).where(ZonaEntrega.ativo == True).order_by(ZonaEntrega.bairro))
    return result.scalars().all()

@router.post("", response_model=ZonaEntregaResponse, status_code=status.HTTP_201_CREATED)
async def create_zona(
    zona: ZonaEntregaCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    if current_user.role != "master":
        raise HTTPException(status_code=403, detail="Acesso restrito")
    
    # Verifica se já existe o bairro
    result = await db.execute(select(ZonaEntrega).where(ZonaEntrega.bairro == zona.bairro.strip()))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Bairro já cadastrado")

    nova_zona = ZonaEntrega(
        bairro=zona.bairro.strip(),
        taxa=zona.taxa,
        ativo=zona.ativo
    )
    db.add(nova_zona)
    await db.commit()
    await db.refresh(nova_zona)
    return nova_zona

@router.patch("/{id}", response_model=ZonaEntregaResponse)
async def update_zona(
    id: UUID,
    zona_update: ZonaEntregaUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    if current_user.role != "master":
        raise HTTPException(status_code=403, detail="Acesso restrito")
        
    result = await db.execute(select(ZonaEntrega).where(ZonaEntrega.id == id))
    zona_db = result.scalar_one_or_none()
    
    if not zona_db:
        raise HTTPException(status_code=404, detail="Zona de entrega não encontrada")

    if zona_update.taxa is not None:
        zona_db.taxa = zona_update.taxa
    if zona_update.ativo is not None:
        zona_db.ativo = zona_update.ativo
        
    await db.commit()
    await db.refresh(zona_db)
    return zona_db

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_zona(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    if current_user.role != "master":
        raise HTTPException(status_code=403, detail="Acesso restrito")
        
    result = await db.execute(select(ZonaEntrega).where(ZonaEntrega.id == id))
    zona_db = result.scalar_one_or_none()
    
    if not zona_db:
        raise HTTPException(status_code=404, detail="Zona de entrega não encontrada")

    await db.delete(zona_db)
    await db.commit()
