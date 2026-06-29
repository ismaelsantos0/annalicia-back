from datetime import datetime, date
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from dateutil.relativedelta import relativedelta
from collections import defaultdict

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, Appointment, Professional

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/metrics")
async def get_dashboard_metrics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    professional_id: UUID = Query(None, description="Filtra por um profissional específico (opcional)")
):
    # Definir o filtro base de acordo com o papel do usuário
    base_filters = []
    
    # Se o usuário for um 'profissional', ele só pode ver os próprios dados
    if current_user.role == "profissional" and current_user.professional_id:
        base_filters.append(Appointment.professional_id == current_user.professional_id)
    elif professional_id:
        base_filters.append(Appointment.professional_id == professional_id)

    # Pegar o mês atual e o mês passado
    today = date.today()
    start_of_current_month = datetime(today.year, today.month, 1)
    # Primeiro dia do mês passado
    start_of_last_month = start_of_current_month - relativedelta(months=1)
    
    # Todos os agendamentos desde o início do mês passado (para evitar trazer a base toda pra memória)
    # Idealmente, poderíamos fazer agregações no banco, mas como a base é pequena/simples, vamos fazer em Python por enquanto
    # ou usar GROUP BY do SQLAlchemy
    
    # 1. Obter total do mês atual vs passado
    query_current_month = select(func.count(Appointment.id)).where(
        and_(
            *base_filters,
            Appointment.start_time >= start_of_current_month
        )
    )
    total_current_month = (await db.execute(query_current_month)).scalar() or 0
    
    query_last_month = select(func.count(Appointment.id)).where(
        and_(
            *base_filters,
            Appointment.start_time >= start_of_last_month,
            Appointment.start_time < start_of_current_month
        )
    )
    total_last_month = (await db.execute(query_last_month)).scalar() or 0

    # 2. Agrupar por status (Somente do mês atual)
    query_status = select(Appointment.status, func.count(Appointment.id)).where(
        and_(
            *base_filters,
            Appointment.start_time >= start_of_current_month
        )
    ).group_by(Appointment.status)
    result_status = await db.execute(query_status)
    by_status = {row[0]: row[1] for row in result_status.all()}
    
    # 3. Agrupar por profissional (Somente do mês atual)
    # Faremos um JOIN com a tabela de profissionais para pegar o nome
    query_professionals = (
        select(Professional.name, func.count(Appointment.id))
        .join(Appointment, Professional.id == Appointment.professional_id)
        .where(
            and_(
                *base_filters,
                Appointment.start_time >= start_of_current_month
            )
        )
        .group_by(Professional.name)
        .order_by(func.count(Appointment.id).desc())
    )
    result_professionals = await db.execute(query_professionals)
    by_professional = [{"name": row[0], "total": row[1]} for row in result_professionals.all()]
    
    # 4. Agrupar por serviço (Somente do mês atual)
    query_services = (
        select(Appointment.service_name, func.count(Appointment.id))
        .where(
            and_(
                *base_filters,
                Appointment.start_time >= start_of_current_month,
                Appointment.service_name != None,
                Appointment.service_name != ""
            )
        )
        .group_by(Appointment.service_name)
        .order_by(func.count(Appointment.id).desc())
    )
    result_services = await db.execute(query_services)
    by_service = [{"name": row[0], "total": row[1]} for row in result_services.all()]
    
    # 5. Agendamentos por dia (para montar o gráfico de linha) - últimos 30 dias
    start_30_days_ago = datetime.combine(today - relativedelta(days=29), datetime.min.time())
    query_daily = (
        select(
            func.date(Appointment.start_time).label('day'),
            func.count(Appointment.id)
        )
        .where(
            and_(
                *base_filters,
                Appointment.start_time >= start_30_days_ago
            )
        )
        .group_by(func.date(Appointment.start_time))
        .order_by(func.date(Appointment.start_time))
    )
    result_daily = await db.execute(query_daily)
    # Criar um dict para facilitar
    daily_counts = {str(row[0]): row[1] for row in result_daily.all()}
    
    # Preencher os buracos (dias sem agendamentos)
    by_day = []
    for i in range(30):
        d = today - relativedelta(days=29 - i)
        d_str = str(d)
        by_day.append({
            "date": d.strftime("%d/%m"),
            "total": daily_counts.get(d_str, 0)
        })

    return {
        "total_current_month": total_current_month,
        "total_last_month": total_last_month,
        "by_status": by_status,
        "by_professional": by_professional,
        "by_service": by_service,
        "by_day": by_day
    }
