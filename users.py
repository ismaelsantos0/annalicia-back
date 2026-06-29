from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.database import AsyncSessionLocal
from app.models import Professional
from app.schemas import ProfessionalCreate, ProfessionalResponse, ProfessionalUpdate
from app.dependencies import get_current_user

router = APIRouter(prefix="/professionals", tags=["Profissionais"])

async def get_db():
    async with AsyncSessionLocal() as db:
        yield db

from app.models import User

@router.get("", response_model=List[ProfessionalResponse])
async def list_professionals(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = select(Professional).where(Professional.is_active == True)
    if current_user.role == "profissional":
        if not current_user.professional_id:
            return []
        query = query.where(Professional.id == current_user.professional_id)
        
    result = await db.execute(query)
    return result.scalars().all()

@router.get("/slug/{slug}", response_model=ProfessionalResponse)
async def get_professional_by_slug(slug: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Professional).where(Professional.slug == slug, Professional.is_active == True))
    prof = result.scalar_one_or_none()
    if not prof:
        raise HTTPException(status_code=404, detail="Profissional não encontrado")
    return prof

@router.post("", response_model=ProfessionalResponse, status_code=status.HTTP_201_CREATED)
async def create_professional(
    prof: ProfessionalCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in ("master", "clinica"):
        raise HTTPException(status_code=403, detail="Acesso negado")
    
    import re
    prof_data = prof.model_dump()
    if not prof_data.get("slug"):
        base_slug = re.sub(r'[^a-z0-9]+', '-', prof_data["name"].lower()).strip('-')
        # Check uniqueness (simplified, append random if exists)
        from sqlalchemy import select
        existing = await db.execute(select(Professional).where(Professional.slug == base_slug))
        if existing.scalar_one_or_none():
            import random
            base_slug = f"{base_slug}-{random.randint(1000,9999)}"
        prof_data["slug"] = base_slug

    new_prof = Professional(**prof_data)
    db.add(new_prof)
    await db.commit()
    await db.refresh(new_prof)
    return new_prof

import uuid

@router.put("/{prof_id}", response_model=ProfessionalResponse)
async def update_professional(
    prof_id: uuid.UUID,
    prof_update: ProfessionalUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in ("master", "clinica"):
        raise HTTPException(status_code=403, detail="Acesso negado")
    
    result = await db.execute(select(Professional).where(Professional.id == prof_id))
    prof = result.scalar_one_or_none()
    if not prof:
        raise HTTPException(status_code=404, detail="Profissional não encontrado")
    
    update_data = prof_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(prof, key, value)
        
    await db.commit()
    await db.refresh(prof)
    return prof

@router.delete("/{prof_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_professional(
    prof_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "master":
        raise HTTPException(status_code=403, detail="Apenas master pode deletar")
    
    result = await db.execute(select(Professional).where(Professional.id == prof_id))
    prof = result.scalar_one_or_none()
    if not prof:
        raise HTTPException(status_code=404, detail="Profissional não encontrado")
    
    # Soft delete
    prof.is_active = False
    await db.commit()
    return None
