from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.database import get_db
from app.models import Usuario
from app.schemas import UsuarioResponse, UsuarioCreate
from app.dependencies import get_current_user
from app.security import hash_password

router = APIRouter(prefix="/usuarios", tags=["Usuários"])

@router.get("", response_model=List[UsuarioResponse])
async def list_usuarios(db: AsyncSession = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    if current_user.role != "master":
        raise HTTPException(status_code=403, detail="Acesso restrito ao master")
        
    result = await db.execute(select(Usuario).where(Usuario.is_active == True))
    return result.scalars().all()

@router.post("", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED)
async def create_usuario(
    usuario: UsuarioCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    if current_user.role != "master":
        raise HTTPException(status_code=403, detail="Acesso restrito ao master")
        
    existing = await db.execute(select(Usuario).where(Usuario.username == usuario.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username já existe")
        
    novo_usuario = Usuario(
        username=usuario.username,
        password_hash=hash_password(usuario.password),
        role="standard"
    )
    db.add(novo_usuario)
    await db.commit()
    await db.refresh(novo_usuario)
    return novo_usuario
