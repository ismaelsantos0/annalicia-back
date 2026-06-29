"""
backend/app/routers/webhooks.py
───────────────────────────────
Escuta eventos da Evolution API.
"""
import logging
from fastapi import APIRouter, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import Appointment, Professional, ClinicSettings
from app.services.whatsapp import enviar_mensagem
from app.config import get_settings
from app.utils.phone import normalize_phone, phones_match

log = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks", tags=["Webhooks"])
settings = get_settings()

@router.post("/whatsapp")
async def receber_resposta_wpp(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Recebe os eventos (messages.upsert) da Evolution API e
    atualiza o status do agendamento se o cliente responder 1 ou 2.
    """
    try:
        payload = await request.json()
    except Exception:
        return {"status": "ok"} # Ignora se não for JSON

    # Verifica se é um evento de mensagem recebida
    if payload.get("event") == "messages.upsert":
        data = payload.get("data", {})
        key_data = data.get("key", {})

        if key_data.get("fromMe"):
            return {"status": "ok"}

        message_data = data.get("message", {})
        
        # Pega o texto da mensagem. Pode vir em text, conversation ou extendedTextMessage
        texto_msg = message_data.get("conversation") or message_data.get("extendedTextMessage", {}).get("text", "")
        texto_msg = texto_msg.strip()
        
        remote_jid = key_data.get("remoteJid", "")
        
        telefone_bruto = None
        if remote_jid and "@s.whatsapp.net" in remote_jid:
            telefone_bruto = remote_jid.split("@")[0]
        elif remote_jid and "@lid" in remote_jid:
            # Se for um LID, tenta resolver o JID real / número via Evolution API
            if settings.evolution_api_url and settings.evolution_api_key:
                try:
                    import httpx
                    url = f"{settings.evolution_api_url.rstrip('/')}/contact/profile/{remote_jid}"
                    headers = {"apikey": settings.evolution_api_key}
                    async with httpx.AsyncClient(timeout=5.0) as client:
                        response = await client.get(url, headers=headers)
                        if response.status_code == 200:
                            data_profile = response.json()
                            real_phone = (
                                data_profile.get("number") or
                                data_profile.get("phoneNumber") or
                                (data_profile.get("id", "").split("@")[0] if "@s.whatsapp.net" in data_profile.get("id", "") else None)
                            )
                            if real_phone:
                                telefone_bruto = real_phone
                                log.info(f"[WPP Webhook] LID {remote_jid} resolvido com sucesso via API para: {telefone_bruto}")
                except Exception as e:
                    log.error(f"[WPP Webhook] Erro resolvendo LID {remote_jid}: {e}")

        if not telefone_bruto and remote_jid:
            telefone_bruto = remote_jid.split("@")[0]

        telefone = normalize_phone(telefone_bruto)
        
        if not telefone or not texto_msg:
            return {"status": "ok"}

        log.info(f"[WPP Webhook] Mensagem de {telefone}: '{texto_msg}'")
            
        # Busca as configurações do banco de dados para usar as mensagens personalizadas
        settings_res = await db.execute(select(ClinicSettings).where(ClinicSettings.id == "default"))
        db_settings = settings_res.scalar_one_or_none()

        # Verifica se respondeu 1 ou 2
        if texto_msg == "1":
            novo_status = "confirmed"
            msg_feedback = (
                db_settings.msg_feedback_confirmed 
                if db_settings and db_settings.msg_feedback_confirmed 
                else "Seu agendamento foi *CONFIRMADO* com sucesso! Aguardamos você."
            )
        elif texto_msg == "2":
            novo_status = "cancelled"
            msg_feedback = (
                db_settings.msg_feedback_cancelled 
                if db_settings and db_settings.msg_feedback_cancelled 
                else "Seu agendamento foi *CANCELADO*."
            )
        else:
            # Resposta não reconhecida, ignora (ou poderia mandar "Opção inválida")
            return {"status": "ok"}
            
        query = select(Appointment, Professional).join(Professional).where(
            Appointment.status == "pending"
        ).order_by(Appointment.start_time.asc())
        
        result = await db.execute(query)
        row = None
        for appt_candidate, prof_candidate in result.all():
            if phones_match(appt_candidate.customer_phone, telefone):
                row = (appt_candidate, prof_candidate)
                break
        
        if row:
            appt, prof = row
            appt.status = novo_status
            
            if novo_status == "cancelled":
                appt.notes = (appt.notes + "\n[WhatsApp]: Cliente cancelou via robô.") if appt.notes else "[WhatsApp]: Cliente cancelou via robô."
                
            await db.commit()
            
            # Formata variáveis dinâmicas
            import pytz
            data_formatada = appt.start_time.astimezone(pytz.timezone('America/Sao_Paulo')).strftime('%d/%m/%Y às %H:%M')
            msg_feedback_final = (
                msg_feedback
                .replace("{cliente}", appt.customer_name)
                .replace("{profissional}", prof.name)
                .replace("{data}", data_formatada)
            )
            
            # Avisa o cliente que deu certo
            await enviar_mensagem(telefone, msg_feedback_final)
            
            # Se for cancelado, avisa o admin
            if novo_status == "cancelled" and settings.admin_phone:
                aviso_admin = f"⚠️ *ATENÇÃO: CANCELAMENTO*\nO cliente {appt.customer_name} cancelou a consulta com {prof.name} do dia {data_formatada}."
                await enviar_mensagem(settings.admin_phone, aviso_admin)
        else:
            log.warning(f"[WPP Webhook] Resposta '{texto_msg}' de {telefone}, mas nenhum agendamento pendente encontrado.")
                
    # Sempre retorne status 200 rápido
    return {"status": "ok"}
