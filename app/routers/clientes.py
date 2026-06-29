from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import asyncio

from app.database import get_db
from app.models import Cliente, Usuario
from app.schemas import ClienteResponse, DisparoCreate
from app.dependencies import get_current_user
from app.services.whatsapp import whatsapp_service

router = APIRouter(prefix="/clientes", tags=["Clientes"])

@router.get("", response_model=List[ClienteResponse])
async def list_clientes(db: AsyncSession = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    if current_user.role != "master":
        raise HTTPException(status_code=403, detail="Acesso restrito")
        
    result = await db.execute(select(Cliente))
    return result.scalars().all()

async def disparar_mensagens_bg(numeros: set, mensagem: str):
    """
    Roda em background enviando mensagens com intervalo para evitar bloqueios.
    """
    for numero in numeros:
        await whatsapp_service.send_text_message(numero, mensagem)
        # Intervalo de segurança (15 segundos)
        await asyncio.sleep(15)

@router.post("/disparo")
async def disparar_mensagens(
    disparo: DisparoCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    if current_user.role != "master":
        raise HTTPException(status_code=403, detail="Acesso restrito")
        
    result = await db.execute(select(Cliente.whatsapp))
    telefones = result.scalars().all()
    
    # Remove duplicados e números em branco usando set
    numeros_unicos = {t for t in telefones if t and len(t) >= 10}
    
    if not numeros_unicos:
        raise HTTPException(status_code=400, detail="Nenhum número válido encontrado para disparo.")
        
    # Lança a background task
    background_tasks.add_task(disparar_mensagens_bg, numeros_unicos, disparo.mensagem)
    
    return {"message": f"Disparo iniciado para {len(numeros_unicos)} contatos. Isso ocorrerá em segundo plano."}
