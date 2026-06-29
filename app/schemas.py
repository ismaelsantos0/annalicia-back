from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional, List

class Token(BaseModel):
    access_token: str
    token_type: str

class UsuarioBase(BaseModel):
    username: str

class UsuarioCreate(UsuarioBase):
    password: str

class UsuarioResponse(UsuarioBase):
    id: UUID
    role: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)

class ProdutoBase(BaseModel):
    nome: str
    descricao: Optional[str] = None
    preco: float
    estoque: int = 0
    imagem_url: Optional[str] = None
    is_active: bool = True

class ProdutoCreate(ProdutoBase):
    pass

class ProdutoResponse(ProdutoBase):
    id: UUID

    model_config = ConfigDict(from_attributes=True)

class ItemPedidoBase(BaseModel):
    produto_id: UUID
    quantidade: int

class ItemPedidoCreate(ItemPedidoBase):
    pass

class ItemPedidoResponse(ItemPedidoBase):
    id: UUID
    preco_unitario: float

    model_config = ConfigDict(from_attributes=True)

class PedidoBase(BaseModel):
    pass

class PedidoCreate(PedidoBase):
    itens: List[ItemPedidoCreate]

class PedidoResponse(PedidoBase):
    id: UUID
    usuario_id: UUID
    status: str
    data_criacao: datetime
    total: float
    itens: List[ItemPedidoResponse]

    model_config = ConfigDict(from_attributes=True)
