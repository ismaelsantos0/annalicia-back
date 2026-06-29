import asyncio
from sqlalchemy import text
from app.database import engine

async def alter_tables():
    async with engine.begin() as conn:
        print("Adicionando coluna whatsapp_loja em configuracoes...")
        try:
            await conn.execute(text("ALTER TABLE configuracoes ADD COLUMN whatsapp_loja VARCHAR;"))
            print("Coluna whatsapp_loja adicionada.")
        except Exception as e:
            print(f"Erro ao adicionar whatsapp_loja: {e}")

        print("Adicionando coluna numero em pedidos...")
        try:
            # SERIAL creates a sequence and sets default
            await conn.execute(text("ALTER TABLE pedidos ADD COLUMN numero SERIAL;"))
            # Then add unique constraint
            await conn.execute(text("ALTER TABLE pedidos ADD CONSTRAINT uq_pedidos_numero UNIQUE (numero);"))
            print("Coluna numero adicionada com sucesso.")
        except Exception as e:
            print(f"Erro ao adicionar numero: {e}")

if __name__ == "__main__":
    asyncio.run(alter_tables())
