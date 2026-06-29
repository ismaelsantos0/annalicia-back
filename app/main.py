import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text
from fastapi.responses import JSONResponse
from fastapi import Request
from fastapi.exceptions import RequestValidationError
import traceback

from app.config import get_settings
from app.database import AsyncSessionLocal, engine, Base
from app.models import Usuario
from app.security import hash_password

from app.routers import auth, usuarios, produtos, pedidos

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
log = logging.getLogger(__name__)
settings = get_settings()

async def seed_master() -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Usuario).where(Usuario.username == settings.admin_username))
        user = result.scalar_one_or_none()
        
        if not user:
            log.info(f"[DB] Criando usuário admin: {settings.admin_username}")
            new_user = Usuario(
                username=settings.admin_username,
                password_hash=hash_password(settings.admin_password),
                role="master"
            )
            db.add(new_user)
            await db.commit()
        else:
            log.info(f"[DB] Atualizando senha do admin: {settings.admin_username}")
            user.password_hash = hash_password(settings.admin_password)
            await db.commit()

@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio
    log.info("=== Iniciando Backend da Loja ===")
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

    log.info("[DB] Sincronizando tabelas no PostgreSQL...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await seed_master()
    yield

app = FastAPI(
    title="Loja API",
    description="Backend para e-commerce",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

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

app.include_router(auth.router)
app.include_router(usuarios.router)
app.include_router(produtos.router)
app.include_router(pedidos.router)

@app.get("/health", tags=["Sistema"])
async def health_check():
    return {"status": "ok", "service": "loja-api"}
