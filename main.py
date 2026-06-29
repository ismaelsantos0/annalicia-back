"""
backend/app/database.py
────────────────────────
Configuração assíncrona do SQLAlchemy com AsyncSession e engine asyncpg.
"""
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


settings = get_settings()

db_url = settings.database_url
if db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

# ── Engine assíncrona ─────────────────────────────────────────────────────────
# pool_pre_ping=True verifica conexões mortas automaticamente
engine = create_async_engine(
    db_url,
    pool_pre_ping=True,
    pool_size=2,
    max_overflow=5,
    pool_recycle=300, # Recycle connections every 5 mins
    echo=False,   # True para debug SQL
)

# ── Session factory ────────────────────────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


# ── Base declarativa ──────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    pass


# ── Dependency para injeção nas rotas FastAPI ─────────────────────────────────
async def get_db() -> AsyncSession:  # type: ignore[return]
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
