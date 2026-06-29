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

class CategoriaBase(BaseModel):
    nome: str

class CategoriaCreate(CategoriaBase):
    pass

class CategoriaResponse(CategoriaBase):
    id: UUID

    model_config = ConfigDict(from_attributes=True)

class ProdutoBase(BaseModel):
    nome: str
    categoria_id: Optional[UUID] = None
    descricao: Optional[str] = None
    preco: float
    estoque: int = 0
    imagem_url: Optional[str] = None
    is_active: bool = True

class ProdutoCreate(ProdutoBase):
    pass

class ProdutoEstoqueUpdate(BaseModel):
    estoque: int

class ProdutoResponse(ProdutoBase):
    id: UUID
    categoria: Optional[CategoriaResponse] = None

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

class ClienteBase(BaseModel):
    nome: str
    whatsapp: str
    endereco: str

class ClienteResponse(ClienteBase):
    id: UUID
    data_criacao: datetime

    model_config = ConfigDict(from_attributes=True)

class PedidoBase(BaseModel):
    pass

class PedidoCreate(PedidoBase):
    cliente_nome: str
    cliente_whatsapp: str
    cliente_endereco: str
    itens: List[ItemPedidoCreate]

class PedidoResponse(PedidoBase):
    id: UUID
    cliente_id: UUID
    usuario_id: Optional[UUID] = None
    status: str
    data_criacao: datetime
    total: float
    itens: List[ItemPedidoResponse]
    cliente: ClienteResponse

    model_config = ConfigDict(from_attributes=True)

class ConfiguracaoBase(BaseModel):
    estoque_critico: int
    estoque_atencao: int

class ConfiguracaoUpdate(ConfiguracaoBase):
    pass

class ConfiguracaoResponse(ConfiguracaoBase):
    id: int
    model_config = ConfigDict(from_attributes=True)
