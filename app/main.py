import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
import sqlalchemy
from sqlalchemy import select, text
from fastapi.responses import JSONResponse
from fastapi import Request
from fastapi.exceptions import RequestValidationError
import traceback

from app.config import get_settings
from app.database import AsyncSessionLocal, engine, Base
from app.models import Usuario, Produto, Banner
from app.security import hash_password

from app.routers import auth, usuarios, produtos, pedidos, clientes, categorias, configuracoes, whatsapp, zonas, banners

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

        # Seed de produtos
        count_prod = await db.scalar(select(sqlalchemy.func.count()).select_from(Produto))
        if count_prod == 0:
            log.info("[DB] Cadastrando produtos iniciais de teste...")
            produtos_iniciais = [
                {"nome": "Cropped Borboleta", "preco": 89.9, "estoque": 24, "imagem_url": "https://images.unsplash.com/photo-1564859228273-274232fdb516?auto=format&fit=crop&w=800&q=80"},
                {"nome": "Saia Plissada Rosa", "preco": 129.9, "estoque": 18, "imagem_url": "https://images.unsplash.com/photo-1577900232427-18219b9166a0?auto=format&fit=crop&w=800&q=80"},
                {"nome": "Vestido Floral Aesthetic", "preco": 189.9, "estoque": 9, "imagem_url": "https://images.unsplash.com/photo-1572804013427-4d7ca7268217?auto=format&fit=crop&w=800&q=80"},
                {"nome": "Conjunto Tricot Pastel", "preco": 219.0, "estoque": 14, "imagem_url": "https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?auto=format&fit=crop&w=800&q=80"},
                {"nome": "Top Coquette Laço", "preco": 79.9, "estoque": 31, "imagem_url": "https://images.unsplash.com/photo-1485968579580-b6d095142e6e?auto=format&fit=crop&w=800&q=80"},
                {"nome": "Vestido Midi Cottage", "preco": 169.9, "estoque": 7, "imagem_url": "https://images.unsplash.com/photo-1496747611176-843222e1e57c?auto=format&fit=crop&w=800&q=80"}
            ]
            for p in produtos_iniciais:
                db.add(Produto(**p))
            await db.commit()

        # Seed de banners
        count_banners = await db.scalar(select(sqlalchemy.func.count()).select_from(Banner))
        if count_banners == 0:
            log.info("[DB] Cadastrando banners iniciais de teste...")
            banners_iniciais = [
                {
                    "badge_text": "Drop de primavera ✨",
                    "title_highlight": "Coleção Primavera:",
                    "title_main": "Seja Você Mesma!",
                    "subtitle": "Looks fofos, coquette e cheios de personalidade pra você arrasar em qualquer rolê.",
                    "image_url": "https://images.unsplash.com/photo-1490481651871-ab68de25d43d?auto=format&fit=crop&w=1200&q=80",
                    "button_text": "Ver Looks",
                    "button_link": "#looks",
                    "cor_destaque": "#ec4899",
                    "ativo": True,
                    "ordem": 0
                },
                {
                    "badge_text": "Novidade 🔥",
                    "title_highlight": "Inverno 2026:",
                    "title_main": "Estilo & Conforto",
                    "subtitle": "Peças exclusivas e quentinhas para você arrasar na estação mais charmosa do ano.",
                    "image_url": "https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?auto=format&fit=crop&w=1200&q=80",
                    "button_text": "Comprar Agora",
                    "button_link": "#produtos",
                    "cor_destaque": "#3b82f6",
                    "ativo": True,
                    "ordem": 1
                }
            ]
            for b in banners_iniciais:
                db.add(Banner(**b))
            await db.commit()
        elif count_banners == 1:
            log.info("[DB] Cadastrando segundo banner...")
            b2 = Banner(
                badge_text="Novidade 🔥",
                title_highlight="Inverno 2026:",
                title_main="Estilo & Conforto",
                subtitle="Peças exclusivas e quentinhas para você arrasar na estação mais charmosa do ano.",
                image_url="https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?auto=format&fit=crop&w=1200&q=80",
                button_text="Comprar Agora",
                button_link="#produtos",
                cor_destaque="#3b82f6",
                ativo=True,
                ordem=1
            )
            db.add(b2)
            await db.commit()

        try:
            await db.execute(text("ALTER TABLE configuracoes ADD COLUMN texto_frete VARCHAR DEFAULT 'Frete grátis acima de R$ 199'"))
            await db.commit()
            log.info("[DB] Coluna texto_frete adicionada")
        except:
            await db.rollback()
            
        try:
            await db.execute(text("ALTER TABLE configuracoes ADD COLUMN texto_brinde VARCHAR DEFAULT 'Brinde fofo no pedido'"))
            await db.commit()
            log.info("[DB] Coluna texto_brinde adicionada")
        except:
            await db.rollback()

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
        
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("ALTER TABLE produtos ADD COLUMN categoria_id UUID REFERENCES categorias(id)"))
            await db.commit()
    except Exception:
        pass # A coluna provavelmente já existe

    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("ALTER TABLE pedidos ADD COLUMN cliente_id UUID REFERENCES clientes(id)"))
            await db.commit()
    except Exception:
        pass

    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("ALTER TABLE pedidos ALTER COLUMN usuario_id DROP NOT NULL"))
            await db.commit()
    except Exception:
        pass

    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("ALTER TABLE configuracoes ADD COLUMN IF NOT EXISTS pix_chave VARCHAR, ADD COLUMN IF NOT EXISTS pix_tipo VARCHAR, ADD COLUMN IF NOT EXISTS pix_nome_recebedor VARCHAR, ADD COLUMN IF NOT EXISTS pix_cidade_recebedor VARCHAR"))
            await db.commit()
    except Exception:
        pass

    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS tipo_entrega VARCHAR DEFAULT 'retirada', ADD COLUMN IF NOT EXISTS taxa_entrega FLOAT DEFAULT 0.0, ADD COLUMN IF NOT EXISTS bairro_entrega VARCHAR"))
            await db.commit()
    except Exception:
        pass

    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("ALTER TABLE pedidos ADD COLUMN numero SERIAL UNIQUE"))
            await db.commit()
    except Exception:
        pass

    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("ALTER TABLE produtos ADD COLUMN preco_custo FLOAT DEFAULT 0.0"))
            await db.commit()
    except Exception:
        pass

    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("ALTER TABLE configuracoes ADD COLUMN IF NOT EXISTS whatsapp_loja VARCHAR, ADD COLUMN IF NOT EXISTS link_instagram VARCHAR, ADD COLUMN IF NOT EXISTS link_tiktok VARCHAR"))
            await db.commit()
    except Exception:
        pass

    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("ALTER TABLE configuracoes ADD COLUMN IF NOT EXISTS popup_ativo BOOLEAN DEFAULT FALSE, ADD COLUMN IF NOT EXISTS popup_titulo VARCHAR, ADD COLUMN IF NOT EXISTS popup_texto VARCHAR, ADD COLUMN IF NOT EXISTS popup_imagem VARCHAR, ADD COLUMN IF NOT EXISTS popup_botao_texto VARCHAR, ADD COLUMN IF NOT EXISTS popup_botao_link VARCHAR"))
            await db.commit()
    except Exception:
        pass

    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("ALTER TABLE banners ADD COLUMN IF NOT EXISTS button2_text VARCHAR, ADD COLUMN IF NOT EXISTS button2_link VARCHAR, ADD COLUMN IF NOT EXISTS cor_destaque VARCHAR"))
            await db.commit()
    except Exception:
        pass

    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("ALTER TABLE produtos ADD COLUMN IF NOT EXISTS data_criacao TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP"))
            await db.commit()
    except Exception:
        pass

    await seed_master()

    try:
        async with AsyncSessionLocal() as db:
            from app.models import Banner
            count_banners = await db.scalar(select(sqlalchemy.func.count()).select_from(Banner))
            if count_banners == 0:
                log.info("[DB] Cadastrando banner inicial...")
                banner = Banner(
                    badge_text="Drop de primavera ✨",
                    title_highlight="Coleção Primavera:",
                    title_main="Seja Você Mesma!",
                    subtitle="Looks fofos, coquette e cheios de personalidade pra você arrasar em qualquer rolê. Encontre a peça que combina com a sua vibe. 💕",
                    image_url="https://images.unsplash.com/photo-1490481651871-ab68de25d43d?auto=format&fit=crop&w=1200&q=80",
                    button_text="Ver Looks",
                    button_link="#looks"
                )
                db.add(banner)
                await db.commit()
    except Exception as e:
        log.warning(f"Erro ao criar banner inicial: {e}")

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
app.include_router(clientes.router)
app.include_router(categorias.router)
app.include_router(configuracoes.router)
app.include_router(whatsapp.router)
app.include_router(zonas.router)
app.include_router(banners.router)

@app.get("/health", tags=["Sistema"])
async def health_check():
    return {"status": "ok", "service": "loja-api"}
