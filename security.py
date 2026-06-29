from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
import httpx
import logging

from app.config import get_settings
from app.dependencies import get_current_user

router = APIRouter(prefix="/whatsapp", tags=["WhatsApp Management"])
log = logging.getLogger(__name__)

class TestMessagePayload(BaseModel):
    telefone: str
    texto: str

@router.get("/status")
async def get_whatsapp_status(current_user = Depends(get_current_user)):
    if current_user.role != "master":
        raise HTTPException(status_code=403, detail="Acesso negado")
    
    settings = get_settings()
    if not settings.evolution_api_url or not settings.evolution_api_key or not settings.evolution_instance:
        return {"status": "unconfigured"}

    url = f"{settings.evolution_api_url.rstrip('/')}/instance/connectionState/{settings.evolution_instance}"
    headers = {"apikey": settings.evolution_api_key}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                state = data.get("instance", {}).get("state", "disconnected")
                return {"status": state}
            return {"status": "error", "detail": response.text}
    except Exception as e:
        log.error(f"Erro ao checar status do WhatsApp: {e}")
        return {"status": "offline"}

@router.get("/qr")
async def get_whatsapp_qr(current_user = Depends(get_current_user)):
    if current_user.role != "master":
        raise HTTPException(status_code=403, detail="Acesso negado")
    
    settings = get_settings()
    if not settings.evolution_api_url or not settings.evolution_api_key or not settings.evolution_instance:
        raise HTTPException(status_code=400, detail="Credenciais não configuradas")

    base_url = settings.evolution_api_url.rstrip('/')
    headers = {"apikey": settings.evolution_api_key}
    
    # 1. Deslogar primeiro para forçar geração de novo QR Code
    logout_url = f"{base_url}/instance/logout/{settings.evolution_instance}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.delete(logout_url, headers=headers)
    except Exception:
        pass # Ignora erro no logout, pois pode já estar deslogado

    # 2. Requisitar novo QR
    connect_url = f"{base_url}/instance/connect/{settings.evolution_instance}"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(connect_url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                if "base64" in data:
                    return {"base64": data["base64"]}
                return {"error": "QR Code não retornado", "data": data}
            return {"error": "Erro ao gerar QR Code", "detail": response.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/test")
async def send_test_message(payload: TestMessagePayload, current_user = Depends(get_current_user)):
    if current_user.role != "master":
        raise HTTPException(status_code=403, detail="Acesso negado")
        
    from app.services.whatsapp import enviar_mensagem
    sucesso, err_msg = await enviar_mensagem(payload.telefone, payload.texto)
    if not sucesso:
        raise HTTPException(status_code=500, detail=f"Falha ao enviar: {err_msg}")
    return {"status": "success"}

@router.post("/logout")
async def logout_whatsapp_instance(current_user = Depends(get_current_user)):
    if current_user.role != "master":
        raise HTTPException(status_code=403, detail="Acesso negado")
        
    settings = get_settings()
    if not settings.evolution_api_url or not settings.evolution_api_key or not settings.evolution_instance:
        raise HTTPException(status_code=400, detail="Credenciais não configuradas")

    base_url = settings.evolution_api_url.rstrip('/')
    logout_url = f"{base_url}/instance/logout/{settings.evolution_instance}"
    headers = {"apikey": settings.evolution_api_key}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.delete(logout_url, headers=headers)
            if resp.status_code in [200, 201]:
                return {"success": True}
            # Se deu 404, significa que já está deslogado ou não existe conexão, o que é sucesso para nós
            if resp.status_code == 404:
                return {"success": True}
            raise HTTPException(status_code=resp.status_code, detail="Erro ao deslogar aparelho")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset")
async def reset_whatsapp_instance(current_user = Depends(get_current_user)):
    if current_user.role != "master":
        raise HTTPException(status_code=403, detail="Acesso negado")
        
    settings = get_settings()
    if not settings.evolution_api_url or not settings.evolution_api_key or not settings.evolution_instance:
        raise HTTPException(status_code=400, detail="Credenciais não configuradas")

    base_url = settings.evolution_api_url.rstrip('/')
    instance = settings.evolution_instance
    headers = {"apikey": settings.evolution_api_key, "Content-Type": "application/json"}
    
    # 1. Tentar ler o webhook atual para não perder a configuração (suporta v1 e v2)
    webhook_url = None
    webhook_events = []
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{base_url}/webhook/find/{instance}", headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, dict):
                    if "webhook" in data and isinstance(data["webhook"], dict):
                        webhook_url = data["webhook"].get("url")
                        webhook_events = data["webhook"].get("events", [])
                    elif "url" in data:
                        webhook_url = data.get("url")
                        webhook_events = data.get("events", [])
    except Exception as e:
        log.warning(f"Erro ao buscar webhook atual: {e}")

    # 2. Deletar a instância para limpar o cache corrompido
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            await client.delete(f"{base_url}/instance/delete/{instance}", headers=headers)
    except Exception as e:
        log.warning(f"Erro ao deletar (pode não existir): {e}")

    # 3. Recriar a instância do zero
    create_payload = {
        "instanceName": instance,
        "qrcode": True,
        "integration": "WHATSAPP-BAILEYS"
    }
    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
            resp = await client.post(f"{base_url}/instance/create", json=create_payload, headers=headers)
            if resp.status_code not in [200, 201]:
                raise HTTPException(status_code=500, detail=f"Erro ao recriar instância: {resp.text}")
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=500, detail=f"Erro HTTP ao recriar: {exc.response.text}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro de rede ao recriar: {str(e)}")

    # 4. Restaurar o webhook se ele existia
    if webhook_url:
        webhook_payload = {
            "webhook": {
                "enabled": True,
                "url": webhook_url,
                "events": webhook_events or ["MESSAGES_UPSERT", "MESSAGES_UPDATE", "CONNECTION_UPDATE"]
            }
        }
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                await client.post(f"{base_url}/webhook/set/{instance}", json=webhook_payload, headers=headers)
        except Exception as e:
            log.warning(f"Erro ao restaurar webhook: {e}")

    return {"success": True, "message": "Instância resetada com sucesso."}
