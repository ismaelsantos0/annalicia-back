"""
backend/app/tasks/lembretes.py
──────────────────────────────
Robô de Lembretes Automáticos de Consultas
Roda a cada 10 minutos via APScheduler.
Envia WhatsApp para agendamentos que estão a X horas de distância.
"""
import logging
import json
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models import Appointment, ClinicSettings, Professional

log = logging.getLogger(__name__)

DEFAULT_REMINDER_MSG = (
    "Olá {cliente}! 👋\n\n"
    "Este é um lembrete do seu agendamento com *{profissional}* amanhã às *{horario}*.\n\n"
    "Esperamos te ver em breve! 😊"
)

DEFAULT_REMINDER_MSG_2H = (
    "Olá {cliente}! 👋\n\n"
    "Seu agendamento com *{profissional}* é *hoje às {horario}*.\n\n"
    "Até já! 😊{maps_link}"
)


async def disparar_lembretes():
    """
    Verifica agendamentos pendentes/confirmados que estão 
    a (reminder_hours_before) horas de distância e dispara lembretes via WhatsApp.
    """
    log.info("[LEMBRETE] Iniciando verificação de lembretes automáticos...")
    
    try:
        async with AsyncSessionLocal() as db:
            # Buscar configurações globais
            result = await db.execute(
                select(ClinicSettings).where(ClinicSettings.id == "default")
            )
            settings = result.scalar_one_or_none()

            if not settings or settings.reminder_hours_before is None:
                log.info("[LEMBRETE] Lembretes desativados ou sem configuração. Pulando.")
                return

            horas = settings.reminder_hours_before
            agora = datetime.now(timezone.utc)
            
            # Janela: o agendamento deve ser entre (agora + horas - 10min) e (agora + horas + 10min)
            # Isso garante que o cron de 10 min não manda dois lembretes
            inicio_janela = agora + timedelta(hours=horas) - timedelta(minutes=10)
            fim_janela = agora + timedelta(hours=horas) + timedelta(minutes=10)

            log.info(f"[LEMBRETE] Buscando agendamentos entre {inicio_janela.isoformat()} e {fim_janela.isoformat()}")

            appts_result = await db.execute(
                select(Appointment).where(
                    and_(
                        Appointment.start_time >= inicio_janela,
                        Appointment.start_time <= fim_janela,
                        Appointment.status.in_(["pending", "confirmed"]),
                        Appointment.reminder_sent == False,
                    )
                )
            )
            agendamentos = appts_result.scalars().all()

            if not agendamentos:
                log.info("[LEMBRETE] Nenhum agendamento elegível para lembrete. Tudo tranquilo!")
                return

            log.info(f"[LEMBRETE] {len(agendamentos)} agendamento(s) para enviar lembrete.")

            # Montar link do Maps se houver endereço
            maps_link = ""
            if settings.address:
                try:
                    addr_data = json.loads(settings.address)
                    partes = [
                        addr_data.get("street", ""),
                        addr_data.get("number", ""),
                        addr_data.get("neighborhood", ""),
                        addr_data.get("city", ""),
                        addr_data.get("state", ""),
                    ]
                    endereco_texto = ", ".join(p for p in partes if p)
                    if addr_data.get("mapsLink"):
                        maps_link = f"\n\n📍 *Endereço:*\n{addr_data['mapsLink']}"
                    elif endereco_texto:
                        from urllib.parse import quote
                        maps_url = f"https://maps.google.com/?q={quote(endereco_texto)}"
                        maps_link = f"\n\n📍 *Como Chegar:*\n{maps_url}"
                except Exception as e:
                    log.warning(f"[LEMBRETE] Não foi possível parsear endereço para maps_link: {e}")

            from app.services.whatsapp import enviar_mensagem
            import pytz

            tz_brasil = pytz.timezone("America/Sao_Paulo")

            for appt in agendamentos:
                try:
                    # Buscar profissional
                    prof_result = await db.execute(
                        select(Professional).where(Professional.id == appt.professional_id)
                    )
                    profissional = prof_result.scalar_one_or_none()
                    nome_prof = profissional.name if profissional else "o profissional"

                    # Formatar horário no horário de Brasília
                    horario_brasil = appt.start_time.astimezone(tz_brasil)
                    horario_str = horario_brasil.strftime("%H:%M")

                    # Selecionar template de mensagem
                    template = settings.reminder_message

                    # Se for lembrete de 2h ou menos, incluir link Maps automaticamente
                    if not template:
                        if horas <= 2:
                            template = DEFAULT_REMINDER_MSG_2H
                        else:
                            template = DEFAULT_REMINDER_MSG

                    # Substituir variáveis
                    maps_parte = maps_link if horas <= 2 else ""
                    mensagem = (
                        template
                        .replace("{cliente}", appt.customer_name)
                        .replace("{profissional}", nome_prof)
                        .replace("{horario}", horario_str)
                        .replace("{maps_link}", maps_parte)
                    )

                    # Se a tag não foi usada explicitamente na mensagem, mas o aviso é de 2h ou menos, anexa no final automaticamente
                    if "{maps_link}" not in template and maps_link and horas <= 2:
                        mensagem += f"\n\n{maps_link}"

                    sucesso, erro = await enviar_mensagem(appt.customer_phone, mensagem)

                    if sucesso:
                        appt.reminder_sent = True
                        log.info(f"[LEMBRETE ✓] Lembrete enviado para {appt.customer_name} ({appt.customer_phone})")
                    else:
                        log.error(f"[LEMBRETE ✗] Falha ao enviar para {appt.customer_name}: {erro}")

                except Exception as e:
                    log.error(f"[LEMBRETE] Erro ao processar agendamento {appt.id}: {e}")

            await db.commit()
            log.info("[LEMBRETE] Verificação de lembretes concluída.")

    except Exception as exc:
        log.error(f"[LEMBRETE] Erro geral no disparador de lembretes: {exc}")
