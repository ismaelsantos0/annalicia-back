import asyncio
from app.database import AsyncSessionLocal
from app.models import ZonaEntrega
from sqlalchemy import select

bairros_boa_vista = [
    "Aeroporto", "Alvorada", "Araceli Souto Maior", "Asa Branca", "Bela Vista", 
    "Buritis", "Caçari", "Caimbé", "Calungá", "Cambará", "Canarinho", "Caranã", 
    "Cauamé", "Centenário", "Centro", "Cidade Satélite", "Cinturão Verde", 
    "Distrito Industrial", "Doutor Sílvio Botelho", "Doutor Sílvio Leite", 
    "Dr. Airton Rocha", "Jardim Caranã", "Jardim Equatorial", "Jardim Floresta", 
    "Jardim Primavera", "Jardim Tropical", "Jóquei Clube", "Nova Cidade", 
    "Olímpico", "Operário", "Paraviana", "Pricumã", "Raiar do Sol", "São Bento", 
    "Senador Hélio Campos", "Pintolândia", "Santa Tereza", "Nova Canaã", "Tancredo Neves"
]

async def seed():
    async with AsyncSessionLocal() as db:
        for bairro in bairros_boa_vista:
            # Verifica se já existe
            result = await db.execute(select(ZonaEntrega).where(ZonaEntrega.bairro == bairro))
            if not result.scalar_one_or_none():
                print(f"Adicionando {bairro}...")
                db.add(ZonaEntrega(bairro=bairro, taxa=10.00, ativo=True))
        await db.commit()
    print("Concluído!")

if __name__ == "__main__":
    asyncio.run(seed())
