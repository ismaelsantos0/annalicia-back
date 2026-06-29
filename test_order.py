import asyncio
from httpx import AsyncClient

async def run():
    async with AsyncClient(base_url="http://localhost:8080") as client:
        payload = {
            "cliente_nome": "Test",
            "cliente_whatsapp": "11999999999",
            "cliente_endereco": "Rua Test",
            "itens": []
        }
        res = await client.post("/pedidos", json=payload)
        print("Status:", res.status_code)
        print("Body:", res.text)

asyncio.run(run())
