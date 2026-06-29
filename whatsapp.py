"""
backend/app/scheduler.py
────────────────────────
Gerencia o APScheduler para tarefas em background.
"""
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore

log = logging.getLogger(__name__)

jobstores = {
    'default': MemoryJobStore()
}

scheduler = AsyncIOScheduler(jobstores=jobstores, timezone="UTC")

def start_scheduler():
    if not scheduler.running:
        from app.tasks.lembretes import disparar_lembretes
        # Roda a cada 10 minutos para verificar e disparar lembretes automáticos
        scheduler.add_job(
            disparar_lembretes,
            trigger='interval',
            minutes=10,
            id='verificar_lembretes',
            replace_existing=True,
            max_instances=1,
        )
        scheduler.start()
        log.info("APScheduler iniciado. Job 'verificar_lembretes' agendado a cada 10 min.")

def shutdown_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        log.info("APScheduler finalizado.")
