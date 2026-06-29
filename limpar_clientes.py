import asyncio
from sqlalchemy import text
from app.database import AsyncSessionLocal

async def limpar():
    async with AsyncSessionLocal() as db:
        print("Limpando itens de pedido...")
        await db.execute(text("DELETE FROM itens_pedido;"))
        print("Limpando pedidos...")
        await db.execute(text("DELETE FROM pedidos;"))
        print("Limpando clientes...")
        await db.execute(text("DELETE FROM clientes;"))
        await db.commit()
        print("Tudo limpo com sucesso!")

if __name__ == "__main__":
    asyncio.run(limpar())
