import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import AsyncSessionLocal, get_db
from app.models import Blockout, Professional
from app.schemas import BlockoutCreate, BlockoutResponse
from app.dependencies import get_current_user

router = APIRouter(prefix="/blockouts", tags=["Bloqueios"])

@router.get("", response_model=List[BlockoutResponse])
async def get_blockouts(
    professional_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db)
):
    query = select(Blockout)
    if professional_id:
        query = query.where(Blockout.professional_id == professional_id)
    
    result = await db.execute(query)
    return result.scalars().all()

@router.post("", response_model=BlockoutResponse, status_code=status.HTTP_201_CREATED)
async def create_blockout(
    blockout_in: BlockoutCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    if current_user.role != "master":
        raise HTTPException(status_code=403, detail="Apenas admin pode gerenciar bloqueios")
        
    prof = await db.get(Professional, blockout_in.professional_id)
    if not prof:
        raise HTTPException(status_code=404, detail="Profissional não encontrado")

    new_blockout = Blockout(
        professional_id=blockout_in.professional_id,
        date=blockout_in.date,
        start_time=blockout_in.start_time,
        end_time=blockout_in.end_time
    )
    db.add(new_blockout)
    await db.commit()
    await db.refresh(new_blockout)
    return new_blockout

@router.delete("/{blockout_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_blockout(
    blockout_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    if current_user.role != "master":
        raise HTTPException(status_code=403, detail="Apenas admin pode gerenciar bloqueios")
        
    blockout = await db.get(Blockout, blockout_id)
    if not blockout:
        raise HTTPException(status_code=404, detail="Bloqueio não encontrado")
        
    await db.delete(blockout)
    await db.commit()
