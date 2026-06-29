from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import Configuracao, Usuario
from app.schemas import ConfiguracaoResponse, ConfiguracaoUpdate
from app.dependencies import get_current_user

router = APIRouter(prefix="/configuracoes", tags=["Configurações"])

@router.get("", response_model=ConfiguracaoResponse)
async def get_configuracao(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Configuracao).where(Configuracao.id == 1))
    config = result.scalar_one_or_none()
    
    if not config:
        config = Configuracao(id=1, estoque_critico=1, estoque_atencao=3)
        db.add(config)
        await db.commit()
        await db.refresh(config)
        
    return config

@router.patch("", response_model=ConfiguracaoResponse)
async def update_configuracao(
    update_data: ConfiguracaoUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    if current_user.role != "master":
        raise HTTPException(status_code=403, detail="Acesso restrito")
        
    result = await db.execute(select(Configuracao).where(Configuracao.id == 1))
    config = result.scalar_one_or_none()
    
    if not config:
        config = Configuracao(id=1, **update_data.model_dump(exclude_unset=True))
        db.add(config)
    else:
        for key, value in update_data.model_dump(exclude_unset=True).items():
            setattr(config, key, value)
            
    await db.commit()
    await db.refresh(config)
    return config
