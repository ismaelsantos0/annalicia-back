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
    categoria_id: Optional[UUID] = None
    nome: str
    descricao: Optional[str] = None
    preco_custo: float = 0.0
    preco: float
    estoque: int = 0
    imagem_url: Optional[str] = None
    is_active: bool = True

class ProdutoCreate(ProdutoBase):
    pass

class ProdutoUpdate(BaseModel):
    categoria_id: Optional[UUID] = None
    nome: Optional[str] = None
    descricao: Optional[str] = None
    preco_custo: Optional[float] = None
    preco: Optional[float] = None
    estoque: Optional[int] = None
    imagem_url: Optional[str] = None
    is_active: Optional[bool] = None
    destaque: Optional[bool] = None

class ProdutoEstoqueUpdate(BaseModel):
    estoque: int

class ProdutoResponse(ProdutoBase):
    id: UUID
    destaque: bool = False
    data_criacao: Optional[datetime] = None
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

class ClienteInscrever(BaseModel):
    nome: str
    whatsapp: str

class DisparoCreate(BaseModel):
    mensagem: str

class PedidoBase(BaseModel):
    pass

class PedidoCreate(PedidoBase):
    cliente_nome: str
    cliente_whatsapp: str
    cliente_endereco: str
    tipo_entrega: str = "retirada"
    bairro_entrega: Optional[str] = None
    taxa_entrega: float = 0.0
    itens: List[ItemPedidoCreate]

class PedidoStatusUpdate(BaseModel):
    status: str

class PedidoResponse(PedidoBase):
    id: UUID
    numero: Optional[int] = None
    cliente_id: Optional[UUID] = None
    usuario_id: Optional[UUID] = None
    status: str
    data_criacao: datetime
    total: float
    tipo_entrega: str
    taxa_entrega: float
    bairro_entrega: Optional[str] = None
    itens: List[ItemPedidoResponse]
    cliente: Optional[ClienteResponse] = None
    pix_copia_cola: Optional[str] = None
    taxa: Optional[float] = None
    ativo: Optional[bool] = None

    model_config = ConfigDict(from_attributes=True)

class ConfiguracaoBase(BaseModel):
    estoque_critico: int = 1
    estoque_atencao: int = 3
    pix_chave: Optional[str] = None
    pix_tipo: Optional[str] = None
    pix_nome_recebedor: Optional[str] = None
    pix_cidade_recebedor: Optional[str] = None
    whatsapp_loja: Optional[str] = None
    link_instagram: Optional[str] = None
    link_tiktok: Optional[str] = None
    popup_ativo: bool = False
    popup_titulo: Optional[str] = None
    popup_texto: Optional[str] = None
    popup_imagem: Optional[str] = None
    popup_botao_texto: Optional[str] = None
    popup_botao_link: Optional[str] = None
    texto_frete: Optional[str] = None
    texto_brinde: Optional[str] = None

class ConfiguracaoResponse(BaseModel):
    id: int
    estoque_critico: int
    estoque_atencao: int
    pix_chave: Optional[str] = None
    pix_tipo: Optional[str] = None
    pix_nome_recebedor: Optional[str] = None
    pix_cidade_recebedor: Optional[str] = None
    whatsapp_loja: Optional[str] = None
    link_instagram: Optional[str] = None
    link_tiktok: Optional[str] = None
    popup_ativo: bool = False
    popup_titulo: Optional[str] = None
    popup_texto: Optional[str] = None
    popup_imagem: Optional[str] = None
    popup_botao_texto: Optional[str] = None
    popup_botao_link: Optional[str] = None
    texto_frete: Optional[str] = None
    texto_brinde: Optional[str] = None
    titulo_destaques: Optional[str] = None
    categoria_destaque_id: Optional[str] = None
    nome_loja: Optional[str] = "Annalicia Modas"
    logo_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class ConfiguracaoUpdate(BaseModel):
    estoque_critico: Optional[int] = None
    estoque_atencao: Optional[int] = None
    pix_chave: Optional[str] = None
    pix_tipo: Optional[str] = None
    pix_nome_recebedor: Optional[str] = None
    pix_cidade_recebedor: Optional[str] = None
    whatsapp_loja: Optional[str] = None
    link_instagram: Optional[str] = None
    link_tiktok: Optional[str] = None
    popup_ativo: Optional[bool] = None
    popup_titulo: Optional[str] = None
    popup_texto: Optional[str] = None
    popup_imagem: Optional[str] = None
    popup_botao_texto: Optional[str] = None
    popup_botao_link: Optional[str] = None
    texto_frete: Optional[str] = None
    texto_brinde: Optional[str] = None
    titulo_destaques: Optional[str] = None
    categoria_destaque_id: Optional[str] = None
    nome_loja: Optional[str] = None
    logo_url: Optional[str] = None

class ZonaEntregaBase(BaseModel):
    bairro: str
    taxa: float = 0.0
    ativo: bool = True

class ZonaEntregaCreate(ZonaEntregaBase):
    pass

class ZonaEntregaUpdate(BaseModel):
    bairro: Optional[str] = None
    taxa: Optional[float] = None
    ativo: Optional[bool] = None

class ZonaEntregaResponse(ZonaEntregaBase):
    id: UUID
    model_config = ConfigDict(from_attributes=True)

class BannerBase(BaseModel):
    badge_text: Optional[str] = None
    title_highlight: Optional[str] = None
    title_main: Optional[str] = None
    subtitle: Optional[str] = None
    image_url: str
    button_text: str = "Ver Looks"
    button_link: str = "#looks"
    button2_text: Optional[str] = None
    button2_link: Optional[str] = None
    cor_destaque: Optional[str] = None
    ativo: bool = True
    ordem: int = 0

class BannerCreate(BannerBase):
    pass

class BannerUpdate(BaseModel):
    badge_text: Optional[str] = None
    title_highlight: Optional[str] = None
    title_main: Optional[str] = None
    subtitle: Optional[str] = None
    image_url: Optional[str] = None
    button_text: Optional[str] = None
    button_link: Optional[str] = None
    button2_text: Optional[str] = None
    button2_link: Optional[str] = None
    cor_destaque: Optional[str] = None
    ativo: Optional[bool] = None
    ordem: Optional[int] = None

class BannerResponse(BannerBase):
    id: UUID
    model_config = ConfigDict(from_attributes=True)
