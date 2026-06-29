import httpx
import logging
from app.config import get_settings

log = logging.getLogger(__name__)
settings = get_settings()

class WhatsAppService:
    def __init__(self):
        self.base_url = settings.evolution_api_url.rstrip("/")
        self.api_key = settings.evolution_api_key
        self.instance_name = settings.evolution_instance or "loja"
        
        self.headers = {
            "apikey": self.api_key,
            "Content-Type": "application/json"
        }

    @property
    def is_configured(self):
        return bool(self.base_url and self.api_key)

    async def get_instance_state(self):
        if not self.is_configured:
            return {"status": "not_configured"}
            
        async with httpx.AsyncClient() as client:
            try:
                # Evolution API v2: get connection state
                url = f"{self.base_url}/instance/connectionState/{self.instance_name}"
                res = await client.get(url, headers=self.headers, timeout=5.0)
                if res.status_code == 200:
                    data = res.json()
                    state = data.get("instance", {}).get("state", "unknown")
                    return {"status": state}
                elif res.status_code == 404:
                    return {"status": "not_created"}
                return {"status": "error", "detail": res.text}
            except Exception as e:
                log.error(f"Erro ao checar status do WhatsApp: {e}")
                return {"status": "error", "detail": str(e)}

    async def create_instance(self):
        if not self.is_configured:
            return None
            
        async with httpx.AsyncClient() as client:
            try:
                url = f"{self.base_url}/instance/create"
                payload = {
                    "instanceName": self.instance_name,
                    "qrcode": True,
                    "integration": "WHATSAPP-BAILEYS"
                }
                res = await client.post(url, json=payload, headers=self.headers, timeout=10.0)
                if res.status_code in (200, 201):
                    return res.json()
                log.error(f"Erro ao criar instancia: {res.text}")
                return None
            except Exception as e:
                log.error(f"Erro ao criar instancia do WhatsApp: {e}")
                return None

    async def get_qr_code(self):
        if not self.is_configured:
            return None
            
        # Tenta pegar status primeiro
        state = await self.get_instance_state()
        if state["status"] == "not_created":
            # Cria a instância
            await self.create_instance()
            
        async with httpx.AsyncClient() as client:
            try:
                url = f"{self.base_url}/instance/connect/{self.instance_name}"
                res = await client.get(url, headers=self.headers, timeout=10.0)
                if res.status_code == 200:
                    data = res.json()
                    # Retorna o QR Code base64 se existir
                    return data.get("base64")
                return None
            except Exception as e:
                log.error(f"Erro ao pegar QR Code do WhatsApp: {e}")
                return None
                
    async def logout_instance(self):
        if not self.is_configured:
            return False
            
        async with httpx.AsyncClient() as client:
            try:
                url = f"{self.base_url}/instance/logout/{self.instance_name}"
                res = await client.delete(url, headers=self.headers, timeout=5.0)
                return res.status_code == 200
            except Exception:
                return False

    async def send_text_message(self, phone: str, message: str):
        if not self.is_configured:
            log.warning("WhatsApp API não configurada, mensagem ignorada.")
            return False
            
        async with httpx.AsyncClient() as client:
            try:
                # Format to 55XXYYYYYYYY
                number = "".join(filter(str.isdigit, phone))
                if len(number) == 10 or len(number) == 11:
                    number = f"55{number}"
                    
                url = f"{self.base_url}/message/sendText/{self.instance_name}"
                payload = {
                    "number": number,
                    "textMessage": {"text": message}
                }
                res = await client.post(url, json=payload, headers=self.headers, timeout=10.0)
                if res.status_code in (200, 201):
                    return True
                log.error(f"Falha ao enviar whatsapp: {res.text}")
                return False
            except Exception as e:
                log.error(f"Erro ao enviar mensagem no WhatsApp: {e}")
                return False

whatsapp_service = WhatsAppService()
