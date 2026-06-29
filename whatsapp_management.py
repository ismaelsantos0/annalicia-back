from datetime import datetime, timedelta, timezone
import logging

import pytz
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import AsyncSessionLocal, get_db
from app.models import ClinicSettings, Appointment, Professional
from app.schemas import (
    ClinicSettingsUpdate,
    ClinicSettingsResponse,
    TestConfirmationMessagePayload,
    TestConfirmationMessageResponse,
    ResetSystemPayload,
)
from app.dependencies import get_current_user
from app.utils.phone import normalize_phone

log = logging.getLogger(__name__)

DEFAULT_MSG_CONFIRMATION = (
    "Olá {cliente}! Você tem um agendamento com {profissional} para {data}.\n\n"
    "Responda *1* para CONFIRMAR ou *2* para CANCELAR."
)
TEST_NOTE = "[TESTE WhatsApp] Agendamento criado para teste de resposta 1/2"

router = APIRouter(prefix="/settings", tags=["Configurações"])

@router.get("", response_model=ClinicSettingsResponse)
async def get_settings(db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(ClinicSettings).where(ClinicSettings.id == "default"))
        settings = result.scalar_one_or_none()
        if not settings:
            settings = ClinicSettings(
                id="default",
                clinic_name=None,
                address=None,
                opening_hours=None,
                appointment_duration_minutes=60,
                msg_created=None,
                msg_confirmation=None,
                msg_feedback_confirmed=None,
                msg_feedback_cancelled=None
            )
            db.add(settings)
            await db.commit()
            await db.refresh(settings)
        return settings
    except Exception as exc:
        log.error(f"[Settings] Erro ao buscar settings: {exc}")
        raise HTTPException(status_code=500, detail=f"Erro no banco de dados: {str(exc)}")

@router.put("", response_model=ClinicSettingsResponse)
async def update_settings(
    settings_in: ClinicSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    if current_user.role not in ["master", "clinica"]:
        raise HTTPException(status_code=403, detail="Apenas admin ou clínica podem alterar configurações")
    
    result = await db.execute(select(ClinicSettings).where(ClinicSettings.id == "default"))
    settings = result.scalar_one_or_none()
    if not settings:
        settings = ClinicSettings(
            id="default",
            clinic_name=None,
            address=None,
            opening_hours=None,
            appointment_duration_minutes=60,
            msg_created=None,
            msg_confirmation=None,
            msg_feedback_confirmed=None,
            msg_feedback_cancelled=None
        )
        db.add(settings)
    
    settings.appointment_duration_minutes = settings_in.appointment_duration_minutes
    if settings_in.clinic_name is not None:
        settings.clinic_name = settings_in.clinic_name
    if settings_in.address is not None:
        settings.address = settings_in.address
    if settings_in.opening_hours is not None:
        settings.opening_hours = settings_in.opening_hours
    if settings_in.msg_created is not None:
        settings.msg_created = settings_in.msg_created
    if settings_in.msg_confirmation is not None:
        settings.msg_confirmation = settings_in.msg_confirmation
    if settings_in.msg_feedback_confirmed is not None:
        settings.msg_feedback_confirmed = settings_in.msg_feedback_confirmed
    if settings_in.msg_feedback_cancelled is not None:
        settings.msg_feedback_cancelled = settings_in.msg_feedback_cancelled
    if settings_in.services is not None:
        settings.services = settings_in.services
    if settings_in.allow_custom_links is not None:
        settings.allow_custom_links = settings_in.allow_custom_links
    if settings_in.reminder_hours_before is not None:
        settings.reminder_hours_before = settings_in.reminder_hours_before
    else:
        settings.reminder_hours_before = None
    if settings_in.reminder_message is not None:
        settings.reminder_message = settings_in.reminder_message
    if settings_in.primary_color is not None:
        settings.primary_color = settings_in.primary_color
    if settings_in.banner_image_url is not None:
        settings.banner_image_url = settings_in.banner_image_url
    if settings_in.logo_url is not None:
        settings.logo_url = settings_in.logo_url
    if settings_in.background_style is not None:
        settings.background_style = settings_in.background_style
    if settings_in.social_instagram is not None:
        settings.social_instagram = settings_in.social_instagram
    if settings_in.social_whatsapp is not None:
        settings.social_whatsapp = settings_in.social_whatsapp
        
    await db.commit()
    await db.refresh(settings)
    return settings

@router.post("/test-confirmation", response_model=TestConfirmationMessageResponse)
async def test_confirmation_message(
    payload: TestConfirmationMessagePayload,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    if current_user.role != "master":
        raise HTTPException(status_code=403, detail="Apenas admin pode testar mensagens")

    telefone = normalize_phone(payload.telefone)
    if len(telefone) < 12:
        raise HTTPException(status_code=400, detail="Informe o número com DDI e DDD (ex: 5511999999999)")

    result = await db.execute(select(ClinicSettings).where(ClinicSettings.id == "default"))
    settings = result.scalar_one_or_none()

    prof_result = await db.execute(
        select(Professional).where(Professional.is_active == True).limit(1)
    )
    prof = prof_result.scalar_one_or_none()
    if not prof:
        raise HTTPException(status_code=400, detail="Cadastre um profissional ativo antes de testar")

    duration_minutes = settings.appointment_duration_minutes if settings else 60

    old_tests = await db.execute(
        select(Appointment).where(
            Appointment.customer_phone == telefone,
            Appointment.status == "pending",
            Appointment.notes.contains("[TESTE WhatsApp]"),
        )
    )
    for old in old_tests.scalars():
        old.status = "cancelled"
        old.notes = f"{old.notes or ''}\n[Cancelado]: substituído por novo teste"

    tz = pytz.timezone("America/Sao_Paulo")
    sample_date = (datetime.now(tz) + timedelta(days=1)).replace(hour=14, minute=30, second=0, microsecond=0)
    start_time = sample_date.astimezone(timezone.utc)
    data_formatada = sample_date.strftime("%d/%m/%Y às %H:%M")
    customer_name = "João Silva (TESTE)"

    template = payload.msg_confirmation
    if template is None and settings:
        template = settings.msg_confirmation
    if not template:
        template = DEFAULT_MSG_CONFIRMATION

    texto = (
        template
        .replace("{cliente}", customer_name)
        .replace("{profissional}", prof.name)
        .replace("{data}", data_formatada)
    )

    new_appt = Appointment(
        professional_id=prof.id,
        customer_name=customer_name,
        customer_phone=telefone,
        start_time=start_time,
        end_time=start_time + timedelta(minutes=duration_minutes),
        status="pending",
        notes=TEST_NOTE,
    )
    db.add(new_appt)
    await db.commit()
    await db.refresh(new_appt)

    from app.services.whatsapp import enviar_mensagem

    sucesso, err_msg = await enviar_mensagem(telefone, texto)
    if not sucesso:
        raise HTTPException(status_code=500, detail=f"Falha ao enviar: {err_msg}")

    return TestConfirmationMessageResponse(
        status="success",
        preview=texto,
        appointment_id=str(new_appt.id),
        professional_name=prof.name,
        customer_name=customer_name,
    )

@router.get("/upgrade-db", status_code=status.HTTP_200_OK)
async def upgrade_db(db: AsyncSession = Depends(get_db)):
    from sqlalchemy import text
    errors = []
    try:
        await db.execute(text("""
        CREATE TABLE IF NOT EXISTS clinic_services (
            id UUID PRIMARY KEY,
            name VARCHAR NOT NULL,
            duration_minutes INTEGER NOT NULL DEFAULT 60,
            price VARCHAR
        )
        """))
    except Exception as e:
        errors.append(str(e))
    
    try:
        await db.execute(text("""
        CREATE TABLE IF NOT EXISTS profissionais_servicos_clinica (
            professional_id UUID REFERENCES profissionais(id),
            clinic_service_id UUID REFERENCES servicos_clinica(id),
            PRIMARY KEY (professional_id, clinic_service_id)
        )
        """))
    except Exception as e:
        errors.append(str(e))
        
    try:
        await db.execute(text("ALTER TABLE configuracoes_clinica ADD COLUMN clinic_name VARCHAR"))
    except Exception: pass
    try:
        await db.execute(text("ALTER TABLE configuracoes_clinica ADD COLUMN address VARCHAR"))
    except Exception: pass
    try:
        await db.execute(text("ALTER TABLE configuracoes_clinica ADD COLUMN opening_hours VARCHAR"))
    except Exception: pass
    try:
        await db.execute(text("ALTER TABLE configuracoes_clinica ADD COLUMN services VARCHAR"))
    except Exception: pass
    try:
        await db.execute(text("ALTER TABLE agendamentos ADD COLUMN service_name VARCHAR"))
    except Exception: pass
    await db.commit()
    
    if errors:
        return {"status": "error", "errors": errors, "version": "new_raw_sql"}
    return {"status": "ok", "version": "new_raw_sql"}

@router.post("/reset", status_code=status.HTTP_200_OK)
async def reset_system(
    payload: ResetSystemPayload,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    if current_user.role != "master":
        raise HTTPException(status_code=403, detail="Apenas admin master pode resetar o sistema.")
    
    from sqlalchemy import delete
    from app.models import Appointment, Blockout, AvailabilityRule, Professional, ClinicService, User, ClinicSettings
    from app.schemas import ResetSystemPayload

    try:
        if payload.reset_appointments:
            await db.execute(delete(Appointment))
            
        if payload.reset_services:
            from app.models import professional_clinic_services
            await db.execute(delete(professional_clinic_services))
            await db.execute(delete(ClinicService))
            
        if payload.reset_professionals:
            # We must delete blockouts and availability rules first if we don't have cascade
            await db.execute(delete(Blockout))
            await db.execute(delete(AvailabilityRule))
            # Delete appointments before deleting professionals just in case reset_appointments wasn't true
            # but if they want to reset professionals, their appointments must go too to avoid FK constraints
            await db.execute(delete(Appointment)) 
            # Nullify professional_id in users
            from sqlalchemy import update
            await db.execute(update(User).values(professional_id=None))
            # Finally delete professionals
            await db.execute(delete(Professional))
            
        if payload.reset_users:
            await db.execute(delete(User).where(User.role != 'master'))
            
        if payload.reset_settings:
            await db.execute(delete(ClinicSettings))
            # Will be recreated on next get
            
        await db.commit()
        return {"status": "success", "message": "Dados deletados com sucesso."}
    except Exception as exc:
        await db.rollback()
        log.error(f"[Reset] Erro ao limpar sistema: {exc}")
        raise HTTPException(status_code=500, detail=f"Erro ao limpar banco de dados: {str(exc)}")
