from sqlalchemy import Column, String, Boolean, Integer, Float, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
import uuid
import datetime

from app.database import Base

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="standard")
    is_active = Column(Boolean, default=True)

    pedidos = relationship("Pedido", back_populates="usuario")

class Cliente(Base):
    __tablename__ = "clientes"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome = Column(String, nullable=False)
    whatsapp = Column(String, unique=True, index=True, nullable=False)
    endereco = Column(String, nullable=False)
    data_criacao = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)

    pedidos = relationship("Pedido", back_populates="cliente")

class Categoria(Base):
    __tablename__ = "categorias"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome = Column(String, unique=True, nullable=False)
    
    produtos = relationship("Produto", back_populates="categoria")

class Produto(Base):
    __tablename__ = "produtos"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    categoria_id = Column(PG_UUID(as_uuid=True), ForeignKey("categorias.id"), nullable=True)
    nome = Column(String, nullable=False)
    descricao = Column(String, nullable=True)
    preco = Column(Float, nullable=False)
    estoque = Column(Integer, default=0)
    imagem_url = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)

    categoria = relationship("Categoria", back_populates="produtos")

class Pedido(Base):
    __tablename__ = "pedidos"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    numero = Column(Integer, unique=True, index=True)
    usuario_id = Column(PG_UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=True)
    cliente_id = Column(PG_UUID(as_uuid=True), ForeignKey("clientes.id"), nullable=True)
    status = Column(String, default="pendente")
    data_criacao = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)
    total = Column(Float, nullable=False)
    tipo_entrega = Column(String, default="retirada")
    bairro_entrega = Column(String, nullable=True)
    taxa_entrega = Column(Float, default=0.0)

    usuario = relationship("Usuario", back_populates="pedidos")
    cliente = relationship("Cliente", back_populates="pedidos")
    itens = relationship("ItemPedido", back_populates="pedido", cascade="all, delete-orphan")

class ItemPedido(Base):
    __tablename__ = "itens_pedido"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pedido_id = Column(PG_UUID(as_uuid=True), ForeignKey("pedidos.id"), nullable=False)
    produto_id = Column(PG_UUID(as_uuid=True), ForeignKey("produtos.id"), nullable=False)
    quantidade = Column(Integer, nullable=False)
    preco_unitario = Column(Float, nullable=False)

    pedido = relationship("Pedido", back_populates="itens")
    produto = relationship("Produto")

class Configuracao(Base):
    __tablename__ = "configuracoes"

    id = Column(Integer, primary_key=True, default=1)
    estoque_critico = Column(Integer, default=1)
    estoque_atencao = Column(Integer, default=3)
    pix_chave = Column(String, nullable=True)
    pix_tipo = Column(String, nullable=True) # cpf, cnpj, email, telefone, aleatoria
    pix_nome_recebedor = Column(String, nullable=True)
    pix_cidade_recebedor = Column(String, nullable=True)
    whatsapp_loja = Column(String, nullable=True)
    link_instagram = Column(String, nullable=True)
    link_tiktok = Column(String, nullable=True)

class ZonaEntrega(Base):
    __tablename__ = "zonas_entrega"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bairro = Column(String, unique=True, nullable=False, index=True)
    taxa = Column(Float, default=0.0)
    ativo = Column(Boolean, default=True)

class Banner(Base):
    __tablename__ = "banners"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    badge_text = Column(String, nullable=True) # Ex: Drop de primavera ✨
    title_highlight = Column(String, nullable=True) # Ex: Coleção Primavera:
    title_main = Column(String, nullable=True) # Ex: Seja Você Mesma!
    subtitle = Column(String, nullable=True) # Ex: Looks fofos, coquette...
    image_url = Column(String, nullable=False)
    button_text = Column(String, default="Ver Looks")
    button_link = Column(String, default="#looks")
    ordem = Column(Integer, default=0)
    ativo = Column(Boolean, default=True)
