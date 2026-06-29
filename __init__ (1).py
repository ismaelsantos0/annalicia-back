import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text

from app.config import get_settings
from app.database import AsyncSessionLocal, engine, Base
from app.models import User
from app.routers import auth, appointments, users, professionals, availability, settings as settings_router, blockouts, services
from app.security import hash_password

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
log = logging.getLogger(__name__)
settings = get_settings()

async def seed_master() -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.username == settings.admin_username))
        user = result.scalar_one_or_none()
        from app.security import hash_password
        
        if not user:
            log.info(f"[DB] Criando usuário admin: {settings.admin_username}")
            new_user = User(
                username=settings.admin_username,
                password_hash=hash_password(settings.admin_password),
                role="master"
            )
            db.add(new_user)
            await db.commit()
        else:
            # Atualiza a senha caso ela tenha mudado no código
            log.info(f"[DB] Atualizando senha do admin: {settings.admin_username}")
            user.password_hash = hash_password(settings.admin_password)
            await db.commit()

@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio
    log.info("=== Iniciando Sistema de Agendamento ===")
    for attempt in range(10):
        try:
            async with AsyncSessionLocal() as db:
                await db.execute(text("SELECT 1"))
            log.info("[DB] Conexão com PostgreSQL estabelecida.")
            break
        except Exception as exc:
            if "too many clients" in str(exc) and attempt < 9:
                log.warning(f"[DB] Banco de dados lotado, aguardando 10s (Tentativa {attempt+1}/10)...")
                await asyncio.sleep(10)
            else:
                log.error(f"[DB] Falha ao conectar: {exc}")
                raise

    from app.scheduler import start_scheduler, shutdown_scheduler
    
    log.info("[DB] Sincronizando tabelas no PostgreSQL...")
    async with engine.begin() as conn:
        renames = [
            ("users", "usuarios"),
            ("professionals", "profissionais"),
            ("clinic_services", "servicos_clinica"),
            ("professional_clinic_services", "profissionais_servicos_clinica"),
            ("availability_rules", "regras_disponibilidade"),
            ("clinic_settings", "configuracoes_clinica"),
            ("blockouts", "bloqueios"),
            ("appointments", "agendamentos"),
            ("otp_verifications", "verificacoes_otp"),
        ]
        for old_name, new_name in renames:
            try:
                await conn.execute(text(f"ALTER TABLE IF EXISTS {old_name} RENAME TO {new_name}"))
            except Exception as e:
                pass

        await conn.run_sync(Base.metadata.create_all)
        
        # Migração implícita (ALTER TABLE IF NOT EXISTS)
        migrations = [
            "ALTER TABLE configuracoes_clinica ADD COLUMN IF NOT EXISTS msg_created VARCHAR",
            "ALTER TABLE configuracoes_clinica ADD COLUMN IF NOT EXISTS msg_confirmation VARCHAR",
            "ALTER TABLE configuracoes_clinica ADD COLUMN IF NOT EXISTS msg_feedback_confirmed VARCHAR",
            "ALTER TABLE configuracoes_clinica ADD COLUMN IF NOT EXISTS msg_feedback_cancelled VARCHAR",
            "ALTER TABLE configuracoes_clinica ADD COLUMN IF NOT EXISTS clinic_name VARCHAR",
            "ALTER TABLE configuracoes_clinica ADD COLUMN IF NOT EXISTS address VARCHAR",
            "ALTER TABLE configuracoes_clinica ADD COLUMN IF NOT EXISTS opening_hours VARCHAR",
            "ALTER TABLE configuracoes_clinica ADD COLUMN IF NOT EXISTS services VARCHAR",
            "ALTER TABLE configuracoes_clinica ADD COLUMN IF NOT EXISTS allow_custom_links BOOLEAN DEFAULT FALSE",
            "ALTER TABLE configuracoes_clinica ADD COLUMN IF NOT EXISTS reminder_hours_before INTEGER",
            "ALTER TABLE configuracoes_clinica ADD COLUMN IF NOT EXISTS reminder_message VARCHAR",
            "ALTER TABLE configuracoes_clinica ADD COLUMN IF NOT EXISTS primary_color VARCHAR",
            "ALTER TABLE configuracoes_clinica ADD COLUMN IF NOT EXISTS banner_image_url VARCHAR",
            "ALTER TABLE configuracoes_clinica ADD COLUMN IF NOT EXISTS social_instagram VARCHAR",
            "ALTER TABLE configuracoes_clinica ADD COLUMN IF NOT EXISTS social_whatsapp VARCHAR",
            "ALTER TABLE configuracoes_clinica ADD COLUMN IF NOT EXISTS logo_url VARCHAR",
            "ALTER TABLE configuracoes_clinica ADD COLUMN IF NOT EXISTS background_style VARCHAR DEFAULT 'minimalist'",
            "ALTER TABLE agendamentos ADD COLUMN IF NOT EXISTS reminder_sent BOOLEAN DEFAULT FALSE",
            "ALTER TABLE agendamentos ADD COLUMN IF NOT EXISTS clinical_notes VARCHAR",
            "ALTER TABLE profissionais ADD COLUMN IF NOT EXISTS profession VARCHAR",
            "ALTER TABLE profissionais ADD COLUMN IF NOT EXISTS contact_number VARCHAR",
            "ALTER TABLE profissionais ADD COLUMN IF NOT EXISTS notify_new BOOLEAN DEFAULT TRUE",
            "ALTER TABLE profissionais ADD COLUMN IF NOT EXISTS notify_cancelled BOOLEAN DEFAULT TRUE",
            "ALTER TABLE profissionais ADD COLUMN IF NOT EXISTS notify_rescheduled BOOLEAN DEFAULT TRUE",
            "ALTER TABLE profissionais ADD COLUMN IF NOT EXISTS notify_upcoming BOOLEAN DEFAULT TRUE",
            "ALTER TABLE profissionais ADD COLUMN IF NOT EXISTS slug VARCHAR UNIQUE",
            "ALTER TABLE profissionais ADD COLUMN IF NOT EXISTS has_custom_link BOOLEAN DEFAULT FALSE",
            "ALTER TABLE configuracoes_clinica ADD COLUMN IF NOT EXISTS allow_custom_links BOOLEAN DEFAULT FALSE",
            "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS professional_id UUID REFERENCES profissionais(id) ON DELETE SET NULL",
            """CREATE TABLE IF NOT EXISTS servicos_clinica (
                id UUID PRIMARY KEY,
                name VARCHAR NOT NULL,
                duration_minutes INTEGER NOT NULL DEFAULT 60,
                price VARCHAR
            )""",
            """CREATE TABLE IF NOT EXISTS profissionais_servicos_clinica (
                professional_id UUID REFERENCES profissionais(id) ON DELETE CASCADE,
                clinic_service_id UUID REFERENCES servicos_clinica(id) ON DELETE CASCADE,
                PRIMARY KEY (professional_id, clinic_service_id)
            )""",
        ]
        for migration_sql in migrations:
            try:
                await conn.execute(text(migration_sql))
                log.info(f"[DB] Migração OK: {migration_sql}")
            except Exception as exc:
                log.warning(f"[DB] Migração falhou (pode ser normal): {exc}")

    await seed_master()
    
    start_scheduler()
    yield
    shutdown_scheduler()

app = FastAPI(
    title="Agendamentos API",
    description="API do Sistema de Agendamentos",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

from fastapi.responses import JSONResponse
from fastapi import Request
from fastapi.exceptions import RequestValidationError
import traceback

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    log.error(f"Global exception: {exc}")
    log.error(traceback.format_exc())
    return JSONResponse(status_code=500, content={"detail": f"Erro Interno: {str(exc)}"})

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    msg = ", ".join([f"{e['loc'][-1]}: {e['msg']}" for e in errors])
    return JSONResponse(status_code=422, content={"detail": f"Erro de Validação: {msg}"})

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.dependencies import require_master, require_operator_or_admin, get_current_user
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(professionals.router, dependencies=[Depends(get_current_user)])
app.include_router(availability.router, dependencies=[Depends(get_current_user)])
app.include_router(blockouts.router, dependencies=[Depends(get_current_user)])
app.include_router(appointments.router, dependencies=[Depends(get_current_user)])
app.include_router(settings_router.router)
app.include_router(services.router, dependencies=[Depends(get_current_user)])
from app.routers import webhooks, whatsapp_management, dashboard
app.include_router(webhooks.router)
app.include_router(whatsapp_management.router, dependencies=[Depends(require_master)])
app.include_router(dashboard.router, dependencies=[Depends(get_current_user)])

@app.get("/health", tags=["Sistema"])
async def health_check():
    return {"status": "ok", "service": "agendamentos-api"}

@app.get("/reset-db-danger", tags=["Sistema"])
async def reset_db():
    log.warning("ZERANDO O BANCO DE DADOS...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    await seed_master()
    return {"status": "Banco recriado com sucesso! Volte ao painel e crie o profissional novamente."}

@app.get("/fix-db-migrations", tags=["Sistema"])
async def fix_db_migrations():
    """Executa as migrações pendentes sem perder dados."""
    results = []
    migrations = [
        "ALTER TABLE clinic_settings ADD COLUMN IF NOT EXISTS msg_created VARCHAR",
        "ALTER TABLE clinic_settings ADD COLUMN IF NOT EXISTS msg_confirmation VARCHAR",
        "ALTER TABLE clinic_settings ADD COLUMN IF NOT EXISTS msg_feedback_confirmed VARCHAR",
        "ALTER TABLE clinic_settings ADD COLUMN IF NOT EXISTS msg_feedback_cancelled VARCHAR",
    ]
    async with engine.begin() as conn:
        for sql in migrations:
            try:
                await conn.execute(text(sql))
                results.append({"sql": sql, "status": "ok"})
            except Exception as exc:
                results.append({"sql": sql, "status": "erro", "detail": str(exc)})
    return {"migrations": results}

@app.get("/diagnose-db", tags=["Sistema"])
async def diagnose_db():
    """Verifica quais colunas existem na tabela clinic_settings."""
    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(text(
                "SELECT column_name, data_type FROM information_schema.columns "
                "WHERE table_name = 'clinic_settings' ORDER BY ordinal_position"
            ))
            cols = [{"column": row[0], "type": row[1]} for row in result.all()]
            return {"table": "clinic_settings", "columns": cols}
        except Exception as exc:
            return {"error": str(exc)}
