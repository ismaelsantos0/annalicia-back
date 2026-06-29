from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from app.dependencies import get_current_user
from app.models import Usuario
from app.services.whatsapp import whatsapp_service

router = APIRouter(prefix="/whatsapp", tags=["WhatsApp"])

class StatusResponse(BaseModel):
    status: str

class QRCodeResponse(BaseModel):
    base64: str | None = None

@router.get("/status", response_model=StatusResponse)
async def get_whatsapp_status(current_user: Usuario = Depends(get_current_user)):
    if current_user.role != "master":
        raise HTTPException(status_code=403, detail="Sem permissão")
    state = await whatsapp_service.get_instance_state()
    return StatusResponse(status=state.get("status", "unknown"))

@router.get("/qrcode", response_model=QRCodeResponse)
async def get_whatsapp_qrcode(current_user: Usuario = Depends(get_current_user)):
    if current_user.role != "master":
        raise HTTPException(status_code=403, detail="Sem permissão")
    qr = await whatsapp_service.get_qr_code()
    if qr:
        return QRCodeResponse(base64=qr)
    raise HTTPException(status_code=400, detail="Não foi possível gerar o QR Code. O WhatsApp já pode estar conectado ou a API não respondeu.")

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout_whatsapp(current_user: Usuario = Depends(get_current_user)):
    if current_user.role != "master":
        raise HTTPException(status_code=403, detail="Sem permissão")
    success = await whatsapp_service.logout_instance()
    if not success:
        raise HTTPException(status_code=400, detail="Falha ao desconectar do WhatsApp")
