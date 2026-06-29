from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_master
from app.models import User
from app.schemas import UserCreate, UserOut, UserUpdate
from app.security import hash_password

router = APIRouter(prefix="/users", tags=["Usuários"])

@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_master)])
async def create_user(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.username == payload.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Username já existe.")

    if payload.role == "master":
        admin_check = await db.execute(select(User.id).where(User.role == "master").limit(1))
        if admin_check.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Já existe um master.")

    user = User(
        username=payload.username, 
        password_hash=hash_password(payload.password), 
        role=payload.role,
        professional_id=payload.professional_id
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

@router.get("", response_model=list[UserOut], dependencies=[Depends(require_master)])
async def list_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.is_active == True).order_by(User.username))
    return result.scalars().all()

@router.put("/{user_id}", response_model=UserOut, dependencies=[Depends(require_master)])
async def update_user(user_id: UUID, payload: UserUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    if payload.username is not None:
        user.username = payload.username
    if payload.password is not None and payload.password.strip():
        user.password_hash = hash_password(payload.password)
    if payload.role is not None:
        user.role = payload.role
    if "professional_id" in payload.model_dump(exclude_unset=True):
        user.professional_id = payload.professional_id
    if payload.is_active is not None:
        user.is_active = payload.is_active

    await db.commit()
    await db.refresh(user)
    return user

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_master)])
async def delete_user(user_id: UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_master)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Você não pode excluir a si mesmo.")
    
    if user.username == "master":
        raise HTTPException(status_code=400, detail="O usuário master principal não pode ser inativado.")

    user.is_active = False
    await db.commit()
    return None
