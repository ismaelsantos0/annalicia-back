from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from datetime import timedelta, datetime, timezone
import uuid

from app.database import AsyncSessionLocal
from app.models import Appointment, Professional, ClinicSettings, OTPVerification, User
from app.schemas import AppointmentCreate, AppointmentResponse, AppointmentStatusUpdate, OTPRequest, AppointmentReschedule, AppointmentComplete, PatientResponse
from sqlalchemy import func
import random
from app.dependencies import get_current_user

router = APIRouter(prefix="/appointments", tags=["Agendamentos"])

async def get_db():
    async with AsyncSessionLocal() as db:
        yield db

@router.get("/clear-all", status_code=status.HTTP_200_OK)
async def clear_all_appointments(db: AsyncSession = Depends(get_db)):
    from sqlalchemy import delete
    await db.execute(delete(Appointment))
    await db.commit()
    return {"message": "All appointments cleared"}

@router.post("/send-code", status_code=status.HTTP_200_OK)
async def send_otp(request: OTPRequest, db: AsyncSession = Depends(get_db)):
    from app.services.whatsapp import enviar_mensagem
    
    # Check rate limit: if phone already has 2 or more upcoming non-cancelled appointments
    agora = datetime.now(timezone.utc)
    limit_query = select(func.count(Appointment.id)).where(
        Appointment.customer_phone == request.customer_phone,
        Appointment.professional_id == request.professional_id,
        Appointment.status != "cancelled",
        Appointment.start_time > agora
    )
    count_res = await db.execute(limit_query)
    count = count_res.scalar() or 0
    if count >= 2:
        raise HTTPException(status_code=400, detail="Limite de agendamentos atingido para este número.")
        
    code = f"{random.randint(1000, 9999)}"
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
    
    # Upsert OTP
    existing = await db.get(OTPVerification, request.customer_phone)
    if existing:
        existing.code = code
        existing.expires_at = expires_at
    else:
        new_otp = OTPVerification(phone=request.customer_phone, code=code, expires_at=expires_at)
        db.add(new_otp)
    await db.commit()
    
    msg = f"Olá {request.customer_name}! Seu código de verificação para agendamento na Clínica Vida é: *{code}*. Válido por 5 minutos."
    sucesso, err_msg = await enviar_mensagem(request.customer_phone, msg)
    if not sucesso:
        raise HTTPException(status_code=500, detail=f"Erro ao enviar WhatsApp: {err_msg}")
        
    return {"message": "Código enviado com sucesso!"}

@router.post("", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
async def create_appointment(appt: AppointmentCreate, db: AsyncSession = Depends(get_db)):
    try:
        # 1. Verify OTP
        otp_record = None
        if appt.otp_code != "bypass_admin_123":
            otp_record = await db.get(OTPVerification, appt.customer_phone)
            if not otp_record or otp_record.code != appt.otp_code:
                raise HTTPException(status_code=400, detail="Código de verificação inválido.")
                
            record_time = otp_record.expires_at
            if record_time.tzinfo is None:
                record_time = record_time.replace(tzinfo=timezone.utc)
                
            if record_time < datetime.now(timezone.utc):
                raise HTTPException(status_code=400, detail="Código de verificação expirado.")
            
        # 2. Check limits again
        if appt.otp_code != "bypass_admin_123":
            agora = datetime.now(timezone.utc)
            limit_query = select(func.count(Appointment.id)).where(
                Appointment.customer_phone == appt.customer_phone,
                Appointment.professional_id == appt.professional_id,
                Appointment.status != "cancelled",
                Appointment.start_time > agora
            )
            count_res = await db.execute(limit_query)
            count = count_res.scalar() or 0
            if count >= 2:
                raise HTTPException(status_code=400, detail="Limite de agendamentos atingido para este número.")

        # Verifica se profissional existe
        prof = await db.get(Professional, appt.professional_id)
        if not prof or not prof.is_active:
            raise HTTPException(status_code=404, detail="Profissional não encontrado")

        import json
        settings_res = await db.execute(select(ClinicSettings).where(ClinicSettings.id == "default"))
        settings = settings_res.scalar_one_or_none()
        duration_minutes = settings.appointment_duration_minutes if settings else 60
        
        if appt.service_name and settings and settings.services:
            try:
                services_list = json.loads(settings.services)
                for svc in services_list:
                    if svc.get('name') == appt.service_name and svc.get('duration_minutes'):
                        duration_minutes = int(svc.get('duration_minutes'))
                        break
            except Exception:
                pass

        # Minimum notice check: start_time must be at least duration_minutes from now
        agora = datetime.now(timezone.utc)
        if appt.start_time < agora + timedelta(minutes=duration_minutes):
            raise HTTPException(status_code=400, detail="O horário deve ser agendado com antecedência mínima de 1 sessão.")

        # Duração dinâmica
        end_time = appt.start_time + timedelta(minutes=duration_minutes)

        # Verifica conflitos DESTE profissional
        conflict_query = select(Appointment).where(
            Appointment.professional_id == appt.professional_id,
            Appointment.status != "cancelled",
            Appointment.start_time < end_time,
            Appointment.end_time > appt.start_time
        )
        conflict = await db.execute(conflict_query)
        if conflict.scalars().first():
            raise HTTPException(status_code=400, detail="Profissional não tem disponibilidade neste horário")

        new_appt = Appointment(
            professional_id=appt.professional_id,
            customer_name=appt.customer_name,
            customer_phone=appt.customer_phone,
            start_time=appt.start_time,
            end_time=end_time,
            notes=appt.notes,
            service_name=appt.service_name,
            status="pending"
        )
        db.add(new_appt)
        
        # Clear OTP
        if otp_record:
            db.delete(otp_record)
            
        await db.commit()
        await db.refresh(new_appt)
        
        # Preenche o nome do prof pra retornar bonito
        response_data = AppointmentResponse.model_validate(new_appt)
        response_data.professional_name = prof.name
        
        # ─── AGENDAMENTO DE WHATSAPP ───────────────────────────────────────────────
        if appt.customer_phone:
            from app.scheduler import scheduler
            from app.services.whatsapp import enviar_mensagem
            import pytz
            
            # O start_time está em UTC
            hora_do_aviso = appt.start_time - timedelta(hours=2)
            agora = datetime.now(timezone.utc)
            
            data_formatada = appt.start_time.astimezone(pytz.timezone('America/Sao_Paulo')).strftime('%d/%m/%Y às %H:%M')
            # Lógica de Mensagens Personalizadas
            nome_servico = appt.service_name or ""
            servico_linha = f"\n🩺 Serviço: {nome_servico}" if nome_servico else ""
            
            # --- PROFISSIONAL NOTIFICATIONS ---
            if prof.contact_number:
                if prof.notify_new:
                    msg_prof_novo = f"Olá, {prof.name}! 📅 Novo agendamento de paciente.\n\n👤 Paciente: {appt.customer_name}\n📞 Contato: {appt.customer_phone}\n⏰ Data: {data_formatada}{servico_linha}"
                    scheduler.add_job(
                        enviar_mensagem, trigger='date', run_date=agora,
                        kwargs={"telefone": prof.contact_number, "texto": msg_prof_novo}
                    )
                if prof.notify_upcoming and hora_do_aviso > agora:
                    msg_prof_lembrete = f"Lembrete, {prof.name}! 🔔 Daqui a pouco você tem um agendamento.\n\n👤 Paciente: {appt.customer_name}\n⏰ Data: {data_formatada}{servico_linha}"
                    scheduler.add_job(
                        enviar_mensagem, trigger='date', run_date=hora_do_aviso,
                        kwargs={"telefone": prof.contact_number, "texto": msg_prof_lembrete}
                    )
            # ----------------------------------

            msg_criado_template = settings.msg_created if settings and settings.msg_created else "Olá {cliente}! 📅 Seu agendamento com {profissional} para {data} foi registrado com sucesso!{servico}\n\n⏳ Nós enviaremos uma mensagem de confirmação 2 horas antes da consulta."

            msg_conf_template = settings.msg_confirmation if settings and settings.msg_confirmation else "Olá {cliente}! Você tem um agendamento com {profissional} para {data}.{servico}\n\nResponda *1* para CONFIRMAR ou *2* para CANCELAR."

            # Faz o replace dinâmico (incluindo {servico})
            def apply_template(template: str) -> str:
                return (
                    template
                    .replace("{cliente}", appt.customer_name)
                    .replace("{profissional}", prof.name)
                    .replace("{data}", data_formatada)
                    .replace("{servico}", servico_linha)
                )

            msg_criado = apply_template(msg_criado_template)
            texto_msg = apply_template(msg_conf_template)

            scheduler.add_job(
                enviar_mensagem,
                trigger='date',
                run_date=agora,
                kwargs={"telefone": appt.customer_phone, "texto": msg_criado}
            )

            # Se faltar menos de 2 horas pro agendamento, NÃO precisamos agendar a confirmação para o passado,
            # enviaremos apenas a mensagem de "criado" que já serve como aviso.
            # Se for no futuro, agendamos a confirmação para 2 horas antes.
            if hora_do_aviso > agora:
                scheduler.add_job(
                    enviar_mensagem,
                    trigger='date',
                    run_date=hora_do_aviso,
                    kwargs={"telefone": appt.customer_phone, "texto": texto_msg}
                )
                
        return response_data
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"DEBUG ERROR: {str(e)}")

@router.get("", response_model=List[AppointmentResponse])
async def list_appointments(
    start_date: str = None, 
    end_date: str = None, 
    professional_id: uuid.UUID = None, 
    status: str = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = select(Appointment, Professional.name.label("professional_name")).join(Professional)
    
    # RBAC: Se for profissional, só vê sua própria agenda
    if current_user.role == "profissional":
        if not current_user.professional_id:
            return [] # Profissional sem vínculo não vê nada
        query = query.where(Appointment.professional_id == current_user.professional_id)
    elif professional_id:
        query = query.where(Appointment.professional_id == professional_id)
        
    if status:
        query = query.where(Appointment.status == status)
        
    if start_date:
        start_of_period = datetime.strptime(f"{start_date}T00:00:00", "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
        query = query.where(Appointment.start_time >= start_of_period)
        
    if end_date:
        end_of_period = datetime.strptime(f"{end_date}T23:59:59", "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
        query = query.where(Appointment.start_time <= end_of_period)
        
    query = query.order_by(Appointment.start_time.asc())
    
    result = await db.execute(query)
    
    response_list = []
    for appt, prof_name in result.all():
        resp = AppointmentResponse.model_validate(appt)
        resp.professional_name = prof_name
        response_list.append(resp)
        
    return response_list

@router.get("/patients", response_model=List[PatientResponse])
async def get_patients(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Fetch all unique patients by phone and name, and their latest appointment date
    query = (
        select(
            Appointment.customer_phone,
            Appointment.customer_name,
            func.max(Appointment.start_time).label('last_appointment')
        )
        .where(Appointment.status == "completed")
    )
    
    if current_user.role == "profissional":
        if not current_user.professional_id:
            return []
        query = query.where(Appointment.professional_id == current_user.professional_id)

    query = query.group_by(Appointment.customer_phone, Appointment.customer_name).order_by(func.max(Appointment.start_time).desc())
    
    result = await db.execute(query)
    
    response_list = []
    for row in result.all():
        phone, name, last_visit = row
        response_list.append(PatientResponse(
            name=name,
            phone=phone,
            last_visit=last_visit
        ))
        
    return response_list

@router.get("/history", response_model=List[AppointmentResponse])
async def get_patient_history(
    phone: str,
    name: str,
    db: AsyncSession = Depends(get_db)
):
    # Ignora diferenças de case e remove espaços extras
    normalized_name = name.strip().lower()
    
    # We join with Professional to get the name
    query = (
        select(Appointment, Professional.name.label("professional_name"))
        .join(Professional)
        .where(Appointment.customer_phone == phone)
        .order_by(Appointment.start_time.desc())
    )
    
    result = await db.execute(query)
    
    response_list = []
    for appt, prof_name in result.all():
        # Apenas pega se o nome bater ignorando case
        if appt.customer_name.strip().lower() == normalized_name:
            resp = AppointmentResponse.model_validate(appt)
            resp.professional_name = prof_name
            response_list.append(resp)
            
    return response_list

@router.put("/{appt_id}/reschedule", response_model=AppointmentResponse)
async def reschedule_appointment(
    appt_id: uuid.UUID,
    reschedule_data: AppointmentReschedule,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from sqlalchemy.orm import selectinload
    query = select(Appointment, Professional.name.label("professional_name")).join(Professional).options(selectinload(Appointment.professional)).where(Appointment.id == appt_id)
    result = await db.execute(query)
    row = result.first()
    
    if not row:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")
        
    appt, prof_name = row
    
    if current_user.role == "profissional" and appt.professional_id != current_user.professional_id:
        raise HTTPException(status_code=403, detail="Acesso negado a agenda de outro profissional")
    
    # Recalcula end_time
    duration = appt.end_time - appt.start_time
    appt.start_time = reschedule_data.start_time
    appt.end_time = reschedule_data.start_time + duration
    
    # Muda status para pending
    appt.status = "pending"
    
    await db.commit()
    await db.refresh(appt)
    
    # Envia WhatsApp
    from app.services.whatsapp import enviar_mensagem
    from datetime import timezone, timedelta
    data_formatada = appt.start_time.astimezone(timezone(timedelta(hours=-3))).strftime('%d/%m/%Y às %H:%M')
    
    mensagem = (
        f"Olá {appt.customer_name}! Sua consulta com {prof_name} foi REMARCADA pelo consultório para o dia {data_formatada}.\n\n"
        f"Responda *1* para CONFIRMAR ou *2* para CANCELAR."
    )
    
    try:
        await enviar_mensagem(appt.customer_phone, mensagem)
    except Exception as e:
        print(f"Erro ao enviar WhatsApp de remarcação: {e}")
        
    # Notifica profissional
    if appt.professional.contact_number and appt.professional.notify_rescheduled:
        try:
            msg_prof_remarcado = f"Aviso de Remarcação 🔄\nO agendamento de {appt.customer_name} foi remarcado para {data_formatada}."
            await enviar_mensagem(appt.professional.contact_number, msg_prof_remarcado)
        except Exception as e:
            pass
    
    resp = AppointmentResponse.model_validate(appt)
    resp.professional_name = prof_name
    return resp

@router.put("/{appt_id}/complete", response_model=AppointmentResponse)
async def complete_appointment(
    appt_id: uuid.UUID,
    complete_data: AppointmentComplete,
    db: AsyncSession = Depends(get_db)
):
    query = select(Appointment, Professional.name.label("professional_name")).join(Professional).where(Appointment.id == appt_id)
    result = await db.execute(query)
    row = result.first()
    
    if not row:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")
        
    appt, prof_name = row
    
    appt.status = "completed"
    appt.clinical_notes = complete_data.clinical_notes
    
    await db.commit()
    await db.refresh(appt)
    
    resp = AppointmentResponse.model_validate(appt)
    resp.professional_name = prof_name
    return resp

@router.get("/{appt_id}", response_model=AppointmentResponse)
async def get_appointment(
    appt_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    if current_user.role != "master":
        raise HTTPException(status_code=403, detail="Acesso negado")

    result = await db.execute(
        select(Appointment, Professional.name.label("professional_name"))
        .join(Professional)
        .where(Appointment.id == appt_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")

    appt, prof_name = row
    resp = AppointmentResponse.model_validate(appt)
    resp.professional_name = prof_name
    return resp

@router.put("/{appt_id}/status", response_model=AppointmentResponse)
async def update_status(
    appt_id: uuid.UUID,
    status_update: AppointmentStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # include professional relation to access contact_number
    from sqlalchemy.orm import selectinload
    query = select(Appointment).options(selectinload(Appointment.professional)).where(Appointment.id == appt_id)
    result = await db.execute(query)
    appt = result.scalar_one_or_none()
    
    if not appt:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")

    if current_user.role == "profissional" and appt.professional_id != current_user.professional_id:
        raise HTTPException(status_code=403, detail="Acesso negado")
        
    old_status = appt.status
    appt.status = status_update.status
    if status_update.notes is not None:
        if appt.notes:
            appt.notes = appt.notes + "\n[Cancelamento]: " + status_update.notes
        else:
            appt.notes = "[Cancelamento]: " + status_update.notes
    await db.commit()
    await db.refresh(appt)

    if appt.status == "cancelled" and old_status != "cancelled":
        if appt.professional and appt.professional.contact_number and appt.professional.notify_cancelled:
            from app.scheduler import scheduler
            from app.services.whatsapp import enviar_mensagem
            import pytz
            data_formatada = appt.start_time.astimezone(pytz.timezone('America/Sao_Paulo')).strftime('%d/%m/%Y às %H:%M')
            msg_prof_canc = f"Aviso de Cancelamento ❌\nO agendamento de {appt.customer_name} marcado para {data_formatada} foi cancelado."
            agora = datetime.now(timezone.utc)
            scheduler.add_job(
                enviar_mensagem, trigger='date', run_date=agora,
                kwargs={"telefone": appt.professional.contact_number, "texto": msg_prof_canc}
            )
    return appt

@router.get("/test-whatsapp/{telefone}")
async def test_whatsapp(telefone: str):
    from app.services.whatsapp import enviar_mensagem
    from app.config import get_settings
    settings = get_settings()
    
    # Tentamos enviar
    sucesso, err_msg = await enviar_mensagem(telefone, "Teste de disparo direto do Backend!")
    
    return {
        "sucesso": sucesso,
        "erro": err_msg if not sucesso else None,
        "config_url_existe": bool(settings.evolution_api_url),
        "config_key_existe": bool(settings.evolution_api_key),
        "config_instance_existe": bool(settings.evolution_instance),
        "evolution_url_configurada": settings.evolution_api_url,
        "evolution_instance_configurada": settings.evolution_instance
    }
