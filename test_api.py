import asyncio
from httpx import AsyncClient

async def test_order():
    async with AsyncClient(base_url="https://annalicia-back-production.up.railway.app") as client:
        # Pega produtos para testar
        res = await client.get("/produtos")
        produtos = res.json()
        
        if not produtos:
            print("Sem produtos")
            return
            
        prod_id = produtos[0]['id']
        print(f"Testando com produto: {prod_id}")
        
        payload = {
            "cliente_nome": "Teste",
            "cliente_whatsapp": "11999999999",
            "cliente_endereco": "Rua Teste, 123",
            "tipo_entrega": "retirada",
            "taxa_entrega": 0.0,
            "itens": [{"produto_id": prod_id, "quantidade": 1}]
        }
        
        print("Criando pedido...")
        res = await client.post("/pedidos", json=payload)
        
        print("Status:", res.status_code)
        try:
            print("Response:", res.json())
        except Exception as e:
            print("Erro parse:", e, res.text)

if __name__ == "__main__":
    asyncio.run(test_order())
