from pydantic import BaseModel, ConfigDict
from typing import Optional

class PedidoResponse(BaseModel):
    id: int
    pix_copia_cola: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class PedidoORM:
    def __init__(self, id):
        self.id = id

obj = PedidoORM(1)
obj.pix_copia_cola = "TESTE"

res = PedidoResponse.model_validate(obj)
print("JSON:", res.model_dump_json())
