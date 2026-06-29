import asyncio
from app.database import AsyncSessionLocal
from sqlalchemy import select
from app.models import Pedido
async def test():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Pedido))
        pedidos = res.scalars().all()
        print(f'Total pedidos: {len(pedidos)}')
        for p in pedidos:
            print(f'Pedido {p.id} cliente {p.cliente_id}')
asyncio.run(test())
