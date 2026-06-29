from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.database import get_db
from app.models import Cliente, Usuario
from app.schemas import ClienteResponse
from app.dependencies import get_current_user

router = APIRouter(prefix="/clientes", tags=["Clientes"])

@router.get("", response_model=List[ClienteResponse])
async def list_clientes(db: AsyncSession = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    if current_user.role != "master":
        raise HTTPException(status_code=403, detail="Acesso restrito")
        
    result = await db.execute(select(Cliente))
    return result.scalars().all()
