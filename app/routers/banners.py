from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from uuid import UUID

from app.database import get_db
from app.models import Banner, Usuario
from app.schemas import BannerCreate, BannerResponse, BannerUpdate
from app.dependencies import get_current_user

router = APIRouter(prefix="/banners", tags=["Banners"])

@router.get("", response_model=List[BannerResponse])
async def list_banners(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Banner).order_by(Banner.ordem.asc()))
    return result.scalars().all()

@router.post("", response_model=BannerResponse, status_code=status.HTTP_201_CREATED)
async def create_banner(
    banner_in: BannerCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    if current_user.role != "master":
        raise HTTPException(status_code=403, detail="Acesso restrito")
    
    db_banner = Banner(**banner_in.model_dump())
    db.add(db_banner)
    await db.commit()
    await db.refresh(db_banner)
    return db_banner

@router.patch("/{banner_id}", response_model=BannerResponse)
async def update_banner(
    banner_id: UUID,
    banner_in: BannerUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    if current_user.role != "master":
        raise HTTPException(status_code=403, detail="Acesso restrito")
        
    result = await db.execute(select(Banner).where(Banner.id == banner_id))
    db_banner = result.scalar_one_or_none()
    if not db_banner:
        raise HTTPException(status_code=404, detail="Banner não encontrado")
        
    for key, value in banner_in.model_dump(exclude_unset=True).items():
        setattr(db_banner, key, value)
        
    await db.commit()
    await db.refresh(db_banner)
    return db_banner

@router.delete("/{banner_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_banner(
    banner_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    if current_user.role != "master":
        raise HTTPException(status_code=403, detail="Acesso restrito")
        
    result = await db.execute(select(Banner).where(Banner.id == banner_id))
    db_banner = result.scalar_one_or_none()
    if not db_banner:
        raise HTTPException(status_code=404, detail="Banner não encontrado")
        
    await db.delete(db_banner)
    await db.commit()
